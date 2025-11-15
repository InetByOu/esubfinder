#!/usr/bin/env python3
# ev03_final.py
# E-V0.3 FINAL — Full feature Subdomain Scanner + Tunnel Analyzer (single file)
# ASCII-only, Python 3.12 compatible

from __future__ import annotations
import os
import sys
import re
import json
import ssl
import socket
import time
import subprocess
import threading
import shutil
import random
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, quote

# -------------------------
# Optional libs
# -------------------------
HAS_REQUESTS = False
try:
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False

HAS_DNSPY = False
try:
    import dns.resolver  # type: ignore
    HAS_DNSPY = True
except Exception:
    HAS_DNSPY = False

# -------------------------
# Paths & Config
# -------------------------
HOME = os.path.expanduser("~")
RESULTS_DIR = os.path.join(HOME, "ev_results")
EXPORTS_DIR = os.path.join(RESULTS_DIR, "exports")
CONFIG_FILE = os.path.join(RESULTS_DIR, "ev_config.json")
HISTORY_FILE = os.path.join(RESULTS_DIR, "history_domains.json")

os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "threads": 20,
    "timeout": 8,
    "max_targets": 300,
    "enable_cloudflare_check": True,
    "enable_auto_follow": True,
    "port_scan_short": [80, 443, 8080, 8443],
    "editor": "nano"
}

config = DEFAULT_CONFIG.copy()
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            config.update(json.load(f))
    except Exception:
        pass

# -------------------------
# Colors (minimalist)
# -------------------------
COLOR = {
    "reset": "\033[0m",
    "title": "\033[95m",
    "info": "\033[96m",
    "success": "\033[92m",
    "warning": "\033[93m",
    "error": "\033[91m",
    "dim": "\033[90m",
}

def color(text: str, kind: str = "info") -> str:
    return COLOR.get(kind, COLOR["info"]) + text + COLOR["reset"]

# -------------------------
# Utils
# -------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def timestamp_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

def safe_resolve(host: str) -> dict:
    try:
        h, aliases, addrs = socket.gethostbyname_ex(host)
        return {"hostname": h, "aliases": aliases, "addresses": addrs}
    except Exception:
        return {"hostname": host, "aliases": [], "addresses": []}

def term_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80

# -------------------------
# Loading animations
# -------------------------
_loading_flag = False

class Loader:
    styles = [
        [".", "..", "...", "...."],
        ["   ", ".  ", ".. ", "...", ".. "],
        ["[=     ]", "[==    ]", "[===   ]", "[====  ]", "[===== ]", "[======]"],
        ["(o    )", "( o   )", "(  o  )", "(   o )", "(    o)"]
    ]

    @staticmethod
    def run(prefix: str = "Processing", style: int = 0, speed: float = 0.14):
        global _loading_flag
        frames = Loader.styles[style % len(Loader.styles)]
        _loading_flag = True
        i = 0
        w = term_width()
        while _loading_flag:
            frame = frames[i % len(frames)]
            sys.stdout.write("\r" + (prefix + " " + frame).ljust(w - 1))
            sys.stdout.flush()
            i += 1
            time.sleep(speed)
        sys.stdout.write("\r" + " " * (w - 1) + "\r")
        sys.stdout.flush()

    @staticmethod
    def start(prefix: str = "Processing", style: int = 0, speed: float = 0.14):
        t = threading.Thread(target=Loader.run, args=(prefix, style, speed))
        t.daemon = True
        t.start()
        return t

    @staticmethod
    def stop():
        global _loading_flag
        _loading_flag = False
        time.sleep(0.05)

# -------------------------
# Progress bar
# -------------------------
def progress_bar(curr: int, total: int, w: int | None = None) -> str:
    if total <= 0:
        return ""
    if w is None:
        w = min(40, max(20, term_width() - 40))
    ratio = float(curr) / float(total)
    filled = int(round(w * ratio))
    empty = w - filled
    bar = "[" + "=" * filled + "." * empty + "]"
    percent = int(ratio * 100)
    return f"{bar} {percent}% {curr}/{total}"

