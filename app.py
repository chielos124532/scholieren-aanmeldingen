import os
import sqlite3
import smtplib
from flask import Flask, render_template, request, redirect, url_for, session
from email.message import EmailMessage
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supergeheimekey")

GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect('aanmeldingen.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS aanmeldingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL COLLATE NOCASE,
            datum TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            aangemaakt_op TEXT
        )
    ''')
    conn.commit()
    conn.close()

# === EMAIL FUNCTIE ===
def stuur_bevestiging_email(email, datums):
    if not email:
        return

    inhoud = "Hallo,\n\nJe aanmelding is ontvangen voor de volgende dag(en):\n"
    for d in datums:
        inhoud += f"- {d}\n"
    inhoud += "\nJe ontvangt later nog een bevestiging met locatie en tijd.\n\nGroet,\nPlanningsteam"

    msg = EmailMessage()
    msg['Subject'] = '📋 Aanmelding ontvangen – Werken via Scholieren Aanmeldingen'
    msg['From'] = GMAIL_SENDER
    msg['To'] = email
    msg.set_content(inhoud)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_SENDER, GMAIL_PASSWORD)
        smtp.send_message(msg)

# === STAP 1: LOGIN MET EMAIL ===
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        session['email'] = email
        return redirect('/aanmelden')
    return render_template('login.html')

# === STAP 2: AANMELDEN VOOR MEERDERE DAGEN ===
@app.route('/aanmelden', methods=['GET', 'POST'])
def aanmelden():
    init_db()
    email = session.get('email')
    if not email:
        return redirect('/')

    email = email.lower()

    # Haal bestaande aanvragen van deze gebruiker op
    conn = sqlite3.connect('aanmeldingen.db')
    c = conn.cursor()
    c.execute('SELECT datum, status FROM aanmeldingen WHERE LOWER(email)=?', (email,))
    rows = c.fetchall()
    bestaande = {datum: status for datum, status in rows}

    if request.method == 'POST':
        datums_raw = request.form.get('datums', '')
        geselecteerde_dagen = [d.strip() for d in datums_raw.split(',') if d.strip()]
        aangemaakt_op = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        vandaag = datetime.today()
        huidige_maandag = vandaag - timedelta(days=vandaag.weekday())

        for datum in geselecteerde_dagen:
            try:
                datum_dt = datetime.strptime(datum, '%Y-%m-%d')
                datum_str = datum_dt.strftime('%Y-%m-%d')
                if datum_dt >= huidige_maandag and datum_str not in bestaande:
                    c.execute('''INSERT INTO aanmeldingen (email, datum, aangemaakt_op)
                                 VALUES (?, ?, ?)''', (email, datum_str, aangemaakt_op))
            except ValueError:
                continue
        conn.commit()
        conn.close()

        stuur_bevestiging_email(email, geselecteerde_dagen)

        return redirect('/mijn-aanmeldingen')

    conn.close()
    return render_template('aanmelden.html', email=email, bestaande=bestaande)

# === STAP 3: OVERZICHT EIGEN AANMELDINGEN ===
@app.route('/mijn-aanmeldingen')
def mijn_aanmeldingen():
    email = session.get('email')
    if not email:
        return redirect('/')

    email = email.lower()
    conn = sqlite3.connect('aanmeldingen.db')
    c = conn.cursor()
    c.execute('SELECT datum, status FROM aanmeldingen WHERE LOWER(email)=? ORDER BY datum', (email,))
    rows = c.fetchall()
    conn.close()

    return render_template('mijn_aanmeldingen.html', email=email, aanmeldingen=rows)

if __name__ == '__main__':
    app.run(debug=True)
