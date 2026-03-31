import os
import logging
import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session
from database import SessionLocal, Lomba, Mentor, PermintaanMentoring, User, FAQ
from groq import AsyncGroq
from dotenv import load_dotenv
from sync_sheets import sync_data
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from sync_sheets import sync_data

load_dotenv()

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
ADMIN_ID = os.getenv("ADMIN_ID")

# Berikan batas waktu 60 detik agar koneksi tidak cepat putus
custom_session = AiohttpSession(timeout=60.0) 
bot = Bot(token=TOKEN, session=custom_session)
dp = Dispatcher()
groq_client = AsyncGroq(api_key=GROQ_API_KEY) # ✅ 1. Inisialisasi Async

# --- FSM STATES ---
class BotStates(StatesGroup):
    waiting_for_nim = State()
    waiting_for_reason = State()

# --- KEYBOARDS ---
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🏆 Info Lomba", callback_data="list_lomba"))
    builder.row(types.InlineKeyboardButton(text="👨‍🏫 Minta Mentoring", callback_data="req_mentor"))
    builder.row(types.InlineKeyboardButton(text="❓ FAQ", callback_data="faq"))
    return builder.as_markup()

# --- HANDLERS ---
import traceback # Tambahkan di bagian atas file

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()

        if not user:
            await state.set_state(BotStates.waiting_for_nim)
            await message.answer(f"Halo {message.from_user.first_name}! 👋\n\nSilakan masukkan **NIM** Anda (khusus mahasiswa SI) untuk verifikasi:")
        else:
            await message.answer(f"Selamat datang kembali, {user.nama}! Ada yang bisa dibantu?", reply_markup=main_menu())
            
    except Exception as e:
        # Jika DB gagal connect, bot akan membalas pesan error ini ke Telegram kamu
        error_msg = f"Aduh, gagal konek ke Database nih:\n{str(e)[:500]}"
        await message.answer(error_msg)

@dp.message(Command("sync"))
async def cmd_sync(message: types.Message):
    admin_env = os.getenv("ADMIN_ID", "")
    daftar_admin = [admin.strip() for admin in admin_env.split(",")]

    # Cek Gatekeeper: Tolak jika ID Telegram pengirim tidak ada di daftar
    if str(message.from_user.id) not in daftar_admin:
        await message.answer("⚠️ Maaf, perintah ini khusus untuk akses Admin/Staf HIMA.")
        return

    # Jika lolos pengecekan, jalankan sinkronisasi
    m = await message.answer("🔄 Sedang menyinkronkan data Lomba, Mentor, dan FAQ dari Google Sheets...")
    
    try:
        # Jalankan fungsi sync yang sudah diperbaiki tadi
        hasil = sync_data() 
        
        if hasil:
            await m.edit_text("✅ Sinkronisasi berhasil! Database Supabase kini menggunakan data terbaru.")
        else:
            await m.edit_text("❌ Sinkronisasi gagal. Cek log server untuk detailnya.")
            
    except Exception as e:
        logging.error(f"Gagal sync via command: {e}")
        await m.edit_text(f"❌ Terjadi kesalahan sistem saat sinkronisasi:\n`{str(e)[:200]}`", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_nim)
async def process_nim(message: types.Message, state: FSMContext):
    nim = message.text.strip()
    if re.match(r"^1872[3-6]\d{4}$", nim):
        with SessionLocal() as db:
            new_user = User(telegram_id=str(message.from_user.id), nim=nim, nama=message.from_user.full_name, is_verified=1)
            db.add(new_user)
            db.commit()
            
        await state.clear()
        await message.answer("✅ Verifikasi Berhasil!", reply_markup=main_menu())
    else:
        await message.answer("❌ Format NIM salah. Pastikan Anda mahasiswa Sistem Informasi.")

