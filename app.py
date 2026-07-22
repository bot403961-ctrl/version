#!/usr/bin/env python3
# ============================================
#  TAKER SMS - Full Dashboard Web App
#  Flask + SQLite
# ============================================

import os
import random
import string
import hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

DB = "taker.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        telegram TEXT,
        password TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        balance REAL DEFAULT 0,
        total_earned REAL DEFAULT 0,
        total_withdrawn REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        number TEXT NOT NULL,
        prefix TEXT,
        country TEXT,
        status TEXT DEFAULT 'waiting',
        source TEXT DEFAULT 'web',
        otp_code TEXT,
        otp_message TEXT,
        app_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        method TEXT,
        account TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS console_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        number TEXT,
        prefix TEXT,
        message TEXT,
        app_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def query(sql, params=(), fetchone=False, fetchall=False):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(sql, params)
    if fetchone: result = c.fetchone()
    elif fetchall: result = c.fetchall()
    else: result = None
    conn.commit()
    conn.close()
    return result

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def generate_api_key():
    return 'TAKER-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=24))

def generate_number(prefix):
    return prefix + ''.join(random.choices(string.digits, k=6))

def generate_otp():
    return str(random.randint(100000, 999999))

def detect_app():
    return random.choice(['WhatsApp', 'Instagram', 'Facebook', 'Telegram', 'Google', 'TikTok', 'Microsoft', 'Netflix'])

def generate_otp_message(code, app):
    return random.choice([
        f"{code} is your {app} verification code.",
        f"<#> {code} is your {app} code. Don't share it.",
        f"Enter {code} on {app} to verify your account.",
    ])

# ============================================
@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data = request.json
    email = data.get('email', '').strip()
    username = data.get('username', '').strip()
    telegram = data.get('telegram', '').strip()
    password = data.get('password', '').strip()
    
    if not email or not username or not password:
        return jsonify({'error': 'All fields required'}), 400
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    api_key = generate_api_key()
    
    try:
        query("INSERT INTO users (email, username, telegram, password, api_key) VALUES (?, ?, ?, ?, ?)",
              (email, username, telegram, hashed, api_key))
        return jsonify({'success': True, 'message': 'Account created!'})
    except:
        return jsonify({'error': 'Email or username already exists'}), 400

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    user = query("SELECT id, email, username FROM users WHERE email=? AND password=?",
                 (email, hashed), fetchone=True)
    
    if user:
        session['user_id'] = user[0]
        session['email'] = user[1]
        session['username'] = user[2]
        return jsonify({'success': True})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    uid = session['user_id']
    today = datetime.now().strftime('%Y-%m-%d')
    
    u = query("SELECT balance, total_earned, total_withdrawn FROM users WHERE id=?", (uid,), fetchone=True)
    return jsonify({
        'today_numbers': query("SELECT COUNT(*) FROM numbers WHERE user_id=? AND date(created_at)=?", (uid, today), fetchone=True)[0],
        'today_otps': query("SELECT COUNT(*) FROM numbers WHERE user_id=? AND status='success' AND date(created_at)=?", (uid, today), fetchone=True)[0],
        'all_numbers': query("SELECT COUNT(*) FROM numbers WHERE user_id=?", (uid,), fetchone=True)[0],
        'active_numbers': query("SELECT COUNT(*) FROM numbers WHERE user_id=? AND status='success'", (uid,), fetchone=True)[0],
        'pending_numbers': query("SELECT COUNT(*) FROM numbers WHERE user_id=? AND status='waiting'", (uid,), fetchone=True)[0],
        'balance': u[0] if u else 0,
        'total_earned': u[1] if u else 0,
        'total_withdrawn': u[2] if u else 0,
    })

@app.route('/numbers')
@login_required
def numbers_page():
    return render_template('numbers.html')

