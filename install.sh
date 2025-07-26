#!/bin/bash
echo "[*] Menginstal Edoll ke Termux..."

# Direktori target
PREFIX="/data/data/com.termux/files/usr"
INSTALL_DIR="$PREFIX/share/edoll"
BIN_FILE="$PREFIX/bin/edoll"

# Buat folder jika belum ada
mkdir -p "$INSTALL_DIR"

# Pindahkan script ke folder share
cp edoll.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/edoll.py"

# Buat symlink ke bin agar bisa dijalankan sebagai perintah
ln -sf "$INSTALL_DIR/edoll.py" "$BIN_FILE"
chmod +x "$BIN_FILE"

echo "[✔] Instalasi selesai. Jalankan dengan perintah: edoll"
