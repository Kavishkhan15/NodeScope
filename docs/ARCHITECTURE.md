# NodeScope — System Architecture & Simulation Engine Specification

**Interactive LAN Simulator and Network Troubleshooting Lab**  
*Document Version:* 2.0  
*Target Environment:* Educational Computer Networks Laboratory & Engineering Project  

---

## 1. High-Level Architectural Model

NodeScope adopts a decoupled **Model-View-Controller (MVC) + Pure Simulation Engine** pattern. The application executes locally inside a single Python Flask process, storing normalized network topologies in an embedded SQLite database and delivering a responsive, single-page-style SVG workspace to the client browser without external frontend frameworks or heavyweight build pipelines.

```
+-----------------------------------------------------------------------------------+
|                                 CLIENT BROWSER                                    |
|                                                                                   |
|  +--------------------+   +---------------------------+   +--------------------+  |
|  |   Device Palette   |   |   SVG Topology Canvas     |   | Property Inspector |  |
|  |  (Routers,Switches,|   |  (Draggable Nodes, Lines, |   | (DHCP/Static, IP,  |  |
|  |   PCs, APs, etc.)  |   |   Status Dots & Halos)    |   |   MAC, Gateways)   |  |
|  +--------------------+   +---------------------------+   +--------------------+  |
|                                         |                                         |
|  +-----------------------------------------------------------------------------+  |
|  |             Tabbed Simulation Console (Console, Ping, ARP, Conflicts)       |  |
|  +-----------------------------------------------------------------------------+  |
+----------------------------------------|------------------------------------------+
                                         | HTTP / JSON REST APIs
                                         v
+-----------------------------------------------------------------------------------+
|                             FLASK APPLICATION SERVER                              |
|                                                                                   |
|  +----------------------------------+       +----------------------------------+  |
|  |        View Routes               |       |         REST JSON API            |  |
|  |  GET /              (Dashboard)  |       |  POST/GET /api/networks          |  |
|  |  GET /workspace/:id (Workspace)  |       |  POST/PUT/DEL /api/devices       |  |
|  |  GET /history/:id   (Audit Logs) |       |  POST/DEL /api/connections       |  |
|  +----------------------------------+       +----------------------------------+  |
|                                         |                                         |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  |                        SIMULATION & NETWORKING ENGINE                       |  |
|  |                                                                             |  |
|  |   [Addressing]       [DHCP Server]      [BFS Topology]      [ARP Table]     |  |
|  |   CIDR & Subnet      Lease Lifecycle    Graph Traversal     Layer 2 to 3    |  |
|  |   Calculations       Pool Allocation    Path Reachability   Resolution      |  |
|  |                                                                             |  |
|  |   [IP Collision Engine]         [Deterministic Ping]      [Audit & Events]  |  |
|  |   Conflict Detection & Guided   ICMP Diagnostic &         Timestamped Event |  |
|  |   Candidate Discovery           Verification Pipeline     Stream & Alerts   |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |                                         |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  |                           EMBEDDED SQLITE DATABASE                          |  |
|  |      networks · devices · connections · dhcp_leases · ip_conflicts · events |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Relational Database Schema Design

The persistence tier relies on SQLite with `PRAGMA foreign_keys = ON;`. The relational structure guarantees referential integrity, cascading deletes, and indexed query performance.

```
 +------------------------+             1:N              +--------------------------+
 |        NETWORKS        |----------------------------->|         DEVICES          |
 +------------------------+                              +--------------------------+
 | id (PK, INTEGER)       |                              | id (PK, INTEGER)         |
 | name (TEXT)            |                              | network_id (FK, INTEGER) |
 | subnet (TEXT, CIDR)    |                              | name (TEXT)              |
 | netmask (TEXT)         |                              | device_type (TEXT)       |
 | gateway (TEXT)         |                              | ip_mode ('dhcp'|'static')|
 | dhcp_enabled (INTEGER) |                              | ip_address (TEXT)        |
 | dhcp_start (TEXT)      |                              | subnet_mask (TEXT)       |
 | dhcp_end (TEXT)        |                              | gateway (TEXT)           |
 | created_at (TIMESTAMP) |                              | mac_address (TEXT)       |
 +------------------------+                              | pos_x, pos_y (INTEGER)   |
      |             |                                    | is_online (INTEGER, bool)|
      | 1:N         | 1:N                                | is_approved (INT, bool)  |
      |             |                                    +--------------------------+
      |             |                                        |                  |
      |             v                                        | 1:N (endpoints)  | 1:N
      |      +---------------------+                         v                  |
      |      |     DHCP_LEASES     |               +---------------------+      |
      |      +---------------------+               |     CONNECTIONS     |      |
      |      | id (PK, INTEGER)    |               +---------------------+      |
      |      | network_id (FK)     |               | id (PK, INTEGER)    |      |
      |      | device_id (FK)      |<--------------| device_a_id (FK)    |      |
      |      | ip_address (TEXT)   |               | device_b_id (FK)    |      |
      |      | mac_address (TEXT)  |               | link_type ('wired') |      |
      |      | status ('active')   |               | status ('active')   |      |
      |      | granted_at (TIME)   |               +---------------------+      |
      |      +---------------------+                                            |
      v                                                                         v
