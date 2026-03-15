# 🤖 Bot Mentoring AI - Himpunan Mahasiswa SI

Sistem asisten digital berbasis Telegram yang dirancang untuk memfasilitasi mentoring lomba dan pusat informasi (FAQ) bagi mahasiswa Sistem Informasi. Bot ini menggunakan kecerdasan buatan (AI) untuk melakukan seleksi awal (Gatekeeper) bagi mahasiswa yang membutuhkan mentor.

## ✨ Fitur Utama
- **Verifikasi NIM:** Akses eksklusif hanya untuk mahasiswa SI yang terverifikasi.
- **AI Gatekeeper:** Menilai kelayakan alasan mahasiswa meminta kontak mentor menggunakan model Llama 3.1 (Groq API).
- **Dynamic FAQ:** Menjawab pertanyaan umum seputar lomba berdasarkan basis pengetahuan yang dikelola pengurus.
- **Sync Google Sheets:** Memudahkan pengurus memperbarui data lomba dan FAQ tanpa menyentuh kode program.
- **Anti-Spam & Rate Limiting:** Melindungi kuota API dan mencegah penyalahgunaan fitur mentoring.

## 🛠️ Tech Stack
- **Language:** Python 3.10+
- **Framework:** [Aiogram 3.x](https://docs.aiogram.dev/) (Asynchronous Bot)
- **AI Engine:** [Groq Cloud](https://groq.com/) (Llama-3.1-8b-instant)
- **Database:** SQLite with SQLAlchemy ORM
- **External API:** Google Sheets API (v4)

## 🚀 Cara Instalasi

1. **Clone Repositori:**
   ```bash
   git clone [https://github.com/username/bot-mentoring-si.git](https://github.com/username/bot-mentoring-si.git)
   cd bot-mentoring-si
   ```

2. **Instalasi Library:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfigurasi Environment:**
   Buat file .env dan isi dengan:
   ``` bash
   TELEGRAM_TOKEN=your_bot_token
   GROQ_API_KEY=your_groq_key
   ```

4. **Persiapan Data:**
   ***Masukkan file credentials.json dari Google Cloud ke folder utama.***
   ***Pastikan Google Sheets sudah dibagikan ke email akun layanan.***

5. Jalankan Sinkronisasi & Bot:
   ```bash
   python sync_sheets.py  # Ambil data dari Sheets ke lokal
   python bot.py          # Jalankan bot
   ```