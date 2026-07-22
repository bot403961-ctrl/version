#!/usr/bin/env python3
# ============================================
#  TAKER SMS - Full Dashboard Web App
#  Flask + SQLite
# ============================================

import os
import re
import uuid
import random
import string
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# ============================================
# DATABASE
# ============================================
DB = "taker_sms.db"

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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        method TEXT,
        account TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
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
    if fetchone:
        result = c.fetchone()
    elif fetchall:
        result = c.fetchall()
    else:
        result = None
    conn.commit()
    conn.close()
    return result

# ============================================
# HELPERS
# ============================================
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
    """توليد رقم وهمي"""
    suffix = ''.join(random.choices(string.digits, k=6))
    return prefix + suffix

def generate_otp():
    """توليد كود OTP وهمي"""
    return str(random.randint(100000, 999999))

def detect_app():
    """اختيار تطبيق عشوائي"""
    apps = ['WhatsApp', 'Instagram', 'Facebook', 'Telegram', 'Google', 'TikTok', 'Microsoft', 'Netflix']
    return random.choice(apps)

def generate_otp_message(code, app):
    """توليد رسالة OTP"""
    messages = [
        f"{code} is your {app} verification code.",
        f"<#> {code} is your {app} code. Don't share it.",
        f"Enter {code} on {app} to verify your account.",
        f"Your {app} code: {code}",
        f"{app} verification: {code}",
    ]
    return random.choice(messages)

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
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
        query(
            "INSERT INTO users (email, username, telegram, password, api_key) VALUES (?, ?, ?, ?, ?)",
            (email, username, telegram, hashed, api_key)
        )
        return jsonify({'success': True, 'message': 'Account created!'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Email or username already exists'}), 400

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    user = query(
        "SELECT id, email, username FROM users WHERE email = ? AND password = ?",
        (email, hashed), fetchone=True
    )
    
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

# ============================================
# DASHBOARD
# ============================================
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    user_id = session['user_id']
    
    # أرقام اليوم
    today = datetime.now().strftime('%Y-%m-%d')
    
    today_numbers = query(
        "SELECT COUNT(*) FROM numbers WHERE user_id = ? AND date(created_at) = ?",
        (user_id, today), fetchone=True
    )[0]
    
    today_otps = query(
        "SELECT COUNT(*) FROM numbers WHERE user_id = ? AND status = 'success' AND date(created_at) = ?",
        (user_id, today), fetchone=True
    )[0]
    
    # كل الوقت
    all_numbers = query("SELECT COUNT(*) FROM numbers WHERE user_id = ?", (user_id,), fetchone=True)[0]
    active_numbers = query("SELECT COUNT(*) FROM numbers WHERE user_id = ? AND status = 'success'", (user_id,), fetchone=True)[0]
    pending_numbers = query("SELECT COUNT(*) FROM numbers WHERE user_id = ? AND status = 'waiting'", (user_id,), fetchone=True)[0]
    
    user = query("SELECT balance, total_earned, total_withdrawn FROM users WHERE id = ?", (user_id,), fetchone=True)
    
    return jsonify({
        'today_numbers': today_numbers,
        'today_otps': today_otps,
        'all_numbers': all_numbers,
        'active_numbers': active_numbers,
        'pending_numbers': pending_numbers,
        'balance': user[0] if user else 0,
        'total_earned': user[1] if user else 0,
        'total_withdrawn': user[2] if user else 0,
    })

# ============================================
# NUMBERS
# ============================================
@app.route('/numbers')
@login_required
def numbers_page():
    return render_template('numbers.html')

@app.route('/api/numbers/generate', methods=['POST'])
@login_required
def generate_numbers():
    data = request.json
    prefix = data.get('prefix', '26134')
    quantity = min(int(data.get('quantity', 1)), 10)
    
    user_id = session['user_id']
    numbers = []
    
    for _ in range(quantity):
        number = generate_number(prefix)
        query(
            "INSERT INTO numbers (user_id, number, prefix, country, source) VALUES (?, ?, ?, ?, ?)",
            (user_id, number, prefix, 'Madagascar', 'web')
        )
        numbers.append(number)
    
    return jsonify({'success': True, 'numbers': numbers})

@app.route('/api/numbers/list')
@login_required
def list_numbers():
    user_id = session['user_id']
    rows = query(
        "SELECT id, number, prefix, country, status, source, otp_code, otp_message, app_name, created_at FROM numbers WHERE user_id = ? ORDER BY created_at DESC LIMIT 50",
        (user_id,), fetchall=True
    )
    
    numbers = []
    for row in rows:
        numbers.append({
            'id': row[0],
            'number': row[1],
            'prefix': row[2],
            'country': row[3],
            'status': row[4],
            'source': row[5],
            'otp_code': row[6],
            'otp_message': row[7],
            'app_name': row[8],
            'created_at': row[9],
        })
    
    return jsonify({'numbers': numbers})

@app.route('/api/numbers/generate-otp', methods=['POST'])
@login_required
def api_generate_otp():
    data = request.json
    number_id = data.get('number_id')
    number = data.get('number')
    prefix = data.get('prefix', '26134')
    
    code = generate_otp()
    app = detect_app()
    message = generate_otp_message(code, app)
    
    query(
        "UPDATE numbers SET status = 'success', otp_code = ?, otp_message = ?, app_name = ? WHERE id = ?",
        (code, message, app, number_id)
    )
    
    # أضف للكونسول
    query(
        "INSERT INTO console_logs (number, prefix, message, app_name) VALUES (?, ?, ?, ?)",
        (number, prefix, message, app)
    )
    
    # أضف أرباح
    user_id = session['user_id']
    query(
        "UPDATE users SET balance = balance + 0.05, total_earned = total_earned + 0.05 WHERE id = ?",
        (user_id,)
    )
    
    return jsonify({'success': True, 'code': code, 'message': message, 'app': app})

@app.route('/api/numbers/delete', methods=['POST'])
@login_required
def delete_number():
    data = request.json
    number_id = data.get('number_id')
    user_id = session['user_id']
    query("DELETE FROM numbers WHERE id = ? AND user_id = ?", (number_id, user_id))
    return jsonify({'success': True})

@app.route('/api/numbers/clear', methods=['POST'])
@login_required
def clear_numbers():
    user_id = session['user_id']
    query("DELETE FROM numbers WHERE user_id = ?", (user_id,))
    return jsonify({'success': True})

# ============================================
# WALLET
# ============================================
@app.route('/wallet')
@login_required
def wallet_page():
    return render_template('wallet.html')

@app.route('/api/wallet/info')
@login_required
def wallet_info():
    user_id = session['user_id']
    user = query(
        "SELECT balance, total_earned, total_withdrawn, api_key FROM users WHERE id = ?",
        (user_id,), fetchone=True
    )
    return jsonify({
        'balance': user[0] if user else 0,
        'total_earned': user[1] if user else 0,
        'total_withdrawn': user[2] if user else 0,
        'api_key': user[3] if user else '',
    })

@app.route('/api/wallet/payout', methods=['POST'])
@login_required
def request_payout():
    data = request.json
    amount = float(data.get('amount', 0))
    method = data.get('method', 'binance')
    account = data.get('account', '')
    
    user_id = session['user_id']
    user = query("SELECT balance FROM users WHERE id = ?", (user_id,), fetchone=True)
    
    if not user or user[0] < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    query(
        "INSERT INTO transactions (user_id, type, amount, method, account) VALUES (?, 'withdraw', ?, ?, ?)",
        (user_id, amount, method, account)
    )
    
    query(
        "UPDATE users SET balance = balance - ?, total_withdrawn = total_withdrawn + ? WHERE id = ?",
        (amount, amount, user_id)
    )
    
    return jsonify({'success': True, 'message': 'Payout requested!'})

@app.route('/api/wallet/transactions')
@login_required
def wallet_transactions():
    user_id = session['user_id']
    rows = query(
        "SELECT type, amount, method, account, status, created_at FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,), fetchall=True
    )
    
    transactions = []
    for row in rows:
        transactions.append({
            'type': row[0],
            'amount': row[1],
            'method': row[2],
            'account': row[3],
            'status': row[4],
            'created_at': row[5],
        })
    
    return jsonify({'transactions': transactions})

# ============================================
# CONSOLE
# ============================================
@app.route('/console')
@login_required
def console_page():
    return render_template('console.html')

@app.route('/api/console/logs')
@login_required
def console_logs():
    rows = query(
        "SELECT number, prefix, message, app_name, created_at FROM console_logs ORDER BY created_at DESC LIMIT 50",
        fetchall=True
    )
    
    logs = []
    for row in rows:
        logs.append({
            'number': row[0],
            'prefix': row[1],
            'message': row[2],
            'app_name': row[3],
            'created_at': row[4],
        })
    
    return jsonify({'logs': logs})

# ============================================
# API DOCS
# ============================================
@app.route('/api-docs')
@login_required
def api_docs():
    return render_template('api_docs.html')

# ============================================
# PUBLIC API
# ============================================
@app.route('/api/v1/get-number', methods=['POST'])
def public_get_number():
    api_key = request.headers.get('mauthapi', '')
    user = query("SELECT id FROM users WHERE api_key = ?", (api_key,), fetchone=True)
    
    if not user:
        return jsonify({'error': 'Invalid API key'}), 401
    
    data = request.json or {}
    prefix = data.get('prefix', '26134')
    quantity = min(int(data.get('quantity', 1)), 5)
    
    numbers = []
    for _ in range(quantity):
        number = generate_number(prefix)
        query(
            "INSERT INTO numbers (user_id, number, prefix, country, source) VALUES (?, ?, ?, ?, ?)",
            (user[0], number, prefix, 'Madagascar', 'api')
        )
        numbers.append(number)
    
    return jsonify({'success': True, 'numbers': numbers})

@app.route('/api/v1/check-otp')
def public_check_otp():
    api_key = request.headers.get('mauthapi', '')
    user = query("SELECT id FROM users WHERE api_key = ?", (api_key,), fetchone=True)
    
    if not user:
        return jsonify({'error': 'Invalid API key'}), 401
    
    rows = query(
        "SELECT number, otp_code, otp_message, app_name FROM numbers WHERE user_id = ? AND status = 'success' ORDER BY created_at DESC LIMIT 20",
        (user[0],), fetchall=True
    )
    
    otps = []
    for row in rows:
        otps.append({
            'number': row[0],
            'code': row[1],
            'message': row[2],
            'app': row[3],
        })
    
    return jsonify({'otps': otps})

# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