+--------------------------+                               +--------------------------+
|       IP_CONFLICTS       |                               |      NETWORK_EVENTS      |
+--------------------------+                               +--------------------------+
| id (PK, INTEGER)         |                               | id (PK, INTEGER)         |
| network_id (FK)          |                               | network_id (FK)          |
| ip_address (TEXT)        |                               | category (TEXT)          |
| conflicting_devices (TXT)|                               | level ('info'|'danger')  |
| status ('active'|'fixed')|                               | message (TEXT)           |
| detected_at (TIMESTAMP)  |                               | created_at (TIMESTAMP)   |
+--------------------------+                               +--------------------------+
```

---

## 3. Core Simulation Algorithms

### 3.1 Addressing & Subnet Boundary Engine (`simulator/addressing.py`)
NodeScope evaluates all IPv4 addressing rules strictly using Python's standard `ipaddress` library:
- **CIDR Parse & Netmask Derivation**: Given a subnet string (e.g. `192.168.10.0/24`), extracts network address, broadcast address, and subnet mask (`255.255.255.0`).
- **Reserved IP Enforcement**: Rejects user assignment to the Network ID (`.0` in a `/24`) or the Broadcast address (`.255` in a `/24`).
- **Free Candidate Discovery**: When resolving an IP collision or allocating a lease, sequentially scans the subnet address space, cross-referencing all currently assigned device IPs and active DHCP allocations to return the lowest available free host IP.

### 3.2 Dynamic Host Configuration Protocol (DHCP) Engine (`simulator/dhcp.py`)
The virtual DHCP service models the standard DORA (Discover, Offer, Request, Acknowledge) outcome:
1. Validates that the requested device has an active network link and is marked `is_online = 1`.
2. Inspects existing active leases for the device's hardware MAC address. If a valid lease exists, it renews the binding.
3. If no lease exists, iterates through the configured range `[dhcp_start, dhcp_end]`.
4. If all pool addresses are claimed by online devices, triggers an explicit **DHCP Pool Exhaustion** diagnostic event.
5. On allocation, records a lease record and updates the device's assigned `ip_address`, `subnet_mask`, and `gateway`.

### 3.3 Topological Path Traversal & Breadth-First Search (`simulator/connectivity.py`)
Packet forwarding between two endpoints requires physical or link-layer path continuity:
- Construct an undirected adjacency list from the active records in the `connections` table.
- Filter edges: a link is only traversable if both attached devices are powered on (`is_online = 1`) and the link status is `active`.
- Execute a **Breadth-First Search (BFS)** traversal starting at `source_device_id` aiming for `destination_device_id`.
- Switches and Wireless Access Points act as Layer 2 multi-port forwarding devices that propagate the frame without consuming the Layer 3 address.
- Returns the complete hop-by-hop traversal trace:
  $$\text{PC 1} \longrightarrow \text{Core Switch} \longrightarrow \text{PC 2}$$

### 3.4 IP Address Conflict Detection & Real-Time Resolution (`simulator/conflicts.py`)
- **Detection Phase**: Scans all online devices with an assigned IPv4. Any IP address associated with $\ge 2$ distinct active hardware devices triggers an active conflict.
- **Canvas Alerting**: Flags devices with `in_conflict = True`, injecting a pulsing red halo and updating the top navigation conflict counter.
- **Resolution Phase**:
  - The guided resolver recommends the lowest unused candidate IP in the subnet.
  - The administrator selects which device to modify (or triggers DHCP lease migration).
  - The engine updates SQLite, clears the conflict state, writes an audit record, and updates the virtual ARP table.

### 3.5 Deterministic ICMP Ping Pipeline (`simulator/ping.py`)
Ping does not rely on random numbers; it evaluates an educational 6-step diagnostic chain:
1. **Source Power Check**: Source device must be powered on (`is_online == 1`).
2. **Destination Power Check**: Destination device must be powered on.
3. **Addressing Check**: Both devices must possess valid IPv4 addresses.
4. **Security Approval & Access Control (NAC)**: Neither device can be an unapproved rogue device (`is_approved == 0`). Network Access Control blocks unapproved devices until an administrator toggles approval.
5. **Subnet Compatibility Check**: Both devices must belong to the identical IPv4 network segment.
6. **No Active Collision**: Destination IP must not be in a collision state (simulates duplicate ARP reply confusion).
7. **Topological Graph Path**: Validates that an unbroken chain of switches/routers connects the two endpoints via BFS.

If all criteria hold, reports **ICMP Echo Reply** with calculated simulated Round-Trip Time (RTT: 1–4ms across switches, TTL: 64). If any criterion fails, reports the exact networking reason for failure (e.g. `Host Unreachable`, `Request Timed Out`, `Subnet Mismatch`, `UNAPPROVED NAC Block`).
