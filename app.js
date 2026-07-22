// App State
let currentPage = 'overview';
let consoleInterval = null;
let otpTimeouts = {};

// DOM Elements
const signInPage = document.getElementById('signInPage');
const signUpPage = document.getElementById('signUpPage');
const dashboard = document.getElementById('dashboard');
const toastContainer = document.getElementById('toastContainer');

// ==================== AUTH ====================
document.getElementById('showSignUp').addEventListener('click', (e) => {
    e.preventDefault();
    signInPage.classList.add('hidden');
    signUpPage.classList.remove('hidden');
});

document.getElementById('showSignIn').addEventListener('click', (e) => {
    e.preventDefault();
    signUpPage.classList.add('hidden');
    signInPage.classList.remove('hidden');
});

document.getElementById('signUpForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('signUpEmail').value;
    const username = document.getElementById('signUpUsername').value;
    const telegram = document.getElementById('signUpTelegram').value;
    const password = document.getElementById('signUpPassword').value;
    
    const { data, error } = await signUp(email, password, username, telegram);
    
    if (error) {
        showToast(error.message, 'error');
    } else {
        showToast('Account created! Check your email for confirmation.', 'success');
        signUpPage.classList.add('hidden');
        signInPage.classList.remove('hidden');
    }
});

document.getElementById('signInForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('signInEmail').value;
    const password = document.getElementById('signInPassword').value;
    
    const { data, error } = await signIn(email, password);
    
    if (error) {
        showToast(error.message, 'error');
    } else {
        signInPage.classList.add('hidden');
        dashboard.classList.remove('hidden');
        loadDashboard();
        showToast('Welcome back!', 'success');
    }
});

document.getElementById('logoutBtn').addEventListener('click', async () => {
    await signOut();
    dashboard.classList.add('hidden');
    signInPage.classList.remove('hidden');
    showToast('Logged out successfully', 'info');
});

// ==================== NAVIGATION ====================
document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const page = item.dataset.page;
        navigateTo(page);
    });
});

function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item, .mobile-nav-item').forEach(n => n.classList.remove('active'));
    
    const pageEl = document.getElementById(page);
    if (pageEl) pageEl.classList.add('active');
    
    document.querySelectorAll(`[data-page="${page}"]`).forEach(n => n.classList.add('active'));
    
    currentPage = page;
    
    if (page === 'console') startConsoleFeed();
    else if (consoleInterval) { clearInterval(consoleInterval); consoleInterval = null; }
    
    if (page === 'numbers') loadNumbers();
    if (page === 'wallet') loadWallet();
    if (page === 'overview') loadDashboard();
}

// ==================== TOAST ====================
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!', 'success');
    });
}

// ==================== DASHBOARD ====================
async function loadDashboard() {
    const today = new Date();
    document.getElementById('currentDate').textContent = today.toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
    
    const stats = await getTodayStats();
    document.getElementById('todayNumbers').textContent = stats.numbersToday;
    document.getElementById('todayOTPs').textContent = stats.otpsToday;
    document.getElementById('todayEarnings').textContent = `$${stats.earningsToday}`;
    
    const { data: allNumbers } = await getAllNumbers();
    if (allNumbers) {
        document.getElementById('allActive').textContent = allNumbers.filter(n => n.status === 'waiting').length;
        document.getElementById('allSuccess').textContent = allNumbers.filter(n => n.status === 'success').length;
        document.getElementById('allPending').textContent = allNumbers.filter(n => n.status === 'waiting').length;
        document.getElementById('allWeb').textContent = allNumbers.filter(n => n.source === 'web').length;
        document.getElementById('allAPI').textContent = allNumbers.filter(n => n.source === 'api').length;
    }
}

// ==================== NUMBERS ====================
const COUNTRIES = {
    "22501": "Côte d'Ivoire", "23276": "Sierra Leone", "26134": "Madagascar",
    "44740": "United Kingdom", "23490": "Nigeria", "25471": "Kenya",
    "24910": "Sudan", "49155": "Germany", "21206": "Morocco"
};

function generateNumber(prefix) {
    const random = Math.floor(Math.random() * 900000) + 100000;
    return `+${prefix}${random}`;
}

