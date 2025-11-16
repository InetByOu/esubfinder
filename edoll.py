#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Edoll E-V3.9 — Full Version (Stabil Edition, Latest)
# Author: Bang Edoll — 2025 (upgraded)

import os, sys, json, time, threading, requests, signal, shutil, re
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib3

# disable insecure https warnings for verify=False usage
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================
# WARNA
# ============================
R="\033[91m"; G="\033[92m"; Y="\033[93m"
B="\033[94m"; C="\033[96m"; W="\033[0m"

# ============================
# DEFAULT SETTINGS
# ============================
TIMEOUT=5
MAX_SUBS=1000
THREADS=50
VERSION="E-V3.9"
REPO_INSTALL_SH="https://raw.githubusercontent.com/InetByOu/esubfinder/main/install.sh"

HOME_DIR=os.path.expanduser("~")
EDOLL_DIR=os.path.join(HOME_DIR,".edoll")
HISTORY_DIR=os.path.join(EDOLL_DIR,"history")
LOG_DIR=os.path.join(EDOLL_DIR,"logs")
os.makedirs(HISTORY_DIR,exist_ok=True)
os.makedirs(LOG_DIR,exist_ok=True)

spinner=["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
stop_event=threading.Event()

# ============================
# CTRL+C HANDLER
# ============================
def handle_exit(sig, frame):
    print(f"\n{Y}[!] Proses dihentikan pengguna.{W}")
    stop_event.set()
signal.signal(signal.SIGINT, handle_exit)

# ============================
# UTILITIES
# ============================
def clear(): os.system("clear")
def safe_input(msg):
    try: return input(msg)
    except: return ""
def timestamp(): return time.strftime("%d%m%y_%H%M")
def clean_filename(name): return "".join(c if c.isalnum() or c in "-_." else "_" for c in name.strip())
def spinning(msg,duration=2):
    for _ in range(duration*10):
        for s in spinner:
            if stop_event.is_set(): return
            print(f"\r{C}{s} {msg}{W}",end="",flush=True)
            time.sleep(0.1)
    print("\r",end="")

# ============================
# DEPENDENCY CHECK
# ============================
def check_dependencies():
    missing=[]
    for d in ["git","curl","python3"]:
        if shutil.which(d) is None: missing.append(d)
    if not missing:
        print(f"{G}✓ Semua dependensi tersedia.{W}")
        return
    print(f"{Y}[!] Menginstall: {', '.join(missing)}{W}")
    os.system("pkg update -y >/dev/null 2>&1")
    for d in missing: os.system(f"pkg install {d} -y >/dev/null 2>&1")

# ============================
# RAPIDDNS SUBDOMAIN SCRAPER (STABIL, RETRY, ADAPTIVE TIMEOUT)
# ============================
def fetch_subdomains(domain):
    print(f"{C}Mengambil subdomain dari RapidDNS...{W}")
    url = f"https://rapiddns.io/subdomain/{domain}?full=1"

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://google.com"
    }

    tries = 0
    html = ""
    timeout = TIMEOUT
    max_retries = 5

    while tries < max_retries:
        if stop_event.is_set():
            print(f"{Y}[!] Dibatalkan pengguna.{W}")
            return []

        try:
            r = requests.get(url, timeout=timeout, headers=headers)
            if r.status_code == 200:
                html = r.text
                break
            else:
                print(f"{Y}[!] RapidDNS respon {r.status_code}, retry... ({tries+1}/{max_retries}){W}")

        except requests.exceptions.Timeout:
            print(f"{Y}[!] Timeout {timeout}s, retry ke-{tries+1}...{W}")

        except Exception as e:
            print(f"{R}[X] Gagal koneksi: {e}{W}")

        tries += 1
        timeout += 2  # adaptive increase
        time.sleep(1)

    if html == "":
        print(f"{R}[X] Gagal mengambil data RapidDNS setelah {tries} percobaan.{W}")
        return []

    # detect anti-bot / cloudflare challenge
    low = html.lower()
    if "checking your browser" in low or "cloudflare" in low or "captcha" in low:
        print(f"{Y}[!] RapidDNS rate-limit / anti-bot terdeteksi. Coba lagi nanti.{W}")
        return []

    found = re.findall(
        r'<td>([a-zA-Z0-9\.\-\_]+\.' + re.escape(domain) + r')</td>',
        html
    )

    if not found:
        print(f"{Y}[!] Tidak ada subdomain ditemukan.{W}")
        return []

    subs = sorted(list(set(found)))[:MAX_SUBS]
    print(f"{G}✓ {len(subs)} subdomain ditemukan.{W}")
    return subs