@dp.callback_query(F.data == "list_lomba")
async def show_lomba(callback: types.CallbackQuery):
    with SessionLocal() as db:
        semua_lomba = db.query(Lomba).all() # ✅ Mengambil data lomba dari database
        
    if not semua_lomba:
        await callback.message.answer("Belum ada data lomba bulan ini.")
        await callback.answer()
        return

    # ✅ Membuat tombol inline untuk setiap nama lomba agar lebih scannable
    builder = InlineKeyboardBuilder()
    for l in semua_lomba:
        # callback_data diarahkan ke detail masing-masing ID lomba
        builder.row(types.InlineKeyboardButton(
            text=f"🏆 {l.nama_lomba}", 
            callback_data=f"detail_lomba_{l.id}"
        ))
    
    await callback.message.answer(
        "📅 **DAFTAR LOMBA AKTIF**\nSilakan pilih lomba untuk melihat detail lebih lanjut:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# ✅ Handler Baru: Menampilkan detail lomba berdasarkan ID yang diklik
@dp.callback_query(F.data.startswith("detail_lomba_"))
async def show_lomba_detail(callback: types.CallbackQuery):
    lomba_id = int(callback.data.split("_")[-1]) # Mengambil ID dari callback_data
    
    with SessionLocal() as db:
        l = db.query(Lomba).filter(Lomba.id == lomba_id).first() #
        
    if not l:
        await callback.answer("Data lomba tidak ditemukan.")
        return

    # ✅ Format tampilan detail yang lebih rapi menggunakan Markdown
    text = (
        f"🏆 **{l.nama_lomba}**\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📁 **Kategori:** {l.kategori}\n"
        f"📅 **Deadline:** {l.deadline}\n\n"
        f"📝 **Deskripsi:**\n{l.deskripsi}\n\n"
        f"🔗 [Klik di sini untuk info lebih lanjut]({l.link_info})"
    )
    
    await callback.message.answer(text, parse_mode="Markdown", disable_web_page_preview=False)
    await callback.answer()

@dp.callback_query(F.data == "faq")
async def show_faq_list(callback: types.CallbackQuery):
    # ✅ 1. Ambil data FAQ dari database (Supabase)
    with SessionLocal() as db:
        faqs = db.query(FAQ).all()
        
    if not faqs:
        await callback.message.answer("Database FAQ saat ini masih kosong.")
        await callback.answer()
        return

    # ✅ 2. Susun teks FAQ untuk ditampilkan langsung
    text = "❓ **FREQUENTLY ASKED QUESTIONS** ❓\n\n"
    for f in faqs:
        text += f"📌 **{f.pertanyaan}**\n└ {f.jawaban}\n\n"
    
    text += "💡 _Anda juga bisa langsung mengetik pertanyaan spesifik untuk dijawab oleh AI._"
    
    # ✅ 3. Kirim pesan dan hapus status loading (jam pasir) pada tombol
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "req_mentor")
async def start_mentoring(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_reason)
    
    # Membuat tombol batal khusus
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="❌ Batalkan Permintaan", callback_data="cancel_request"))
    
    await callback.message.answer(
        "📝 **Formulir Mentoring**\n\nJelaskan progres tim Anda (Lomba apa, tim, draf idea). "
        "AI akan mengevaluasi kelayakan Anda mendapatkan mentor.",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "cancel_request")
