#!/usr/bin/env python3
# edoll.py
# EDOLL — Full Inject-ready Scanner (Fixed)
# Copy & run: edoll

import os
import sys
import time
import json
import socket
import ssl
import threading
import datetime
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Auto-install minimal required libs if missing
REQUIRED = ("requests", "bs4", "rich")
_missing = []
for _pkg in REQUIRED:
    try:
        __import__(_pkg)
    except ImportError:
        _missing.append(_pkg)

if _missing:
    print("Installing missing packages:", ", ".join(_missing))
    os.system(f"{sys.executable} -m pip install " + " ".join(_missing))

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# -------------------------
# Settings (editable in menu)
# -------------------------
SETTINGS = {
    "timeout": 5,
    "max_subscan": 300,
    "threads": 30
}

HISTORY_DIR = "history"
os.makedirs(HISTORY_DIR, exist_ok=True)

SPIN_FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

# -------------------------
# Logging helpers (safe names)
# -------------------------
def log_ok(msg):
    console.print(f"[green]✔[/green] {msg}")

def log_info(msg):
    console.print(f"[cyan][i][/cyan] {msg}")

def log_warn(msg):
    console.print(f"[yellow]![/yellow] {msg}")

def log_error(msg):
    console.print(f"[red]✘[/red] {msg}")

# -------------------------
# Small utilities
# -------------------------
def safe_input(prompt="> "):
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print()
        return ""

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def timestamp_for_file():
    return datetime.datetime.now().strftime("%d%m%y_%H%M")

def clean_filename(s: str) -> str:
    s = s.strip()
    s = re.sub(r"<.*?>", "", s)
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    s = s.replace(" ", "_")
    return s

def anim_once(text, dur=0.6):
    start = time.time()
    i = 0
    while time.time() - start < dur:
        console.print(f"[cyan]{SPIN_FRAMES[i % len(SPIN_FRAMES)]}[/cyan] {text}", end="\r")
        time.sleep(0.08)
        i += 1
    print(" " * 120, end="\r")

# -------------------------
# Provider/ASN lookup
# -------------------------
def provider_lookup(ip: str) -> dict:
    if not ip or ip in ("-", None):
        return {"org": None, "country": None}
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=SETTINGS["timeout"])
        j = r.json()
        return {"org": j.get("org"), "country": j.get("country")}
    except Exception:
        return {"org": None, "country": None}

# -------------------------
# HTTP/HTTPS checks
# -------------------------
def http_check(host: str, use_ssl: bool=False) -> dict:
    proto = "https" if use_ssl else "http"
    url = f"{proto}://{host}"
    try:
        r = requests.get(url, timeout=SETTINGS["timeout"], allow_redirects=True, verify=False)
        hdrs = {k.lower(): v for k, v in r.headers.items()}
        title = None
        if "<title" in r.text.lower():
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                t = soup.title
                title = t.string.strip() if t and t.string else None
            except Exception:
                title = None
        return {
            "alive": True,
            "status": r.status_code,
            "server": hdrs.get("server"),
            "via": hdrs.get("via"),
            "powered": hdrs.get("x-powered-by"),
            "cloudflare": ("cloudflare" in str(hdrs) or "cf-ray" in hdrs),
            "title": title
        }
    except Exception:
        return {"alive": False, "status": None, "server": None, "via": None, "powered": None, "cloudflare": False, "title": None}

# -------------------------
# Socket / TLS checks
# -------------------------
def check_port(host: str, port: int) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=SETTINGS["timeout"])
        s.close()
        return True
    except Exception:
        return False

def tls_sni_test(host: str) -> dict:
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(SETTINGS["timeout"])
            s.connect((host, 443))
            cert = s.getpeercert()
            cn = None
            sans = []
            try:
                for t in cert.get("subject", []):
                    for k, v in t:
                        if k == "commonName":
                            cn = v
                for name_type, name in cert.get("subjectAltName", []):
                    if name_type.lower() == "dns":
                        sans.append(name)
            except Exception:
                pass
            return {"ok": True, "cn": cn, "sans": sans}
    except Exception:
        return {"ok": False, "cn": None, "sans": []}