def print_progress(curr: int, total: int, info: str = ""):
    s = progress_bar(curr, total)
    if info:
        s = s + " " + info
    sys.stdout.write("\r" + s.ljust(term_width() - 1))
    sys.stdout.flush()
    if curr >= total:
        sys.stdout.write("\n")

# -------------------------
# Dependencies manager
# -------------------------
REQUIRED = [
    {"name": "python3", "cmd": "python3 --version"},
    {"name": "pip", "cmd": "pip --version"},
    {"name": "requests (python)", "cmd": "python3 -c \"import requests\""}
]
OPTIONAL = [
    {"name": "dnspython", "cmd": "python3 -c \"import dns\""}
]

missing_required = []
missing_optional = []

def check_dependencies() -> tuple[list[str], list[str]]:
    global missing_required, missing_optional
    missing_required = []
    missing_optional = []
    for d in REQUIRED:
        try:
            rc = os.system(d["cmd"] + " > /dev/null 2>&1")
            if rc != 0:
                missing_required.append(d["name"])
        except Exception:
            missing_required.append(d["name"])
    for d in OPTIONAL:
        try:
            rc = os.system(d["cmd"] + " > /dev/null 2>&1")
            if rc != 0:
                missing_optional.append(d["name"])
        except Exception:
            missing_optional.append(d["name"])
    return missing_required, missing_optional

def install_dependencies(auto: bool = False):
    check_dependencies()
    if not missing_required and not missing_optional:
        print(color("All dependencies present.", "success"))
        return
    if not auto:
        print(color("Missing required: " + ", ".join(missing_required), "warning") if missing_required else color("No required missing", "info"))
        print(color("Missing optional: " + ", ".join(missing_optional), "info") if missing_optional else color("No optional missing", "info"))
    # Try install required
    for m in missing_required:
        if "requests" in m:
            os.system("pip install requests")
        elif "pip" in m:
            os.system("pkg install python-pip -y")
        elif "python3" in m:
            os.system("pkg install python -y")
        else:
            os.system("pip install " + m)
    for m in missing_optional:
        os.system("pip install " + m)
    check_dependencies()

# -------------------------
# DNS / CNAME helpers
# -------------------------
def get_cname(name: str) -> list:
    if HAS_DNSPY:
        try:
            import dns.resolver  # type: ignore
            answers = dns.resolver.resolve(name, "CNAME")
            return [str(r.target).rstrip(".") for r in answers]
        except Exception:
            return []
    # fallback nslookup
    try:
        p = subprocess.run(["nslookup", "-type=cname", name], capture_output=True, text=True, timeout=6)
        out = p.stdout + p.stderr
        cnames = []
        for line in out.splitlines():
            if "canonical name" in line.lower() or "cname" in line.lower():
                parts = line.split("=")
                if len(parts) >= 2:
                    cnames.append(parts[-1].strip().rstrip("."))
        return cnames
    except Exception:
        return []

# -------------------------
# SSL info
# -------------------------
def get_ssl_info(host: str, port: int = 443, timeout: int = 6) -> dict:
    info = {"success": False, "cn": None, "is_wildcard": False, "san": [], "error": None}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
                cn = None
                subject = cert.get("subject", ())
                for item in subject:
                    for k, v in item:
                        if k == "commonName":
                            cn = v
                info["cn"] = cn
                info["is_wildcard"] = bool(cn and cn.startswith("*"))
                for typ, val in cert.get("subjectAltName", ()):
                    if typ and val:
                        info["san"].append(val)
                info["success"] = True
    except Exception as e:
        info["error"] = str(e)
    return info

