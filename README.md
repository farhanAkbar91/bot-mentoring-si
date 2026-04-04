# 🤖 AI Mentoring Bot - HIMSI Information Systems UNAIR

A Telegram-based digital assistant designed to facilitate competition mentoring and provide an information hub (FAQ) for Information Systems students at Universitas Airlangga.

This bot leverages artificial intelligence (AI) as a *gatekeeper* to evaluate and filter mentoring requests, ensuring that access to mentors is more structured, relevant, and efficient.

---

## 📌 Project Overview

In academic environments, several challenges commonly arise:
- Difficulty in accessing structured mentoring for competitions
- Repetitive questions regarding competitions and administrative processes
- Inefficient information distribution by student organizations

**Proposed solution:**
- AI filters mentoring requests based on quality and intent
- Automated FAQ reduces repetitive inquiries
- Google Sheets integration enables non-technical staff to manage data easily

---

## ✨ Key Features

- 🔐 **Student Verification (NIM-based)**  
  Restricted access for Information Systems students only

- 🧠 **AI Gatekeeper (Llama 3.1 - Groq)**  
  Evaluates mentoring requests (ACCEPT / REJECT + reasoning)

- 📚 **Dynamic FAQ System**  
  Answers questions based on continuously updated knowledge base

- 🏆 **Competition Information System**  
  Provides real-time competition listings and details

- 🔄 **Google Sheets ↔ Database Synchronization**  
  Enables easy data updates without modifying code

- ⚡ **Rate Limiting & Anti-Spam**  
  Protects API usage and prevents abuse

---

## 🧩 System Architecture

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
```

**Notes:**
- Google Sheets acts as the *source of truth* for dynamic data (FAQ & competitions)
- Supabase is used as the primary database for system operations

---

## 💬 Main Commands

| Command          | Description |
|------------------|------------|
| `/start`         | Initialize bot & verify user |
| `/faq`           | Display frequently asked questions |
| `/list_lomba`    | Show available competitions |
| `/detail_lomba`  | Show competition details |
| `/req_mentor`    | Submit mentoring request |
| `/sync` (admin)  | Sync data from Google Sheets |

---

## 🧠 AI Gatekeeper Logic

The model evaluates mentoring requests based on:

- Clarity of the user's goals
- Level of seriousness and effort
- Relevance of the mentoring request

**Output:**
- ✅ `ACCEPT` → User is granted access to mentor
- ❌ `REJECT` → User is redirected to FAQ or alternative resources  
- 📝 Includes reasoning for transparency

---

## 🗄️ Data Structure

The database stores:

- 👤 User data (verified students)
- 🏆 Competition data
- 🎓 Mentor data
- ❓ FAQ data
- 🧠 Mentoring request logs + AI responses

---

## 🔄 Data Pipeline

- Competition & FAQ data are maintained via **Google Sheets**
- Data synchronization is triggered using `/sync` (admin command)
- Synced data is stored in **Supabase**

---

## 🚀 Deployment

- **Platform:** Koyeb (Frankfurt region)
- **Database:** Supabase (Japan region)
- **AI API:** Groq Cloud

---

## ⚠️ Limitations & Challenges

Current limitations include:

- ⏱️ High latency  
  (Geographical distance: Frankfurt server ↔ Japan database)

- 🐢 Slow response on initial interactions

- 🤖 AI is prompt-based  
  (No fine-tuning or conversational memory yet)

- 🌐 Dependency on external APIs (Groq)

---

## 🚧 Future Improvements

Planned enhancements:

- 🧠 Intent Classification
- 🔍 Named Entity Recognition (NER)
- 💾 Session-based memory (context-aware conversations)
- ⚡ Migration to **FastAPI** for better scalability
- 📊 Logging & usage analytics
- 🔎 Semantic FAQ search using vector database

---

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Framework:** Aiogram 3.x
- **AI Engine:** Groq (Llama-3.1-8b-instant)
- **Database:** Supabase (PostgreSQL)
- **ORM:** SQLAlchemy
- **External API:** Google Sheets API v4

---

## ⚙️ Installation

```bash
git clone https://github.com/username/bot-mentoring-si.git
cd bot-mentoring-si
pip install -r requirements.txt
````

### 🔑 Environment Variables

Create a `.env` file:

```env id="b2m1xk"
TELEGRAM_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
```

### 📄 Data Setup

* Add `credentials.json` from Google Cloud
* Ensure your Google Sheets is shared with the service account

### ▶️ Run the Project

```bash id="7d2mza"
python sync_sheets.py
python bot.py
```

---

## 📊 Project Status

* ✅ Tested internally (HIMSI Information Systems UNAIR)
* 🚀 Deployed on Koyeb
* 🧪 Currently in experimental stage

---

## 👥 Target Users

Information Systems students at Universitas Airlangga who:

* Need competition mentoring
* Require structured academic information

---

## 📌 Notes

This project is developed as an *experimental system* integrating:

* AI-driven decision making
* Information systems
* Real-world academic workflows

The long-term goal is to evolve into a scalable and intelligent mentoring platform.
