#!/data/data/com.termux/files/usr/bin/bash
set -e

INSTALL_DIR="$PREFIX/share/.edoll"
LAUNCHER="$PREFIX/bin/edoll"
PYTHON_BIN="python"

mkdir -p "$INSTALL_DIR"

echo "📦 Instalasi Edoll dimulai..."


# ============================
# Deteksi Python
# ============================
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif ! command -v python >/dev/null 2>&1; then
    echo "🔧 Menginstal Python..."
    pkg install -y python >/dev/null 2>&1
fi


# ============================
# Cek koneksi internet
# ============================
echo "🔍 Mengecek internet..."
if ! curl -I --max-time 5 http://example.com >/dev/null 2>&1; then
    echo "❌ Tidak ada internet!"
    exit 1
fi


# ============================
# Cek dependensi minimal
# ============================
echo "🔧 Cek dependensi..."

command -v curl >/dev/null 2>&1 || pkg install -y curl >/dev/null 2>&1
command -v openssl >/dev/null 2>&1 || pkg install -y openssl >/dev/null 2>&1


# ============================
# Install Modul Python (cepat)
# ============================
echo "📦 Instal modul Python..."

$PYTHON_BIN - <<EOF
import pkgutil, subprocess, sys
deps = ["aiohttp", "requests", "rich", "beautifulsoup4"]
missing = [d for d in deps if not pkgutil.find_loader(d)]
if missing:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir"] + missing)
EOF


# ============================
# Download Edoll
# ============================
echo "⬇️ Mengunduh edoll.py..."
curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/edoll.py -o "$INSTALL_DIR/edoll.py"


# ============================
# Launcher Fast Mode
# ============================
echo "⚙️ Membuat launcher..."
cat <<EOF > "$LAUNCHER"
#!/data/data/com.termux/files/usr/bin/bash
$PYTHON_BIN $INSTALL_DIR/edoll.py "\$@"
EOF

chmod +x "$LAUNCHER"


# ============================
# Bersih-bersih Cepat
# ============================
rm -rf $PREFIX/tmp/* >/dev/null 2>&1 || true


# ============================
# Tes Minimal
# ============================
echo "🎉 Edoll selesai diinstal!"
echo "👉 Jalankan: edoll"

exit 0
