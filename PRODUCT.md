# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Academic and Computer Networks students, educators, and lab instructors demonstrating ARP discovery, subnet calculation, rogue device detection, and IP collision resolution, as well as home lab / SOHO administrators seeking clear visibility into private LANs.

## Product Purpose

NodeScope is a lightweight LAN monitoring, rogue device detection, and IP conflict resolution assistance system. It provides real-time visibility into local network devices, identifies unfamiliar MAC addresses against an approved registry, flags dual-MAC collisions on shared IP addresses, and provides structured, step-by-step manual remediation guidance.

## Positioning

Unlike complex enterprise topology mappers or passive sniffers, NodeScope operates as a safe, educational diagnostic assistant. It pairs Scapy ARP discovery with an explicit Approved Device Registry and an intelligent candidate IP calculator in the local /24 subnet, presenting conflicts with clear technical evidence rather than automatic accusations or risky remote changes.

## Operating Context

Academic computer networking laboratories, classroom demonstrations, project evaluations, and personal home labs. Typically executed locally via PowerShell (`flask run`) or in permission-free demo mode (`$env:NODESCOPE_DEMO="1"; flask run`) when raw socket permissions or Npcap drivers are unavailable.

## Capabilities and Constraints

### Capabilities
- **Subnet Validation & ARP Scanning:** Validates CIDR notation, restricts scans to private IPv4 ranges, and limits scanning scope to subnets up to /22 (max 1022 hosts) using Scapy.
- **Approved Device Registry:** Tracks MAC addresses, allows renaming and approval, and flags unapproved devices as potential rogues.
- **Conflict Detection:** Identifies IP addresses responding from multiple distinct MAC addresses, capturing timestamps and raw observation history.
- **Guided Resolution:** Analyzes in-use addresses in the subnet, computes free candidate alternative IPs, and produces manual reconfiguration checklists.
- **Activity & Alerts Audit Log:** Records notable network events with 60-second deduplication and offers alert triage (acknowledge/dismiss).
- **Demo Mode:** Built-in seed and reset CLI commands (`flask seed-demo`, `flask reset-demo`) for deterministic, permissionless lab demonstrations.

### Constraints
- **Read-Only / Advisory:** NodeScope never executes remote host reconfiguration or packet disruption; remediation is strictly manual by the network administrator.
- **Scope Limit:** Supports only IPv4 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.0.0/16, 127.0.0.0/8).
- **Windows Live Scanning Dependency:** Requires Npcap installed with WinPcap compatibility for live ARP socket broadcasts.
- **Architectural Stack:** Python 3.11+, Flask 3.1, SQLite (`sqlite3`), Bootstrap 5, Jinja2 templates, vanilla JavaScript.

## Brand Commitments

- **Name:** NodeScope
- **Voice:** Clear, technical, objective, and educational. Avoid alarmist warnings; use accurate network terminology (CIDR, ARP, MAC, Subnet, Broadcast).
- **Design Philosophy:** Utilitarian, scannable dashboard UI with clear status indicators and badges.

## Evidence on Hand

- Complete working Flask application with SQLite database schema ([`database/schema.sql`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/database/schema.sql)).
- Comprehensive pytest test suite with 49 passing tests ([`tests/`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/tests)).
- Realistic demo data generator with sample rogue devices and IP conflicts ([`demo/seed.py`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/demo/seed.py)).
- Project overview, architecture diagrams, and setup instructions ([`README.md`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/README.md)).

## Product Principles

1. **Safety First, No Silent Mutations:** Never attempt remote host reconfiguration or active ARP spoofing/blocking; provide actionable, manual guidance with clear explanations.
2. **Evidence-Based Diagnostics:** Present multi-MAC observations as "Possible Conflicts" backed by timestamped observations and technical caveats (ARP caching, VM interfaces, MAC randomization).
3. **Zero-Friction Educational Demonstration:** Always provide a reliable, deterministic demo mode so students and instructors can evaluate and demonstrate workflows without special network privileges.
4. **Operational Clarity:** High-contrast, scannable, accessible UI prioritizing status badges, structured tables, and clear step-by-step remediation flows.
