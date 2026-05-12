import sqlite3

# Veritabanına bağlan
conn = sqlite3.connect('egitimler.db')
cursor = conn.cursor()

# SADECE "goko" kaydını (ID: 10) hedefliyoruz
hedef_id = 10

try:
    # SQL komutu: id'si 10 olanı sil
    cursor.execute("DELETE FROM kayit WHERE id = ?", (hedef_id,))
    
    conn.commit()
    print(f"ID numarası {hedef_id} olan kayıt (goko) başarıyla silindi!")
    
except Exception as e:
    print("Bir hata oluştu:", e)
    
finally:
    conn.close()