# -------------------------
# Subdomain fetchers
# -------------------------
def fetch_rapiddns(domain):
    try:
        url = f"https://rapiddns.io/subdomain/{domain}?full=1"
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        subs = []
        table = soup.find("table")
        if table:
            for row in table.find_all("tr")[1:]:
                cols = row.find_all("td")
                if cols:
                    s = cols[0].get_text(strip=True)
                    if s:
                        subs.append(s)
        return subs
    except Exception:
        return []

def fetch_crtsh(domain):
    try:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        r = requests.get(url, timeout=12)
        j = r.json()
        subs = set()
        for it in j:
            nv = it.get("name_value") or ""
            for line in nv.splitlines():
                line = line.strip()
                if line and domain in line:
                    subs.add(line.lower())
        return list(subs)
    except Exception:
        return []

def fetch_riddler(domain):
    try:
        url = f"https://riddler.io/search/exportcsv?q=pld:{domain}"
        r = requests.get(url, timeout=10)
        subs = set()
        for ln in r.text.splitlines():
            parts = ln.split(",")
            if len(parts) >= 1:
                candidate = parts[0].strip().strip('"')
                if domain in candidate:
                    subs.add(candidate)
        return list(subs)
    except Exception:
        return []

def fetch_sonar(domain):
    try:
        url = f"https://sonar.omnisint.io/subdomains/{domain}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            j = r.json()
            return [x for x in j if domain in x]
        return []
    except Exception:
        return []

def fetch_bufferover(domain):
    try:
        url = f"https://dns.bufferover.run/dns?q=.{domain}"
        r = requests.get(url, timeout=10).json()
        subs = set()
        for k in ("FDNS_A", "RDNS"):
            for e in r.get(k, []):
                if isinstance(e, str) and domain in e:
                    parts = e.split(",")
                    if len(parts) > 1:
                        subs.add(parts[1].strip())
        return list(subs)
    except Exception:
        return []

def fetch_hackertarget(domain):
    try:
        url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
        r = requests.get(url, timeout=8)
        subs = []
        for ln in r.text.splitlines():
            if domain in ln:
                subs.append(ln.split(",")[0].strip())
        return subs
    except Exception:
        return []

def fetch_threatcrowd(domain):
    try:
        url = f"https://www.threatcrowd.org/searchApi/v2/domain/report/?domain={domain}"
        r = requests.get(url, timeout=8).json()
        return r.get("subdomains", []) or []
    except Exception:
        return []

def fetch_anubis(domain):
    try:
        url = f"https://jldc.me/anubis/subdomains/{domain}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.json()
        return []
    except Exception:
        return []

def fetch_webarchive(domain):
    try:
        url = f"http://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&collapse=urlkey"
        r = requests.get(url, timeout=10).json()
        subs = set()
        for row in r[1:]:
            host = row[2]
            host = host.replace("http://", "").replace("https://", "").split("/")[0]
            if domain in host:
                subs.add(host)
        return list(subs)
    except Exception:
        return []

def fetch_threatminer(domain):
    try:
        url = f"https://api.threatminer.org/v2/domain.php?q={domain}&rt=5"
        r = requests.get(url, timeout=8).json()
        return r.get("results", []) or []
    except Exception:
        return []

def fetch_dnsdumpster(domain):
    try:
        url = f"https://dnsdumpster.com/static/map/{domain}.json"
        r = requests.get(url, timeout=8)
        j = r.json()
        hosts = []
        for h in j.get("dns_records", {}).get("host", []):
            domainname = h.get("domain")
            if domainname:
                hosts.append(domainname)
        return hosts
    except Exception:
        return []

def fetch_google_ct(domain):
    try:
        url = f"https://transparencyreport.google.com/transparencyreport/api/v3/httpsreport/ct/v1/domain/{domain}"
        r = requests.get(url, timeout=10)
        txt = r.text
        if txt.startswith(")]}'"):
            txt = txt[4:]
        j = json.loads(txt)
        subs = set()
        for cert in j.get("report", {}).get("certificates", []):
            for dn in cert.get("dnsNames", []):
                if domain in dn:
                    subs.add(dn)
        return list(subs)
    except Exception:
        return []

SUB_FETCHERS = [
    fetch_rapiddns, fetch_crtsh, fetch_riddler, fetch_sonar,
    fetch_bufferover, fetch_hackertarget, fetch_threatcrowd,
    fetch_anubis, fetch_webarchive, fetch_threatminer,
    fetch_dnsdumpster, fetch_google_ct
]

