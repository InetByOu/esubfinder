#!/data/data/com.termux/files/usr/bin/bash
rm -rf $PYTHON_BIN $INSTALL_DIR/edoll.py
sleep 5
set -e

INSTALL_DIR="$PREFIX/share/.edoll"
LAUNCHER="$PREFIX/bin/edoll"
PYTHON_BIN="python"

mkdir -p "$INSTALL_DIR"

echo "📦 Instalasi Edoll dimulai..."


# ============================
# Spinner / Progress bar
# ============================
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\'
    while kill -0 $pid 2>/dev/null; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}


# ============================
# Cek Python
# ============================
echo -n "🔧 Cek Python..."
{
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif ! command -v python >/dev/null 2>&1; then
    pkg install -y python >/dev/null 2>&1
fi
} & spinner $!
echo " ✅"


# ============================
# Cek koneksi internet
# ============================
echo -n "🌐 Mengecek koneksi internet..."
{
curl -I --max-time 5 http://google.com >/dev/null 2>&1
} & spinner $!
echo " ✅"


# ============================
# Install dependencies
# ============================
echo -n "🔧 Memastikan dependensi minimal..."
{
command -v curl >/dev/null 2>&1 || pkg install -y curl >/dev/null 2>&1
command -v openssl >/dev/null 2>&1 || pkg install -y openssl >/dev/null 2>&1
} & spinner $!
echo " ✅"


# ============================
# Install Python modules
# ============================
echo -n "📦 Instal modul Python..."
{
$PYTHON_BIN - <<EOF
import pkgutil, subprocess, sys
deps = ["aiohttp","requests","rich","beautifulsoup4"]
missing = [d for d in deps if not pkgutil.find_loader(d)]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir"] + missing)
EOF
} & spinner $!
echo " ✅"


# ============================
# Download Edoll
# ============================
echo -n "⬇️ Mengunduh edoll.py..."
{
curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/edoll.py -o "$INSTALL_DIR/edoll.py"
} & spinner $!
echo " ✅"

# ============================
# Buat launcher
# ============================
echo -n "⚙️ Membuat launcher..."
{
cat <<EOF > "$LAUNCHER"
#!/data/data/com.termux/files/usr/bin/bash
$PYTHON_BIN $INSTALL_DIR/edoll.py "\$@"
EOF

chmod +x "$LAUNCHER"
} & spinner $!
echo " ✅"


# ============================
# Bersih-bersih cepat
# ============================
echo -n "🧹 Membersihkan temporary files..."
{
rm -rf $PREFIX/tmp/* >/dev/null 2>&1 || true
} & spinner $!
echo " ✅"


# ============================
# Selesai
# ============================
echo -e "\n🎉 Instalasi / Update selesai!"
echo "👉 Jalankan: edoll"
exit 0
