# NodeScope

**Smart LAN Monitoring, Rogue Device Detection and IP Conflict Resolution Assistance System**

A Computer Networks mini-project built with Flask, Bootstrap 5 and Python.

---

## Problem Statement

Home and small-office networks are rarely monitored. Unknown devices connect unnoticed, IP address conflicts silently disrupt connectivity, and network changes are never recorded. Administrators have no structured way to investigate or resolve these issues.

## Objectives

- Discover devices on a local network using ARP scanning.
- Identify unfamiliar devices that are not in the approved registry.
- Detect possible IP address conflicts from scan observations.
- Record all network changes in a searchable history.
- Guide administrators step-by-step through conflict resolution.

---

## How it Differs from NetMap

This project was built independently from scratch. The NetMap repository (GPL-3.0, github.com/xoriin/netmap) was consulted as a reference only for understanding general approaches to network discovery. NodeScope uses a completely different stack (Flask vs FastAPI, Bootstrap 5 vs React, sqlite3 vs SQLAlchemy), different page designs, different branding, and focuses specifically on rogue-device detection and guided conflict resolution rather than topology mapping.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, Flask 3.1 |
| Network discovery | Scapy (ARP scan) |
| Database | SQLite via Python's built-in `sqlite3` |
| Frontend | HTML5, CSS3, Bootstrap 5 (CDN), Vanilla JavaScript |
| Testing | Pytest 8, pytest-flask |
| Platform | Windows (VS Code) |

---

## Features

### 1. Local Network Discovery
ARP-based scan of a private subnet. Validates CIDR input, restricts to private ranges, limits to /22 (1022 hosts maximum). Falls back to demo mode when raw sockets are unavailable (no administrator privileges needed for demo).

### 2. Approved Device Registry and Rogue Detection
Every observed MAC address is compared against the approved registry. Unknown devices trigger an alert. Administrators can approve devices, assign friendly names, and add notes.

### 3. IP Conflict Detection
Identifies IP addresses observed responding from more than one MAC address. Records the conflicting MACs, timestamps and evidence. Uses statuses: `Possible Conflict → Under Investigation → Resolved`.

**Important:** Multiple MACs for one IP may also be caused by ARP caching, proxy ARP, virtual machines or MAC randomisation. NodeScope presents these as *possible* conflicts requiring investigation, not automatic accusations.

### 4. Device Identity and Activity History
Records every notable network event: new devices, IP changes, conflict detections, approvals, and alert dismissals. Deduplicates events within 60 seconds to avoid log flooding. Supports filtering by event type.

### 5. Guided IP Conflict Resolution
When a conflict is detected, NodeScope:
1. Explains why the conflict was flagged.
2. Suggests a candidate alternative IP in the same /24 subnet (excluding network, gateway, broadcast, and known-in-use addresses).
3. Lists step-by-step corrective actions.
4. Records the administrator's resolution attempt.
5. Allows verification after a follow-up scan.

NodeScope **cannot** remotely reconfigure devices. All changes must be made manually on the affected device(s).

---

## Pages

| Page | URL | Purpose |
|------|-----|---------|
| Dashboard | `/` | Stats, latest scan, recent alerts and activity |
| Device Inventory | `/inventory/` | All devices, search, approve |
| Network Scan | `/scan/` | Run ARP scan or load demo |
| IP Conflicts | `/conflicts/` | List and investigate conflicts |
| Activity History | `/history` | Filtered event log |
| Alerts | `/alerts` | Acknowledge and dismiss alerts |

---

## Database Schema

```
scans              — scan runs with subnet, status, timestamps
devices            — known devices with MAC, IP, approval status
device_observations — raw per-scan IP/MAC pairs
alerts             — active and resolved alerts
ip_conflicts       — detected conflicts with evidence
activity_events    — deduplicated event log
resolution_actions — administrator resolution attempts
```

All tables include an `is_demo` column so demo records can be added and removed independently from real records.

---

## Architecture

```
app.py
├── database/
│   ├── schema.sql     — CREATE TABLE statements
│   └── db.py          — get_db(), init_db(), Flask teardown
├── services/
│   ├── discovery.py        — ARP scan (Scapy), subnet validation, demo fallback
│   ├── device_registry.py  — register observations, approve devices
│   ├── conflict_detection.py — detect IP→multi-MAC, record conflicts
│   ├── activity_history.py — record events, create alerts
│   └── resolution.py       — suggest alternative IPs, record actions
├── routes/
│   ├── dashboard.py   — GET /
│   ├── inventory.py   — /inventory/
│   ├── scan.py        — /scan/
│   ├── conflicts.py   — /conflicts/
│   └── history.py     — /history, /alerts
├── templates/         — Jinja2 + Bootstrap 5 HTML
├── static/            — nodescope.css, nodescope.js
├── demo/seed.py       — demo data seeding and reset
└── tests/             — pytest test suite (49 tests)
```

---

## Setup on Windows (VS Code)

### Prerequisites

- Python 3.11 or later — https://www.python.org/downloads/
- Git — https://git-scm.com/
- VS Code — https://code.visualstudio.com/
- Npcap (for live scanning only) — https://npcap.com/

### Step 1 — Clone the repository

```powershell
cd C:\Users\YourName\Documents
git clone https://github.com/Kavishkhan15/NodeScope.git
cd NodeScope
```

### Step 2 — Open in VS Code

```powershell
code .
```

### Step 3 — Create a virtual environment

```powershell
python -m venv venv
```

### Step 4 — Activate the virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

If you see an execution policy error, run this first (once):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 5 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 6 — Start NodeScope

```powershell
$env:FLASK_APP = "app"
flask run
```

Open your browser at: **http://127.0.0.1:5000**

The database is created automatically on first startup in the `instance/` folder.

---

