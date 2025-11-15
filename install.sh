#!/bin/bash

echo "=============================================="
echo "        Installing E-DOLL Super Scanner"
echo "=============================================="

PREFIX="/data/data/com.termux/files/usr"
INSTALL_DIR="$PREFIX/share/edoll"
BIN_FILE="$PREFIX/bin/edoll"
SOURCE_FILE="edoll.py"

# Cek apakah file script ada
if [ ! -f "$SOURCE_FILE" ]; then
    echo "[X] ERROR: File edoll.py tidak ditemukan!"
    echo "     Pastikan file ini berada di folder yang sama dengan installer."
    exit 1
fi

echo "[*] Membuat direktori instalasi..."
mkdir -p "$INSTALL_DIR"

echo "[*] Membersihkan sisa instalasi lama..."
rm -f "$BIN_FILE"
rm -rf "$INSTALL_DIR"/*

echo "[*] Menyalin file script..."
cp "$SOURCE_FILE" "$INSTALL_DIR/edoll.py"
chmod +x "$INSTALL_DIR/edoll.py"

echo "[*] Membuat symlink ke /usr/bin..."
ln -sf "$INSTALL_DIR/edoll.py" "$BIN_FILE"
chmod +x "$BIN_FILE"

# Clean leftover temp files
echo "[*] Membersihkan file sementara..."
rm -f install.sh~
rm -f .edoll_tmp 2>/dev/null

echo "=============================================="
echo "[✔] Instalasi berhasil!"
echo "[✔] Jalankan dengan perintah:  edoll"
echo "=============================================="