# -------------------------
# HTTP probe (requests if available)
# -------------------------
def http_probe(host: str, timeout: int = None) -> dict:
    timeout = timeout or config.get("timeout", 8)
    result = {"status": None, "server": None, "headers": {}, "redirect": None, "scheme": None}
    if HAS_REQUESTS:
        headers = {"User-Agent": "ev03_final/1.0"}
        for prefix in ("https://", "http://"):
            try:
                r = requests.get(prefix + host, headers=headers, timeout=timeout, allow_redirects=False, verify=False)
                result["status"] = r.status_code
                result["server"] = r.headers.get("Server")
                result["headers"] = dict(r.headers)
                result["scheme"] = prefix.replace("://", "")
                if r.is_redirect or (300 <= r.status_code < 400 and "Location" in r.headers):
                    result["redirect"] = r.headers.get("Location")
                return result
            except Exception:
                continue
        return result
    # socket fallback minimal
    for scheme, port in (("https", 443), ("http", 80)):
        try:
            if scheme == "https":
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with socket.create_connection((host, port), timeout=timeout) as s:
                    with ctx.wrap_socket(s, server_hostname=host) as ss:
                        req = f"GET / HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
                        ss.sendall(req.encode("utf-8"))
                        data = ss.recv(4096).decode("utf-8", errors="ignore")
                        if data:
                            first_line = data.splitlines()[0]
                            if first_line.startswith("HTTP/"):
                                result["status"] = first_line.split()[1] if len(first_line.split()) > 1 else None
                                result["scheme"] = "https"
                                return result
            else:
                with socket.create_connection((host, port), timeout=timeout) as s:
                    req = f"GET / HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n"
                    s.sendall(req.encode("utf-8"))
                    data = s.recv(4096).decode("utf-8", errors="ignore")
                    if data:
                        first_line = data.splitlines()[0]
                        if first_line.startswith("HTTP/"):
                            result["status"] = first_line.split()[1] if len(first_line.split()) > 1 else None
                            result["scheme"] = "http"
                            return result
        except Exception:
            continue
    return result

# -------------------------
# Port check
# -------------------------
def check_port(host: str, port: int, timeout: int = None) -> bool:
    timeout = timeout or config.get("timeout", 8)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

# -------------------------
# Cloudflare detection helper
# -------------------------
def is_cloudflare_ip(ip: str) -> bool:
    if not ip: return False
    return ip.startswith(("104.", "172.64.", "172.65.", "172.66.", "173.245.", "103.", "190.93.", "188.114."))

# -------------------------
# Subdomain fetch (rapidDNS)
# -------------------------
def fetch_subdomains_rapiddns(domain: str) -> list:
    subs = set()
    if not HAS_REQUESTS:
        return []
    url = "https://rapiddns.io/subdomain/" + quote(domain) + "?full=1"
    headers = {"User-Agent": "ev03_final/1.0"}
    t = Loader.start("Querying rapiddns", style=0)
    try:
        r = requests.get(url, headers=headers, timeout=20, verify=False)
        if r.status_code == 200:
            text = r.text
            pattern = re.compile(r'([a-zA-Z0-9][a-zA-Z0-9\-\._]*\.' + re.escape(domain) + r')', re.IGNORECASE)
            for m in pattern.findall(text):
                subs.add(m.strip().lower())
    except Exception:
        pass
    finally:
        Loader.stop()
    return sorted(subs)

def fetch_subdomains(domain: str) -> list:
    subs = set()
    subs.update(fetch_subdomains_rapiddns(domain))
    # add common ones
    for p in ("www", "api", "m", "cdn", "dev", "test", "beta", "mail", "ftp"):
        subs.add(f"{p}.{domain}")
    result = []
    for s in sorted(subs):
        s = s.strip().lower()
        if s.endswith(domain) and len(s) > len(domain) and "*" not in s:
            result.append(s)
    maxn = config.get("max_targets", 300)
    if len(result) > maxn:
        return result[:maxn]
    return result

