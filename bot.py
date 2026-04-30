import os
import logging
import asyncio
import re
import traceback
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from database import SessionLocal, Lomba, Mentor, PermintaanMentoring, User, FAQ
from groq import AsyncGroq
from groq import APIConnectionError, APITimeoutError, RateLimitError, APIStatusError
from dotenv import load_dotenv
from sync_sheets import sync_data
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

load_dotenv()

# --- CONFIG ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
ADMIN_ID = os.getenv("ADMIN_ID")

# Retry config
GROQ_MAX_RETRIES = 3
GROQ_RETRY_DELAY = 2.0   # detik, di-double setiap retry (exponential backoff)
GROQ_TIMEOUT = 20.0       # detik

bot = Bot(token=TOKEN)
dp = Dispatcher()
groq_client = AsyncGroq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT)

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

# ─────────────────────────────────────────────────────────────
# TEMPLATE JAWABAN STANDAR
# ─────────────────────────────────────────────────────────────
TEMPLATE_OUT_OF_CONTEXT = (
    "Maaf, pertanyaan tersebut berada di luar topik yang bisa saya bantu 🙏\n\n"
    "Saya adalah asisten khusus untuk mahasiswa Sistem Informasi yang bisa membantu soal:\n"
    "• 🏆 Informasi & deadline lomba\n"
    "• 👨‍🏫 Permintaan sesi mentoring\n"
    "• ❓ FAQ seputar himpunan & akademik\n\n"
    "Silakan gunakan menu di bawah atau ketik pertanyaan yang sesuai topik di atas."
)

TEMPLATE_AI_ERROR = (
    "⚠️ Maaf, sistem AI sedang tidak dapat diakses saat ini.\n\n"
    "Kamu tetap bisa menggunakan fitur berikut:\n"
    "• Ketuk *🏆 Info Lomba* untuk melihat lomba aktif\n"
    "• Ketuk *👨‍🏫 Minta Mentoring* untuk menghubungi mentor\n"
    "• Ketuk *❓ FAQ* untuk pertanyaan umum\n\n"
    "Coba lagi beberapa saat kemudian ya 🙂"
)

TEMPLATE_AI_RATE_LIMIT = (
    "⏳ Sistem sedang sibuk, mohon coba lagi dalam beberapa menit.\n\n"
    "Sementara itu, kamu bisa menggunakan menu utama di bawah."
)

TEMPLATE_DB_ERROR = (
    "⚠️ Maaf, terjadi gangguan koneksi ke database.\n"
    "Silakan coba kembali dalam beberapa saat."
)

# ─────────────────────────────────────────────────────────────
# HELPER: GROQ API dengan Retry + Exponential Backoff
# ─────────────────────────────────────────────────────────────
async def groq_chat_with_retry(messages: list, model: str = GROQ_MODEL):
    """
    Memanggil Groq API dengan mekanisme retry otomatis.
    Return: string konten jawaban, "__RATE_LIMITED__", atau None jika semua percobaan gagal.
    """
    delay = GROQ_RETRY_DELAY
    for attempt in range(1, GROQ_MAX_RETRIES + 1):
        try:
            completion = await groq_client.chat.completions.create(
                messages=messages,
                model=model,
            )
            return completion.choices[0].message.content

        except RateLimitError as e:
            logging.warning(f"[Groq] Rate limit (attempt {attempt}/{GROQ_MAX_RETRIES}): {e}")
            if attempt < GROQ_MAX_RETRIES:
                await asyncio.sleep(delay * 2)
                delay *= 2
            else:
                logging.error("[Groq] Rate limit: semua retry habis.")
                return "__RATE_LIMITED__"

        except (APIConnectionError, APITimeoutError) as e:
            logging.warning(f"[Groq] Koneksi/Timeout (attempt {attempt}/{GROQ_MAX_RETRIES}): {e}")
            if attempt < GROQ_MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logging.error("[Groq] Koneksi gagal: semua retry habis.")
                return None

        except APIStatusError as e:
            if e.status_code >= 500:
                logging.warning(f"[Groq] Server error {e.status_code} (attempt {attempt}/{GROQ_MAX_RETRIES}): {e}")
                if attempt < GROQ_MAX_RETRIES:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    logging.error("[Groq] Server error: semua retry habis.")
                    return None
            else:
                logging.error(f"[Groq] Client error {e.status_code}: {e}")
                return None

        except Exception as e:
            logging.error(f"[Groq] Unexpected error (attempt {attempt}/{GROQ_MAX_RETRIES}): {e}\n{traceback.format_exc()}")
            if attempt < GROQ_MAX_RETRIES:
                await asyncio.sleep(delay)
                delay *= 2
            else:
                return None

    return None

