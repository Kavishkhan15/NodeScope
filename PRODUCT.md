# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Academic and Computer Networks students, educators, and lab instructors demonstrating virtual LAN creation, subnet calculations, dynamic DHCP leases, Layer 2/3 ARP binding, ICMP ping reachability, and intentional IP collision troubleshooting during college presentations and vivas.

## Product Purpose

NodeScope is an interactive virtual LAN creation, configuration, and network troubleshooting laboratory. It provides a visual, drag-and-drop network topology canvas, models realistic IPv4 addressing, DHCP lease pools, and ARP resolution, and enables students to intentionally introduce and resolve IP address conflicts with step-by-step diagnostic guidance.

## Positioning

Unlike complex packet-level enterprise emulators (e.g. Cisco Packet Tracer) or passive hardware packet sniffers, NodeScope is a zero-privilege, 100% simulation-based educational platform. It runs locally with standard Python and Flask, requires no Npcap or root permissions, and provides immediate, deterministic feedback on networking rules and address collisions.

## Operating Context

Academic computer networking laboratories, viva examinations, student project presentations, and personal home study. Runs on local Windows systems via PowerShell (`python app.py`) with zero external network dependencies.

## Capabilities and Constraints

### Capabilities
- **Virtual Network Creation Wizard:** Configures IPv4 CIDR subnets, subnet masks, default gateways, and dynamic DHCP ranges with strict validation.
- **Interactive Topology Canvas:** Drag-and-drop device nodes with live SVG connection lines, power status indicators, unapproved device badges, and pulsing conflict halos.
- **Multi-Device Palette:** Supports End Devices (Laptops, Desktops, Smartphones, Printers, Servers) and Networking Devices (Routers, Switches, Access Points) with auto-generated unique MACs.
- **Dynamic DHCP & Static Addressing:** Simulates sequential DHCP pool allocation, lease renewal, lease release, and pool exhaustion, as well as manual static assignments.
- **Deterministic Ping Engine:** Uses Breadth-First Search (BFS) graph traversal to evaluate end-to-end path continuity, power states, and subnet alignment.
- **Virtual ARP Table:** Displays Layer 2 to Layer 3 mappings and flags ambiguous duplicate IP bindings.
- **Guided Conflict Resolution:** Automatically detects IP collisions, computes free candidate IPs in the subnet, and applies real-time database reconfigurations.
- **5 Educational Demo Scenarios:** One-click pre-configured setups for live classroom demonstrations.

### Constraints
- **Single Broadcast Domain:** Models one virtual IPv4 LAN per saved project; inter-LAN routing protocols (OSPF/BGP) and VLANs are out of scope.
- **Layer 2 Simplification:** Switches and APs forward frames without simulating STP convergence delays.
- **Simulation Only:** Does not transmit real physical packets or interact with physical network interfaces.

## Brand Commitments

- **Name:** NodeScope
- **Tagline:** Interactive Virtual LAN Simulator and Network Troubleshooting Lab
- **Voice:** Educational, technically rigorous, objective, and beginner-friendly.
- **Aesthetic:** Dark-navy header with cyber-indigo, cyan, and violet accents, high-contrast status dots, and clean Bootstrap 5 cards.

## Evidence on Hand

- Complete working application with SQLite schema ([`database/schema.sql`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/database/schema.sql)).
- Automated Pytest test suite with 18 passing unit and integration tests ([`tests/`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/tests)).
- Pre-packaged educational presentation scenarios ([`simulator/scenarios.py`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/simulator/scenarios.py)).
- Project overview, architecture, and Windows setup instructions in [`README.md`](file:///C:/Users/kavish/OneDrive/Attachments/Documents/GitHub/NodeScope/README.md).

## Product Principles

1. **Zero-Privilege Reliability:** Must run anywhere out of the box with `python app.py` without requiring raw sockets, WinPcap/Npcap, or administrator rights.
2. **Deterministic Networking Rules:** Never rely on randomized packet loss; all communication verdicts must stem from verified topology paths, power states, and IP validity.
3. **Real In-Memory & Database Resolution:** Conflict resolution must actually reconfigure the simulated device in SQLite and re-verify the network, not merely hide visual alerts.
4. **Presentation-Ready Usability:** High-contrast visual indicators, intuitive drag-and-drop topology, and one-click demo scenarios for seamless college presentations.