@app.route('/api/numbers/generate', methods=['POST'])
@login_required
def generate_numbers():
    data = request.json
    prefix = data.get('prefix', '26134')
    qty = min(int(data.get('quantity', 1)), 10)
    uid = session['user_id']
    nums = []
    for _ in range(qty):
        n = generate_number(prefix)
        query("INSERT INTO numbers (user_id, number, prefix, country, source) VALUES (?,?,?,?,?)",
              (uid, n, prefix, 'Madagascar', 'web'))
        nums.append(n)
    return jsonify({'success': True, 'numbers': nums})

@app.route('/api/numbers/list')
@login_required
def list_numbers():
    rows = query("SELECT * FROM numbers WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                 (session['user_id'],), fetchall=True)
    cols = ['id','user_id','number','prefix','country','status','source','otp_code','otp_message','app_name','created_at']
    return jsonify({'numbers': [dict(zip(cols, r)) for r in rows] if rows else []})

@app.route('/api/numbers/generate-otp', methods=['POST'])
@login_required
def api_generate_otp():
    data = request.json
    nid = data.get('number_id')
    num = data.get('number')
    prefix = data.get('prefix', '26134')
    code = generate_otp()
    app_name = detect_app()
    msg = generate_otp_message(code, app_name)
    
    query("UPDATE numbers SET status='success', otp_code=?, otp_message=?, app_name=? WHERE id=?",
          (code, msg, app_name, nid))
    query("INSERT INTO console_logs (number, prefix, message, app_name) VALUES (?,?,?,?)",
          (num, prefix, msg, app_name))
    
    uid = session['user_id']
    query("UPDATE users SET balance=balance+0.05, total_earned=total_earned+0.05 WHERE id=?", (uid,))
    
    return jsonify({'success': True, 'code': code, 'message': msg, 'app': app_name})

@app.route('/api/numbers/delete', methods=['POST'])
@login_required
def delete_number():
    query("DELETE FROM numbers WHERE id=? AND user_id=?", (request.json.get('number_id'), session['user_id']))
    return jsonify({'success': True})

@app.route('/api/numbers/clear', methods=['POST'])
@login_required
def clear_numbers():
    query("DELETE FROM numbers WHERE user_id=?", (session['user_id'],))
    return jsonify({'success': True})

@app.route('/wallet')
@login_required
def wallet_page():
    return render_template('wallet.html')

@app.route('/api/wallet/info')
@login_required
def wallet_info():
    u = query("SELECT balance, total_earned, total_withdrawn, api_key FROM users WHERE id=?",
              (session['user_id'],), fetchone=True)
    return jsonify({
        'balance': u[0] or 0, 'total_earned': u[1] or 0,
        'total_withdrawn': u[2] or 0, 'api_key': u[3] or ''
    })

@app.route('/api/wallet/payout', methods=['POST'])
@login_required
def request_payout():
    d = request.json
    amt = float(d.get('amount', 0))
    uid = session['user_id']
    u = query("SELECT balance, total_withdrawn FROM users WHERE id=?", (uid,), fetchone=True)
    if not u or u[0] < amt:
        return jsonify({'error': 'Insufficient balance'}), 400
    query("INSERT INTO transactions (user_id, type, amount, method, account) VALUES (?,?,?,?,?)",
          (uid, 'withdraw', amt, d.get('method','binance'), d.get('account','')))
    query("UPDATE users SET balance=balance-?, total_withdrawn=total_withdrawn+? WHERE id=?",
          (amt, amt, uid))
    return jsonify({'success': True})

@app.route('/api/wallet/transactions')
@login_required
def wallet_transactions():
    rows = query("SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
                 (session['user_id'],), fetchall=True)
    cols = ['id','user_id','type','amount','method','account','status','created_at']
    return jsonify({'transactions': [dict(zip(cols, r)) for r in rows] if rows else []})

@app.route('/console')
@login_required
def console_page():
    return render_template('console.html')

@app.route('/api/console/logs')
@login_required
def console_logs():
    rows = query("SELECT * FROM console_logs ORDER BY created_at DESC LIMIT 50", fetchall=True)
    cols = ['id','number','prefix','message','app_name','created_at']
    return jsonify({'logs': [dict(zip(cols, r)) for r in rows] if rows else []})

@app.route('/api-docs')
@login_required
def api_docs():
    return render_template('api_docs.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
