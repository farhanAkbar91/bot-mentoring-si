import gspread
from google.oauth2.service_account import Credentials # Menggunakan library yang didukung Google
from database import SessionLocal, Lomba, Mentor, FAQ

# Setup Google Sheets API
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open("data bot-aa")

def sync_data():
    db = SessionLocal()

    try:
        # --- Sinkronisasi Tabel Lomba ---
        print("Sinkronisasi data Lomba...")
        lomba_sheet = sheet.worksheet("Lomba").get_all_records()

        # Hapus Data Lama
        db.query(Lomba).delete()

        for row in lomba_sheet:
            new_lomba = Lomba(
                nama_lomba=row['Nama Lomba'],
                kategori=row['Kategori'],
                deskripsi=row['Deskripsi'],
                deadline=str(row['Deadline']),
                link_info=row['Link Info']
            )
            db.add(new_lomba)

        # --- Sinkronisasi Tabel Mentor ---
        print("Sinkronisasi data Mentor...")
        mentor_sheet = sheet.worksheet("Mentor").get_all_records()
        
        db.query(Mentor).delete()
        
        for row in mentor_sheet:
            new_mentor = Mentor(
                nama_mentor=row['Nama Mentor'],
                spesialisasi=row['Spesialisasi'],
                kontak=str(row['Kontak'])
            )
            db.add(new_mentor)

        # --- Sinkronisasi Tabel FAQ ---
        print("Sinkronisasi data FAQ...")
        faq_sheet = sheet.worksheet("FAQ").get_all_records()
        
        db.query(FAQ).delete()
        
        for row in faq_sheet:
            new_faq = FAQ(
                pertanyaan=row['Pertanyaan'],
                jawaban=row['Jawaban']
            )
            db.add(new_faq)

        db.commit()
        print("Sinkronisasi Berhasil!")
        return True
        
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        db.rollback()
        return False

    finally:
        db.close()

if __name__ == "__main__":
    sync_data()