-- NodeScope database schema
-- All timestamps stored as ISO 8601 UTC strings

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subnet TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',  -- running, completed, failed
    device_count INTEGER DEFAULT 0,
    error_message TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mac_address TEXT NOT NULL UNIQUE,
    ip_address TEXT,
    friendly_name TEXT,
    approved INTEGER NOT NULL DEFAULT 0,  -- 0=unknown/needs_review, 1=approved
    notes TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS device_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL,
    mac_address TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,  -- unknown_device, ip_conflict, ip_change
    device_mac TEXT,
    ip_address TEXT,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- active, acknowledged, dismissed
    created_at TEXT NOT NULL,
    acknowledged_at TEXT,
    notes TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ip_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL,
    mac_address_1 TEXT NOT NULL,
    mac_address_2 TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'possible_conflict',  -- possible_conflict, under_investigation, resolved
    evidence TEXT,   -- JSON: list of observations
    investigation_notes TEXT,
    is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS activity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    -- device_discovered, device_not_seen, ip_changed, conflict_detected,
    -- conflict_resolved, device_approved, alert_created
    device_mac TEXT,
    ip_address TEXT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS resolution_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conflict_id INTEGER NOT NULL,
    recommended_ip TEXT,
    action_taken TEXT,
    admin_notes TEXT,
    created_at TEXT NOT NULL,
    verified INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (conflict_id) REFERENCES ip_conflicts(id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_observations_ip ON device_observations(ip_address);
CREATE INDEX IF NOT EXISTS idx_observations_mac ON device_observations(mac_address);
CREATE INDEX IF NOT EXISTS idx_conflicts_ip ON ip_conflicts(ip_address);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_events_type ON activity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_devices_mac ON devices(mac_address);