## Demo Mode (No Network Permissions Required)

Demo mode loads simulated data without performing any real network scan. It works with no administrator privileges and no Npcap installed.

### Enable demo mode

```powershell
$env:FLASK_APP = "app"
$env:NODESCOPE_DEMO = "1"
flask run
```

### Load demo data from the browser

1. Go to **http://127.0.0.1:5000**
2. Click **Load Demo Data** on the Dashboard or Network Scan page
3. Explore all features with the pre-seeded data

### Load demo data from the terminal

```powershell
flask seed-demo
```

### Remove demo data

```powershell
flask reset-demo
```

---

## Live Network Scan (Windows)

Live scanning requires:
1. **Run VS Code or PowerShell as Administrator**
2. **Npcap installed** — https://npcap.com/ (free, select "WinPcap compatibility mode" during install)

Then:

```powershell
$env:FLASK_APP = "app"
flask run
```

Navigate to **Network Scan → enter your subnet → check the authorisation box → Start ARP Scan**.

Example subnet: `192.168.1.0/24`

Only scan networks you own or have explicit permission to scan.

---

## Running the Tests

```powershell
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

Expected: **49 passed**. No network access or elevated privileges needed — all tests use an in-memory SQLite database.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Activate.ps1 cannot be loaded` | Run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `Permission denied` on scan | Run VS Code/terminal as Administrator; install Npcap |
| `Scapy not installed` | `pip install scapy` |
| `No module named 'flask'` | Activate venv: `.\venv\Scripts\Activate.ps1` |
| Scan finds no devices | Your machine may need Npcap in WinPcap mode; try demo mode |
| `instance/nodescope.db` not created | Run `flask init-db` manually |

---

## Limitations

- ARP scanning only works on the same LAN segment. Devices on different VLANs or subnets are not reachable.
- NodeScope cannot change device IP configurations remotely.
- An ARP scan only sees devices that are online and respond. Sleeping, isolated, or firewall-protected devices may not appear.
- A "Possible Conflict" may be a false positive (stale ARP cache, VM, MAC randomisation). Always investigate before taking action.
- Conflict resolution suggestions are based on current observations only. A suggested IP might still be in use if the occupying device was offline during the scan.
- No user authentication is implemented — designed for local single-administrator use only.

---

## Future Scope

- Scheduled periodic scans with change notifications.
- DHCP lease file import to improve conflict analysis.
- Device type detection using MAC OUI prefix lookup.
- Export reports to PDF or CSV.
- Optional login for multi-user environments.

---

## How Network Discovery Works

NodeScope uses **ARP (Address Resolution Protocol)** to discover devices:

1. For each target IP in the subnet, an ARP request is broadcast: *"Who has IP x.x.x.x?"*
2. Online devices that own that IP reply with their MAC address.
3. NodeScope collects the IP↔MAC pairs from all replies.

Scapy sends these packets at the Ethernet layer. On Windows this requires Npcap (a packet capture driver). On Linux/Mac, raw socket access is needed (`sudo` or `CAP_NET_RAW`).

---

## Viva Preparation

**Q: What is an IP address?**
A: A logical address assigned to a device to identify it on a network. IPv4 addresses are 32-bit numbers written as four octets (e.g. 192.168.1.10).

**Q: What is a MAC address?**
A: A hardware address permanently assigned to a network interface. It is 48 bits, written as six hex pairs (e.g. AA:BB:CC:DD:EE:FF). MAC addresses operate at Layer 2 (Data Link).

**Q: What is ARP?**
A: Address Resolution Protocol maps an IP address to a MAC address on a local network. A device broadcasts "Who has IP x?" and the owner replies with its MAC. NodeScope uses ARP requests to discover all responding devices in a subnet.

**Q: What is an IP conflict?**
A: When two devices are configured with the same IP address. Both try to claim the address, causing connection failures, dropped packets, and unpredictable behaviour for both devices.

**Q: How does NodeScope identify an unknown device?**
A: Every observed MAC address is looked up in the approved device registry. If the MAC is not present or not approved, the device is flagged as Unknown and an alert is created.

**Q: How does NodeScope detect a possible IP conflict?**
A: It groups ARP observations by IP address. If the same IP appears with two or more different MAC addresses in one scan, NodeScope records it as a possible conflict.

**Q: Why might a conflict alert be a false positive?**
A: ARP caching can cause a device to respond briefly on behalf of another IP it recently communicated with. Virtual machines or containers may share a host's NIC with their own virtual MACs. Mobile devices use MAC randomisation, making them appear as new devices on each connection. NodeScope marks these as *possible* conflicts, not confirmed ones.

**Q: Why is changing a device's IP different from detecting a conflict?**
A: Detection only requires reading ARP packets passively. Changing an IP requires logging into the device's operating system or network configuration and modifying its settings — something NodeScope deliberately does not do, to avoid accidental or unauthorised network changes.

**Q: What is the difference between DHCP and a static IP?**
A: DHCP (Dynamic Host Configuration Protocol) automatically assigns IP addresses from a pool managed by a router or server. A static IP is manually configured on the device and does not change. Conflicts are more common with static IPs because two administrators might assign the same address independently.

**Q: Why is guided resolution safer than automatic reconfiguration?**
A: Automatic reconfiguration could change the wrong device, break existing connections, or conflict with DHCP reservations. Guided resolution gives the administrator full visibility and control — they review the recommendation, verify it is appropriate for their specific network, make the change manually, and then confirm the result.

---

## Licence and Attribution

NodeScope is an original implementation created as a Computer Networks mini-project.

The NetMap repository (https://github.com/xoriin/netmap, GPL-3.0 licence) was consulted as a reference to understand network discovery approaches. No source code from NetMap was copied into NodeScope.

NodeScope is released under the MIT Licence.
