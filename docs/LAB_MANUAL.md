# NodeScope — Computer Networks Laboratory Manual & Viva Guide

**Department of Computer Engineering / Information Technology**  
*Course:* Computer Networks & Data Communications  
*Project Title:* NodeScope — Interactive Virtual LAN Simulator & Troubleshooting Lab  

---

## Index of Practical Experiments

| Exp No. | Experiment Title | Networking Concepts Covered |
| :---: | :--- | :--- |
| **01** | Virtual Local Area Network Setup & DHCP Pool Allocation | IPv4 Subnetting, Default Gateways, DORA Process, Leases |
| **02** | Layer 3 ICMP Ping & Topological Path Continuity (BFS) | Packet Forwarding, Star Topologies, Cable Fault Isolation |
| **03** | IPv4 Address Collisions, Virtual ARP Table & Guided Resolution | Duplicate IP Hazards, ARP Cache Poisoning, MAC-IP Bindings |
| **04** | Rogue Device Identification & Network Access Control (NAC) | Unapproved Hardware, MAC Filtering, Port Security Concepts |

---

## Experiment 1: Virtual Local Area Network Setup & DHCP Allocation

### 1.1 Objective
To create a private IPv4 Class C Local Area Network, configure subnet boundaries, establish a Default Gateway router, and verify dynamic IP assignment via DHCP.

### 1.2 Networking Theory
- **Subnetting (CIDR `/24`)**: A `/24` prefix yields a 32-bit netmask `255.255.255.0`, leaving 8 host bits ($2^8 - 2 = 254$ assignable host addresses).
- **Default Gateway**: The Layer 3 interface on the router (e.g. `192.168.10.1`) that serves as the access point for hosts sending packets outside their local subnet.
- **Dynamic Host Configuration Protocol (DHCP)**: Automatically provides network configuration parameters to client devices via the DORA process (Discover, Offer, Request, Acknowledge).

### 1.3 Step-by-Step Procedure
1. Launch NodeScope by executing `python app.py` and navigate to `http://127.0.0.1:5000`.
2. Click **Create New Virtual LAN**.
3. Configure the network parameters:
   - **Network Name**: `Engineering Lab A`
   - **Subnet (CIDR)**: `192.168.10.0/24`
   - **Default Gateway**: `192.168.10.1`
   - **DHCP Enabled**: Checked
   - **DHCP Start Range**: `192.168.10.100`
   - **DHCP End Range**: `192.168.10.150`
4. Click **Create & Open Workspace**.
5. Observe the initial topology: the Default Gateway Router is automatically generated at `192.168.10.1`.
6. From the left **Device Palette**, add one **Core Switch** and two **Desktop Workstations** (`PC 1`, `PC 2`).
7. Click the **Connect Link** tool:
   - Click `PC 1`, then click the `Core Switch`.
   - Click `PC 2`, then click the `Core Switch`.
   - Click the `Core Switch`, then click the `Gateway Router`.
8. Select `PC 1` to inspect its properties: observe that it has automatically received a dynamic lease `192.168.10.100` from the DHCP pool.
9. Select `PC 2`: observe that it has received the sequential lease `192.168.10.101`.

### 1.4 Expected Output
- All devices display green online status indicators.
- Connection links render as solid blue wired lines.
- IP labels below each node display their respective dynamically granted addresses.

---

## Experiment 2: End-to-End ICMP Ping & Fault Isolation

### 2.1 Objective
To analyze end-to-end network reachability using the ICMP Echo Request / Echo Reply protocol and diagnose topological link disconnections.

### 2.2 Networking Theory
- **ICMP (Internet Control Message Protocol)**: Operates at Layer 3 to perform diagnostic reachability tests.
- **Breadth-First Search (BFS) in Networks**: In a switched Ethernet LAN, forwarding decisions depend on active Layer 2 forwarding paths between switch ports. If a physical or logical link is severed, packets cannot traverse the segment.

### 2.3 Step-by-Step Procedure
1. Load **Scenario 1 (College Computer Lab)** from the welcome dashboard.
2. In the bottom simulation console, open the **Ping Simulator** tab.
3. Set **Source Device** to `Workstation 01 (192.168.10.101)`.
4. Set **Destination Device** to `Workstation 02 (192.168.10.102)`.
5. Click **Simulate Ping**.
6. Review the 5 verification checks:
   - Source is Powered On & Configured
   - Destination is Powered On & Configured
   - Same Subnet Compatibility (`192.168.10.0/24`)
   - Destination IP has No Active Conflict
   - Forwarding Path Verified (`Workstation 01 → Main Lab Switch → Workstation 02`)
