#!/data/data/com.termux/files/usr/bin/bash

set -e

INSTALL_DIR="$PREFIX/share/.edoll"
LAUNCHER="$PREFIX/bin/edoll"

mkdir -p "$INSTALL_DIR"

echo "📦 Memulai instalasi / update Edoll..."
sleep 1

# ============================
# Cek koneksi internet
# ============================
echo "🔍 Mengecek koneksi internet..."
curl --max-time 5 http://example.com >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Tidak bisa mengakses internet."
    echo "💡 Tips: Pastikan Termux versi F-Droid atau gunakan VPN."
    exit 1
fi
echo "✅ Internet OK!"
sleep 1

# ============================
# Update certificate & repo
# ============================
echo "🔧 Memperbarui certificate SSL..."
pkg install -y openssl ca-certificates >/dev/null 2>&1 || \
    echo "⚠️ Gagal update certificates. Gunakan F-Droid Termux atau VPN."

echo "🔄 Memperbarui repository..."
pkg update -y >/dev/null 2>&1 || \
    echo "⚠️ Repo SSL gagal, coba mirror alternatif dengan 'termux-change-repo' atau gunakan F-Droid/VPN."

# ============================
# Install dependencies
# ============================
echo "🔧 Mengecek dependensi..."

install_pkg() {
    local pkgname="$1"
    echo "🔧 Menginstal $pkgname..."
    if ! pkg install -y "$pkgname" >/dev/null 2>&1; then
        echo "❌ Gagal menginstal $pkgname."
        echo "💡 Gunakan Termux versi F-Droid atau aktifkan VPN."
        return 1
    fi
    return 0
}

command -v git >/dev/null 2>&1 || install_pkg git
command -v python >/dev/null 2>&1 || install_pkg python

# ============================
# Install Python modules
# ============================
echo "📦 Memastikan modul Python tersedia..."
python -m ensurepip --upgrade >/dev/null 2>&1 || true
python -m pip install --upgrade pip >/dev/null 2>&1 || true
pip install requests beautifulsoup4 >/dev/null 2>&1 || \
    echo "⚠️ Gagal install modul Python. Jalankan: pip install requests beautifulsoup4"
    
# ============================
# Unduh edoll.py
# ============================
echo "⬇️ Mengunduh edoll.py terbaru..."
if ! curl -sSLk https://raw.githubusercontent.com/InetByOu/esubfinder/main/edoll.py -o "$INSTALL_DIR/edoll.py"; then
    echo "❌ Gagal download edoll.py."
    echo "💡 Gunakan Termux versi F-Droid atau aktifkan VPN."
    exit 1
fi

# ============================
# Buat launcher global
# ============================
echo "⚙️ Membuat launcher global..."
cat <<EOF > "$LAUNCHER"
#!/data/data/com.termux/files/usr/bin/bash
python $INSTALL_DIR/edoll.py "\$@"
EOF

chmod +x "$LAUNCHER"

# ============================
# Bersihkan cache
# ============================
echo "🧹 Membersihkan cache apt..."
rm -rf $PREFIX/var/cache/apt/* >/dev/null 2>&1 || true

echo
echo "🎉 Instalasi / Update selesai!"
echo "👉 Jalankan: edoll"
