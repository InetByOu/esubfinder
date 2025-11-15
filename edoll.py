#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Edoll E-V3.9 — Full Version
# Author: Bang Edoll — 2025

import os, sys, json, time, threading, requests, signal, shutil, re
from concurrent.futures import ThreadPoolExecutor

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
# RAPIDDNS SUBDOMAIN SCRAPER
# ============================
def fetch_subdomains(domain):
    print(f"{C}Mengambil subdomain dari RapidDNS...{W}")
    url=f"https://rapiddns.io/subdomain/{domain}?full=1"
    try:
        r=requests.get(url,timeout=TIMEOUT,headers={"User-Agent":"Mozilla/5.0"})
    except requests.exceptions.Timeout:
        print(f"{R}[X] Timeout mengambil data.{W}"); return []
    except:
        print(f"{R}[X] Gagal terhubung ke RapidDNS.{W}"); return []
    if r.status_code!=200:
        print(f"{R}[X] RapidDNS menolak permintaan (status {r.status_code}).{W}"); return []
    found=re.findall(r'<td>([a-zA-Z0-9\.-]+\.'+re.escape(domain)+r')</td>',r.text)
    if not found:
        print(f"{Y}[!] Tidak ditemukan subdomain.{W}"); return []
    subs=sorted(list(set(found)))[:MAX_SUBS]
    print(f"{G}✓ {len(subs)} subdomain ditemukan.{W}")
    return subs

# ============================
# SCANNER
# ============================
def scan(sub):
    if stop_event.is_set(): return (sub,"STOP","-","STOP")
    url=f"http://{sub}"
    try:
        r=requests.get(url,timeout=TIMEOUT)
        return (sub,r.status_code,r.headers.get("Server","Unknown"),False)
    except requests.exceptions.Timeout: return (sub,"TIMEOUT","-",True)
    except: return (sub,"ERROR","-",True)

def scanner(subs):
    results=[]
    print(f"\n{C}Memindai subdomain...{W}")
    with ThreadPoolExecutor(max_workers=THREADS) as exec:
        future={exec.submit(scan,s):s for s in subs}
        total=len(subs); count=0
        for f in future:
            if stop_event.is_set():
                print(f"{Y}[!] Scan dihentikan oleh pengguna.{W}"); break
            sub,status,srv,err=f.result()
            count+=1
            pct=int((count/total)*20)
            bar="["+("#"*pct)+"-"*(20-pct)+"]"
            if status=="STOP": break
            if err: print(f"{R}[ERROR]{W} {sub} {bar} {count}/{total}")
            else: print(f"{G}[{status}]{W} {sub} ({srv}) {bar} {count}/{total}")
            results.append({"domain":sub,"status":status,"server":srv})
    stop_event.clear()
    return results

# ============================
# HISTORY
# ============================
def save_result(data,domain):
    fname=f"{clean_filename(domain)}_{timestamp()}.json"
    path=os.path.join(HISTORY_DIR,fname)
    with open(path,"w") as f: json.dump(data,f,indent=2)
    print(f"{G}✓ Hasil disimpan: {path}{W}")

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
                    if choice=="1" and isinstance(data,list) and "status" in data[0]: filtered.append(f)
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
                    for f in filtered: os.remove(os.path.join(HISTORY_DIR,f))
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
    data=json.load(open(os.path.join(HISTORY_DIR,fname)))
    print(f"{Y}Mode:{W} 1=Satu | 2=Semua"); mode=safe_input("> ")
    if mode=="1":
        for i,d in enumerate(data): print(f"{G}{i+1}.{W} {d['domain']}")
        sel=int(safe_input("> "))-1; test_single(data[sel]['domain'])
    elif mode=="2":
        for d in data: test_single(d['domain'])

def test_single(domain):
    if stop_event.is_set(): return
    print(f"{C}Testing: {domain}{W}")
    try:
        r=requests.get(f"http://{domain}",timeout=TIMEOUT)
        print(f"{G}OK{W} {r.status_code} ({r.headers.get('Server','Unknown')})")
    except requests.exceptions.Timeout: print(f"{Y}Timeout{W} {domain}")
    except: print(f"{R}Gagal{W} {domain}")

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
        if c=="1": TIMEOUT=int(safe_input("Timeout: "))
        elif c=="2": MAX_SUBS=int(safe_input("Max Subdomain: "))
        elif c=="3": THREADS=int(safe_input("Threads: "))
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
    except:
        print(f"{R}[X] Gagal update! Restore versi lama...{W}")
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