# -------------------------
# Aggregator
# -------------------------
def collect_subdomains(domain: str):
    domain = domain.strip().lower()
    log_info(f"Collecting subdomains for {domain} from {len(SUB_FETCHERS)} sources...")
    allsubs = set()
    for src in SUB_FETCHERS:
        name = src.__name__.replace("fetch_", "").upper()
        anim_once(f"Query {name}...", dur=0.6)
        try:
            subs = src(domain) or []
            for s in subs:
                if isinstance(s, str) and domain in s:
                    allsubs.add(clean_filename(s.lower()))
        except Exception:
            pass
    subs_list = sorted(allsubs)
    log_info(f"Found {len(subs_list)} unique subdomains (capped to {SETTINGS['max_subscan']})")
    return subs_list[:SETTINGS["max_subscan"]]

# -------------------------
# Vertical display
# -------------------------
def display_vertical(results: list):
    sep = "-" * 60
    for r in results:
        console.print(f"\n[bold cyan]{r.get('host')}[/bold cyan]")
        console.print(f"  IP        : {r.get('ip', '-')}")
        prov = r.get('provider') or {}
        console.print(f"  Provider  : {prov.get('org') or '-'}")
        console.print(f"  Country   : {prov.get('country') or '-'}")
        console.print(f"  Port80    : {r.get('port80')}")
        console.print(f"  Port443   : {r.get('port443')}")
        http = r.get('http') or {}
        https = r.get('https') or {}
        console.print(f"  HTTP      : {http.get('status') or '-'}  | server: {http.get('server') or '-'} | CF: {http.get('cloudflare')}")
        console.print(f"  HTTPS     : {https.get('status') or '-'}  | server: {https.get('server') or '-'} | CF: {https.get('cloudflare')}")
        tls = r.get('tls') or {}
        if tls.get('ok'):
            cn = tls.get('cn') or "-"
            sans = ", ".join(tls.get('sans') or []) or "-"
            console.print(f"  TLS CN    : {cn}")
            console.print(f"  TLS SANs  : {sans}")
        console.print(sep)

# -------------------------
# Host scanner worker
# -------------------------
def scan_host(host: str) -> dict:
    host = host.strip()
    result = {"host": host, "ip": "-", "provider": None, "port80": "CLOSED", "port443": "CLOSED", "http": {}, "https": {}, "tls": {}}
    try:
        ip = socket.gethostbyname(host)
        result["ip"] = ip
    except Exception:
        result["ip"] = "-"
    # ports
    try:
        result["port80"] = "OPEN" if check_port(host, 80) else "CLOSED"
        result["port443"] = "OPEN" if check_port(host, 443) else "CLOSED"
    except Exception:
        pass
    # http/https checks
    try:
        result["http"] = http_check(host, use_ssl=False)
    except Exception:
        result["http"] = {}
    try:
        result["https"] = http_check(host, use_ssl=True)
    except Exception:
        result["https"] = {}
    # tls sni
    try:
        result["tls"] = tls_sni_test(host)
    except Exception:
        result["tls"] = {"ok": False, "cn": None, "sans": []}
    # provider/asn
    try:
        result["provider"] = provider_lookup(result["ip"]) if result["ip"] != "-" else {"org": None, "country": None}
    except Exception:
        result["provider"] = {"org": None, "country": None}
    return result

# -------------------------
# Save history
# -------------------------
def save_scan_history(domain: str, results: list):
    fname = f"{clean_filename(domain)}_{timestamp_for_file()}.json"
    path = os.path.join(HISTORY_DIR, fname)
    try:
        payload = {
            "domain": domain,
            "timestamp": datetime.datetime.now().isoformat(),
            "settings": SETTINGS,
            "count": len(results),
            "data": results
        }
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
        log_ok(f"Saved results to {path}")
        return path
    except Exception as e:
        log_error(f"Failed saving history: {e}")
        return None

