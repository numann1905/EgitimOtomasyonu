import sqlite3
import os

def veritabani_olustur():
    # Veritabanı dosyasını proje klasörüne kaydeder
    db_yolu = os.path.join(os.path.dirname(__file__), '..', 'egitimler.db')
    conn = sqlite3.connect(db_yolu)
    cursor = conn.cursor()

    # Eğitim tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS egitim (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        baslik TEXT NOT NULL,
                        kategori TEXT,
                        kontenjan TEXT,
                        fiyat INTEGER 
                      )''')

    # Kayıt tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS kayit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ad_soyad TEXT NOT NULL,
                        egitim_id INTEGER NOT NULL,
                        FOREIGN KEY (egitim_id) REFERENCES egitim(id)
                      )''')

    # Kullanıcı tablosu (admin bilgileri buraya)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT DEFAULT 'user'
                      )''')

    conn.commit()
    conn.close()
    print("✅ Veritabanı ve tablolar oluşturuldu.")

# Eğer bu dosya direkt çalıştırılırsa:
if __name__ == "__main__":
    veritabani_olustur()
