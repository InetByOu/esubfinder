#!/bin/bash
# ===============================================
# Edoll Installer / Updater (Termux / Linux)
# Versi: E-V3.9
# ===============================================

EDOLL_DIR="$HOME/.edoll"
BIN_DIR="$PREFIX/bin"
LAUNCHER="$BIN_DIR/edoll"
REPO="https://github.com/InetByOu/esubfinder.git"

echo ""
echo "📦 Menginstal / Memperbarui Edoll..."

# Cek dependensi
for d in git curl python; do
    if ! command -v $d &>/dev/null; then
        echo "🔧 Menginstal $d..."
        pkg install -y $d || apt install -y $d
    fi
done

# Backup jika sudah ada
if [ -d "$EDOLL_DIR" ]; then
    echo "♻️  Membuat backup versi lama..."
    cp "$EDOLL_DIR/edoll.py" "$EDOLL_DIR/edoll.py.bak" 2>/dev/null || true
fi

# Buat direktori tersembunyi
mkdir -p "$EDOLL_DIR/history"
mkdir -p "$EDOLL_DIR/logs"

# Unduh file utama
echo "⬇️  Mengunduh edoll.py terbaru..."
curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/edoll.py -o "$EDOLL_DIR/edoll.py" || {
    echo "❌ Gagal download, restore versi lama..."
    [ -f "$EDOLL_DIR/edoll.py.bak" ] && cp "$EDOLL_DIR/edoll.py.bak" "$EDOLL_DIR/edoll.py"
    exit 1
}

chmod +x "$EDOLL_DIR/edoll.py"

# Buat launcher global
echo "⚙️  Membuat launcher global..."
cat <<EOF > "$LAUNCHER"
#!/bin/bash
python3 "$EDOLL_DIR/edoll.py" "\$@"
EOF

chmod +x "$LAUNCHER"

echo ""
echo "🎉 Instalasi / Update selesai!"
echo "Sekarang jalankan: edoll"
