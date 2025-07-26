#!/usr/bin/env python3
# E-V0.1 BUG FINDER by.edoll

import requests, socket, threading, os, json, signal, sys, re, time, ssl
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

THREADS = 50
subdomain_file = "subdomains.json"
result_file = "result.json"
stop_flag = False
lock = threading.Lock()

def typewriter(text, delay=0.04):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def banner():
    os.system("clear")
    art = """\033[1;32m
╔═════════════════════════════════════════════════╗
║                                                 ║
║    \033[1;31m██████╗ ██╗   ██╗ ██████╗ ██╗     ██╗\033[1;32m        ║
║    \033[1;31m██╔══██╗╚██╗ ██╔╝██╔═══██╗██║     ██║\033[1;32m        ║
║    \033[1;31m██████╔╝ ╚████╔╝ ██║   ██║██║     ██║\033[1;32m        ║
║    \033[1;31m██╔═══╝   ╚██╔╝  ██║   ██║██║     ██║\033[1;32m        ║
║    \033[1;31m██║        ██║   ╚██████╔╝███████╗███████╗\033[1;32m   ║
║                                                 ║
╚═════════════════════════════════════════════════╝\033[0m
"""
    print(art)
    typewriter("\033[1;37m     ⚡ E-V0.1 BUG FINDER by.edoll ⚡\033[0m", delay=0.04)

def fetch_subdomains(domain):
    try:
        url = f"https://rapiddns.io/subdomain/{quote(domain)}?full=1&down=1"
        html = requests.get(url, headers={"User-Agent": "Mozilla"}, timeout=60).text
        found = list(set(re.findall(r'>([\w\.-]+\.' + re.escape(domain) + r')<', html)))
        with open(subdomain_file, "w") as f:
            json.dump(found, f, indent=2)
        print(f"\n\n\033[1;32m[✓] Ditemukan {len(found)} subdomain.\033[0m")
        return found
    except Exception as e:
        print(f"\n\033[1;31m[!] Gagal mengambil subdomain: {e}\033[0m")
        return []

def is_cloudflare(ip):
    ranges = [
        ("104.16.0.0", "104.31.255.255"),
        ("172.64.0.0", "172.71.255.255"),
        ("131.0.72.0", "131.0.72.255"),
        ("190.93.240.0", "190.93.255.255"),
        ("188.114.96.0", "188.114.111.255"),
    ]
    try:
        ip_addr = list(map(int, ip.split(".")))
        for start, end in ranges:
            start_ip = list(map(int, start.split(".")))
            end_ip = list(map(int, end.split(".")))
            if start_ip <= ip_addr <= end_ip:
                return True
    except: pass
    return False

def scan(sub):
    global stop_flag
    if stop_flag: return None
    result = {
        "subdomain": sub,
        "ip": "-",
        "status": "-",
        "server": "-",
        "cloudflare": False,
        "mode": "-"
    }
    try:
        ip = socket.gethostbyname(sub)
        result["ip"] = ip
        cf = is_cloudflare(ip)
        result["cloudflare"] = cf

        try:
            r = requests.get("http://" + sub, timeout=20)
            result["status"] = f"{r.status_code} {r.reason}"
            result["server"] = r.headers.get("Server", "-")
            if r.status_code == 200:
                result["mode"] = "WS/ENHANCED"
        except:
            try:
                ctx = ssl.create_default_context()
                conn = ctx.wrap_socket(socket.socket(), server_hostname=sub)
                conn.settimeout(15)
                conn.connect((sub, 443))
                conn.send(b"GET / HTTP/1.1\r\nHost: " + sub.encode() + b"\r\n\r\n")
                response = conn.recv(1024).decode(errors="ignore")
                if "200 OK" in response:
                    result["status"] = "200 OK"
                    result["mode"] = "SNI/ENHANCED"
            except: pass

        # Print hasil
        warna = "\033[1;32m[✓]" if "200" in result["status"] else "\033[1;33m[-]"
        mode = f" \033[1;35m[{result['mode']}]\033[0m" if "ENHANCED" in result["mode"] else ""
        cf_tag = "[CF]" if cf else ""
        print(f"{warna} \033[1;36m{sub}\033[0m | {result['status']} | {result['server']} | {ip} {cf_tag}{mode}")
        return result
    except:
        return None

def save_result(results):
    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)

def start_scan(domain):
    global stop_flag
    banner()
    print(f"\033[1;37m[•] Mengambil subdomain untuk: \033[1;36m{domain}\033[0m\nWaiting...\n")
    subs = fetch_subdomains(domain)
    if not subs: return
    print("\033[1;31m[>] Tekan CTRL+C Berkali-kali untuk stop paksa.\033[0m")
    print(f"\n\033[1;33m[!] Memindai subdomain aktif...\n Tunggu sebentar...\033[0m\n")
    results = []
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        tasks = {executor.submit(scan, sub): sub for sub in subs}
        for future in as_completed(tasks):
            if stop_flag: break
            result = future.result()
            if result: results.append(result)
    save_result(results)
    print(f"\n\033[1;32m[✓] Scan selesai. Ditemukan {len(results)} subdomain aktif.\n Pergi ke menu 2.Hasil untuk menampilkan...'\033[0m")

def handle_exit(sig, frame):
    global stop_flag
    stop_flag = True
    print("\n\033[1;31m[!] Dihentikan oleh pengguna. Kembali ke menu...\033[0m\n")

def menu():
    while True:
        banner()
        print("\033[1;34m╔═══════════════ MENU ══════════════╗")
        print("\033[1;34m║ \033[1;33m1. Get SubDomain                  \033[1;34m║")
        print("\033[1;34m║ \033[1;33m2. Hasil                          \033[1;34m║")
        print("\033[1;34m║ \033[1;33m0. Keluar                         \033[1;34m║")
        print("╚═══════════════════════════════════╝")
        try:
            choice = input("\n\033[1;32m[?] Pilih opsi by number: \033[0m")
            if choice == "1":
                domain = input("\033[1;36m[+] Masukkan domain target: \033[0m").strip()
                if domain:
                    start_scan(domain)
                input("\n\033[1;35m[↩] Tekan Enter untuk kembali ke menu...\033[0m")
            elif choice == "2":
                if os.path.exists(result_file):
                    with open(result_file) as f:
                        data = json.load(f)
                        print("\n\033[1;34m═══════════ HASIL SCAN ═══════════\033[0m\n")
                        for r in data:
                            warna = "\033[1;32m[✓]" if "200" in r["status"] else "\033[1;33m[-]"
                            mode = f" \033[1;35m[{r.get('mode', '-') }]\033[0m" if "ENHANCED" in r.get("mode", "") else ""
                            cf_tag = "[CF]" if r.get("cloudflare") else ""
                            print(f"{warna} \033[1;36m{r['subdomain']}\033[0m | {r['status']} | {r['server']} | {r['ip']} {cf_tag}{mode}")
                else:
                    print("\033[1;31m[!] Belum ada hasil. Silakan scan dulu.\033[0m")
                input("\n\033[1;35m[↩] Tekan Enter untuk kembali ke menu...\033[0m")
            elif choice == "0":
                print("\n\033[1;32m[✓] Keluar...\033[0m")
                break
            else:
                print("\033[1;31m[!] Pilihan tidak valid.\033[0m")
        except KeyboardInterrupt:
            print("\n\033[1;31m[!] Operasi dibatalkan.\033[0m")
            continue

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    menu()
