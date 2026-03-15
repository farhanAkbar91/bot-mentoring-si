from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi DB Lokal
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL) 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    nim = Column(String)
    nama = Column(String)
    is_verified = Column(Integer, default=0) # 0: Belum, 1: Terverifikasi

class FAQ(Base):
    __tablename__ = "faq"
    id = Column(Integer, primary_key=True, index=True)
    pertanyaan = Column(String)
    jawaban = Column(Text)

class Lomba(Base):
    __tablename__ = "lomba"
    id = Column(Integer, primary_key=True, index=True)
    nama_lomba = Column(String, index=True)
    kategori = Column(String) # Contoh UI/UX, Web Dev, Esai, dll
    deskripsi = Column(Text)
    deadline = Column(String)
    link_info = Column(String)

class Mentor(Base):
    __tablename__ = "mentor"
    id = Column(Integer, primary_key=True, index=True)
    nama_mentor = Column(String)
    spesialisasi = Column(String) # Bidang keahlian
    kontak = Column(String) # Nomor WA atau ID Telegram

class PermintaanMentoring(Base):
    __tablename__ = "permintaan_mentoring"
    id = Column(Integer, primary_key=True, index=True)
    user_id_telegram = Column(String) # ID pengirim di Telegram
    nama_mahasiswa = Column(String)
    alasan = Column(Text)
    status_ai = Column(String) # 'SETUJU' atau 'TOLAK'
    analisis_ai = Column(Text) # Penjelasan mengapa AI setuju/menolak
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# Membuat tabel secara otomatis
def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database dan Tabel berhasil dibuat!")