# -------------------------
# Single subdomain scan
# -------------------------
def scan_subdomain(sub: str) -> dict:
    rec = {
        "subdomain": sub,
        "scanned_at": now_iso(),
        "ip": None,
        "aliases": [],
        "cname": [],
        "ports": {},
        "http": {},
        "tls": {},
        "cloudflare": False
    }
    try:
        r = safe_resolve(sub)
        rec["aliases"] = r.get("aliases", [])
        addrs = r.get("addresses", [])
        if addrs:
            rec["ip"] = addrs[0]
            rec["cloudflare"] = is_cloudflare_ip(rec["ip"]) if config.get("enable_cloudflare_check", True) else False
    except Exception:
        pass

    try:
        cnames = get_cname(sub)
        if cnames:
            rec["cname"] = cnames
    except Exception:
        rec["cname"] = []

    try:
        tls = get_ssl_info(sub, port=443, timeout=config.get("timeout", 8))
        if tls.get("success"):
            rec["tls"] = {"cn": tls.get("cn"), "is_wildcard": tls.get("is_wildcard"), "san": tls.get("san", [])}
        else:
            rec["tls"] = {"error": tls.get("error")}
    except Exception:
        rec["tls"] = {}

    for p in config.get("port_scan_short", [80, 443, 8080, 8443]):
        try:
            rec["ports"][str(p)] = check_port(sub, p, timeout=config.get("timeout", 8))
        except Exception:
            rec["ports"][str(p)] = False

    try:
        rec["http"] = http_probe(sub, timeout=config.get("timeout", 8))
    except Exception:
        rec["http"] = {}

    return rec

# -------------------------
# Tunnel analyzer + scoring
# -------------------------
def analyze_tunnel_info(info: dict) -> dict:
    out = {
        "subdomain": info.get("subdomain"),
        "ip": info.get("ip"),
        "scanned_at": now_iso(),
        "open_ports": [],
        "score": 0,
        "wildcard_v2ray_ready": False,
        "enhanced_ssh_ready": False,
        "notes": []
    }
    for ps, v in info.get("ports", {}).items():
        try:
            p = int(ps)
            if v:
                out["open_ports"].append(p)
        except Exception:
            pass
    score = 0
    tls = info.get("tls", {})
    if isinstance(tls, dict) and tls.get("cn"):
        score += 25
        if tls.get("is_wildcard"):
            score += 20
            out["notes"].append("wildcard cert")
    if 443 in out["open_ports"]:
        score += 30
    if 22 in out["open_ports"]:
        score += 20
    score += min(len(out["open_ports"]) * 5, 20)
    out["score"] = score
    out["wildcard_v2ray_ready"] = bool(tls.get("is_wildcard") and (443 in out["open_ports"]) and score >= 50)
    out["enhanced_ssh_ready"] = bool((22 in out["open_ports"]) and (443 in out["open_ports"]) and score >= 40)
    return out

# -------------------------
# Auto-scan loop
# -------------------------
def run_auto_scan(domain: str) -> list:
    print(color(f"Fetching subdomains for {domain}", "info"))
    subs = fetch_subdomains(domain)
    if not subs:
        print(color("No subdomains found.", "warning"))
        return []

    # save to history
    save_history(domain)

    seen = set()
    queue = []
    results = []
    for s in subs:
        if s not in seen:
            seen.add(s)
            queue.append(s)

    max_targets = config.get("max_targets", 300)
    threads = config.get("threads", 10)
    print(color(f"Starting scan loop — max targets {max_targets}", "info"))

    while queue and len(seen) <= max_targets:
        batch = []
        while queue and len(batch) < threads:
            batch.append(queue.pop(0))
        if not batch:
            break

        t = Loader.start("Scanning batch", style=2)
        with ThreadPoolExecutor(max_workers=min(len(batch), threads)) as ex:
            futures = {ex.submit(scan_subdomain, s): s for s in batch}
            completed = 0
            for fut in as_completed(futures):
                s = futures[fut]
                try:
                    info = fut.result()
                except Exception as e:
                    print(color(f"Scan error {s}: {e}", "error"))
                    info = None
                if info:
                    results.append(info)
                    completed += 1
                    print_progress(completed, len(batch), info=s)
                    # auto-follow
                    if config.get("enable_auto_follow", True):
                        for cn in info.get("cname", []) or []:
                            if cn and cn not in seen and (domain in cn or cn.endswith(domain)):
                                seen.add(cn); queue.append(cn)
                        for san in (info.get("tls", {}).get("san") or []):
                            if san and san not in seen and (domain in san or san.endswith(domain)):
                                seen.add(san); queue.append(san)
                        loc = info.get("http", {}).get("redirect")
                        if loc:
                            try:
                                p = urlparse(loc)
                                if p.hostname and p.hostname not in seen:
                                    seen.add(p.hostname); queue.append(p.hostname)
                            except Exception:
                                pass
                if len(seen) >= max_targets:
                    break
        Loader.stop()
        print(color(f"Progress: scanned {len(results)}, queue {len(queue)}, seen {len(seen)}", "info"))

    print(color(f"Scan loop finished. Total scanned: {len(results)}", "success"))
    return results