# --- HANDLERS ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.telegram_id == str(message.from_user.id)).first()

        if not user:
            await state.set_state(BotStates.waiting_for_nim)
            await message.answer(
                f"Halo {message.from_user.first_name}! 👋\n\n"
                "Silakan masukkan **NIM** Anda (khusus mahasiswa SI) untuk verifikasi:"
            )
        else:
            await message.answer(
                f"Selamat datang kembali, {user.nama}! Ada yang bisa dibantu?",
                reply_markup=main_menu()
            )
            
    except SQLAlchemyError as e:
        logging.error(f"[DB] Error pada /start: {e}")
        await message.answer(TEMPLATE_DB_ERROR)

@dp.message(Command("sync"))
async def cmd_sync(message: types.Message):
    admin_env = os.getenv("ADMIN_ID", "")
    daftar_admin = [admin.strip() for admin in admin_env.split(",")]

    if str(message.from_user.id) not in daftar_admin:
        await message.answer("⚠️ Maaf, perintah ini khusus untuk akses Admin/Staf HIMA.")
        return

    m = await message.answer("🔄 Sedang menyinkronkan data Lomba, Mentor, dan FAQ dari Google Sheets...")
    
    try:
        hasil = sync_data()
        if hasil:
            await m.edit_text("✅ Sinkronisasi berhasil! Database kini menggunakan data terbaru.")
        else:
            await m.edit_text("❌ Sinkronisasi gagal. Cek log server untuk detailnya.")
    except Exception as e:
        logging.error(f"[Sync] Gagal sync via command: {e}")
        await m.edit_text(f"❌ Terjadi kesalahan sistem saat sinkronisasi:\n`{str(e)[:200]}`", parse_mode="Markdown")

@dp.message(BotStates.waiting_for_nim)
async def process_nim(message: types.Message, state: FSMContext):
    nim = message.text.strip()
    if re.match(r"^1872[3-6]\d{4}$", nim):
        try:
            with SessionLocal() as db:
                new_user = User(
                    telegram_id=str(message.from_user.id),
                    nim=nim,
                    nama=message.from_user.full_name,
                    is_verified=1
                )
                db.add(new_user)
                db.commit()
            await state.clear()
            await message.answer("✅ Verifikasi Berhasil!", reply_markup=main_menu())
        except SQLAlchemyError as e:
            logging.error(f"[DB] Gagal menyimpan user baru: {e}")
            await message.answer(TEMPLATE_DB_ERROR)
    else:
        await message.answer("❌ Format NIM salah. Pastikan Anda mahasiswa Sistem Informasi.")