async def process_cancel_click(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Permintaan mentoring telah dibatalkan.")
    await callback.message.answer("Ada hal lain yang bisa saya bantu?", reply_markup=main_menu())

# --- LOGIKA REMINDER ---
async def check_deadlines():
    """Fungsi untuk mengecek lomba yang akan berakhir dalam 3 hari"""
    today = datetime.now()
    three_days_later = today + timedelta(days=3)
    
    with SessionLocal() as db:
        # Ambil semua lomba
        semua_lomba = db.query(Lomba).all()
        # Ambil semua user yang sudah terverifikasi untuk dikirimi broadcast 
        users = db.query(User).filter(User.is_verified == 1).all()
    upcoming_lomba = []
    for l in semua_lomba:
        try:
            # Mengubah string deadline menjadi objek datetime untuk perbandingan
            deadline_date = datetime.strptime(l.deadline, "%Y-%m-%d")
            # Jika deadline dalam rentang 0 - 3 hari ke depan
            if today <= deadline_date <= three_days_later:
                upcoming_lomba.append(l)
        except ValueError:
            continue # Abaikan jika format tanggal di Google Sheets tidak sesuai

    if upcoming_lomba and users:
        for user in users:
            msg = "🔔 **PENGINGAT DEADLINE LOMBA** 🔔\n\n"
            for l in upcoming_lomba:
                msg += f"⚠️ **{l.nama_lomba}**\n📅 Deadline: {l.deadline}\n"
            
            msg += "\nSegera selesaikan progres Anda dan ajukan mentoring jika butuh bantuan!"
            try:
                await bot.send_message(user.telegram_id, msg, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Gagal kirim reminder ke {user.telegram_id}: {e}")

# --- LOGIKA GATEKEEPER & MENTOR ---
@dp.message(BotStates.waiting_for_reason)
async def process_mentoring_reason(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    with SessionLocal() as db:
        # Anti-Spam
        last_req = db.query(PermintaanMentoring).filter_by(user_id_telegram=user_id).order_by(PermintaanMentoring.timestamp.desc()).first()
        if last_req and (datetime.utcnow() - last_req.timestamp < timedelta(minutes=30)):
            await message.answer("⚠️ Mohon tunggu 30 menit sebelum mengajukan lagi.")
            return

    if len(message.text) < 30:
        await message.answer("⚠️ Alasan terlalu singkat (min. 30 karakter).")
        return

    await message.answer("🔍 Mengevaluasi alasan dengan AI...")

    try:
        # ✅ 1. Tambahkan 'await' agar event loop bot tidak terblokir
        completion = await groq_client.chat.completions.create(
            messages=[{"role": "system", "content": "Koordinator Lomba. Nilai alasan. Kriteria: progres 50%. Balas [SETUJU] atau [TOLAK] + alasan."},
                      {"role": "user", "content": message.text}],
            model=GROQ_MODEL,
        )
        ai_response = completion.choices[0].message.content

        log_status = "TOLAK"
        if "[SETUJU]" in ai_response.upper():
            log_status = "SETUJU"
            
            # Contextual Mentor
            cat_res = await groq_client.chat.completions.create(
                messages=[{"role": "user", "content": f"Kategori lomba dari teks: '{message.text}'. Balas 1 kata saja (UI/UX, Web, Esai, Data)."}],
                model=GROQ_MODEL
            )
            raw_cat = cat_res.choices[0].message.content.strip().upper()
            
            # ✅ 3. Optimasi: Ambil kata kunci yang pasti, abaikan tanda baca dari LLM
            kategori_valid = ["UI/UX", "WEB", "ESAI", "DATA"]
            cat = next((k for k in kategori_valid if k in raw_cat), "WEB") # Default ke Web jika AI ngaco

            with SessionLocal() as db:
                # Menggunakan ilike untuk pencarian case-insensitive yang lebih aman
                mentor = db.query(Mentor).filter(Mentor.spesialisasi.ilike(f"%{cat}%")).first() or db.query(Mentor).first()
                
            res_text = f"✅ **DISETUJUI**\n\n{ai_response}\n\nHubungi: **{mentor.nama_mentor}**\nWA: https://wa.me/{mentor.kontak}"
            await message.answer(res_text, parse_mode="Markdown")
        else:
            await message.answer(f"❌ **DITOLAK**\n\n{ai_response}")

        # Simpan Log
        with SessionLocal() as db:
            new_log = PermintaanMentoring(
                user_id_telegram=user_id,
                nama_mahasiswa=message.from_user.full_name,
                alasan=message.text,
                status_ai=log_status,
                analisis_ai=ai_response
            )
            db.add(new_log)
            db.commit()

    except Exception as e:
        logging.error(f"Error AI: {e}")
        await message.answer("⚠️ Maaf, sistem AI sedang mengalami gangguan.")
    finally:
        await state.clear()

# --- HANDLER FAQ ---
@dp.message(F.text)
async def handle_faq(message: types.Message):
    if message.text.startswith("/"): return

    with SessionLocal() as db:
        # ✅ Ambil semua data agar AI punya konteks lengkap
        faqs = db.query(FAQ).all()
        lombas = db.query(Lomba).all()
        mentors = db.query(Mentor).all()
    
    # ✅ Gabungkan data menjadi satu Knowledge Base (KB)
    kb_faq = "\n".join([f"Q: {f.pertanyaan}\nA: {f.jawaban}" for f in faqs])
    kb_lomba = "\n".join([f"- {l.nama_lomba} ({l.kategori}): {l.deskripsi}. Deadline: {l.deadline}" for l in lombas])
    kb_mentor = "\n".join([f"- {m.nama_mentor} (Ahli: {m.spesialisasi})" for m in mentors])
    
    # ✅ System Prompt yang lebih instruktif
    sys_prompt = (
        "Anda adalah asisten cerdas Himpunan Mahasiswa SI. "
        "Tugas Anda menjawab pertanyaan berdasarkan data di bawah ini. "
        "Jika ada pertanyaan tentang topik tertentu (misal: AI/ML), cari yang relevan di daftar lomba.\n\n"
        f"[DATA FAQ]\n{kb_faq}\n\n"
        f"[DATA LOMBA]\n{kb_lomba}\n\n"
        f"[DATA MENTOR]\n{kb_mentor}\n\n"
        "Jawablah dengan ramah dan informatif."
    )
    
    try:
        res = await groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_prompt}, 
                {"role": "user", "content": message.text}
            ],
            model=GROQ_MODEL, # Menggunakan variabel model dari .env
        )
        await message.answer(res.choices[0].message.content)
    except Exception as e:
        logging.error(f"Error FAQ: {e}")
        await message.answer("Maaf, saya sedang kesulitan memproses informasi tersebut.")

# Tambahkan fungsi health check sederhana
async def handle_health_check(request):
    return web.Response(text="Bot is running!")

# --- CONFIG WEBHOOK ---
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST") 
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Setup web server untuk Webhook
app = web.Application()

# ... (Kode di atasnya tetap sama) ...

async def on_startup(bot: Bot):
    # ✅ Tambahkan drop_pending_updates=True agar pesan lama yang nyangkut dihapus
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    logging.warning("Shutting down..")
    await bot.delete_webhook()

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Inisialisasi Scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_deadlines, 'cron', hour=8, minute=0)
    scheduler.start()

    # Daftarkan startup/shutdown actions
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Hubungkan Aiogram dengan Aiohttp
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # ✅ DAFTARKAN HEALTH CHECK DI SINI
    app.router.add_get("/", handle_health_check)

    # Jalankan Web Server
    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    logging.info(f"Starting web application on port {port}...")
    await site.start()

    # Biarkan server terus berjalan
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")