# -------------------------
# Run tunnel analysis batch
# -------------------------
def run_tunnel_analysis(scan_results: list) -> list:
    if not scan_results:
        print(color("No scan results", "warning"))
        return []
    print(color("Starting tunnel analysis...", "info"))
    out = []
    t = Loader.start("Analyzing tunnels", style=0)
    with ThreadPoolExecutor(max_workers=min(12, config.get("threads", 10))) as ex:
        futures = {ex.submit(analyze_tunnel_info, item): item for item in scan_results}
        completed = 0
        total = len(futures)
        for fut in as_completed(futures):
            try:
                r = fut.result()
            except Exception:
                r = None
            if r:
                out.append(r)
            completed += 1
            print_progress(completed, total, "tunnel")
    Loader.stop()
    print(color(f"Tunnel analysis complete. {len(out)} results.", "success"))
    return out

# -------------------------
# Save/load result helpers
# -------------------------
def result_paths(domain: str) -> dict:
    ts = timestamp_str()
    folder = os.path.join(RESULTS_DIR, datetime.now(timezone.utc).strftime("%Y-%m"))
    os.makedirs(folder, exist_ok=True)
    base = domain + "_" + ts
    return {
        "subfile": os.path.join(folder, "subscan_" + base + ".json"),
        "tunnelfile": os.path.join(folder, "tunnel_" + base + ".json"),
        "latest_sub": os.path.join(RESULTS_DIR, domain + "_sub_latest.json"),
        "latest_tunnel": os.path.join(RESULTS_DIR, domain + "_tunnel_latest.json")
    }

def save_sub_results(domain: str, results: list):
    paths = result_paths(domain)
    try:
        with open(paths["subfile"], "w") as f:
            json.dump({"meta": {"domain": domain, "generated": now_iso()}, "results": results}, f, indent=2)
        with open(paths["latest_sub"], "w") as f:
            json.dump({"meta": {"domain": domain, "generated": now_iso()}, "results": results}, f, indent=2)
        print(color("Saved subdomain results to " + paths["subfile"], "success"))
    except Exception as e:
        print(color("Failed to save sub results: " + str(e), "error"))

def save_tunnel_results(domain: str, results: list):
    paths = result_paths(domain)
    try:
        with open(paths["tunnelfile"], "w") as f:
            json.dump({"meta": {"domain": domain, "generated": now_iso()}, "results": results}, f, indent=2)
        with open(paths["latest_tunnel"], "w") as f:
            json.dump({"meta": {"domain": domain, "generated": now_iso()}, "results": results}, f, indent=2)
        print(color("Saved tunnel results to " + paths["tunnelfile"], "success"))
    except Exception as e:
        print(color("Failed to save tunnel results: " + str(e), "error"))