# -------------------------
# Scan flow
# -------------------------
def perform_scan(domain: str):
    domain = domain.strip().lower()
    anim_once(f"Collecting subdomains for {domain}...", dur=0.8)
    subs = collect_subdomains(domain)
    if not subs:
        log_warn("No subdomains found.")
        return
    log_info(f"Scanning {len(subs)} subdomains with {SETTINGS['threads']} threads...")
    results = []
    with ThreadPoolExecutor(max_workers=SETTINGS["threads"]) as ex:
        futures = {ex.submit(scan_host, h): h for h in subs}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                results.append(r)
                console.print(f"[green]Scanned[/green] {r['host']}  [blue]{r['ip']}[/blue]")
            except Exception:
                pass
    results = sorted(results, key=lambda x: x.get("host", ""))
    save_scan_history(domain, results)
    display_vertical(results)

# -------------------------
# History manager
# -------------------------
def list_history_files():
    return sorted([f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")])

def view_file(path):
    try:
        j = json.load(open(path))
        console.print_json(data=j)
    except Exception as e:
        log_error(f"Failed to view file: {e}")

def export_all_history():
    files = list_history_files()
    out = []
    for f in files:
        try:
            j = json.load(open(os.path.join(HISTORY_DIR, f)))
            out.append(j)
        except:
            pass
    if not out:
        log_warn("No history to export")
        return
    with open("ALL_HISTORY.json", "w") as o:
        json.dump(out, o, indent=2)
    log_ok("Exported ALL_HISTORY.json")

def merge_history():
    files = list_history_files()
    merged = {}
    for f in files:
        try:
            j = json.load(open(os.path.join(HISTORY_DIR, f)))
            domain = j.get("domain", "unknown")
            merged.setdefault(domain, []).append(j)
        except:
            pass
    with open("MERGED_HISTORY.json", "w") as o:
        json.dump(merged, o, indent=2)
    log_ok("Merged into MERGED_HISTORY.json")

def history_menu():
    while True:
        clear_screen()
        console.print("[bold cyan]History Manager[/bold cyan]")
        files = list_history_files()
        if not files:
            console.print("[yellow]No history files yet.[/yellow]")
            safe_input("Press ENTER to return...")
            return
        table = Table(show_lines=False, box=box.SIMPLE)
        table.add_column("No", width=4)
        table.add_column("File", overflow="fold")
        table.add_column("Count", width=6)
        for i, f in enumerate(files, start=1):
            count = "-"
            try:
                j = json.load(open(os.path.join(HISTORY_DIR, f)))
                count = str(j.get("count", "-"))
            except:
                count = "-"
            table.add_row(str(i), f, count)
        console.print(table)
        console.print("Options: v <no> = view, e = export ALL, m = merge, d <all|no|days> = delete, b = back")
        cmd = safe_input("> ").strip().lower()
        if not cmd:
            continue
        if cmd == "b":
            return
        if cmd.startswith("v"):
            parts = cmd.split()
            if len(parts) >= 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                if 0 <= idx < len(files):
                    view_file(os.path.join(HISTORY_DIR, files[idx]))
                else:
                    log_warn("Index out of range")
            else:
                log_warn("Usage: v <number>")
            safe_input("Enter to continue...")
        elif cmd == "e":
            export_all_history(); safe_input("Enter to continue...")
        elif cmd == "m":
            merge_history(); safe_input("Enter to continue...")
        elif cmd.startswith("d"):
            parts = cmd.split()
            if len(parts) >= 2:
                arg = parts[1]
                if arg == "all":
                    for f in files:
                        os.remove(os.path.join(HISTORY_DIR, f))
                    log_ok("All history removed.")
                elif arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(files):
                        os.remove(os.path.join(HISTORY_DIR, files[idx])); log_ok("Deleted.")
                    else:
                        log_warn("Index out of range.")
                else:
                    try:
                        days = int(arg)
                        cutoff = time.time() - days * 86400
                        removed = 0
                        for f in files:
                            p = os.path.join(HISTORY_DIR, f)
                            if os.path.getmtime(p) < cutoff:
                                os.remove(p); removed += 1
                        log_ok(f"Removed {removed} files older than {days} days.")
                    except Exception:
                        log_warn("Unknown delete argument.")
            else:
                log_warn("Usage: d <all|number|days>")
            safe_input("Enter to continue...")
        else:
            log_warn("Unknown command")
            safe_input("Enter to continue...")

# -------------------------
# Inject tester menu
# -------------------------
def inject_tester_menu():
    files = list_history_files()
    chosen_hosts = []
    if files:
        console.print("[cyan]Choose history file to pick hosts (or press Enter to input manual)[/cyan]")
        for i,f in enumerate(files, start=1):
            console.print(f"{i}. {f}")
        sel = safe_input("Select file number (or Enter to skip): ").strip()
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(files):
                j = json.load(open(os.path.join(HISTORY_DIR, files[idx])))
                hosts = [d.get("host") for d in j.get("data", []) if d.get("host")]
                console.print("[cyan]Choose hosts by number separated by comma, or press Enter to take all[/cyan]")
                for i,h in enumerate(hosts, start=1):
                    console.print(f"{i}. {h}")
                choose = safe_input("Pick (e.g. 1,3) or Enter: ").strip()
                if choose:
                    for token in choose.split(","):
                        try:
                            hidx = int(token.strip()) - 1
                            if 0 <= hidx < len(hosts):
                                chosen_hosts.append(hosts[hidx])
                        except:
                            pass
                else:
                    chosen_hosts = hosts
    console.print("[cyan]Now you can input additional hosts (one per line). Type DONE when finished.[/cyan]")
    while True:
        line = safe_input("> ").strip()
        if not line:
            continue
        if line.lower() in ("done", "d", "stop"):
            break
        chosen_hosts.append(line.strip())
    if not chosen_hosts:
        log_warn("No hosts selected")
        return
    for host in chosen_hosts:
        console.print(f"\n[bold]{host}[/bold]")
        ok80 = check_port(host, 80)
        ok443 = check_port(host, 443)
        console.print(f"  Port 80: {ok80}")
        console.print(f"  Port 443: {ok443}")
        # try real connect 443
        try:
            s = socket.socket()
            s.settimeout(SETTINGS["timeout"])
            t0 = time.time()
            s.connect((host, 443))
            dur = (time.time() - t0) * 1000
            s.close()
            log_ok(f"  TLS handshake OK — {int(dur)} ms")
        except Exception:
            log_warn("  TLS handshake failed or blocked")

# -------------------------
# Settings menu
# -------------------------
def settings_menu():
    while True:
        clear_screen()
        console.print("[bold cyan]Settings[/bold cyan]")
        console.print(f"1. Timeout (seconds): {SETTINGS['timeout']}")
        console.print(f"2. Max subdomains returned: {SETTINGS['max_subscan']}")
        console.print(f"3. Threads: {SETTINGS['threads']}")
        console.print("4. Back")
        ch = safe_input("> ").strip()
        if ch == "1":
            val = safe_input("New timeout (seconds): ").strip()
            try:
                SETTINGS['timeout'] = int(val); log_ok("Timeout updated")
            except:
                log_warn("Invalid")
        elif ch == "2":
            val = safe_input("Max subdomains (int): ").strip()
            try:
                SETTINGS['max_subscan'] = int(val); log_ok("Max subscan updated")
            except:
                log_warn("Invalid")
        elif ch == "3":
            val = safe_input("Threads (int): ").strip()
            try:
                SETTINGS['threads'] = int(val); log_ok("Threads updated")
            except:
                log_warn("Invalid")
        elif ch == "4":
            return
        else:
            log_warn("Unknown choice")

# -------------------------
# Main menu
# -------------------------
def main_menu():
    while True:
        clear_screen()
        console.print("[bold cyan]EDOLL — Full Inject-ready Scanner (fixed)[/bold cyan]")
        console.print("1) Scan domain (multi-source + full analysis)")
        console.print("2) Inject tester (choose from history / manual)")
        console.print("3) History Manager (view/export/merge/delete)")
        console.print("4) Settings")
        console.print("0) Exit")
        ch = safe_input("> ").strip()
        if ch == "1":
            dom = safe_input("Enter target domain (e.g. example.com): ").strip()
            if dom:
                perform_scan(dom)
                safe_input("Press ENTER to continue...")
        elif ch == "2":
            inject_tester_menu()
            safe_input("Press ENTER to continue...")
        elif ch == "3":
            history_menu()
        elif ch == "4":
            settings_menu()
        elif ch == "0":
            console.print("Bye.")
            break
        else:
            log_warn("Invalid selection")
            time.sleep(0.6)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\nInterrupted. Exiting.")
