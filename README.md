# NodeScope

**Interactive Virtual LAN Simulator and Network Troubleshooting Lab**

A Computer Networks engineering mini-project built with **Python (Flask)**, **SQLite**, **HTML5/SVG**, and **Bootstrap 5**.

---

## 1. Project Overview

**NodeScope** is a fully simulation-based virtual Local Area Network (LAN) creation, configuration, and troubleshooting platform. Designed specifically as an educational laboratory for Computer Engineering students and educators, it allows users to:

- Create and manage virtual IPv4 private networks.
- Interactively build network topologies using an intuitive SVG-powered drag-and-drop canvas.
- Configure virtual devices with static IPs or dynamic DHCP leases.
- Deterministically simulate end-to-end communication using a graph-traversal ICMP Ping engine.
- Inspect Layer 2 to Layer 3 bindings in a real-time Virtual ARP Table.
- Intentionally trigger duplicate IPv4 address collisions and resolve them in real-time using an intelligent **Guided Conflict Resolution** workflow.
- Audit network activity, link changes, and rogue device security alerts.

> [!IMPORTANT]
> **100% Simulation-Based:** NodeScope requires **no physical network scanning**, **no raw sockets**, **no Npcap/WinPcap**, and **no administrator privileges**. All networking rules are evaluated deterministically using Python standard library networking logic.

---

## 2. Core Modules & Features

| Module | Features & Capabilities |
| :--- | :--- |
| **1. Network Management** | Create virtual LAN projects with custom CIDR subnets (e.g., `192.168.10.0/24`), subnet masks, default gateways, and configurable DHCP lease pools. Saved networks persist across restarts in SQLite. |
| **2. Interactive Topology Workspace** | Interactive visual workspace with draggable nodes, dynamic SVG connection lines, live status badges, online/offline toggles, and collision halo indicators. |
| **3. Device Inventory & Palette** | Add End Devices (Laptops, Desktops, Smartphones, Printers, Servers) and Networking Devices (Routers, Core Switches, Wireless Access Points). Automatically generates locally-administered unicast MAC addresses (`02:xx:xx:...`). |
| **4. Static & DHCP Addressing** | Configurable IP allocation mode. Supports static address configuration with duplicate detection, as well as a virtual DHCP server that allocates leases sequentially, tracks active leases, and detects pool exhaustion. |
| **5. IP Conflict Detection & Resolution** | Automatically detects when two active interfaces share an identical IPv4 address on the LAN. Highlights colliding devices, flags ambiguous ARP entries, computes free candidate IPs in the subnet, and applies real-time database reconfigurations. |
| **6. ICMP Ping Simulator** | Deterministic reachability analysis based on device power states, IP validity, same-subnet membership, and Breadth-First Search (BFS) graph path continuity through intermediate switches. |
| **7. Virtual ARP Table** | Educational Layer 2 (MAC) to Layer 3 (IP) resolution table displaying dynamic bindings and flagging ambiguous mappings caused by IP conflicts. |
| **8. Security Triage & Event Console** | Unapproved rogue host flagging, administrator authorization workflow, and persistent timestamped event logging. |

---

## 3. Technology Stack

- **Backend:** Python 3.11+ / Python 3.14, Flask 3.x
- **Database:** SQLite via Python's built-in `sqlite3` (parameterized queries, foreign keys, and indexes)
- **Networking Logic:** Python built-in `ipaddress` module
- **Testing:** Pytest 8.x, pytest-flask
- **Frontend:** HTML5, CSS3, Bootstrap 5 (CDN), Bootstrap Icons, Vanilla JavaScript, SVG Vector Graphics

---

## 4. Architecture & Project Structure

```text
NodeScope/
├── app.py                      # Application entry point & CLI commands
├── requirements.txt            # Minimal dependencies (Flask, Pytest)
├── README.md                   # Complete documentation & setup instructions
├── database/
│   ├── db.py                   # SQLite connection pooling & initialization
│   └── schema.sql              # Normalized relational schema (networks, devices, links, leases, conflicts)
├── simulator/                  # Pure Python simulation & networking engine
│   ├── addressing.py           # CIDR calculations, IP/MAC validation & candidate discovery
│   ├── dhcp.py                 # Virtual DHCP pool allocator & lease lifecycle
│   ├── connectivity.py         # BFS graph traversal for topological link paths
│   ├── conflicts.py            # Duplicate IP detection & real-time resolution
│   ├── ping.py                 # Deterministic ICMP Ping diagnostic engine
│   ├── arp.py                  # Virtual ARP resolution & collision table
│   ├── events.py               # Activity audit logging & alert triage
│   └── scenarios.py            # 5 Pre-packaged educational presentation setups
├── routes/
│   ├── views.py                # HTML routes: Welcome (/), Workspace (/workspace/<id>), History (/history/<id>)
│   └── api.py                  # REST JSON API for dynamic canvas operations
├── templates/
│   ├── base.html               # Master layout with NodeScope logo & global creation modal
│   ├── index.html              # Welcome screen, saved networks & scenario launcher
│   ├── workspace.html          # Central interactive topology workspace & tools
│   └── history.html            # Event audit stream & security alerts history
├── static/
│   ├── css/nodescope.css       # Custom cyber-indigo design tokens & node styles
│   ├── js/workspace.js         # Vanilla JS drag-and-drop & canvas SVG engine
│   └── img/                    # NodeScope vector logo & favicons
└── tests/                      # Automated Pytest suite (18 unit & integration tests)
```

