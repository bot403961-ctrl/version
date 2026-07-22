// Supabase Configuration
const SUPABASE_URL = 'https://qvbtzeqvteavcczrywoi.supabase.co';
const SUPABASE_KEY = 'sb_publishable_2dTOK8q44KmKaAqKjrVJlQ_Q1LAHZOF';

const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

// Auth Functions
async function signUp(email, password, username, telegram) {
    const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
            data: {
                username,
                telegram
            }
        }
    });
    return { data, error };
}

async function signIn(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password
    });
    return { data, error };
}

async function signOut() {
    const { error } = await supabase.auth.signOut();
    return { error };
}

async function getSession() {
    const { data: { session } } = await supabase.auth.getSession();
    return session;
}

// Numbers Functions
async function createNumber(fullNumber, prefix, country, source = 'web') {
    const { data, error } = await supabase
        .from('numbers')
        .insert([{
            full_number: fullNumber,
            prefix,
            country,
            source,
            status: 'waiting'
        }])
        .select();
    return { data, error };
}

async function getAllNumbers() {
    const { data, error } = await supabase
        .from('numbers')
        .select('*')
        .order('created_at', { ascending: false });
    return { data, error };
}

async function deleteNumber(id) {
    const { error } = await supabase
        .from('numbers')
        .delete()
        .eq('id', id);
    return { error };
}

async function deleteAllNumbers() {
    const { error } = await supabase
        .from('numbers')
        .delete()
        .neq('id', 0);
    return { error };
}

async function updateNumberOTP(id, otpCode, otpMessage) {
    const { data, error } = await supabase
        .from('numbers')
        .update({
            otp_code: otpCode,
            otp_message: otpMessage,
            status: 'success'
        })
        .eq('id', id)
        .select();
    return { data, error };
}

// Wallet Functions
async function getWallet() {
    const { data, error } = await supabase
        .from('wallet')
        .select('*')
        .single();
    return { data, error };
}

async function updateWalletBalance(amount) {
    const wallet = await getWallet();
    if (wallet.data) {
        const { data, error } = await supabase
            .from('wallet')
            .update({
                balance: wallet.data.balance + amount,
                total_earned: wallet.data.total_earned + amount
            })
            .eq('id', wallet.data.id);
        return { data, error };
    }
}

async function createPayout(amount, method, account) {
    const { data, error } = await supabase
        .from('transactions')
        .insert([{
            type: 'withdrawal',
            amount,
            method,
            account,
            status: 'pending'
        }])
        .select();
    return { data, error };
}

async function getTransactions() {
    const { data, error } = await supabase
        .from('transactions')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(20);
    return { data, error };
}

// Console Functions
async function addConsoleLog(rangeTag, message, app) {
    const { data, error } = await supabase
        .from('console_logs')
        .insert([{
            range_tag: rangeTag,
            message,
            app
        }])
        .select();
    return { data, error };
}

async function getConsoleLogs() {
    const { data, error } = await supabase
        .from('console_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50);
    return { data, error };
}

// Stats Functions
async function getTodayStats() {
    const today = new Date().toISOString().split('T')[0];
    
    const { data: numbers, error: numbersError } = await supabase
        .from('numbers')
        .select('*')
        .gte('created_at', today);
    
    const numbersToday = numbers ? numbers.length : 0;
    const otpsToday = numbers ? numbers.filter(n => n.status === 'success').length : 0;
    const earningsToday = (otpsToday * 0.002).toFixed(4);
    
    return {
        numbersToday,
        otpsToday,
        earningsToday
    };
}