function detectApp(message) {
    const msg = message.toLowerCase();
    if (msg.includes('whatsapp')) return 'WhatsApp';
    if (msg.includes('instagram')) return 'Instagram';
    if (msg.includes('facebook')) return 'Facebook';
    if (msg.includes('google') || msg.includes('gmail')) return 'Google';
    if (msg.includes('telegram')) return 'Telegram';
    if (msg.includes('tiktok')) return 'TikTok';
    if (msg.includes('microsoft')) return 'Microsoft';
    if (msg.includes('netflix')) return 'Netflix';
    return 'OTP';
}

function generateOTPMessage(app) {
    const code = Math.floor(100000 + Math.random() * 900000).toString();
    const messages = {
        'WhatsApp': `${code} is your WhatsApp verification code`,
        'Instagram': `${code} is your Instagram code. Don't share it.`,
        'Facebook': `<#> ${code} is your Facebook code H29Q+Fsn4Sr`,
        'Google': `G-${code} is your Google verification code`,
        'Telegram': `Telegram code: ${code}`,
        'TikTok': `${code} is your TikTok verification code`,
        'Microsoft': `${code} is your Microsoft verification code`,
        'Netflix': `${code} is your Netflix verification code`
    };
    return { code, message: messages[app] || `${code} is your verification code` };
}

async function loadNumbers() {
    const { data: numbers } = await getAllNumbers();
    const grid = document.getElementById('numbersGrid');
    
    if (!numbers || numbers.length === 0) {
        grid.innerHTML = '<p class="empty-state">No numbers allocated yet. Request one above.</p>';
        return;
    }
    
    grid.innerHTML = numbers.map(num => `
        <div class="number-card glass" id="num-${num.id}">
            <button class="delete-btn" onclick="deleteNumberCard(${num.id})"><i class="fas fa-times"></i></button>
            <div class="number" onclick="copyToClipboard('${num.full_number}')" title="Click to copy">${num.full_number} <i class="fas fa-copy" style="font-size:14px;opacity:0.5;"></i></div>
            <div class="country-time">${num.country} · ${new Date(num.created_at).toLocaleTimeString()}</div>
            <span class="badge badge-${num.source}">${num.source.toUpperCase()}</span>
            ${num.status === 'success' ? `
                <div class="otp-code" onclick="copyToClipboard('${num.otp_code}')" title="Click to copy">${num.otp_code} <i class="fas fa-copy" style="font-size:14px;opacity:0.5;"></i></div>
                <div class="otp-message">${num.otp_message}</div>
            ` : `
                <div class="loader"><div class="spinner"></div> Awaiting OTP payload...</div>
            `}
        </div>
    `).join('');
    
    // Start OTP generation for waiting numbers
    numbers.filter(n => n.status === 'waiting').forEach(num => {
        if (!otpTimeouts[num.id]) {
            otpTimeouts[num.id] = setTimeout(() => generateOTP(num), 10000);
        }
    });
}

async function generateOTP(num) {
    const apps = ['WhatsApp', 'Instagram', 'Facebook', 'Google', 'Telegram', 'TikTok', 'Microsoft', 'Netflix'];
    const app = apps[Math.floor(Math.random() * apps.length)];
    const { code, message } = generateOTPMessage(app);
    
    await updateNumberOTP(num.id, code, message);
    await addConsoleLog(num.prefix, message, app);
    await updateWalletBalance(0.002);
    
    loadNumbers();
    loadDashboard();
    delete otpTimeouts[num.id];
}

document.getElementById('getNumberBtn').addEventListener('click', async () => {
    const prefix = document.getElementById('rangePrefix').value.trim();
    const quantity = parseInt(document.getElementById('quantity').value) || 1;
    
    if (!prefix) { showToast('Please enter a range prefix', 'error'); return; }
    
    const country = COUNTRIES[prefix] || 'Unknown';
    
    for (let i = 0; i < quantity; i++) {
        const number = generateNumber(prefix);
        await createNumber(number, prefix, country, 'web');
    }
    
    showToast(`${quantity} number(s) allocated!`, 'success');
    loadNumbers();
    loadDashboard();
});

async function deleteNumberCard(id) {
    await deleteNumber(id);
    showToast('Number deleted', 'info');
    loadNumbers();
    loadDashboard();
}

document.getElementById('clearAllBtn').addEventListener('click', async () => {
    if (confirm('Are you sure you want to delete ALL numbers?')) {
        await deleteAllNumbers();
        showToast('All numbers cleared', 'info');
        loadNumbers();
        loadDashboard();
    }
});

