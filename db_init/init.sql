-- ==============================================================================
-- 1. CLEANUP
-- ==============================================================================
DROP TABLE IF EXISTS contain CASCADE;
DROP TABLE IF EXISTS config CASCADE;
DROP TABLE IF EXISTS interact CASCADE;
DROP TABLE IF EXISTS schedule_apply CASCADE;
DROP TABLE IF EXISTS threshold_apply CASCADE;
DROP TABLE IF EXISTS logs CASCADE;
DROP TABLE IF EXISTS schedules CASCADE;
DROP TABLE IF EXISTS thresholds CASCADE;
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS sensors CASCADE;
DROP TABLE IF EXISTS controllers CASCADE;
DROP TABLE IF EXISTS devices CASCADE;
DROP TABLE IF EXISTS zones CASCADE;
DROP TABLE IF EXISTS user_phones CASCADE;
DROP TABLE IF EXISTS user_addresses CASCADE;
DROP TABLE IF EXISTS admins CASCADE;
DROP TABLE IF EXISTS members CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ==============================================================================
-- 2. Entity
-- ==============================================================================

-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    fname VARCHAR(255) NOT NULL,
    lname VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    status BOOLEAN DEFAULT TRUE,
    home_id VARCHAR(255) NOT NULL
);

CREATE TABLE admins (
    uid INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE members (
    uid INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE users_phones (
    uid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    phone VARCHAR(20) NOT NULL,
    PRIMARY KEY (uid, phone)
);

CREATE TABLE users_addresses (
    uid INTEGER REFERENCES users(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    PRIMARY KEY (uid, address)
);

-- Zones
CREATE TABLE zones (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(uid) ON DELETE SET NULL,
    floor INTEGER DEFAULT 1 CHECK (floor > 0),
    room VARCHAR(255) NOT NULL
);

-- Devices
CREATE TABLE devices (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER REFERENCES admins(uid) ON DELETE SET NULL,
    zone_id INTEGER REFERENCES zones(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'OFF',
    feed_id VARCHAR(100)
);

CREATE TABLE sensors (
    did INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    value FLOAT
);

CREATE TABLE controllers (
    did INTEGER PRIMARY KEY REFERENCES devices(id) ON DELETE CASCADE,
    mode VARCHAR(20) DEFAULT 'manual',
    speed INTEGER DEFAULT NULL CHECK (speed >= 0 AND speed <= 100)
);

-- Settings
CREATE TABLE settings (
    id SERIAL PRIMARY KEY
);

CREATE TABLE thresholds (
    sid INTEGER PRIMARY KEY REFERENCES settings(id) ON DELETE CASCADE,
    name VARCHAR(255),
    value FLOAT NOT NULL,
    condition BOOLEAN NOT NULL
);

CREATE TABLE schedules (
    sid INTEGER PRIMARY KEY REFERENCES settings(id) ON DELETE CASCADE,
    name VARCHAR(255),
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
    home_id VARCHAR(255) NOT NULL
);

-- Many to many
CREATE TABLE threshold_apply (
    threshold_id INTEGER REFERENCES thresholds(sid) ON DELETE CASCADE,
    sensor_id INTEGER REFERENCES sensors(did) ON DELETE CASCADE,
    PRIMARY KEY (threshold_id, sensor_id)
);

CREATE TABLE schedule_apply (
    schedule_id INTEGER REFERENCES schedules(sid) ON DELETE CASCADE,
    controller_id INTEGER REFERENCES controllers(did) ON DELETE CASCADE,
    PRIMARY KEY (schedule_id, controller_id)
);

-- Log event
CREATE TABLE interact (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    log_id INTEGER REFERENCES logs(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, devices_id, log_id)
);

CREATE TABLE contain (
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    setting_id INTEGER REFERENCES settings(id) ON DELETE CASCADE,
    log_id INTEGER REFERENCES logs(id) ON DELETE CASCADE,
    PRIMARY KEY (device_id, setting_id, log_id)
);

CREATE TABLE config (
    admin_id INTEGER REFERENCES admins(uid) ON DELETE CASCADE,
    setting_id INTEGER REFERENCES settings(id) ON DELETE CASCADE,
    log_id INTEGER REFERENCES logs(id) ON DELETE CASCADE,
    PRIMARY KEY (admin_id, setting_id, log_id)
);

CREATE INDEX idx_logs_home_id ON logs(home_id);

-- ==============================================================================
-- TEST DATA
-- ==============================================================================
INSERT INTO users (fname, lname, email, password) 
VALUES ('test', 'admin', 'admin@gmail.com', 'admin'),
       ('test', 'member', 'member@gmail.com', 'member');

INSERT INTO admins (uid) VALUES (1);
INSERT INTO members (uid) VALUES (2);

INSERT INTO zones (admin_id, floor, room) 
VALUES (1, 1, 'test room');

INSERT INTO devices (admin_id, zone_id, name, status, feed_id) 
VALUES (1, 1, 'test controller', 'OFF', 'led-control');

INSERT INTO controllers (did) VALUES (1);