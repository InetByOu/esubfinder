# Edoll - Smart Subdomain Scanner & Inject Tester
**Versi:** E-V3.9  
**Author:** Bang Edoll (2025)  
**Platform:** Termux & Linux  
**Lisensi:** MIT  

---

## 🔍 Apa Itu Edoll?
**Edoll** adalah tool **intelligent subdomain scanner** dan **inject tester** yang:

- Mengambil subdomain dari banyak sumber publik (RapidDNS, crt.sh, Riddler, Sonar, dll.)
- Scan HTTP/HTTPS + port 80/443 secara paralel
- Deteksi server, Cloudflare, TLS certificate
- Lookup provider/ASN
- Simpan hasil scan lengkap ke history (JSON)
- History Manager (view, export, merge, delete)
- Inject tester sederhana untuk testing connectivity

Dibuat untuk **bug hunting**, **reconnaissance**, **inject config testing**, dan **V2Ray/tunneling eksperimen**.

---

## 🚀 Instalasi (Termux / Linux)
```bash
curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/install.sh -o install.sh && bash install.sh && edoll
```

Setelah install, cukup jalankan perintah:
```bash
edoll
```

## ⭐ Fitur Utama
- Multithread subdomain scanning
- Parallel fetching dari multiple sources
- Full active checks (port, HTTP, HTTPS, TLS, provider)
- Auto history JSON dengan timestamp
- History Manager lengkap
- Settings yang bisa diubah
- UI terminal warna + animasi (rich)
- Aman terhadap Ctrl+C

## 📝 Catatan
- Tool ini bersifat **passive + active reconnaissance**.
- Gunakan hanya pada domain yang kamu miliki atau punya izin.
- Beberapa sumber data publik kadang tidak stabil.
- Fitur updater otomatis masih dalam pengembangan.

---

Semua pengaturan bisa diubah lewat menu **Settings**.