@dp.callback_query(F.data == "list_lomba")
async def show_lomba(callback: types.CallbackQuery):
    try:
        with SessionLocal() as db:
            semua_lomba = db.query(Lomba).all()
    except SQLAlchemyError as e:
        logging.error(f"[DB] Gagal ambil data lomba: {e}")
        await callback.message.answer(TEMPLATE_DB_ERROR)
        await callback.answer()
        return
        
    if not semua_lomba:
        await callback.message.answer("Belum ada data lomba bulan ini.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for l in semua_lomba:
        builder.row(types.InlineKeyboardButton(
            text=f"🏆 {l.nama_lomba}",
            callback_data=f"detail_lomba_{l.id}"
        ))
    
    await callback.message.answer(
        "📅 **DAFTAR LOMBA AKTIF**\nSilakan pilih lomba untuk melihat detail lebih lanjut:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("detail_lomba_"))
async def show_lomba_detail(callback: types.CallbackQuery):
    lomba_id = int(callback.data.split("_")[-1])
    
    try:
        with SessionLocal() as db:
            l = db.query(Lomba).filter(Lomba.id == lomba_id).first()
    except SQLAlchemyError as e:
        logging.error(f"[DB] Gagal ambil detail lomba {lomba_id}: {e}")
        await callback.answer(TEMPLATE_DB_ERROR[:200], show_alert=True)
        return
        
    if not l:
        await callback.answer("Data lomba tidak ditemukan.")
        return

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
    try:
        with SessionLocal() as db:
            faqs = db.query(FAQ).all()
    except SQLAlchemyError as e:
        logging.error(f"[DB] Gagal ambil data FAQ: {e}")
        await callback.message.answer(TEMPLATE_DB_ERROR)
        await callback.answer()
        return
        
    if not faqs:
        await callback.message.answer("Database FAQ saat ini masih kosong.")
        await callback.answer()
        return

    text = "❓ **FREQUENTLY ASKED QUESTIONS** ❓\n\n"
    for f in faqs:
        text += f"📌 **{f.pertanyaan}**\n└ {f.jawaban}\n\n"
    
    text += "💡 _Anda juga bisa langsung mengetik pertanyaan spesifik untuk dijawab oleh AI._"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "req_mentor")
async def start_mentoring(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_reason)
    
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
    
    try:
        with SessionLocal() as db:
            semua_lomba = db.query(Lomba).all()
            users = db.query(User).filter(User.is_verified == 1).all()
    except SQLAlchemyError as e:
        logging.error(f"[Reminder] Gagal ambil data dari DB: {e}")
        return

    upcoming_lomba = []
    for l in semua_lomba:
        try:
            deadline_date = datetime.strptime(l.deadline, "%Y-%m-%d")
            if today <= deadline_date <= three_days_later:
                upcoming_lomba.append(l)
        except ValueError:
            continue

    if upcoming_lomba and users:
        for user in users:
            msg = "🔔 **PENGINGAT DEADLINE LOMBA** 🔔\n\n"
            for l in upcoming_lomba:
                msg += f"⚠️ **{l.nama_lomba}**\n📅 Deadline: {l.deadline}\n"
            msg += "\nSegera selesaikan progres Anda dan ajukan mentoring jika butuh bantuan!"
            try:
                await bot.send_message(user.telegram_id, msg, parse_mode="Markdown")
            except Exception as e:
                logging.error(f"[Reminder] Gagal kirim ke {user.telegram_id}: {e}")

# --- LOGIKA GATEKEEPER & MENTOR ---
@dp.message(BotStates.waiting_for_reason)
async def process_mentoring_reason(message: types.Message, state: FSMContext):
    user_id = str(message.from_user.id)
    
    # Anti-Spam check
    try:
        with SessionLocal() as db:
            last_req = (
                db.query(PermintaanMentoring)
                .filter_by(user_id_telegram=user_id)
                .order_by(PermintaanMentoring.timestamp.desc())
                .first()
            )
            if last_req and (datetime.utcnow() - last_req.timestamp < timedelta(minutes=30)):
                await message.answer("⚠️ Mohon tunggu 30 menit sebelum mengajukan lagi.")
                return
    except SQLAlchemyError as e:
        logging.error(f"[DB] Gagal cek anti-spam: {e}")
        await message.answer(TEMPLATE_DB_ERROR)
        return

    if len(message.text) < 30:
        await message.answer("⚠️ Alasan terlalu singkat (min. 30 karakter).")
        return

    thinking_msg = await message.answer("🔍 Mengevaluasi alasan dengan AI...")

    # Evaluasi dengan AI + retry
    ai_response = await groq_chat_with_retry(
        messages=[
            {
                "role": "system",
                "content": (
                    "Kamu adalah Koordinator Lomba HIMA Sistem Informasi. "
                    "Nilailah alasan permintaan mentoring berikut. "
                    "Kriteria utama: mahasiswa harus menunjukkan progres minimal 50% "
                    "(ada tim, ada lomba yang dituju, ada draf/ide). "
                    "Balas dengan format: [SETUJU] atau [TOLAK], diikuti alasan singkat."
                )
            },
            {"role": "user", "content": message.text}
        ]
    )

    # Tangani kegagalan AI
    if ai_response is None:
        await thinking_msg.delete()
        await message.answer(TEMPLATE_AI_ERROR, reply_markup=main_menu())
        await state.clear()
        return

    if ai_response == "__RATE_LIMITED__":
        await thinking_msg.delete()
        await message.answer(TEMPLATE_AI_RATE_LIMIT, reply_markup=main_menu())
        await state.clear()
        return

    log_status = "TOLAK"
    if "[SETUJU]" in ai_response.upper():
        log_status = "SETUJU"
        
        # Kategorisasi dengan AI + retry
        cat_response = await groq_chat_with_retry(
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Dari teks berikut, tentukan kategori lomba yang paling sesuai.\n"
                        f"Teks: '{message.text}'\n"
                        f"Pilih SATU dari: UI/UX, WEB, ESAI, DATA\n"
                        f"Balas hanya dengan 1 kata kategorinya saja."
                    )
                }
            ]
        )

        if cat_response and cat_response != "__RATE_LIMITED__":
            raw_cat = cat_response.strip().upper()
            kategori_valid = ["UI/UX", "WEB", "ESAI", "DATA"]
            cat = next((k for k in kategori_valid if k in raw_cat), "WEB")
        else:
            cat = "WEB"
            logging.warning("[Mentoring] Gagal kategorisasi AI, gunakan default 'WEB'")

        try:
            with SessionLocal() as db:
                mentor = (
                    db.query(Mentor).filter(Mentor.spesialisasi.ilike(f"%{cat}%")).first()
                    or db.query(Mentor).first()
                )
            
            if mentor:
                res_text = (
                    f"✅ **DISETUJUI**\n\n{ai_response}\n\n"
                    f"Hubungi: **{mentor.nama_mentor}**\n"
                    f"WA: https://wa.me/{mentor.kontak}"
                )
            else:
                res_text = (
                    f"✅ **DISETUJUI**\n\n{ai_response}\n\n"
                    "Silakan hubungi admin HIMA untuk mendapatkan mentor yang tersedia."
                )
        except SQLAlchemyError as e:
            logging.error(f"[DB] Gagal ambil mentor: {e}")
            res_text = (
                f"✅ **DISETUJUI**\n\n{ai_response}\n\n"
                "⚠️ Data mentor tidak dapat diambil saat ini. Hubungi admin HIMA."
            )

        await thinking_msg.delete()
        await message.answer(res_text, parse_mode="Markdown")
    else:
        await thinking_msg.delete()
        await message.answer(f"❌ **DITOLAK**\n\n{ai_response}", parse_mode="Markdown")

    # Simpan Log — jangan gagalkan flow utama jika log gagal disimpan
    try:
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
    except SQLAlchemyError as e:
        logging.error(f"[DB] Gagal simpan log mentoring: {e}")

    await state.clear()