# -------------------------
# Preview with colored groups
# -------------------------
def preview_results(domain: str, kind: str = "sub"):
    latest = os.path.join(RESULTS_DIR, domain + ("_sub_latest.json" if kind == "sub" else "_tunnel_latest.json"))
    if not os.path.exists(latest):
        print(color("No latest result found for " + domain, "error"))
        return
    try:
        with open(latest, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(color("Failed to read latest file: " + str(e), "error"))
        return
    entries = data.get("results", [])
    clear_screen()
    print(color("Preview: " + domain + " (" + kind + ")", "title"))
    for i, e in enumerate(entries, start=1):
        sub = e.get("subdomain") or e.get("subdomain", "")
        status = str(e.get("http", {}).get("status", "") or "")
        server = e.get("http", {}).get("server") or ""
        cf = "CF" if e.get("cloudflare") else ""
        time_ms = e.get("http", {}).get("response_time", "")
        # choose color by group
        if status.startswith("200"):
            c = "success"
        elif status.startswith("301") or status.startswith("302"):
            c = "info"
        elif status and status.isdigit():
            c = "warning"
        else:
            c = "error"
        extra = ""
        # tunnel-ready tags
        if kind == "tunnel":
            if e.get("wildcard_v2ray_ready"):
                extra += " [V2R]"
            if e.get("enhanced_ssh_ready"):
                extra += " [SSH]"
        # print line
        print(color(f"{i:03d}. {sub} | {status} | {server} {cf} {extra}", c))
    input("\nPress Enter to continue...")

# -------------------------
# Export active to txt
# -------------------------
def export_active(domain: str):
    latest = os.path.join(RESULTS_DIR, domain + "_sub_latest.json")
    if not os.path.exists(latest):
        print(color("No latest sub scan found", "error"))
        return
    try:
        with open(latest, "r") as f:
            data = json.load(f)
        out = []
        for r in data.get("results", []):
            status = str(r.get("http", {}).get("status", "") or "")
            if status in ("200", "301", "302"):
                out.append(r.get("subdomain", ""))
        if not out:
            print(color("No active subdomains found", "warning"))
            return
        path = os.path.join(EXPORTS_DIR, domain + "_active_" + timestamp_str() + ".txt")
        with open(path, "w") as f:
            for s in out:
                f.write(s + "\n")
        print(color("Exported active to " + path, "success"))
    except Exception as e:
        print(color("Export failed: " + str(e), "error"))

# -------------------------
# Open latest file in editor (for copy/paste)
# -------------------------
def open_latest_in_editor(domain: str, kind: str = "sub"):
    path = os.path.join(RESULTS_DIR, domain + ("_sub_latest.json" if kind == "sub" else "_tunnel_latest.json"))
    if not os.path.exists(path):
        print(color("File not found: " + path, "error"))
        return
    editor = config.get("editor", "nano")
    try:
        subprocess.call([editor, path])
    except Exception as e:
        print(color("Failed to open editor: " + str(e), "error"))

# -------------------------
# History helpers
# -------------------------
def load_history_list() -> list:
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    return []

def save_history(domain: str):
    hist = load_history_list()
    if domain in hist:
        # move to front
        hist.remove(domain)
    hist.insert(0, domain)
    hist = hist[:50]
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(hist, f, indent=2)
    except Exception:
        pass

def show_history_menu():
    hist = load_history_list()
    if not hist:
        print(color("History empty", "info"))
        input("Press Enter...")
        return None
    clear_screen()
    print(color("History Domains", "title"))
    for idx, d in enumerate(hist, 1):
        print(color(f"{idx}. {d}", "info"))
    print(color("00. Delete all", "warning"))
    print(color("0. Back", "dim"))
    choice = input("Select: ").strip()
    if choice == "0":
        return None
    if choice == "00":
        confirm = input("Delete all history? (y/N): ").strip().lower()
        if confirm == "y":
            try:
                os.remove(HISTORY_FILE)
                print(color("History cleared", "success"))
            except Exception:
                print(color("Failed to clear history", "error"))
        input("Press Enter...")
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(hist):
            return hist[idx]
    except Exception:
        pass
    print(color("Invalid selection", "warning"))
    time.sleep(0.8)
    return None

# -------------------------
# Settings menu
# -------------------------
def settings_menu():
    while True:
        clear_screen()
        print(color("Settings", "title"))
        print(f"1) Threads: {config.get('threads')}")
        print(f"2) Timeout: {config.get('timeout')}s")
        print(f"3) Max targets: {config.get('max_targets')}")
        print(f"4) Cloudflare check: {config.get('enable_cloudflare_check')}")
        print(f"5) Auto follow related: {config.get('enable_auto_follow')}")
        print(f"6) Editor: {config.get('editor')}")
        print("9) Save & Back")
        print("0) Back")
        c = input("Choice: ").strip()
        if c == "1":
            try:
                v = int(input("Threads (1-200): ").strip())
                config["threads"] = max(1, min(200, v))
            except Exception:
                print(color("Invalid", "error"))
                time.sleep(0.5)
        elif c == "2":
            try:
                v = int(input("Timeout seconds: ").strip())
                config["timeout"] = max(1, min(120, v))
            except Exception:
                print(color("Invalid", "error"))
                time.sleep(0.5)
        elif c == "3":
            try:
                v = int(input("Max targets: ").strip())
                config["max_targets"] = max(10, min(5000, v))
            except Exception:
                print(color("Invalid", "error"))
                time.sleep(0.5)
        elif c == "4":
            config["enable_cloudflare_check"] = not config.get("enable_cloudflare_check", True)
            print(color("Cloudflare check toggled", "success"))
            time.sleep(0.5)
        elif c == "5":
            config["enable_auto_follow"] = not config.get("enable_auto_follow", True)
            print(color("Auto follow toggled", "success"))
            time.sleep(0.5)
        elif c == "6":
            ed = input("Editor (nano/vi): ").strip()
            if ed:
                config["editor"] = ed
        elif c == "9":
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2)
                print(color("Config saved", "success"))
            except Exception as e:
                print(color("Save failed: " + str(e), "error"))
            time.sleep(0.6)
            break
        elif c == "0":
            break
        else:
            print(color("Invalid", "warning"))
            time.sleep(0.5)

