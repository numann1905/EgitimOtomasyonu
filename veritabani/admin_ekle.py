import sqlite3
import bcrypt
import os

def admin_ekle(username, password):
    # ✅ Veritabanının tam yolunu göster
    db_path = os.path.join(os.path.dirname(__file__), '..', 'egitimler.db')
    db_path = os.path.abspath(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                       (username, password_hash))
        conn.commit()
        print(f"✅ '{username}' adlı admin başarıyla eklendi!")
    except sqlite3.OperationalError as e:
        print("⚠️ Tablo bulunamadı. Lütfen önce 'veritabani_olustur.py' dosyasını çalıştır.")
        print("Hata:", e)
    except sqlite3.IntegrityError:
        print("⚠️ Bu kullanıcı adı zaten mevcut.")
    finally:
        conn.close()

if __name__ == "__main__":
    admin_ekle("admin", "1234")


