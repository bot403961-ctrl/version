#!/usr/bin/env python3
# ============================================
#  TAKER SMS - Full Dashboard Web App
#  Flask + Supabase
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
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# ============================================
# SUPABASE CONFIG
# ============================================
SUPABASE_URL = 'https://qvbtzeqvteavcczrywoi.supabase.co'
SUPABASE_KEY = 'sb_publishable_2dTOK8q44KmKaAqKjrVJlQ_Q1LAHZOF'

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    suffix = ''.join(random.choices(string.digits, k=6))
    return prefix + suffix

def generate_otp():
    return str(random.randint(100000, 999999))

def detect_app():
    apps = ['WhatsApp', 'Instagram', 'Facebook', 'Telegram', 'Google', 'TikTok', 'Microsoft', 'Netflix']
    return random.choice(apps)

def generate_otp_message(code, app):
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
        supabase.table('users').insert({
            'email': email,
            'username': username,
            'telegram': telegram,
            'password': hashed,
            'api_key': api_key,
            'balance': 0,
            'total_earned': 0,
            'total_withdrawn': 0
        }).execute()
        return jsonify({'success': True, 'message': 'Account created!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    hashed = hashlib.sha256(password.encode()).hexdigest()
    
    res = supabase.table('users').select('*').eq('email', email).eq('password', hashed).execute()
    
    if res.data:
        user = res.data[0]
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['username'] = user['username']
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
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Numbers today
    today_numbers = supabase.table('numbers').select('count', count='exact').eq('user_id', user_id).gte('created_at', today).execute().count
    
    # OTPs today
    today_otps = supabase.table('numbers').select('count', count='exact').eq('user_id', user_id).eq('status', 'success').gte('created_at', today).execute().count
    
    # All stats
    all_numbers = supabase.table('numbers').select('count', count='exact').eq('user_id', user_id).execute().count
    active_numbers = supabase.table('numbers').select('count', count='exact').eq('user_id', user_id).eq('status', 'success').execute().count
    pending_numbers = supabase.table('numbers').select('count', count='exact').eq('user_id', user_id).eq('status', 'waiting').execute().count
    
    user = supabase.table('users').select('balance,total_earned,total_withdrawn').eq('id', user_id).execute()
    u = user.data[0] if user.data else {}
    
    return jsonify({
        'today_numbers': today_numbers,
        'today_otps': today_otps,
        'all_numbers': all_numbers,
        'active_numbers': active_numbers,
        'pending_numbers': pending_numbers,
        'balance': u.get('balance', 0),
        'total_earned': u.get('total_earned', 0),
        'total_withdrawn': u.get('total_withdrawn', 0),
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
        supabase.table('numbers').insert({
            'user_id': user_id,
            'number': number,
            'prefix': prefix,
            'country': 'Madagascar',
            'source': 'web',
            'status': 'waiting'
        }).execute()
        numbers.append(number)
    
    return jsonify({'success': True, 'numbers': numbers})

@app.route('/api/numbers/list')
@login_required
def list_numbers():
    user_id = session['user_id']
    res = supabase.table('numbers').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(50).execute()
    
    return jsonify({'numbers': res.data if res.data else []})

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
    
    supabase.table('numbers').update({
        'status': 'success',
        'otp_code': code,
        'otp_message': message,
        'app_name': app
    }).eq('id', number_id).execute()
    
    # Console log
    supabase.table('console_logs').insert({
        'number': number,
        'prefix': prefix,
        'message': message,
        'app_name': app
    }).execute()
    
    # Add earnings
    user_id = session['user_id']
    user = supabase.table('users').select('balance,total_earned').eq('id', user_id).execute()
    if user.data:
        bal = user.data[0]['balance'] + 0.05
        te = user.data[0]['total_earned'] + 0.05
        supabase.table('users').update({'balance': bal, 'total_earned': te}).eq('id', user_id).execute()
    
    return jsonify({'success': True, 'code': code, 'message': message, 'app': app})

@app.route('/api/numbers/delete', methods=['POST'])
@login_required
def delete_number():
    data = request.json
    number_id = data.get('number_id')
    supabase.table('numbers').delete().eq('id', number_id).execute()
    return jsonify({'success': True})

@app.route('/api/numbers/clear', methods=['POST'])
@login_required
def clear_numbers():
    user_id = session['user_id']
    supabase.table('numbers').delete().eq('user_id', user_id).execute()
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
    res = supabase.table('users').select('balance,total_earned,total_withdrawn,api_key').eq('id', user_id).execute()
    u = res.data[0] if res.data else {}
    
    return jsonify({
        'balance': u.get('balance', 0),
        'total_earned': u.get('total_earned', 0),
        'total_withdrawn': u.get('total_withdrawn', 0),
        'api_key': u.get('api_key', ''),
    })

@app.route('/api/wallet/payout', methods=['POST'])
@login_required
def request_payout():
    data = request.json
    amount = float(data.get('amount', 0))
    method = data.get('method', 'binance')
    account = data.get('account', '')
    
    user_id = session['user_id']
    user = supabase.table('users').select('balance').eq('id', user_id).execute()
    
    if not user.data or user.data[0]['balance'] < amount:
        return jsonify({'error': 'Insufficient balance'}), 400
    
    supabase.table('transactions').insert({
        'user_id': user_id,
        'type': 'withdraw',
        'amount': amount,
        'method': method,
        'account': account
    }).execute()
    
    bal = user.data[0]['balance'] - amount
    tw = user.data[0].get('total_withdrawn', 0) + amount
    supabase.table('users').update({'balance': bal, 'total_withdrawn': tw}).eq('id', user_id).execute()
    
    return jsonify({'success': True, 'message': 'Payout requested!'})

@app.route('/api/wallet/transactions')
@login_required
def wallet_transactions():
    user_id = session['user_id']
    res = supabase.table('transactions').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(20).execute()
    
    return jsonify({'transactions': res.data if res.data else []})

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
    res = supabase.table('console_logs').select('*').order('created_at', desc=True).limit(50).execute()
    return jsonify({'logs': res.data if res.data else []})

# ============================================
# API DOCS
# ============================================
@app.route('/api-docs')
@login_required
def api_docs():
    return render_template('api_docs.html')

# ============================================
# RUN
# ============================================
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