---

## 5. Local Setup on Windows (VS Code)

### Prerequisites

- **Python 3.11 or newer** installed (ensure "Add Python to PATH" is checked during installation).
- **Git** installed.
- **VS Code** (recommended editor).

### Step 1: Open Terminal in Project Directory

Open Windows PowerShell or VS Code Integrated Terminal (`Ctrl + ~`) in the project directory:

```powershell
cd C:\Path\To\NodeScope
```

### Step 2: Activate Virtual Environment

If a virtual environment is not already created:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(If PowerShell execution policy restricts script execution, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`)*

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application

```powershell
python app.py
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:5000/`**

---

## 6. Running the Test Suite

Run the full automated test suite using Pytest:

```powershell
pytest
```

All 18 tests will execute in in-memory SQLite, verifying network creation, device management, DHCP leases, BFS connectivity, conflict detection, resolution, ping rules, and API endpoints.

---

## 7. Educational Viva & Presentation Scenarios

NodeScope comes pre-loaded with **5 ready-made demonstration scenarios** designed for live classroom and viva evaluations:

| Scenario | Objective & What to Demonstrate |
| :--- | :--- |
| **Scenario 1: Working Computer Lab** | A standard healthy star topology (Gateway router, central switch, 2 workstations, laptop, printer). Demonstrate opening the **Ping Simulator**, selecting Workstation 1 → Workstation 2, and observing the successful ICMP reply and BFS path trace (`PC1 → Switch → PC2`). |
| **Scenario 2: Duplicate IP Conflict** | Workstation Alpha and Beta are both assigned static IP `192.168.10.50`. Show the pulsing red collision halo on the canvas. Open the **Conflicts & Resolution** tab, click **Guided Resolution**, select Workstation Beta, review the suggested candidate IP (`192.168.10.2`), and click **Apply Resolution**. Witness the conflict immediately clear and the ARP table return to normal. |
| **Scenario 3: DHCP Dynamic Leases** | Demonstrates dynamic host configuration over a Wireless Access Point. Show dynamic address assignment from the pool, inspect the leases, and demonstrate releasing/renewing leases. |
| **Scenario 4: Disconnected Device Diagnostic** | Workstation 2 is physically disconnected from the departmental switch. Demonstrate running a ping and explaining why it fails (`No active physical or wireless link connects...`). Use the **Connect Link** tool to bridge the cable, re-ping, and show instant recovery. |
| **Scenario 5: Unapproved Rogue Device** | An unauthorized personal laptop attaches to the LAN. Demonstrate security triage: observe the yellow dashed unapproved badge, inspect the security alert, and perform administrator approval. |

---

## 8. Presentation Walkthrough Script (Step-by-Step Viva Demo)

1. **Launch & Overview:**
   - Run `python app.py` and open `http://127.0.0.1:5000/`.
   - Explain the motivation: Home/SOHO networks lack visibility; this lab models LAN dynamics, ARP, and IP conflicts safely without complex physical hardware.
2. **Create a Virtual LAN:**
   - Click **Create New Virtual LAN**. Enter Name: `College Lab`, Subnet: `192.168.10.0/24`, Gateway: `192.168.10.1`, DHCP Range: `192.168.10.100–192.168.10.150`.
   - Click **Create & Open Workspace**.
3. **Build the Topology:**
   - From the left palette, add a **Switch**, a **Desktop PC**, and a **Laptop**.
   - Drag them into position on the canvas.
   - Click **Connect Link**, click the Desktop then the Switch. Repeat to connect the Switch to the Default Gateway Router.
4. **Test DHCP & Ping:**
   - Select the Desktop, verify it received a DHCP lease (`192.168.10.100`).
   - Open the **Ping Simulator** tab at the bottom, select Desktop → Router, and click **Simulate Ping**. Show the 5-step verification breakdown (Power, IP assignment, Subnet check, Conflict check, Topology path).
5. **Demonstrate IP Conflict & Guided Resolution:**
   - Select the Laptop, switch to **Static** mode, and intentionally enter `192.168.10.100`.
   - Click Save. Instantly, both the Desktop and Laptop light up with a **pulsing red conflict halo**.
   - Show the **Virtual ARP Table** tab: point out the `AMBIGUOUS (IP Conflict)` status.
   - Click **Resolve Conflict** in the property panel or bottom tab.
   - Accept the candidate free IP calculated by NodeScope, click **Apply Resolution**.
   - Show that the conflict clears, the nodes turn healthy green, and the event is permanently stored in **Activity History**.

---

## 9. Deliberate Simulation Assumptions & Limitations

- **Single Broadcast Domain:** Models one virtual IPv4 LAN per saved project. Multi-router inter-LAN routing protocols (OSPF/BGP) and VLAN tagging are intentionally out of scope.
- **Layer 2 Simplification:** Switches and Access Points act as transparent forwarding hubs without simulating Spanning Tree Protocol (STP) convergence delays.
- **Deterministic ICMP:** Ping evaluations are rule-based and deterministic rather than relying on randomized artificial packet loss.

---

## 10. License

Developed for academic and educational demonstration purposes under the **MIT License**.