// ==================== WALLET ====================
async function loadWallet() {
    const { data: wallet } = await getWallet();
    if (wallet) {
        document.getElementById('walletBalance').textContent = `$${wallet.balance.toFixed(4)}`;
        document.getElementById('walletEarned').textContent = `$${wallet.total_earned.toFixed(2)}`;
        document.getElementById('walletWithdrawn').textContent = `$${wallet.total_withdrawn.toFixed(2)}`;
        document.getElementById('apiKeyDisplay').textContent = wallet.api_key;
    }
    
    const { data: transactions } = await getTransactions();
    const txList = document.getElementById('transactionsList');
    if (transactions && transactions.length > 0) {
        txList.innerHTML = '<h3>Transaction History</h3>' + transactions.map(tx => `
            <div class="transaction-item">
                <span>${tx.type.toUpperCase()} · ${tx.method || 'N/A'}</span>
                <span style="color: ${tx.type === 'withdrawal' ? 'var(--red)' : 'var(--green)'}">$${tx.amount}</span>
                <span style="color: var(--text-secondary); font-size: 12px;">${new Date(tx.created_at).toLocaleDateString()}</span>
            </div>
        `).join('');
    }
}

document.getElementById('toggleApiKey').addEventListener('click', function() {
    const el = document.getElementById('apiKeyDisplay');
    const icon = this.querySelector('i');
    if (el.textContent.startsWith('•')) {
        loadWallet();
        icon.className = 'fas fa-eye-slash';
    } else {
        el.textContent = '••••••••••••••••';
        icon.className = 'fas fa-eye';
    }
});

document.getElementById('copyApiKey').addEventListener('click', async () => {
    const { data: wallet } = await getWallet();
    if (wallet) {
        await navigator.clipboard.writeText(wallet.api_key);
        showToast('API key copied!', 'success');
    }
});

document.getElementById('requestPayoutBtn').addEventListener('click', async () => {
    const amount = parseFloat(document.getElementById('payoutAmount').value);
    const method = document.getElementById('payoutMethod').value;
    const account = document.getElementById('payoutAccount').value;
    
    if (!amount || !account) { showToast('Fill all fields', 'error'); return; }
    
    const { data: wallet } = await getWallet();
    if (wallet && wallet.balance < amount) {
        showToast('Insufficient balance', 'error');
        return;
    }
    
    await createPayout(amount, method, account);
    
    if (wallet) {
        await supabase.from('wallet').update({
            balance: wallet.balance - amount,
            total_withdrawn: wallet.total_withdrawn + amount
        }).eq('id', wallet.id);
    }
    
    showToast('Payout requested!', 'success');
    loadWallet();
});

// ==================== CONSOLE ====================
function startConsoleFeed() {
    loadConsole();
    consoleInterval = setInterval(loadConsole, 5000);
}

async function loadConsole() {
    const { data: logs } = await getConsoleLogs();
    const feed = document.getElementById('consoleFeed');
    
    if (!logs || logs.length === 0) {
        feed.innerHTML = '<p class="empty-state">Waiting for OTP hits...</p>';
        return;
    }
    
    feed.innerHTML = logs.map(log => `
        <div class="console-entry">
            <span class="range-tag">[${log.range_tag}XXX]</span>
            ${log.message}
            <span class="app-badge app-${log.app.toLowerCase()}">${log.app}</span>
            <span style="color: var(--text-secondary); font-size: 10px; margin-left: 8px;">${new Date(log.created_at).toLocaleTimeString()}</span>
        </div>
    `).join('');
}

// ==================== API DOCS ====================
function loadDocs() {
    const prefixButtons = document.getElementById('prefixButtons');
    prefixButtons.innerHTML = Object.entries(COUNTRIES).map(([prefix, country]) => `
        <button class="prefix-btn" onclick="document.getElementById('rangePrefix').value='${prefix}'; navigateTo('numbers');">${prefix} · ${country}</button>
    `).join('');
}

// ==================== INIT ====================
document.addEventListener('DOMContentLoaded', async () => {
    const session = await getSession();
    if (session) {
        signInPage.classList.add('hidden');
        dashboard.classList.remove('hidden');
        loadDashboard();
    }
    
    loadDocs();
});
