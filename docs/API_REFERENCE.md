# NodeScope — REST API Reference Specification

NodeScope provides a lightweight, JSON-based RESTful API consumed by the frontend topology canvas and available for programmatic automation.

---

## 1. Network Management Endpoints

### `GET /api/networks`
Retrieve all saved virtual LAN projects.
- **Response**:
```json
{
  "success": true,
  "networks": [
    {
      "id": 1,
      "name": "College Computer Lab",
      "subnet": "192.168.10.0/24",
      "netmask": "255.255.255.0",
      "gateway": "192.168.10.1",
      "dhcp_enabled": 1,
      "dhcp_start": "192.168.10.100",
      "dhcp_end": "192.168.10.150",
      "device_count": 6,
      "conflict_count": 0
    }
  ]
}
```

### `POST /api/networks`
Create a new virtual LAN.
- **Payload**:
```json
{
  "name": "Engineering Lab",
  "subnet": "192.168.20.0/24",
  "gateway": "192.168.20.1",
  "dhcp_enabled": true,
  "dhcp_start": "192.168.20.100",
  "dhcp_end": "192.168.20.200"
}
```
- **Response**: `{"success": true, "network_id": 2}`

### `GET /api/networks/:id/topology`
Fetch the complete snapshot of the topology workspace, including devices, connections, active conflicts, and recent events.
- **Response**:
```json
{
  "success": true,
  "network": { "id": 1, "name": "...", "subnet": "...", "gateway": "..." },
  "devices": [
    {
      "id": 10,
      "name": "Workstation 01",
      "device_type": "desktop",
      "ip_mode": "dhcp",
      "ip_address": "192.168.10.101",
      "mac_address": "02:1a:2b:3c:4d:5e",
      "pos_x": 320,
      "pos_y": 140,
      "is_online": 1,
      "is_approved": 1,
      "in_conflict": false
    }
  ],
  "connections": [
    { "id": 5, "device_a_id": 10, "device_b_id": 2, "link_type": "wired", "status": "active" }
  ],
  "conflicts": [],
  "recent_events": []
}
```

---

## 2. Device Management Endpoints

### `POST /api/networks/:id/devices`
Add a new virtual device to the network canvas.
- **Payload**:
```json
{
  "name": "Laptop 02",
  "device_type": "laptop",
  "pos_x": 200,
  "pos_y": 180,
  "ip_mode": "dhcp",
  "is_approved": 1
}
```
- **Response**: `{"success": true, "device": { ... }}`

### `PUT /api/devices/:id`
Update device properties (coordinates, power state, approval status, static IP).
- **Payload**:
```json
{
  "name": "Core Server",
  "pos_x": 450,
  "pos_y": 210,
  "is_online": 1,
  "is_approved": 1,
  "ip_mode": "static",
  "ip_address": "192.168.10.20"
}
```
- **Response**: `{"success": true, "device": { ... }}`

### `DELETE /api/devices/:id`
Remove a device and cascade-delete its connection links and DHCP leases.
- **Response**: `{"success": true, "message": "Device deleted."}`

### `POST /api/devices/:id/dhcp`
Request or renew a dynamic DHCP lease.
- **Response**: `{"success": true, "ip_address": "192.168.10.103", "lease": { ... }}`

### `POST /api/devices/:id/dhcp/release`
Release an active DHCP lease back to the address pool.
- **Response**: `{"success": true, "message": "Lease released."}`

---

## 3. Network Connections Endpoints

### `POST /api/networks/:id/connections`
Bridge a link between two devices.
- **Payload**:
```json
{
  "device_a_id": 10,
  "device_b_id": 2,
  "link_type": "wired"
}
```
- **Response**: `{"success": true, "connection": { ... }}`

### `DELETE /api/connections/:id`
Remove an existing connection link.
- **Response**: `{"success": true, "message": "Connection removed."}`

---

## 4. Diagnostics & Troubleshooting Endpoints

### `POST /api/networks/:id/ping`
Run deterministic ICMP Ping reachability and path verification.
- **Payload**:
```json
{
  "source_id": 10,
  "destination_id": 12
}
```
- **Response (Success)**:
```json
{
  "success": true,
  "result": {
    "status": "success",
    "rtt_ms": 2.4,
    "ttl": 64,
    "message": "Reply from 192.168.10.102: bytes=32 time=2.4ms TTL=64",
    "steps": [
      { "check": "Source Device", "passed": true, "detail": "Workstation 01 is powered ON" },
      { "check": "Destination Device", "passed": true, "detail": "Workstation 02 is powered ON" },
      { "check": "IP Configuration", "passed": true, "detail": "192.168.10.101 -> 192.168.10.102" },
      { "check": "Subnet Membership", "passed": true, "detail": "Both hosts reside on 192.168.10.0/24" },
      { "check": "IP Conflict Check", "passed": true, "detail": "No active address collision detected" },
      { "check": "Topology Forwarding Path", "passed": true, "detail": "Path: Workstation 01 -> Switch -> Workstation 02" }
    ]
  }
}
```

### `GET /api/networks/:id/arp`
Fetch the active Layer 2 to Layer 3 Virtual ARP table entries.
- **Response**:
```json
{
  "success": true,
  "arp_table": [
    {
      "ip_address": "192.168.10.1",
      "mac_address": "02:00:c0:a8:0a:01",
      "device_name": "Gateway Router",
      "device_type": "router",
      "status": "VALID (Gateway)",
      "is_conflict": false,
      "notes": "Default Gateway Interface"
    }
  ]
}
```

### `GET /api/conflicts/:id`
Inspect active IP collision diagnostic details and candidate recommendations.
- **Response**:
```json
{
  "success": true,
  "diagnostic": {
    "conflict_id": 1,
    "ip_address": "192.168.10.50",
    "suggested_ip": "192.168.10.2",
    "devices": [
      { "id": 4, "name": "Workstation Alpha", "mac_address": "02:00:c0:a8:0a:32" },
      { "id": 5, "name": "Workstation Beta", "mac_address": "02:00:c0:a8:0a:33" }
    ]
  }
}
```

### `POST /api/conflicts/:id/resolve`
Apply guided resolution to clear an IP collision.
- **Payload**:
```json
{
  "target_device_id": 5,
  "mode": "static",
  "new_ip": "192.168.10.2"
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Assigned new static IP 192.168.10.2 to 'Workstation Beta'. Conflict resolved."
}
```
