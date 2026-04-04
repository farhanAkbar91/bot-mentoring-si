# 🤖 Bot Mentoring AI - HIMSI SI UNAIR

Sistem asisten digital berbasis Telegram yang dirancang untuk memfasilitasi mentoring lomba dan pusat informasi (FAQ) bagi mahasiswa Sistem Informasi Universitas Airlangga.

Bot ini menggunakan kecerdasan buatan (AI) sebagai *gatekeeper* untuk melakukan seleksi awal terhadap mahasiswa yang ingin mengakses mentor, sehingga proses mentoring menjadi lebih terarah dan efisien.

---

## 📌 Project Overview

Dalam lingkungan akademik, terdapat beberapa permasalahan utama:
- Sulitnya akses terstruktur ke mentor lomba
- Banyaknya pertanyaan berulang terkait lomba dan administrasi
- Distribusi informasi yang tidak efisien

**Solusi yang ditawarkan:**
- AI digunakan untuk menyaring permintaan mentoring berdasarkan kualitas alasan
- FAQ otomatis untuk mengurangi beban pengurus
- Integrasi Google Sheets untuk memudahkan pengelolaan data oleh non-developer

---

## ✨ Fitur Utama

- 🔐 **Verifikasi NIM**  
  Akses hanya untuk mahasiswa Sistem Informasi UNAIR

- 🧠 **AI Gatekeeper (Llama 3.1 - Groq)**  
  Mengevaluasi kelayakan permintaan mentor (ACCEPT / REJECT + alasan)

- 📚 **Dynamic FAQ System**  
  Menjawab pertanyaan berdasarkan basis pengetahuan yang terus diperbarui

- 🏆 **Informasi Lomba Terintegrasi**  
  Menampilkan daftar dan detail lomba secara real-time

- 🔄 **Sinkronisasi Google Sheets ↔ Database**  
  Memungkinkan update data tanpa menyentuh kode

- ⚡ **Rate Limiting & Anti-Spam**  
  Melindungi API dari penyalahgunaan

---

## 🧩 Arsitektur Sistem

```

User (Telegram)
↓
Bot (Aiogram - Async)
↓
AI Gatekeeper (Groq API - Llama 3.1)
↓
Backend Logic
↓
Database (Supabase)
↓
Google Sheets (Data Source)

````

**Catatan:**
- Google Sheets digunakan sebagai *source of truth* untuk data dinamis (FAQ & lomba)
- Supabase digunakan sebagai storage utama untuk sistem

---

## 💬 Command Utama

| Command          | Deskripsi |
|------------------|----------|
| `/start`         | Memulai bot & verifikasi user |
| `/faq`           | Menampilkan FAQ |
| `/list_lomba`    | Menampilkan daftar lomba |
| `/detail_lomba`  | Detail lomba tertentu |
| `/req_mentor`    | Mengajukan permintaan mentoring |
| `/sync` (admin)  | Sinkronisasi data dari Google Sheets |

---

## 🧠 AI Gatekeeper Logic

Model digunakan untuk mengevaluasi permintaan mentoring berdasarkan:

- Kejelasan tujuan mengikuti lomba
- Tingkat keseriusan dan effort
- Relevansi kebutuhan mentoring

**Output:**
- ✅ `ACCEPT` → User mendapatkan akses ke mentor
- ❌ `REJECT` → User diarahkan ke FAQ atau sumber lain  
- 📝 Disertai alasan dari AI untuk transparansi

---

## 🗄️ Struktur Data

Database menyimpan:

- 👤 User (terverifikasi NIM)
- 🏆 Data lomba
- 🎓 Data mentor
- ❓ FAQ
- 🧠 Log permintaan mentoring + respon AI

---

## 🔄 Data Pipeline

- Data lomba & FAQ diperbarui melalui **Google Sheets**
- Sinkronisasi dilakukan via command `/sync` (admin)
- Data kemudian disimpan di **Supabase**

---

## 🚀 Deployment

- **Platform:** Koyeb (server di Frankfurt)
- **Database:** Supabase (region Jepang)
- **AI API:** Groq Cloud

---

## ⚠️ Limitations & Challenges

Beberapa kendala saat ini:

- ⏱️ Latensi cukup tinggi  
  (Server di Frankfurt + DB di Jepang)

- 🐢 Respons awal bot terkadang lambat

- 🤖 AI masih berbasis prompt  
  (belum fine-tuned / belum ada memory)

- 🌐 Bergantung pada API eksternal (Groq)

---

## 🚧 Future Improvements

Pengembangan selanjutnya:

- 🧠 Intent Classification (klasifikasi tujuan user)
- 🔍 Named Entity Recognition (NER)
- 💾 Session / Memory (context-aware conversation)
- ⚡ Migrasi ke **FastAPI** (scalability & performance)
- 📊 Logging & analytics penggunaan bot
- 🔎 Semantic search untuk FAQ (vector database)

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Framework:** Aiogram 3.x
- **AI Engine:** Groq (Llama-3.1-8b-instant)
- **Database:** Supabase (PostgreSQL)
- **ORM:** SQLAlchemy
- **External API:** Google Sheets API v4

---

## ⚙️ Instalasi

```bash
git clone https://github.com/username/bot-mentoring-si.git
cd bot-mentoring-si
pip install -r requirements.txt
````

### 🔑 Environment Variables

Buat file `.env`:

```env
TELEGRAM_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
```

### 📄 Setup Data

* Tambahkan `credentials.json` dari Google Cloud
* Pastikan Google Sheets sudah di-share ke service account

### ▶️ Jalankan

```bash
python sync_sheets.py
python bot.py
```

---

## 📊 Status Proyek

* ✅ Sudah diuji coba internal (HIMSI SI UNAIR)
* 🚀 Sudah deployed (Koyeb)
* 🧪 Masih dalam tahap pengembangan (experimental system)

---

## 👥 Target Pengguna

Mahasiswa Sistem Informasi Universitas Airlangga, khususnya yang:

* Membutuhkan mentoring lomba
* Membutuhkan informasi akademik terkait kompetisi

---

## 📌 Catatan

Proyek ini dikembangkan sebagai sistem awal (*experimental system*) untuk mengintegrasikan:

* AI decision-making
* Information system
* Real-world academic workflow

Ke depannya, sistem ini dirancang untuk berkembang menjadi platform mentoring yang lebih scalable dan intelligent.
