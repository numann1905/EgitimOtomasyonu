from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import sqlite3
import bcrypt


app = Flask(__name__)


# --- Veritabanı ayarları ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'egitimler.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "gizli_anahtar_v2"

db = SQLAlchemy(app)

# --- Veritabanı modelleri ---
class Egitim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50))
    kontenjan = db.Column(db.String(50))
    fiyat = db.Column(db.Integer)

class Kayit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_soyad = db.Column(db.String(100), nullable=False)
    tc_no = db.Column(db.String(11))
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    notlar = db.Column(db.Text)

    egitim_id = db.Column(db.Integer, db.ForeignKey('egitim.id'), nullable=False)
    egitim = db.relationship('Egitim', backref=db.backref('kayitlar', lazy=True))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False) 
    role = db.Column(db.String(20), default='user')


# --- Ana sayfa ---
@app.route('/')
def index():
    egitimler = Egitim.query.all()
    return render_template('index.html', egitimler=egitimler)


# --- Ogrenci girisi ---
@app.route('/ogrenci_giris', methods=['GET', 'POST'])
def ogrenci_giris():
    hata = None

    if request.method == 'POST':
        tc_no = request.form.get('tc_no', '').strip()
        email = request.form.get('email', '').strip().lower()

        kayit = Kayit.query.filter_by(tc_no=tc_no).first()
        if kayit and (kayit.email or '').strip().lower() == email:
            session['student_id'] = kayit.id
            session['student_name'] = kayit.ad_soyad
            flash("Ogrenci paneline hos geldiniz.", "success")
            return redirect(url_for('ogrenci_panel'))

        hata = "Kayit bulunamadi. TC / ogrenci no ve e-posta bilgilerinizi kontrol edin."

    return render_template('ogrenci_giris.html', hata=hata)


@app.route('/ogrenci_panel')
def ogrenci_panel():
    student_id = session.get('student_id')
    if not student_id:
        return redirect(url_for('ogrenci_giris'))

    kayit = Kayit.query.get_or_404(student_id)
    return render_template('ogrenci_panel.html', kayit=kayit)


# --- Chatbot ---
@app.route('/chatbot')
def chatbot():
    egitimler = Egitim.query.all()
    return render_template('chatbot.html', egitimler=egitimler)


@app.route('/chatbot/mesaj', methods=['POST'])
def chatbot_mesaj():
    mesaj = (request.json or {}).get('mesaj', '').strip()
    mesaj_kucuk = mesaj.lower()

    if not mesaj:
        return jsonify({'cevap': 'Size yardimci olabilmem icin kisa bir soru yazabilirsiniz.'})

    egitimler = Egitim.query.all()

    if any(kelime in mesaj_kucuk for kelime in ['egitim', 'kurs', 'program', 'liste']):
        if not egitimler:
            cevap = 'Su anda listelenecek aktif egitim bulunmuyor.'
        else:
            satirlar = [
                f"{e.baslik} - {e.kategori or 'Genel'} - Kontenjan: {e.kontenjan or '-'} - Ucret: {e.fiyat} TL"
                for e in egitimler
            ]
            cevap = 'Aktif egitimler:\n' + '\n'.join(satirlar)
    elif any(kelime in mesaj_kucuk for kelime in ['kayit', 'basvuru', 'katil']):
        cevap = 'Kayit olmak icin ana sayfadaki egitim kartindan "Kayit Ol" butonuna tiklayip formu doldurabilirsiniz.'
    elif any(kelime in mesaj_kucuk for kelime in ['ucret', 'fiyat', 'tl', 'para']):
        cevap = 'Ucret bilgisi her egitim kartinda ayri ayri gosterilir. Isterseniz "egitimleri listele" yazarak tum ucretleri gorebilirsiniz.'
    elif any(kelime in mesaj_kucuk for kelime in ['kontenjan', 'yer']):
        cevap = 'Kontenjan bilgisi egitim kartlarinda yer alir. Guncel kontenjanlari listelemek icin "egitimleri listele" yazabilirsiniz.'
    elif any(kelime in mesaj_kucuk for kelime in ['ogrenci', 'giris', 'panel']):
        cevap = 'Ogrenci girisi sayfasindan TC / ogrenci no ve e-posta bilginizle kayitli egitiminizi gorebilirsiniz.'
    elif any(kelime in mesaj_kucuk for kelime in ['merhaba', 'selam', 'hello']):
        cevap = 'Merhaba, egitimler, kayit, ucret ve ogrenci girisi hakkinda yardimci olabilirim.'
    else:
        cevap = 'Bunu tam anlayamadim. "Egitimleri listele", "Kayit nasil yapilir?", "Ucretler nedir?" veya "Ogrenci girisi" diye sorabilirsiniz.'

    return jsonify({'cevap': cevap})

