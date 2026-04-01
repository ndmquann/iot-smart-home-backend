-- ==============================================================================
-- 1. CLEANUP
-- ==============================================================================
DROP TABLE IF EXISTS apply CASCADE;
DROP TABLE IF EXISTS logs CASCADE;
DROP TABLE IF EXISTS schedules CASCADE;
DROP TABLE IF EXISTS thresholds CASCADE;
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS sensors CASCADE;
DROP TABLE IF EXISTS controllers CASCADE;
DROP TABLE IF EXISTS devices CASCADE;
DROP TABLE IF EXISTS zones CASCADE;
DROP TABLE IF EXISTS admins CASCADE;
DROP TABLE IF EXISTS members CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS sensor_history CASCADE;
DROP TABLE IF EXISTS homes CASCADE;
DROP TRIGGER IF EXISTS log_sensor_history ON sensors;
DROP FUNCTION IF EXISTS log_sensor_history();

-- ==============================================================================
-- 2. Entity
-- ==============================================================================

-- Home
CREATE TABLE homes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    fname VARCHAR(255) NOT NULL,
    lname VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    status BOOLEAN DEFAULT TRUE,
    home_id INTEGER REFERENCES homes(id) ON DELETE CASCADE
);

CREATE TABLE admins (
    uid INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE members (
    uid INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE
);

-- Zones
CREATE TABLE zones (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(uid) ON DELETE CASCADE,
    floor INTEGER DEFAULT 1 CHECK (floor > 0),
    room VARCHAR(255) NOT NULL
);

-- Devices
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(uid) ON DELETE CASCADE,
    zone_id INTEGER REFERENCES zones(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'OFF',
    feed_id VARCHAR(100)
);

CREATE TABLE sensors (
    device_id INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    value FLOAT
);

CREATE TABLE controllers (
    device_id INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    mode VARCHAR(20) DEFAULT 'manual',
    speed INTEGER DEFAULT NULL CHECK (speed >= 0 AND speed <= 100)
);

-- Settings
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    admin_id INTEGER REFERENCES admins(uid) ON DELETE CASCADE
);

CREATE TABLE thresholds (
    setting_id INTEGER PRIMARY KEY REFERENCES settings(id) ON DELETE CASCADE,
    value FLOAT NOT NULL,
    condition BOOLEAN NOT NULL
);

CREATE TABLE schedules (
    setting_id INTEGER PRIMARY KEY REFERENCES settings(id) ON DELETE CASCADE,
    date_start DATE NOT NULL,
    date_end DATE,
    time_start TIME NOT NULL,
    timer INTEGER
);

-- Logs
CREATE TABLE logs (
    id SERIAL PRIMARY KEY,
    type VARCHAR(255) NOT NULL CHECK (type IN ('user action', 'admin action', 'system action', 'sensor alert')),
    description TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    home_id INTEGER REFERENCES homes(id) ON DELETE CASCADE
);

CREATE TABLE apply (
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    setting_id INTEGER REFERENCES settings(id) ON DELETE CASCADE,
    PRIMARY KEY (device_id, setting_id)
);

CREATE TABLE sensor_history(
    device_id INTEGER REFERENCES sensors(device_id) ON DELETE CASCADE,
    value FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id, timestamp)
);

CREATE INDEX idx_logs_home_id ON logs(home_id);
CREATE INDEX idx_users_home_id ON users(home_id);
CREATE INDEX idx_sensor_history_device_id_time ON sensor_history(device_id, timestamp DESC);

-- ==============================================================================
-- TRIGGER
-- ==============================================================================
CREATE OR REPLACE FUNCTION log_sensor_history()
RETURNS TRIGGER AS $$
BEGIN
    -- only save to history if value has changed
    IF OLD.value IS DISTINCT FROM NEW.value THEN
        INSERT INTO sensor_history (device_id, value) 
        VALUES (NEW.device_id, NEW.value);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_sensor_history
AFTER UPDATE ON sensors
FOR EACH ROW EXECUTE FUNCTION log_sensor_history();