# ============================
# SCANNER (ENHANCED: HTTP+HTTPS, CF DETECT, TAG)
# ============================
def scan(sub):
    """
    Returns tuple:
    (sub, status_display, server_header, err_flag, cloudflare_bool, tag)
    status_display: prefer tag (SNI/ENHANCED or WS/ENHANCED) else http status else https status or '-'
    """
    if stop_event.is_set(): return (sub,"STOP","-","STOP", False, "")

    http_status = None
    https_status = None
    server = "-"
    cloudflare = False
    tag = ""
    err = False

    # HTTP
    try:
        r = requests.get(f"http://{sub}", timeout=TIMEOUT, headers={"User-Agent":"Mozilla/5.0"})
        http_status = r.status_code
        server = r.headers.get("Server", server) or server
        if "cloudflare" in server.lower() or "cf-ray" in r.headers.get("Server","").lower() or "cloudflare" in " ".join([k.lower() for k in r.headers.keys()]):
            cloudflare = True
        if r.status_code == 200:
            tag = "WS/ENHANCED"
    except requests.exceptions.Timeout:
        http_status = "TIMEOUT"
    except Exception:
        http_status = "ERROR"

    # HTTPS (check SNI)
    try:
        r2 = requests.get(f"https://{sub}", timeout=TIMEOUT, headers={"User-Agent":"Mozilla/5.0"}, verify=False)
        https_status = r2.status_code
        # prefer server header from https if present
        server = r2.headers.get("Server", server) or server
        if r2.status_code == 200:
            tag = "SNI/ENHANCED"
        # cloudflare detection via https headers too
        if "cloudflare" in server.lower() or "cf-ray" in r2.headers.get("Server","").lower():
            cloudflare = True
    except requests.exceptions.Timeout:
        if https_status is None:
            https_status = "TIMEOUT"
    except Exception:
        if https_status is None:
            https_status = "ERROR"

    # decide display status
    status_display = tag or (http_status if http_status not in (None, "ERROR") else (https_status or "-"))
    # normalize
    if status_display is None: status_display = "-"

    # consider general error flag
    if (http_status in ("ERROR","TIMEOUT") and https_status in ("ERROR","TIMEOUT")):
        err = True

    return (sub, status_display, server, err, cloudflare, tag)

def scanner(subs):
    results=[]
    print(f"\n{C}Memindai subdomain...{W}")
    total = len(subs)
    if total == 0:
        return results

    with ThreadPoolExecutor(max_workers=min(THREADS, total or 1)) as executor:
        future_to_sub = {executor.submit(scan, s): s for s in subs}
        count = 0
        for future in as_completed(future_to_sub):
            if stop_event.is_set():
                print(f"{Y}[!] Scan dihentikan oleh pengguna.{W}")
                break
            try:
                sub,status,srv,err,cloudflare,tag = future.result()
            except Exception as e:
                # unexpected
                sub = future_to_sub.get(future, "unknown")
                status = "ERROR"
                srv = "-"
                err = True
                cloudflare = False
                tag = ""
            count += 1
            pct = int((count/total)*20)
            bar = "[" + ("#"*pct) + ("-"*(20-pct)) + "]"
            cf_badge = f"{C}[CF]{W}" if cloudflare else ""
            if status == "STOP":
                break
            if err:
                print(f"{R}[ERROR]{W} {sub} {cf_badge} {bar} {count}/{total}")
            else:
                print(f"{G}[{status}]{W} {sub} {cf_badge} ({srv}) {bar} {count}/{total}")
            # append enhanced result
            results.append({
                "domain": sub,
                "status": status,
                "server": srv,
                "cloudflare": bool(cloudflare),
                "tag": tag
            })

    stop_event.clear()
    return results

# ============================
# HISTORY
# ============================
def save_result(data,domain):
    fname=f"{clean_filename(domain)}_{timestamp()}.json"
    path=os.path.join(HISTORY_DIR,fname)
    try:
        with open(path,"w") as f: json.dump(data,f,indent=2)
        print(f"{G}✓ Hasil disimpan: {path}{W}")
    except Exception as e:
        print(f"{R}[X] Gagal menyimpan history: {e}{W}")

def history_list(): return sorted(os.listdir(HISTORY_DIR))

def history_manager():
    while True:
        clear()
        print(f"{C}=== HISTORY MANAGER ==={W}")
        print("1. History Scan Domain")
        print("2. History Inject Tester")
        print("0. Kembali")
        choice = safe_input("> ").strip()
        if choice=="0": return
        elif choice in ["1","2"]:
            files=history_list()
            if not files:
                print(f"{R}(Kosong){W}"); safe_input("\nEnter untuk kembali..."); continue
            filtered=[]
            for f in files:
                try:
                    data=json.load(open(os.path.join(HISTORY_DIR,f)))
                    # detection is lenient to support different result shapes
                    if choice=="1" and isinstance(data,list) and data and "status" in data[0]: filtered.append(f)
                    elif choice=="2" and isinstance(data,list): filtered.append(f)
                except: continue
            if not filtered:
                print(f"{Y}[!] Tidak ada history sesuai tipe.{W}")
                safe_input("\nEnter untuk kembali..."); continue
            while True:
                clear()
                print(f"{C}=== {'Scan Domain' if choice=='1' else 'Inject Tester'} ==={W}")
                for i,f in enumerate(filtered): print(f"{G}{i+1}.{W} {f}")
                print(f"{Y}0.{W} Kembali | {R}D.{W} Hapus semua")
                c2=safe_input("> ").strip()
                if c2=="0": break
                if c2.lower()=="d":
                    for f in filtered:
                        try: os.remove(os.path.join(HISTORY_DIR,f))
                        except: pass
                    print(f"{Y}✓ Semua history dihapus.{W}"); time.sleep(1); break
                try:
                    idx=int(c2)-1
                    fname=filtered[idx]
                    full=os.path.join(HISTORY_DIR,fname)
                    print(open(full).read())
                    safe_input("\nEnter untuk kembali...")
                except: continue
        else:
            print(f"{R}[!] Pilihan tidak valid.{W}"); time.sleep(1)