# --- Kayıt sayfası (DOĞRULAMA EKLENMİŞ HALİ) ---
@app.route('/kayit_ol/<int:egitim_id>', methods=['GET', 'POST'])
def kayit_ol(egitim_id):
    egitim = Egitim.query.get_or_404(egitim_id)

    if request.method == 'POST':
        ad_soyad = request.form['ad_soyad'].strip()
        tc_no = request.form.get('tc_no', '').strip()
        telefon = request.form.get('telefon', '').strip()
        email = request.form.get('email', '').strip()
        notlar = request.form.get('notlar', '').strip()

        # --- DOĞRULAMALAR (Kritik Kısım) ---
        
        # 1. Ad Soyad kontrolü: Sadece harf ve boşluk olmalı (Rakam içermemeli)
        # replace(' ', '') ile boşlukları temizleyip harf kontrolü yapıyoruz
        if not ad_soyad.replace(' ', '').isalpha():
            flash("Ad Soyad sadece harflerden oluşmalıdır.", "danger")
            return render_template('kayit.html', egitim=egitim)

        # 2. TC Kimlik No kontrolü: Sadece rakam ve tam 11 hane olmalı
        if not tc_no.isdigit() or len(tc_no) != 11:
            flash("TC Kimlik No tam 11 haneli bir sayı olmalıdır.", "danger")
            return render_template('kayit.html', egitim=egitim)

        # 3. Telefon kontrolü: Sadece rakam olmalı
        if not telefon.isdigit():
            flash("Telefon numarası sadece rakamlardan oluşmalıdır.", "danger")
            return render_template('kayit.html', egitim=egitim)

        # Eğer her şey tamamsa kaydı yap
        try:
            yeni_kayit = Kayit(
                ad_soyad=ad_soyad,
                tc_no=tc_no,
                telefon=telefon,
                email=email,
                notlar=notlar,
                egitim=egitim
            )
            db.session.add(yeni_kayit)
            db.session.commit()
            flash("Kaydınız başarıyla alındı!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash("Kayıt sırasında teknik bir hata oluştu.", "danger")
            return render_template('kayit.html', egitim=egitim)

    return render_template('kayit.html', egitim=egitim)


# --- Giriş ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    hata = None

    if request.method == 'POST':
        girilen_username = request.form['kullanici_adi']
        girilen_sifre = request.form['sifre']

        user = User.query.filter_by(username=girilen_username).first()

        if user:
            if bcrypt.checkpw(girilen_sifre.encode('utf-8'), user.password_hash):
                session['user_id'] = user.id
                session['username'] = user.username
                session['role'] = user.role
                
                if user.role == 'admin':
                    return redirect(url_for('admin'))
                else:
                    return redirect(url_for('index'))
            else:
                hata = "Şifre hatalı."
        else:
            hata = "Kullanıcı bulunamadı."

    return render_template('login.html', hata=hata)

# --- Admin paneli ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        baslik = request.form.get('baslik', '').strip()
        kategori = request.form.get('kategori', '').strip()
        kontenjan = request.form.get('kontenjan', '').strip()
        fiyat_raw = request.form.get('fiyat', '').strip()

        # Basit doğrulama
        if not baslik:
            flash("Başlık zorunlu.", "danger")
            return redirect(url_for('admin'))

        try:
            if fiyat_raw == '':
                raise ValueError("Fiyat boş olamaz.")
            fiyat = int(fiyat_raw)
        except ValueError:
            flash("Fiyat sayısal olmalı.", "danger")
            return redirect(url_for('admin'))

        try:
            yeni_egitim = Egitim(
                baslik=baslik,
                kategori=kategori or None,
                kontenjan=kontenjan or None,
                fiyat=fiyat
            )
            db.session.add(yeni_egitim)
            db.session.commit()
            flash("Eğitim eklendi.", "success")
        except Exception as e:
            db.session.rollback()
            # Konsolda görebilmen için:
            print("ADMIN EKLE HATASI:", e)
            flash("Bir hata oluştu, konsola bakınız.", "danger")

        return redirect(url_for('admin'))

    egitimler = Egitim.query.all()
    return render_template('admin.html', egitimler=egitimler)



# --- Eğitim detayları ---
@app.route('/egitim_detay/<int:egitim_id>')
def egitim_detay(egitim_id):
    egitim = Egitim.query.get_or_404(egitim_id)
    kayitlar = Kayit.query.filter_by(egitim_id=egitim.id).all()
    return render_template('egitim_detay.html', egitim=egitim, kayitlar=kayitlar)

# --- Eğitim silme ---
@app.route('/egitim_sil/<int:egitim_id>', methods=['POST', 'GET'])
def egitim_sil(egitim_id):
    # GET ile gelinirse kibarca admin sayfasına dön (405 ekranı yerine)
    if request.method == 'GET':
        flash('Silme işlemi yalnızca buton üzerinden yapılabilir.', 'warning')
        return redirect(url_for('admin'))

    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    egitim = Egitim.query.get_or_404(egitim_id)
    try:
        # Eğitime bağlı kayıtlar varsa önce onları sil
        for k in egitim.kayitlar:
            db.session.delete(k)

        db.session.delete(egitim)
        db.session.commit()
        flash("Eğitim silindi.", "success")
    except Exception as e:
        db.session.rollback()
        print("ADMIN SİL HATASI:", e)
        flash("Silme sırasında bir hata oluştu.", "danger")

    return redirect(url_for('admin'))


# --- Çıkış ---
@app.route('/logout')
def logout():
    session.clear()  
    flash("Başarıyla çıkış yapıldı.", "info")
    return redirect(url_for('index'))
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)    