7. Now simulate a fault: click the connection link between `Workstation 02` and the `Main Lab Switch`, and confirm deletion.
8. Re-run the ping from `Workstation 01` to `Workstation 02`.
9. Observe the result: **PING FAILED (DESTINATION UNREACHABLE)**. The path traversal reports `No active physical or wireless link connects Workstation 01 to Workstation 02`.
10. Use **Connect Link** to reconnect `Workstation 02` to the switch, re-run the ping, and observe immediate restoration of the ICMP reply.

---

## Experiment 3: IPv4 Address Collisions & Guided Resolution

### 3.1 Objective
To understand the causes and hazards of duplicate IP address conflicts in a Local Area Network, observe ambiguous ARP cache entries, and execute guided conflict resolution.

### 3.2 Networking Theory
- **IP Address Conflict**: Occurs when two distinct Network Interface Cards (NICs) on the same broadcast domain are configured with identical Layer 3 IP addresses.
- **ARP Ambiguity**: Address Resolution Protocol (ARP) maps an IP address to a hardware MAC address. When two MAC addresses reply to ARP requests for the same IP, switch forwarding tables and host ARP caches become corrupted (ARP cache poisoning/flapping).

### 3.3 Step-by-Step Procedure
1. Load **Scenario 2 (IP Address Conflict Demonstration)**.
2. Observe the canvas: both `Workstation Alpha` and `Workstation Beta` display **pulsing red conflict halos** and an alert badge `!`.
3. Open the **Virtual ARP Table** tab in the bottom console.
4. Locate the entry for `192.168.10.50`:
   - Status shows `AMBIGUOUS (IP Conflict)`.
   - Notes report that multiple MAC addresses are claiming the identical IPv4 address.
5. In the bottom console, switch to the **Conflicts & Resolution** tab.
6. Click **Launch Guided Conflict Resolution**.
7. In the resolution modal:
   - The diagnostic engine computes the next available unallocated IP in the subnet (`192.168.10.2`).
   - Select `Workstation Beta` as the target device to reconfigure.
   - Choose **Assign Free Candidate IP** (`192.168.10.2`).
8. Click **Apply Resolution & Verify**.
9. Observe the real-time recovery:
   - The red collision halos disappear immediately.
   - `Workstation Beta` updates its IP badge to `192.168.10.2`.
   - The Virtual ARP Table status transitions to `VALID (Active)`.
   - The conflict alert counter in the top navigation returns to zero.

---

## Experiment 4: Rogue Device Detection & Access Control

### 4.1 Objective
To demonstrate network security auditing by identifying unauthorized (rogue) devices attached to the LAN and executing administrator authorization workflows.

### 4.2 Networking Theory
- **Rogue Devices**: Unregistered or unmanaged hardware (e.g. personal laptops, unauthorized access points) that connect to an organizational LAN, presenting a security vulnerability.
- **Network Access Control (NAC)**: The enforcement of security policy preventing non-compliant or unapproved endpoints from communicating across internal corporate or campus networks.

### 4.3 Step-by-Step Procedure
1. Load **Scenario 5 (Unapproved Rogue Device)**.
2. Identify the unauthorized device: `Unidentified Personal Laptop` is surrounded by a **yellow dashed warning border** and a shield alert badge.
3. Open the **Ping Simulator** tab in the bottom console.
4. Attempt to run a ping from `Staff Workstation (192.168.40.10)` to `Unidentified Personal Laptop (192.168.40.77)`.
5. Observe the result: **PING FAILED / BLOCKED**. The diagnostic pipeline reports:
   - `Security State (Destination): Unapproved rogue device blocked by NAC`.
   - Packets are rejected by Network Access Control / port security policy.
6. Now click `Unidentified Personal Laptop` to open the **Device Properties** panel.
7. Observe the **Access Approval** control showing `Unapproved (Rogue Alert)`.
8. Toggle the **Approved Host** switch to ON (`Approved LAN host`).
9. Re-run the ping from `Staff Workstation` to `Unidentified Personal Laptop`.
10. Observe the result: **PING SUCCESSFUL**. The security check now passes (`Authorized device`), the warning border clears, and full communication is restored.
11. Open the **Activity History** page from the top navigation to view the complete audit trail.

---

## 20 Essential Computer Networks Viva Questions & Answers

### Q1. What is NodeScope and what is its primary educational objective?
**Ans:** NodeScope is an interactive, simulation-based virtual LAN platform designed to model IPv4 subnetting, dynamic DHCP allocation, Layer 2-to-3 ARP resolution, and duplicate IP conflict troubleshooting without requiring real network scanning, Scapy, or physical router hardware.

### Q2. Why does NodeScope not require Npcap or Administrator privileges?
**Ans:** Because it is 100% simulation-driven. All networking rules (CIDR calculations, MAC address mappings, BFS graph packet traversal, and collision detection) are computed deterministically in pure Python using data structures and SQLite.

