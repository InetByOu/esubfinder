# Edoll E‑V3.0

**Advanced Subdomain Scanner & Tunnel Analyzer (Termux Edition)**\
Versi terbaru Edoll menghadirkan pemindaian cepat, analisis tunnel
otomatis, manajemen dependensi, riwayat domain, dan tampilan modern
dengan animasi loading.

------------------------------------------------------------------------

## 🎯 Fitur Utama

### 🔍 1. **Subdomain Scanner**

-   Pemindaian cepat multi-thread.
-   Deteksi: HTTP Status, Cloudflare, IP, Server, Redirect.
-   Extreme Scan (Deep mode + Header expand).

### 🔐 2. **Tunnel Analyzer**

-   Deteksi otomatis:
    -   WS (WebSocket)
    -   SNI/HTTPS 443
    -   Enhanced Tunnel Ready
    -   V2Ray readiness

### 📁 3. **History Manager**

-   Menyimpan domain yang pernah dipindai.
-   Dapat dipilih kembali sebagai opsi cepat.
-   Fitur hapus dan reset riwayat.

### ⚙️ 4. **Dependensi Manager**

-   Auto-scan dependensi penting.
-   Menampilkan status (Installed / Missing).
-   Menawarkan instalasi otomatis bila diperlukan.

### 📝 5. **Preview & Editor Mode**

-   Hasil scan bisa dibuka di text viewer internal.
-   Memudahkan copy--paste ke aplikasi lain.

### 🎨 6. **UI Profesional**

-   Warna kategori: info, warning, success, danger.
-   Animasi loading modern tanpa simbol rumit.
-   Layout responsive friendly untuk Termux.

------------------------------------------------------------------------

## 📦 Dependensi

Edoll membutuhkan dependensi berikut agar berfungsi penuh:

  Dependensi    Fungsi         Status
  ------------- -------------- ----------
  `python3`     Core engine    Wajib
  `requests`    HTTP Request   Wajib
  `dnspython`   DNS Resolve    Wajib
  `openssl`     SSL Checking   Wajib
  `curl`        Backup fetch   Opsional
  `nano`        Text editor    Opsional

Semua dapat dipasang melalui menu **Dependensi Manager**.

------------------------------------------------------------------------

## 🚀 Cara Instalasi

### 1. Unduh `edoll.py` dan `install.sh`

Letakkan kedua file dalam satu folder.

### 2. Jalankan installer

``` bash
bash install.sh
```

### 3. Jalankan Edoll

``` bash
edoll
```

------------------------------------------------------------------------

## 🧠 Cara Penggunaan

### ▶ Mode Utama

-   **Auto Scan** → Pemindaian standar cepat.\
-   **Auto Cek Result** → Analisis hasil scan lama.\
-   **Extreme Scan + Cek** → Mode agresif & deep check.\
-   **Tunnel Mode** → Menampilkan domain siap WS/SNI.\
-   **History** → Daftar domain yang pernah dipindai.\
-   **Dependensi Manager** → Scan & install paket.\
-   **Settings** → Pengaturan global.

------------------------------------------------------------------------

## 🛠 Struktur File

    /data/data/com.termux/files/usr/share/edoll/
     ├─ edoll.py
     ├─ history.json
     ├─ results/
     ├─ config.json
     └─ assets/

------------------------------------------------------------------------

## ❤️ Kontribusi

Anda dapat mengembangkan Edoll dengan: - Membuat modul scanner baru -
Meningkatkan kecepatan threading - Menambah database bug host

------------------------------------------------------------------------

## 📜 Lisensi

Edoll E‑V3.0 dirilis dengan lisensi **MIT License**.\
Anda bebas memodifikasi & mendistribusikan selama menyertakan atribusi.

------------------------------------------------------------------------

## 🤝 Kredit

Dikembangkan khusus untuk pengguna Termux\
Dibangun dengan fokus: *stabil, cepat, dan tidak membosankan*.