# -------------------------
# Clear screen helper
# -------------------------
def clear_screen():
    os.system("clear" if os.name == "posix" else "cls")

# -------------------------
# Main menu (layout requested)
# -------------------------
def main_menu():
    while True:
        clear_screen()
        print(color("===============================================================", "title"))
        print(color("              E-V0.3 Super - Full Feature Scanner", "title"))
        print(color("===============================================================", "title"))
        req, opt = check_dependencies()
        if req:
            print()
            print(color("[ ! ] WARNING [ ! ]", "warning"))
            for d in req:
                print(color(f"({d}) Not exist.", "warning"))
            print(color("Install in Dependencies Manager", "warning"))
            print()
        print("1) AUTO SCAN")
        print("2) AUTO CEK RESULT (summary)")
        print("3) EXTREME SCAN + CEK")
        print("4) HISTORY")
        print("5) EXPORT TO TXT")
        print("6) TUNNEL USE AVAILABLE")
        print("7) DEPENDENCIES MANAGER")
        print("8) Settings")
        print("0) Exit")
        choice = input("Select: ").strip()
        if choice == "1":
            method = input("Enter domain or type 'h' to pick from history: ").strip()
            if method.lower() == "h":
                domain = show_history_menu()
                if not domain:
                    continue
            else:
                domain = method.strip().lower()
            if not domain:
                print(color("No domain", "warning")); time.sleep(0.6); continue
            subs = run_auto_scan(domain)
            if subs:
                save_sub_results(domain, subs)
            input("Press Enter to continue...")
        elif choice == "2":
            domain = input("Domain to summary check (or 'h'): ").strip().lower()
            if domain == "h":
                domain = show_history_menu()
                if not domain: continue
            latest = os.path.join(RESULTS_DIR, domain + "_sub_latest.json")
            if not os.path.exists(latest):
                print(color("No latest scan found", "error")); time.sleep(0.6); continue
            with open(latest, "r") as f:
                data = json.load(f)
            results = data.get("results", [])
            active = [r for r in results if str(r.get("http", {}).get("status", "") or "") in ("200", "301", "302")]
            print(color(f"Total scanned: {len(results)}", "info"))
            print(color(f"Active: {len(active)}", "success"))
            input("Press Enter...")
        elif choice == "3":
            domain = input("Domain for extreme scan: ").strip().lower()
            if not domain: print(color("No domain", "warning")); time.sleep(0.6); continue
            subs = run_auto_scan(domain)
            if subs:
                save_sub_results(domain, subs)
                tunnels = run_tunnel_analysis(subs)
                save_tunnel_results(domain, tunnels)
            input("Press Enter...")
        elif choice == "4":
            sel = show_history_menu()
            if sel:
                # show quick actions
                while True:
                    clear_screen()
                    print(color(f"History: {sel}", "title"))
                    print("1) Scan subdomains")
                    print("2) Tunnel analysis from latest")
                    print("3) Preview latest")
                    print("4) Open latest in editor")
                    print("5) Delete from history")
                    print("0) Back")
                    act = input("Choice: ").strip()
                    if act == "1":
                        subs = run_auto_scan(sel)
                        if subs: save_sub_results(sel, subs)
                        input("Press Enter...")
                    elif act == "2":
                        latest = os.path.join(RESULTS_DIR, sel + "_sub_latest.json")
                        if not os.path.exists(latest):
                            print(color("No latest scan", "warning")); time.sleep(0.6); continue
                        with open(latest, "r") as f:
                            data = json.load(f)
                        tunnels = run_tunnel_analysis(data.get("results", []))
                        save_tunnel_results(sel, tunnels)
                        input("Press Enter...")
                    elif act == "3":
                        kind = input("Preview (sub/tunnel) [sub]: ").strip().lower() or "sub"
                        preview_results(sel, kind if kind=="tunnel" else "sub")
                    elif act == "4":
                        kind = input("Open (sub/tunnel) [sub]: ").strip().lower() or "sub"
                        open_latest_in_editor(sel, kind if kind=="tunnel" else "sub")
                    elif act == "5":
                        # delete from history
                        hist = load_history_list()
                        if sel in hist:
                            hist.remove(sel)
                            try:
                                with open(HISTORY_FILE, "w") as f:
                                    json.dump(hist, f, indent=2)
                                print(color("Removed from history", "success"))
                            except Exception:
                                print(color("Remove failed", "error"))
                        input("Press Enter...")
                        break
                    elif act == "0":
                        break
                    else:
                        print(color("Invalid", "warning")); time.sleep(0.5)
        elif choice == "5":
            domain = input("Domain to export active list (or 'h'): ").strip().lower()
            if domain == "h":
                domain = show_history_menu()
                if not domain: continue
            export_active(domain)
            input("Press Enter...")
        elif choice == "6":
            domain = input("Domain to check tunnel usage (or 'h'): ").strip().lower()
            if domain == "h":
                domain = show_history_menu()
                if not domain: continue
            latest = os.path.join(RESULTS_DIR, domain + "_sub_latest.json")
            if not os.path.exists(latest):
                print(color("No latest scan, run scan first", "warning")); time.sleep(0.6); continue
            with open(latest, "r") as f:
                data = json.load(f)
            tunnels = run_tunnel_analysis(data.get("results", []))
            comp = [r for r in tunnels if r.get("wildcard_v2ray_ready") or r.get("enhanced_ssh_ready")]
            if not comp:
                print(color("No compatible subdomains", "warning"))
            else:
                print(color("Compatible subdomains", "title"))
                for i,c in enumerate(sorted(comp, key=lambda x: x.get("score",0), reverse=True), start=1):
                    tags = []
                    if c.get("wildcard_v2ray_ready"): tags.append("V2R")
                    if c.get("enhanced_ssh_ready"): tags.append("SSH")
                    print(color(f"{i:02d}. {c.get('subdomain')} | score={c.get('score')} | {' '.join(tags)}", "info"))
            input("Press Enter...")
        elif choice == "7":
            check_dependencies()
            print(color("Required missing: " + ", ".join(missing_required) if missing_required else "None", "warning" if missing_required else "success"))
            print(color("Optional missing: " + ", ".join(missing_optional) if missing_optional else "None", "info"))
            if missing_required or missing_optional:
                if input("Install missing? (y/N): ").strip().lower() == "y":
                    install_dependencies()
            input("Press Enter...")
        elif choice == "8":
            settings_menu()
        elif choice == "0":
            print(color("Exiting...", "info")); time.sleep(0.3); sys.exit(0)
        else:
            print(color("Invalid option", "warning")); time.sleep(0.5)

# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    print(color("Starting E-V0.3 Final", "title"))
    if not HAS_REQUESTS:
        print(color("requests not available: HTTP probes use socket fallback", "warning"))
    else:
        print(color("requests available", "success"))
    if HAS_DNSPY:
        print(color("dnspython available for CNAME lookup", "success"))
    else:
        print(color("dnspython not available: using nslookup fallback", "warning"))
    try:
        main_menu()
    except KeyboardInterrupt:
        print()
        print(color("Interrupted by user. Exiting.", "warning"))
        sys.exit(0)
