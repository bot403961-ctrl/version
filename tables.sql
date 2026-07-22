-- جدول الأرقام
CREATE TABLE numbers (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  full_number TEXT NOT NULL,
  prefix TEXT NOT NULL,
  country TEXT NOT NULL,
  status TEXT DEFAULT 'waiting',
  otp_code TEXT,
  otp_message TEXT,
  source TEXT DEFAULT 'web',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول المحفظة
CREATE TABLE wallet (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  balance DECIMAL DEFAULT 0,
  total_earned DECIMAL DEFAULT 0,
  total_withdrawn DECIMAL DEFAULT 0,
  api_key TEXT UNIQUE
);

-- جدول المعاملات
CREATE TABLE transactions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  type TEXT NOT NULL,
  amount DECIMAL NOT NULL,
  method TEXT,
  account TEXT,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- جدول سجل العمليات
CREATE TABLE console_logs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  range_tag TEXT NOT NULL,
  message TEXT NOT NULL,
  app TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- بيانات أولية للمحفظة
INSERT INTO wallet (balance, total_earned, total_withdrawn, api_key)
VALUES (0.3560, 45.50, 10.00, 'xwd_sk_' || gen_random_uuid());
