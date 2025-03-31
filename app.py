import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supergeheimekey")

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect('aanmeldingen.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS aanmeldingen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            datum TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            aangemaakt_op TEXT
        )
    ''')
    conn.commit()
    conn.close()

# === STAP 1: LOGIN MET EMAIL ===
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
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

    vandaag = datetime.today()
    weekdagen = [(vandaag + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    if request.method == 'POST':
        geselecteerde_dagen = request.form.getlist('datums')
        aangemaakt_op = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect('aanmeldingen.db')
        c = conn.cursor()
        for datum in geselecteerde_dagen:
            c.execute('''INSERT INTO aanmeldingen (email, datum, aangemaakt_op)
                         VALUES (?, ?, ?)''', (email, datum, aangemaakt_op))
        conn.commit()
        conn.close()
        return redirect('/mijn-aanmeldingen')

    return render_template('aanmelden.html', weekdagen=weekdagen, email=email)

# === STAP 3: OVERZICHT EIGEN AANMELDINGEN ===
@app.route('/mijn-aanmeldingen')
def mijn_aanmeldingen():
    email = session.get('email')
    if not email:
        return redirect('/')

    conn = sqlite3.connect('aanmeldingen.db')
    c = conn.cursor()
    c.execute('SELECT datum, status FROM aanmeldingen WHERE email=? ORDER BY datum', (email,))
    rows = c.fetchall()
    conn.close()

    return render_template('mijn_aanmeldingen.html', email=email, aanmeldingen=rows)

if __name__ == '__main__':
    app.run(debug=True)