### Q3. How does NodeScope calculate whether an IP address belongs to a subnet?
**Ans:** It uses Python's built-in `ipaddress.ip_network` and `ipaddress.ip_address` modules to check bitwise containment (`ip_obj in network_obj`).

### Q4. What is the difference between a Network Address and a Broadcast Address in a `/24` subnet?
**Ans:** In a `/24` subnet (e.g. `192.168.10.0/24`), `192.168.10.0` is the Network ID (identifies the entire segment; all host bits are 0) and `192.168.10.255` is the Broadcast Address (used to address all hosts simultaneously; all host bits are 1). Neither can be assigned to a host interface.

### Q5. What is the role of the Default Gateway in a LAN?
**Ans:** The Default Gateway is the IP address of the local router interface that receives frames destined for IP addresses outside the local subnet prefix and routes them to external networks or the Internet.

### Q6. How is MAC address formatting enforced in NodeScope?
**Ans:** Devices are automatically assigned locally administered unicast MAC addresses conforming to IEEE 802 standards (e.g. `02:xx:xx:...` where the second least significant bit of the first byte is set to 1).

### Q7. Explain the four steps of the DHCP DORA process.
**Ans:**
1. **Discover**: Client broadcasts a message looking for available DHCP servers.
2. **Offer**: Server offers an available IP address with subnet mask and lease time.
3. **Request**: Client formally requests the offered IP address.
4. **Acknowledge (ACK)**: Server commits the lease and confirms network parameters.

### Q8. What happens when the DHCP address pool is exhausted?
**Ans:** When all IP addresses between `dhcp_start` and `dhcp_end` are bound to active online devices, new hosts requesting dynamic leases are denied and the system logs an explicit `DHCP POOL EXHAUSTION` warning.

### Q9. How does NodeScope simulate ICMP Ping reachability?
**Ans:** It evaluates a deterministic 5-step checklist: source power state, destination power state, IP allocation, subnet membership, conflict state, and topological BFS reachability through interconnected switches.

### Q10. What graph algorithm is used to verify packet forwarding between two devices?
**Ans:** Breadth-First Search (BFS) is executed over an undirected graph where vertices are devices and edges are active connections. A path is traversable only if intermediate devices (like switches) are powered on.

### Q11. Can an Ethernet Switch have an IP address in NodeScope?
**Ans:** By design, unmanaged Layer 2 switches in NodeScope operate strictly at the Data Link Layer and do not require or expose a Layer 3 IP address; they transparently forward frames between connected ports.

### Q12. What causes an IP address conflict in an Ethernet LAN?
**Ans:** An IP conflict occurs when two active devices are manually assigned the same static IP address or when a static IP overlaps with an address assigned by a DHCP server.

### Q13. How does an IP address conflict affect the ARP Table?
**Ans:** When two devices share one IP address, both respond to ARP queries with different MAC addresses. This causes ARP cache ambiguity and flapping, leading to intermittent packet drops or total communication failure.

### Q14. How does NodeScope's Guided Conflict Resolution choose a candidate IP?
**Ans:** It scans the network's subnet from the lowest host address upwards, cross-references all assigned static IPs, gateways, and active DHCP leases, and suggests the first available unassigned IPv4 address.

### Q15. What is the difference between a Collapsed console and an Expanded console in the workspace?
**Ans:** The bottom console can collapse to a compact 38px tab bar to maximize canvas workspace for large topologies, or expand up to 500px using a vertical drag handle or tab header controls for detailed diagnostic analysis.

### Q16. What is a Rogue Device in computer networking?
**Ans:** A rogue device is any unauthorized or unmanaged computer, mobile device, or access point connected to a secure network without administrative approval or compliance checks.

### Q17. How does NodeScope detect rogue devices?
**Ans:** Devices maintain an `is_approved` flag in the SQLite database. If a device has `is_approved = 0`, the UI highlights it with a yellow dashed warning halo and logs a security audit event until an administrator toggles approval.

### Q18. How does the SQLite database preserve state across application restarts?
**Ans:** All networks, devices, coordinates, links, leases, and conflicts are stored in relational tables in a persistent SQLite file (`nodescope.db`). On application restart, topologies and positions reload seamlessly.

### Q19. How are device coordinates and layout modifications saved?
**Ans:** Device node positions (`pos_x`, `pos_y`) are updated live during drag events and persisted to SQLite via `PUT /api/devices/<id>` or by clicking the **Save Layout** button.

### Q20. What are the key architectural advantages of using Vanilla JavaScript and SVG over heavy frameworks for this simulator?
**Ans:**
- Zero frontend build tool overhead (no Node.js, Webpack, or npm dependencies).
- Direct DOM manipulation and native SVG vector lines provide smooth 60fps link dragging.
- The complete application is startable with a single command (`python app.py`) from any standard Windows computer.