# ============================
# INJECT TESTER
# ============================
def inject_test():
    files=history_list()
    if not files:
        print(f"{R}[X] Tidak ada history.{W}")
        safe_input("\nEnter..."); return
    for i,f in enumerate(files): print(f"{G}{i+1}.{W} {f}")
    c=safe_input("> ")
    try: fname=files[int(c)-1]
    except: return
    try:
        data=json.load(open(os.path.join(HISTORY_DIR,fname)))
    except Exception as e:
        print(f"{R}[X] Gagal baca file: {e}{W}"); return
    print(f"{Y}Mode:{W} 1=Satu | 2=Semua"); mode=safe_input("> ")
    if mode=="1":
        for i,d in enumerate(data): print(f"{G}{i+1}.{W} {d.get('domain',d.get('sub',str(d)))}")
        sel=int(safe_input("> "))-1
        test_single(data[sel].get('domain', data[sel].get('sub')))
    elif mode=="2":
        for d in data:
            test_single(d.get('domain', d.get('sub')))

def test_single(domain):
    if stop_event.is_set(): return
    print(f"{C}Testing: {domain}{W}")
    try:
        r=requests.get(f"http://{domain}",timeout=TIMEOUT)
        print(f"{G}OK{W} {r.status_code} ({r.headers.get('Server','Unknown')})")
    except requests.exceptions.Timeout: print(f"{Y}Timeout{W} {domain}")
    except Exception as e: print(f"{R}Gagal{W} {domain} ({e})")

# ============================
# SETTINGS
# ============================
def settings_menu():
    global TIMEOUT, MAX_SUBS, THREADS
    while True:
        clear(); print(f"{C}=== SETTINGS ==={W}")
        print(f"1. Timeout (detik)   : {TIMEOUT}")
        print(f"2. Max Subdomain      : {MAX_SUBS}")
        print(f"3. Threads            : {THREADS}")
        print("4. Kembali")
        c=safe_input("> ").strip()
        if c=="1":
            try: TIMEOUT=int(safe_input("Timeout: "))
            except: print(f"{Y}Input tidak valid.{W}"); time.sleep(1)
        elif c=="2":
            try: MAX_SUBS=int(safe_input("Max Subdomain: "))
            except: print(f"{Y}Input tidak valid.{W}"); time.sleep(1)
        elif c=="3":
            try: THREADS=int(safe_input("Threads: "))
            except: print(f"{Y}Input tidak valid.{W}"); time.sleep(1)
        elif c=="4": return

# ============================
# UPDATE SCRIPT
# ============================
def update_script():
    print(f"{C}Mengecek update via install.sh...{W}")
    try:
        backup=os.path.join(EDOLL_DIR,"edoll.py.bak")
        mainfile=os.path.join(EDOLL_DIR,"edoll.py")
        if os.path.exists(mainfile): shutil.copy2(mainfile,backup)
        os.system(f"curl -sSL {REPO_INSTALL_SH} -o {os.path.join(EDOLL_DIR,'install.sh')}")
        os.system(f"bash {os.path.join(EDOLL_DIR,'install.sh')}")
        print(f"{G}✓ Update selesai!{W}")
    except Exception as e:
        print(f"{R}[X] Gagal update! Restore versi lama... ({e}){W}")
        if os.path.exists(backup): shutil.copy2(backup,mainfile)
    safe_input("\nEnter untuk kembali...")

# ============================
# MAIN MENU
# ============================
def menu():
    clear()
    print(f"{C}EDOLL SUBDOMAIN TOOL • {VERSION}{W}")
    print("----------------------------------------")
    print(f"{G}1{W}. Scan Domain      {G}2{W}. Inject Tester")
    print(f"{G}3{W}. History Manager  {G}4{W}. Settings")
    print(f"{G}5{W}. Update Script    {R}6{W}. Keluar")
    c=safe_input("> ")
    if c=="1":
        check_dependencies()
        dom=input(f"{C}Masukkan domain: {W}")
        subs=fetch_subdomains(dom)
        if subs:
            results=scanner(subs)
            save_result(results,dom)
        safe_input("\nEnter untuk kembali..."); menu()
    elif c=="2":
        inject_test(); safe_input("\nEnter untuk kembali..."); menu()
    elif c=="3":
        history_manager(); menu()
    elif c=="4":
        settings_menu(); menu()
    elif c=="5":
        update_script(); menu()
    elif c=="6":
        print(f"{Y}Keluar...{W}"); sys.exit(0)
    else:
        print(f"{R}[!] Pilihan tidak valid.{W}"); time.sleep(1); menu()

# ============================
# START
# ============================
if __name__=="__main__":
    menu()
