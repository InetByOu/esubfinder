#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, asyncio, time, json, random, signal
from datetime import datetime

# ===== AUTO INSTALL MODULES =====
REQUIRED = ["aiohttp", "rich", "tqdm"]
missing = []

for module in REQUIRED:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)

if missing:
    print(f"[!] Missing modules detected: {', '.join(missing)}")
    print("[+] Installing missing dependencies...\n")
    os.system(f"pip install {' '.join(missing)}")
    print("\n[+] Done! Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

# ===== AFTER INSTALL, SAFE IMPORT =====
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.spinner import Spinner
from tqdm import tqdm

console = Console()
HISTORY_PATH = os.path.expanduser("~/.edoll_history")

os.makedirs(HISTORY_PATH, exist_ok=True)

# ====== UTIL =====
def clear():
    os.system("clear")

def ts():
    return int(time.time())

def save_history(filename, content):
    with open(os.path.join(HISTORY_PATH, filename), "w") as f:
        f.write(json.dumps(content, indent=2))

def list_history():
    return sorted(os.listdir(HISTORY_PATH))

# ====== FETCH SUBDOMAINS =====
async def fetch_subdomains(domain):
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30) as r:
            if r.status != 200:
                return []
            try:
                data = await r.json()
            except:
                return []
    subs = sorted(set(row["name_value"] for row in data))
    return [s for s in subs if "*" not in s]

# ====== CHECK HOST =====
async def check_host(session, host):
    url = f"http://{host}"
    try:
        async with session.get(url, timeout=3) as r:
            return {
                "sub": host,
                "code": r.status,
                "server": r.headers.get("Server", "?"),
                "cloudflare": "cf-cache-status" in (k.lower() for k in r.headers.keys())
            }
    except:
        return {
            "sub": host,
            "code": 0,
            "server": "-",
            "cloudflare": False
        }

# ====== SCANNER WITH PROGRESS BAR =====
async def scan_subdomains(subdomains):
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [check_host(session, s) for s in subdomains]

        pbar = tqdm(
            total=len(tasks),
            desc="Scanning",
            unit="sub",
            ncols=80,
            smoothing=0.3
        )

        for coro in asyncio.as_completed(tasks):
            res = await coro
            results.append(res)
            pbar.update(1)

        pbar.close()
    return results

# ====== SHOW TABLE =====
def print_table(results):
    table = Table(title="Scan Results")

    table.add_column("Subdomain", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Server", style="yellow")
    table.add_column("CF", style="magenta")

    for r in results:
        table.add_row(
            r["sub"],
            str(r["code"]),
            r["server"],
            "YES" if r["cloudflare"] else "NO"
        )
    console.print(table)

# ====== SPINNER WRAPPER =====
async def with_spinner(msg, coro):
    with console.status(
        f"[bold green]{msg}...",
        spinner="point",
        spinner_style="bold green"
    ):
        return await coro

# ====== MAIN MENU =====
async def menu():
    while True:
        clear()
        console.print("[bold cyan]EDOLL - Subdomain Scanner[/]")
        console.print("[white]=================================[/]")
        console.print("1. Scan Domain")
        console.print("2. History Manager")
        console.print("3. Update Tool")
        console.print("4. Exit\n")

        choice = console.input("[yellow]Select option: [/]")
        if choice == "1":
            domain = console.input("\nEnter domain: ").strip()
            clear()
            subs = await with_spinner("Fetching subdomains", fetch_subdomains(domain))

            if not subs:
                console.print("[red]No subdomains found.[/]")
                console.input("\n[Press enter]")
                continue

            console.print(f"[green]Found {len(subs)} subdomains![/]\n")
            time.sleep(0.8)

            results = await scan_subdomains(subs)

            clear()
            print_table(results)

            fname = f"{domain}-{ts()}.json"
            save_history(fname, results)
            console.print(f"\n[green]Saved → {fname}[/]\n")
            console.input("[Press enter]")

        elif choice == "2":
            files = list_history()
            clear()

            if not files:
                console.print("[red]No scan history saved.[/]")
                console.input("\n[Press enter]")
                continue

            console.print("[cyan]SCAN HISTORY:[/]\n")
            for i, f in enumerate(files):
                console.print(f"{i+1}. {f}")

            idx = console.input("\nSelect file (0=back): ")
            if idx == "0":
                continue

            try:
                idx = int(idx) - 1
                fname = files[idx]
            except:
                continue

            clear()
            console.print(f"[cyan]Preview: {fname}\n[/]")

            with open(os.path.join(HISTORY_PATH, fname)) as f:
                data = json.load(f)

            print_table(data)
            console.print("\n1. Delete")
            console.print("0. Back\n")

            act = console.input("Select: ")
            if act == "1":
                os.remove(os.path.join(HISTORY_PATH, fname))
                console.print("[green]Deleted![/]")
                time.sleep(1)

        elif choice == "3":
            clear()
            console.print("[yellow]Updating EDOLL...[/]")
            console.print("Please wait...\n")

            os.system("curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/install.sh -o install.sh")
            os.system("bash install.sh")

            if os.path.exists("install.sh"):
                os.remove("install.sh")
            if os.path.exists("esubfinder"):
                os.system("rm -rf esubfinder")

            clear()
            console.print("[green]Update complete! Relaunching...[/]")
            time.sleep(1)
            os.execv(sys.executable, ['python'] + sys.argv)

        elif choice == "4":
            console.print("[blue]Bye![/]")
            sys.exit()

        else:
            continue

# ===== RUN =====
if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    asyncio.run(menu())
