-- NodeScope Simulator Database Schema
-- All timestamps stored as ISO 8601 UTC strings

CREATE TABLE IF NOT EXISTS networks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    subnet TEXT NOT NULL,          -- e.g. '192.168.10.0/24'
    netmask TEXT NOT NULL,         -- e.g. '255.255.255.0'
    gateway TEXT NOT NULL,         -- e.g. '192.168.10.1'
    dhcp_enabled INTEGER NOT NULL DEFAULT 1,
    dhcp_start TEXT,              -- e.g. '192.168.10.100'
    dhcp_end TEXT,                -- e.g. '192.168.10.199'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    device_type TEXT NOT NULL,     -- router, switch, access_point, laptop, desktop, smartphone, printer, server
    mac_address TEXT NOT NULL,     -- e.g. '02:00:5E:10:00:01'
    ip_address TEXT,              -- e.g. '192.168.10.10'
    subnet_mask TEXT,
    gateway TEXT,
    ip_mode TEXT NOT NULL DEFAULT 'dhcp', -- 'dhcp' or 'static'
    is_online INTEGER NOT NULL DEFAULT 1,
    is_approved INTEGER NOT NULL DEFAULT 1,
    pos_x REAL NOT NULL DEFAULT 150,
    pos_y REAL NOT NULL DEFAULT 150,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER NOT NULL,
    device_a_id INTEGER NOT NULL,
    device_b_id INTEGER NOT NULL,
    link_type TEXT NOT NULL DEFAULT 'wired', -- 'wired', 'wireless', 'backbone'
    status TEXT NOT NULL DEFAULT 'active',    -- 'active' or 'down'
    cost INTEGER NOT NULL DEFAULT 1,          -- Routing metric/cost (1-100)
    delay_ms INTEGER NOT NULL DEFAULT 2,      -- Simulated latency in ms
    created_at TEXT NOT NULL,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE,
    FOREIGN KEY (device_a_id) REFERENCES devices(id) ON DELETE CASCADE,
    FOREIGN KEY (device_b_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dhcp_leases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    lease_state TEXT NOT NULL DEFAULT 'active', -- 'active', 'released'
    assigned_at TEXT NOT NULL,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ip_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    device_ids TEXT NOT NULL,     -- JSON array of device IDs, e.g. '[1, 2]'
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'resolved'
    detected_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER NOT NULL,
    alert_type TEXT NOT NULL,     -- 'unapproved_device', 'ip_conflict', 'dhcp_exhausted', 'disconnected_device', 'invalid_ip'
    device_id INTEGER,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active', -- 'active', 'acknowledged', 'dismissed'
    created_at TEXT NOT NULL,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS simulation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    network_id INTEGER NOT NULL,
    category TEXT NOT NULL,       -- 'network', 'device', 'connection', 'dhcp', 'conflict', 'ping', 'approval'
    level TEXT NOT NULL DEFAULT 'info', -- 'info', 'success', 'warning', 'danger'
    message TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (network_id) REFERENCES networks(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_devices_network ON devices(network_id);
CREATE INDEX IF NOT EXISTS idx_connections_network ON connections(network_id);
CREATE INDEX IF NOT EXISTS idx_events_network ON simulation_events(network_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_network ON ip_conflicts(network_id);
CREATE INDEX IF NOT EXISTS idx_alerts_network ON alerts(network_id);
