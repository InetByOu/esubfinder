#!/data/data/com.termux/files/usr/bin/bash
# Edoll Installer / Updater for Termux
set -e

INSTALL_DIR="$PREFIX/share/.edoll"
LAUNCHER="$PREFIX/bin/edoll"
PYTHON_BIN="python3"

# Cleanup old files if exist
if [ -f "$INSTALL_DIR/edoll.py" ]; then
    echo "🧹 Menghapus versi lama..."
    rm -rf "$INSTALL_DIR"
fi

mkdir -p "$INSTALL_DIR"

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\\'
    while kill -0 $pid 2>/dev/null; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

echo "📦 Instalasi / Update Edoll dimulai..."

# Cek Python
echo -n "🔧 Mengecek Python... "
if ! command -v python3 >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        pkg install -y python >/dev/null 2>&1
        PYTHON_BIN="python"
    fi
fi
echo "✅ ($PYTHON_BIN)"

# Cek koneksi
echo -n "🌐 Mengecek koneksi internet... "
curl -I --max-time 5 -s http://google.com >/dev/null && echo "✅" || { echo "❌"; exit 1; }

# Install system deps
echo -n "🔧 Memastikan dependensi sistem... "
command -v curl >/dev/null 2>&1 || pkg install -y curl >/dev/null 2>&1
command -v openssl >/dev/null 2>&1 || pkg install -y openssl >/dev/null 2>&1
echo "✅"

# Install Python modules (tanpa aiohttp yang tidak dipakai)
echo -n "📦 Menginstall modul Python... "
$PYTHON_BIN - <<'EOF' >/dev/null 2>&1 || true
 import pkgutil, subprocess, sys
 deps = ["requests", "rich", "beautifulsoup4"]
 missing = [d for d in deps if not pkgutil.find_loader(d)]
 if missing:
     subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir"] + missing)
EOF
echo "✅"

# Download latest edoll.py
echo -n "⬇️ Mengunduh edoll.py terbaru... "
curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/edoll.py -o "$INSTALL_DIR/edoll.py"
echo "✅"

# Buat launcher
echo -n "⚙️ Membuat launcher command 'edoll'... "
cat > "$LAUNCHER" <<EOF
#!/data/data/com.termux/files/usr/bin/bash
$PYTHON_BIN $INSTALL_DIR/edoll.py "\$@"
EOF
chmod +x "$LAUNCHER"
echo "✅"

# Bersihkan
rm -rf $PREFIX/tmp/* 2>/dev/null || true

echo -e "\n🎉 Instalasi / Update selesai!"
echo "👉 Jalankan: edoll"
echo "   Atau: python $INSTALL_DIR/edoll.py"
exit 0