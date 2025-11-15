# Edoll - Smart Subdomain Scanner & Inject Tester
**Versi:** E‑V3.9  
**Author:** Bang Edoll (2025)  
**Platform:** Termux & Linux  
**Lisensi:** MIT  

---

## 🔍 Apa Itu Edoll?
**Edoll** adalah tool **intelligent subdomain scanner** dan **inject tester** yang:

- Mengambil subdomain dari RapidDNS
- Scan HTTP/HTTPS + port 80/443
- Deteksi server & Cloudflare
- Simpan hasil scan ke history
- Bisa test inject satu-per-satu atau semua otomatis
- Menyimpan semua data ke folder tersembunyi
- Memiliki updater otomatis dengan backup & restore

Dibuat untuk membantu proses **bug hunting**, **inject config**, **V2Ray testing**, dan **tunneling eksperimen**.

---

Semua bisa diubah lewat menu **Settings**.

---

## 🚀 Instalasi (Termux / Linux)
Copy dan jalankan:

```bash
curl -sSL https://raw.githubusercontent.com/InetByOu/esubfinder/main/install.sh -o install.sh && bash install.sh && edoll 
```
---

## ⭐ Fitur Utama
- Scan subdomain cepat (multithread)
- Inject tester (individual / bulk)
- Auto history JSON
- Auto restore jika update gagal
- Ctrl+C aman (bisa menghentikan proses)
- Dependen otomatis dicek sebelum install
- UI terminal yang ramah(warna + animasi)
- Semua data tersimpan rapi
