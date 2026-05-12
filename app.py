from flask import Flask, render_template, request, redirect, url_for, session, flash
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

# --- Kayıt sayfası ---
@app.route('/kayit_ol/<int:egitim_id>', methods=['GET', 'POST'])
def kayit_ol(egitim_id):
    egitim = Egitim.query.get_or_404(egitim_id)

    if request.method == 'POST':
        ad_soyad = request.form['ad_soyad']
        tc_no = request.form.get('tc_no', '')
        telefon = request.form.get('telefon', '')
        email = request.form.get('email', '')
        notlar = request.form.get('notlar', '')

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
        return redirect(url_for('index'))

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