# ─────────────────────────────────────────────────────────────
# HANDLER FAQ — dengan instruksi out-of-context yang tegas
# ─────────────────────────────────────────────────────────────
@dp.message(F.text)
async def handle_faq(message: types.Message):
    if message.text.startswith("/"): return

    try:
        with SessionLocal() as db:
            faqs = db.query(FAQ).all()
            lombas = db.query(Lomba).all()
            mentors = db.query(Mentor).all()
    except SQLAlchemyError as e:
        logging.error(f"[DB] Gagal ambil knowledge base: {e}")
        await message.answer(TEMPLATE_DB_ERROR)
        return
    
    kb_faq = "\n".join([f"Q: {f.pertanyaan}\nA: {f.jawaban}" for f in faqs])
    kb_lomba = "\n".join([
        f"- {l.nama_lomba} ({l.kategori}): {l.deskripsi}. Deadline: {l.deadline}"
        for l in lombas
    ])
    kb_mentor = "\n".join([f"- {m.nama_mentor} (Ahli: {m.spesialisasi})" for m in mentors])
    
    # System prompt yang lebih ketat dan konsisten
    sys_prompt = (
        "Kamu adalah asisten resmi Himpunan Mahasiswa Sistem Informasi (HIMA SI). "
        "Tugasmu HANYA menjawab pertanyaan seputar topik berikut:\n"
        "1. Informasi lomba yang ada di DATA LOMBA\n"
        "2. Informasi mentor yang ada di DATA MENTOR\n"
        "3. Pertanyaan umum yang ada di DATA FAQ\n"
        "4. Cara mengajukan mentoring\n"
        "5. Info umum tentang HIMA SI\n\n"
        "ATURAN PENTING:\n"
        "- Jika pertanyaan TIDAK berkaitan dengan topik di atas (misalnya: cuaca, politik, "
        "matematika umum, resep makanan, atau hal pribadi), balas PERSIS dengan token ini saja:\n"
        "__OUT_OF_CONTEXT__\n"
        "- Jangan tambahkan penjelasan apapun selain token tersebut untuk pertanyaan di luar topik.\n"
        "- Jika informasi ada tapi tidak lengkap, sampaikan yang ada dan arahkan ke admin HIMA.\n"
        "- Jawablah dengan ramah, singkat, dan informatif.\n\n"
        f"[DATA FAQ]\n{kb_faq or 'Belum ada data FAQ.'}\n\n"
        f"[DATA LOMBA]\n{kb_lomba or 'Belum ada data lomba aktif.'}\n\n"
        f"[DATA MENTOR]\n{kb_mentor or 'Belum ada data mentor.'}"
    )
    
    ai_response = await groq_chat_with_retry(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": message.text}
        ]
    )

    if ai_response is None:
        await message.answer(TEMPLATE_AI_ERROR, reply_markup=main_menu())
        return

    if ai_response == "__RATE_LIMITED__":
        await message.answer(TEMPLATE_AI_RATE_LIMIT, reply_markup=main_menu())
        return

    if "__OUT_OF_CONTEXT__" in ai_response:
        await message.answer(TEMPLATE_OUT_OF_CONTEXT, reply_markup=main_menu())
        return

    await message.answer(ai_response)

# Health check
async def handle_health_check(request):
    return web.Response(text="Bot is running!")

# --- CONFIG WEBHOOK ---
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

app = web.Application()

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Webhook set to {WEBHOOK_URL}")

async def on_shutdown(bot: Bot):
    logging.warning("Shutting down..")
    await bot.delete_webhook()

async def main():
    logging.basicConfig(level=logging.INFO)
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_deadlines, 'cron', hour=8, minute=0)
    scheduler.start()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        handle_in_background=True,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    app.router.add_get("/", handle_health_check)

    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    
    logging.info(f"Starting web application on port {port}...")
    await site.start()

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
