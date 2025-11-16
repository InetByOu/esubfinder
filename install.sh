#!/data/data/com.termux/files/usr/bin/bash
set -e

INSTALL_DIR="$PREFIX/share/.edoll"
LAUNCHER="$PREFIX/bin/edoll"
PYTHON_BIN="python"

mkdir -p "$INSTALL_DIR"

echo "📦 Memulai instalasi / update Edoll..."
sleep 1


# ============================
# Deteksi Python
# ============================
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "❌ Python tidak ditemukan!"
    echo "🔧 Menginstal Python..."
    pkg install -y python
    PYTHON_BIN="python"
fi


# ============================
# Cek koneksi internet
# ============================
echo "🔍 Mengecek koneksi internet..."
curl -I --max-time 5 http://example.com >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Tidak bisa mengakses internet."
    echo "💡 Tips: Pastikan Termux versi F-Droid atau gunakan VPN."
    exit 1
fi
echo "✅ Internet OK!"
sleep 1


# ============================
# Update SSL & Repository
# ============================
echo "🔒 Memperbarui certificates..."
pkg install -y openssl ca-certificates >/dev/null 2>&1 || true

echo "🔄 Memperbarui repository..."
pkg update -y >/dev/null 2>&1 || true


# ============================
# Install Termux dependencies
# ============================
echo "🔧 Mengecek dependensi..."

install_pkg() {
    local pkgname="$1"
    echo "🔧 Instal $pkgname..."
    pkg install -y "$pkgname" >/dev/null 2>&1 || \
        echo "⚠️ Gagal instal $pkgname! Coba aktifkan VPN"
}

command -v git >/dev/null 2>&1 || install_pkg git
command -v curl >/dev/null 2>&1 || install_pkg curl
command -v wget >/dev/null 2>&1 || install_pkg wget


# ============================
# Python Pip Fix
# ============================
echo "📦 Memperbaiki pip..."
$PYTHON_BIN -m ensurepip --upgrade >/dev/null 2>&1 || true
$PYTHON_BIN -m pip install --upgrade pip >/dev/null 2>&1 || true


# ============================
# Install Python Modules
# ============================
echo "📦 Install modul Python Edoll..."
$PYTHON_BIN -m pip install --upgrade \
    aiohttp \
    requests \
    rich \
    beautifulsoup4 \
    --no-cache-dir >/dev/null 2>&1 || {

    echo "⚠️ Gagal install modul Python."
    echo "🔄 Mencoba mirror pip lain..."
    $PYTHON_BIN -m pip install --upgrade \
        aiohttp \
        requests \
        rich \
        beautifulsoup4 \
        -i https://pypi.org/simple
}


# ============================
# Download Latest EDOLL
# ============================
echo "⬇️ Mengunduh edoll.py terbaru..."
if ! curl -sSLk \
  https://raw.githubusercontent.com/InetByOu/esubfinder/main/edoll.py \
  -o "$INSTALL_DIR/edoll.py"; then

    echo "❌ Gagal download edoll.py"
    echo "💡 Coba mode VPN!"
    exit 1
fi


# ============================
# Buat Global Launcher
# ============================
echo "⚙️ Membuat launcher global..."
cat <<EOF > "$LAUNCHER"
#!/data/data/com.termux/files/usr/bin/bash
$PYTHON_BIN $INSTALL_DIR/edoll.py "\$@"
EOF

chmod +x "$LAUNCHER"


# ============================
# Cleanup
# ============================
echo "🧹 Membersihkan cache..."
rm -rf $PREFIX/var/cache/apt/* >/dev/null 2>&1 || true
rm -rf $PREFIX/tmp/* >/dev/null 2>&1 || true


# ============================
# Run test
# ============================
echo "🧪 Menjalankan test Edoll..."
if ! $LAUNCHER >/dev/null 2>&1; then
    echo "⚠️ Edoll gagal dijalankan!"
    echo "🔧 Coba manual: python $INSTALL_DIR/edoll.py"
else
    echo "🎉 Edoll siap digunakan!"
    echo "👉 Jalankan: edoll"
fi
