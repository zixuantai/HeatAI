-- HeatAI 数据库初始化脚本
-- 创建数据库和用户（需以 postgres 超级用户执行）

CREATE USER heatai WITH PASSWORD 'heatai123';
CREATE DATABASE heatai OWNER heatai;
GRANT ALL PRIVILEGES ON DATABASE heatai TO heatai;

-- 以下表由 SQLAlchemy 自动创建，此处仅作为参考

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    email           VARCHAR(100) UNIQUE,
    phone           VARCHAR(20) UNIQUE,
    nickname        VARCHAR(50),
    role            VARCHAR(20) DEFAULT 'user',
    status          VARCHAR(20) DEFAULT 'active',
    last_login_at   TIMESTAMP,
    last_login_ip   VARCHAR(45),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    refresh_token_hash VARCHAR(255) NOT NULL,
    ip_address      VARCHAR(45),
    is_active       BOOLEAN DEFAULT TRUE,
    expires_at      TIMESTAMP NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW(),
    last_used_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);

-- Token 黑名单表
CREATE TABLE IF NOT EXISTS token_blacklist (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token           VARCHAR(500) NOT NULL,
    token_type      VARCHAR(10),
    expires_at      TIMESTAMP NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_token ON token_blacklist(token);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);
