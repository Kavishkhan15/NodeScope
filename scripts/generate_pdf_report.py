import os
import subprocess
import base64

def get_base64_image(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    if ext == "svg":
        ext = "svg+xml"
    return f"data:image/{ext};base64,{data}"

def build_html():
    img_logo = get_base64_image("static/img/nodescope-logo.svg")
    img_welcome = get_base64_image("docs/screenshots/01-welcome-dashboard.png")
    img_workspace = get_base64_image("docs/screenshots/02-workspace-topology.png")
    img_conflict = get_base64_image("docs/screenshots/03-ip-conflict-detected.png")
    img_rogue = get_base64_image("docs/screenshots/04-unapproved-rogue-device.png")
    img_history = get_base64_image("docs/screenshots/05-activity-audit-history.png")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>NodeScope — Academic Project Report & Detailed Technical Specification</title>
<style>
  @page {{
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @bottom-right {{
      content: counter(page);
    }}
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    line-height: 1.55;
    font-size: 10.5pt;
    margin: 0;
    padding: 0;
  }}
  h1, h2, h3, h4 {{
    color: #0f172a;
    font-weight: 700;
  }}
  h1 {{ font-size: 22pt; margin-bottom: 6px; }}
  h2 {{ font-size: 14pt; border-bottom: 2px solid #2563eb; padding-bottom: 4px; margin-top: 24pt; margin-bottom: 10pt; page-break-after: avoid; }}
  h3 {{ font-size: 12pt; color: #1e40af; margin-top: 14pt; margin-bottom: 6pt; page-break-after: avoid; }}
  h4 {{ font-size: 10.5pt; color: #334155; margin-top: 10pt; margin-bottom: 4pt; }}
  p {{ margin-top: 0; margin-bottom: 8pt; text-align: justify; }}
  ul, ol {{ margin-top: 0; margin-bottom: 8pt; padding-left: 20px; }}
  li {{ margin-bottom: 3pt; }}
  
  .page-break {{ page-break-before: always; }}
  .avoid-break {{ page-break-inside: avoid; }}

  /* Cover Page */
  .cover-page {{
    text-align: center;
    padding-top: 40px;
    height: 90vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }}
  .cover-logo {{
    width: 220px;
    margin: 0 auto 20px auto;
  }}
  .cover-title {{
    font-size: 26pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
  }}
  .cover-subtitle {{
    font-size: 13pt;
    color: #2563eb;
    font-weight: 600;
    margin-bottom: 25px;
  }}
  .cover-badge-container {{
    margin-bottom: 30px;
  }}
  .badge {{
    display: inline-block;
    padding: 4px 10px;
    font-size: 8.5pt;
    font-weight: 600;
    border-radius: 4px;
    background: #eff6ff;
    color: #1d4ed8;
    border: 1px solid #bfdbfe;
    margin: 2px;
  }}
  .cover-meta-box {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 20px;
    max-width: 500px;
    margin: 0 auto;
    text-align: left;
    font-size: 10pt;
  }}
  .meta-row {{
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    border-bottom: 1px dashed #e2e8f0;
  }}
  .meta-row:last-child {{ border-bottom: none; }}
  .meta-label {{ font-weight: 600; color: #475569; }}
  .meta-val {{ font-weight: 700; color: #0f172a; }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10pt 0;
    font-size: 9pt;
  }}
  th, td {{
    border: 1px solid #cbd5e1;
    padding: 6px 8px;
    text-align: left;
  }}
  th {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 600;
  }}
  tr:nth-child(even) {{ background-color: #f8fafc; }}

  /* Code blocks */
  pre, code {{
    font-family: "Consolas", "Courier New", monospace;
  }}
  code {{
    background: #f1f5f9;
    padding: 1px 4px;
    border-radius: 3px;
    color: #0f172a;
    font-size: 9pt;
  }}
  pre {{
    background: #0f172a;
    color: #f8fafc;
    padding: 10px;
    border-radius: 6px;
    font-size: 8.5pt;
    line-height: 1.4;
    overflow-x: hidden;
    page-break-inside: avoid;
  }}

  /* Callout Alert */
  .callout {{
    border-left: 4px solid #2563eb;
    background: #eff6ff;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    margin: 10pt 0;
    font-size: 9.5pt;
  }}
  .callout.danger {{
    border-left-color: #dc2626;
    background: #fef2f2;
  }}
  .callout.success {{
    border-left-color: #16a34a;
    background: #f0fdf4;
  }}

  /* Screenshots */
  .screenshot-box {{
    margin: 12pt 0;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    overflow: hidden;
    page-break-inside: avoid;
    box-shadow: 0 2px 4px rgba(0,0,0,0.06);
  }}
  .screenshot-box img {{
    width: 100%;
    height: auto;
    display: block;
  }}
  .screenshot-caption {{
    background: #f8fafc;
    padding: 6px 10px;
    font-size: 8.5pt;
    color: #475569;
    border-top: 1px solid #e2e8f0;
    font-weight: 600;
    text-align: center;
  }}
</style>
</head>
<body>

<!-- ========================================== -->
<!-- COVER PAGE                                -->
<!-- ========================================== -->
<div class="cover-page">
  <div>
    <img src="{img_logo}" alt="NodeScope Logo" class="cover-logo">
    <div class="cover-title">NodeScope</div>
    <div class="cover-subtitle">Interactive Virtual LAN Simulator and Network Troubleshooting Lab</div>
    <div class="cover-badge-container">
      <span class="badge">Python 3.11+ / Flask</span>
      <span class="badge">SQLite Relational Engine</span>
      <span class="badge">Vanilla JS + SVG Topology</span>
      <span class="badge">18/18 Pytest Verified</span>
      <span class="badge">100% Simulation-Driven</span>
    </div>
  </div>

  <div class="cover-meta-box">
    <div class="meta-row">
      <span class="meta-label">Course:</span>
      <span class="meta-val">Computer Networks &amp; Distributed Systems</span>
    </div>
    <div class="meta-row">
      <span class="meta-label">Project Type:</span>
      <span class="meta-val">Computer Engineering Mini-Project</span>
    </div>
    <div class="meta-row">
      <span class="meta-label">Technology Stack:</span>
      <span class="meta-val">Python, Flask, SQLite, Bootstrap 5, SVG</span>
    </div>
    <div class="meta-row">
      <span class="meta-label">Repository:</span>
      <span class="meta-val">github.com/Kavishkhan15/NodeScope</span>
    </div>
    <div class="meta-row">
      <span class="meta-label">Academic Year:</span>
      <span class="meta-val">2026 – Final Examination Defense</span>
    </div>
  </div>

  <div style="font-size: 9pt; color: #64748b; margin-top: 20px;">
    Department of Computer Engineering &amp; Information Technology<br>
    Laboratory Practical &amp; Viva Voce Project Documentation
  </div>
</div>

<div class="page-break"></div>

<!-- ========================================== -->
<!-- EXECUTIVE SUMMARY & ABSTRACT              -->
<!-- ========================================== -->
<h2>1. Executive Summary &amp; Abstract</h2>
<p>
  <strong>NodeScope</strong> is an interactive, simulation-driven educational virtual Local Area Network (LAN) platform engineered specifically for undergraduate Computer Engineering and Information Technology students. Traditional Computer Networks education suffers from a persistent disconnect between theoretical textbook concepts (such as CIDR subnetting, Address Resolution Protocol, the DHCP DORA sequence, and ICMP ping diagnostics) and hands-on laboratory experience. Physical networking hardware is costly and difficult to reconfigure safely, while commercial emulation suites such as Cisco Packet Tracer demand significant system resources and emphasize vendor-specific Command Line Interface (CLI) memorization over fundamental troubleshooting logic.
</p>
<p>
  NodeScope eliminates these hurdles by delivering a <strong>zero-configuration, web-based laboratory</strong> executable on standard Windows workstations using Python 3 and modern web standards. Unlike physical network sniffers or Scapy-based utilities that require root/administrator privileges and physical packet injection, NodeScope models private IPv4 local area networks <strong>100% deterministically in application software</strong>. The platform features an SVG-driven drag-and-drop workspace, automatic IEEE-compliant MAC generation, dynamic DHCP lease pool management, Layer 2 to Layer 3 Virtual ARP Tables, Breadth-First Search (BFS) topological packet forwarding verification, and an intelligent <strong>Guided IP Address Conflict Resolver</strong>.
</p>

<div class="callout success">
  <strong>Key Innovation Highlight:</strong> When an IP address collision occurs, NodeScope dynamically detects the conflict across active interfaces, highlights affected devices with real-time pulsing red collision halos, marks the corresponding ARP entry as <code>AMBIGUOUS (IP Conflict)</code>, and computes the lowest available unassigned candidate IP in the subnet to guide students through real-time resolution.
</div>

<!-- ========================================== -->
<!-- COMPARATIVE STUDY & MOTIVATION             -->
<!-- ========================================== -->
<h2>2. Problem Statement &amp; Comparative Analysis</h2>
<p>
  In academic networking laboratories, students must grasp how packets traverse switches and how common misconfigurations—such as duplicate static IPs or disconnected patch cables—impair LAN communication.
</p>

<table>
  <thead>
    <tr>
      <th>Feature / Dimension</th>
      <th>Physical Hardware Lab</th>
      <th>Cisco Packet Tracer</th>
      <th>Wireshark / Scapy</th>
      <th>NodeScope (Our Project)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Cost &amp; Hardware Requirements</strong></td>
      <td>High (Routers, Switches, NICs, Patch Cords)</td>
      <td>Free with NetAcad account (500MB installer)</td>
      <td>Free, but requires physical LAN traffic</td>
      <td><strong>Zero cost, 100% portable Python application</strong></td>
    </tr>
    <tr>
      <td><strong>Privilege Requirements</strong></td>
      <td>Physical console access</td>
      <td>Standard user</td>
      <td>Requires WinPcap / Npcap &amp; Administrator privileges</td>
      <td><strong>Zero root/admin privileges needed</strong></td>
    </tr>
    <tr>
      <td><strong>IP Conflict Visualization</strong></td>
      <td>Silent failure or OS popup</td>
      <td>Generic packet drop</td>
      <td>Requires packet inspection analysis</td>
      <td><strong>Pulsing red visual halos &amp; ambiguous ARP flag</strong></td>
    </tr>
    <tr>
      <td><strong>Guided Conflict Resolution</strong></td>
      <td>Manual trial &amp; error</td>
      <td>Manual CLI commands</td>
      <td>None (analyzer only)</td>
      <td><strong>Automated candidate IP scan &amp; 1-click fix</strong></td>
    </tr>
    <tr>
      <td><strong>Extensibility &amp; Codebase</strong></td>
      <td>Hardware firmware (Closed)</td>
      <td>Proprietary (Closed Source)</td>
      <td>Open Source C/Python library</td>
      <td><strong>Open, readable Python Flask + SQLite architecture</strong></td>
    </tr>
  </tbody>
</table>

<div class="page-break"></div>

<!-- ========================================== -->
<!-- SYSTEM ARCHITECTURE                        -->
<!-- ========================================== -->
<h2>3. System Architecture &amp; Relational Data Model</h2>
<p>
  NodeScope adopts a decoupled Model-View-Controller (MVC) architecture coupled with a pure Python simulation engine. All network states—including topologies, device coordinates, dynamic leases, and event histories—are persisted in an embedded SQLite database.
</p>

<pre>
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
                                         | Asynchronous HTTP / JSON REST APIs
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
|  |   [Addressing Engine]    [DHCP Server Engine]    [BFS Path Traversal]       |  |
|  |   CIDR & Subnet Range    Lease Lifecycle & Pool  Adjacency Graph Continuity |  |
|  |                                                                             |  |
|  |   [Virtual ARP Engine]   [IP Collision Engine]   [Deterministic Ping]       |  |
|  |   Layer 2-to-3 Mappings  Conflict Detection &    5-Step ICMP Diagnostic     |  |
|  |   & Ambiguity Badging    Guided Candidate Scan   Pipeline & RTT Calculator  |  |
|  +-----------------------------------------------------------------------------+  |
|                                         |                                         |
|                                         v                                         |
|  +-----------------------------------------------------------------------------+  |
|  |                           EMBEDDED SQLITE DATABASE                          |  |
|  |      networks · devices · connections · dhcp_leases · ip_conflicts · events |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
</pre>

<h3>Relational Database Schema</h3>
<p>
  The underlying SQLite schema maintains foreign-key integrity (<code>PRAGMA foreign_keys = ON;</code>) to guarantee that when a device or network is deleted, all dependent links, leases, and conflicts cascade cleanly:
</p>
<ul>
  <li><code>networks</code>: Stores virtual LAN definition, subnet CIDR (e.g. <code>192.168.10.0/24</code>), derived netmask, gateway, and DHCP bounds.</li>
  <li><code>devices</code>: Stores device type (router, switch, desktop, etc.), power state (<code>is_online</code>), approval state (<code>is_approved</code>), mode (<code>dhcp</code> vs <code>static</code>), assigned IPv4, MAC address, and canvas coordinates (<code>pos_x</code>, <code>pos_y</code>).</li>
  <li><code>connections</code>: Stores bidirectional link edges (<code>device_a_id</code>, <code>device_b_id</code>) and physical link type (<code>wired</code> vs <code>wireless</code>).</li>
  <li><code>dhcp_leases</code>: Tracks dynamic host configuration state, MAC bindings, lease granted timestamps, and release statuses.</li>
  <li><code>ip_conflicts</code>: Real-time registry of detected address collisions and resolutions.</li>
  <li><code>network_events</code>: Persistent timestamped audit stream for security alerts, lease updates, and diagnostic outcomes.</li>
</ul>

<div class="page-break"></div>

<!-- ========================================== -->
<!-- SIMULATION LOGIC & ALGORITHMS              -->
<!-- ========================================== -->
<h2>4. Core Simulation Algorithms</h2>

<h3>4.1 Subnetting &amp; Addressing Engine (<code>simulator/addressing.py</code>)</h3>
<p>
  All IPv4 subnet operations are governed strictly by Python's built-in <code>ipaddress</code> module:
</p>
<ul>
  <li><strong>Subnet Validation:</strong> Verifies that user-provided subnets conform to RFC 1918 private space and valid prefix lengths (<code>/8</code> to <code>/30</code>).</li>
  <li><strong>Boundary Constraints:</strong> Prevents assignment to the Network Address (host bits = 0) or Directed Broadcast Address (host bits = 1).</li>
  <li><strong>Candidate Discovery Algorithm:</strong>
    <pre>
def find_available_ip(network_cidr, assigned_ips):
    net = ipaddress.ip_network(network_cidr)
    for host in net.hosts():
        ip_str = str(host)
        if ip_str not in assigned_ips and ip_str != net_gateway:
            return ip_str # Returns lowest unused candidate IPv4
    return None # Pool exhaustion</pre>
  </li>
</ul>

<h3>4.2 Deterministic ICMP Ping Pipeline (<code>simulator/ping.py</code>)</h3>
<p>
  Rather than generating random packet loss, the ICMP Ping Simulator evaluates a deterministic 5-step diagnostic chain modeled after standard networking failure modes:
</p>
<ol>
  <li><strong>Source State Verification:</strong> Source device must be powered on (<code>is_online == 1</code>) and configured with an IP.</li>
  <li><strong>Destination State Verification:</strong> Destination device must be powered on and assigned an IP.</li>
  <li><strong>Subnet Match:</strong> Evaluates bitwise whether both hosts reside within the identical CIDR network prefix.</li>
  <li><strong>Address Uniqueness Check:</strong> Verifies that the destination IPv4 address is not involved in an active address collision (simulating the duplicate ARP reply dilemma).</li>
  <li><strong>Topological BFS Graph Reachability:</strong> Constructs an adjacency graph from the <code>connections</code> table and executes Breadth-First Search (BFS). Packet forwarding succeeds only if an unbroken sequence of powered-on switches or wireless access points connects the endpoints.</li>
</ol>

<h3>4.3 Intelligent IP Conflict Detection &amp; Resolution (<code>simulator/conflicts.py</code>)</h3>
<p>
  When an IP address is saved, the collision engine queries all active interfaces:
</p>
<pre>
SELECT ip_address, COUNT(*) as count 
FROM devices 
WHERE network_id = ? AND is_online = 1 AND ip_address IS NOT NULL 
GROUP BY ip_address HAVING count > 1;
</pre>
<p>
  If a duplicate is identified:
</p>
<ol>
  <li>The conflict is recorded in <code>ip_conflicts</code>.</li>
  <li>Colliding nodes are assigned a CSS <code>conflict-halo</code> (pulsing red animation).</li>
  <li>The Virtual ARP Table sets status to <code>AMBIGUOUS (IP Conflict)</code>.</li>
  <li>The administrator can launch the <strong>Guided Conflict Resolver</strong>, which suggests the lowest free candidate IP, updates the target device, and instantly clears the fault.</li>
</ol>

<div class="page-break"></div>

<!-- ========================================== -->
<!-- VISUAL INTERFACE TOUR                      -->
<!-- ========================================== -->
<h2>5. Visual Application Tour</h2>

<div class="screenshot-box">
  <img src="{img_welcome}" alt="NodeScope Welcome Dashboard">
  <div class="screenshot-caption">Figure 5.1: NodeScope Welcome Screen featuring pre-configured educational scenarios and LAN creation wizard.</div>
</div>

<div class="screenshot-box">
  <img src="{img_workspace}" alt="NodeScope Workspace">
  <div class="screenshot-caption">Figure 5.2: Interactive 3-Panel Topology Workspace with SVG connection links and newly refined Device Inspector.</div>
</div>

<div class="screenshot-box">
  <img src="{img_conflict}" alt="IP Conflict Visualized">
  <div class="screenshot-caption">Figure 5.3: Duplicate IP Collision with pulsing red halos and top-bar conflict alert.</div>
</div>

<div class="page-break"></div>

<div class="screenshot-box">
  <img src="{img_rogue}" alt="Rogue Device Warning">
  <div class="screenshot-caption">Figure 5.4: Unauthorized Rogue Device identified with dashed warning borders and Network Access Control inspection.</div>
</div>

<div class="screenshot-box">
  <img src="{img_history}" alt="Audit History Log">
  <div class="screenshot-caption">Figure 5.5: Persistent Activity Audit Stream tracking DHCP leases, pings, and security alerts.</div>
</div>

<!-- ========================================== -->
<!-- TESTING & VERIFICATION                     -->
<!-- ========================================== -->
<h2>6. Software Testing &amp; Verification Suite</h2>
<p>
  The simulator is rigorously verified through an automated test suite implemented in <strong>Pytest</strong>. The test suite executes in in-memory SQLite (<code>:memory:</code>), requiring zero network access:
</p>

<table>
  <thead>
    <tr>
      <th>Test Module</th>
      <th>Tests</th>
      <th>Target Validation Logic</th>
      <th>Result</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>test_sim_addressing.py</code></td>
      <td>9 Tests</td>
      <td>CIDR parsing, netmask calculation, reserved IP detection, candidate search</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_devices.py</code></td>
      <td>1 Test</td>
      <td>Device CRUD, MAC formatting, online toggling, and coordinate storage</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_dhcp.py</code></td>
      <td>1 Test</td>
      <td>Sequential lease allocation, MAC binding, lease renewal, and pool exhaustion</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_connectivity.py</code></td>
      <td>1 Test</td>
      <td>BFS graph traversal through multi-port switches and severed link detection</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_conflicts.py</code></td>
      <td>1 Test</td>
      <td>Duplicate IP collision trigger, halo state, and candidate resolution</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_ping.py</code></td>
      <td>1 Test</td>
      <td>5-step ICMP diagnostic breakdown, power check, and subnet matching</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_arp.py</code></td>
      <td>1 Test</td>
      <td>Layer 2-to-3 resolution, active lease bindings, and ambiguous collision flags</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_scenarios.py</code></td>
      <td>1 Test</td>
      <td>Pre-packaged verification of all 5 educational presentation scenarios</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_api.py</code></td>
      <td>1 Test</td>
      <td>Flask JSON REST API integration, HTTP status codes, and JSON response models</td>
      <td>PASS (100%)</td>
    </tr>
    <tr>
      <td><code>test_sim_events.py</code></td>
      <td>1 Test</td>
      <td>Audit stream persistence and security triage alert logging</td>
      <td>PASS (100%)</td>
    </tr>
  </tbody>
</table>

<div class="callout success">
  <strong>Test Execution Summary:</strong> 18 passed in 0.57s on Python 3.14 / pytest-8.3.5. Zero warnings, zero regressions.
</div>

<div class="page-break"></div>

<!-- ========================================== -->
<!-- VIVA VOCE QUESTIONS & SCRIPT               -->
<!-- ========================================== -->
<h2>7. Viva Voce Examination Guide &amp; Technical Defense</h2>

<h3>Top 10 High-Frequency Oral Exam Questions</h3>

<p><strong>Q1: What is the primary difference between a Hub and a Switch in your simulator?</strong><br>
<em>Answer:</em> In NodeScope, the Switch functions as an intelligent Layer 2 multi-port forwarding device that maintains topological path continuity for connected nodes without consuming a Layer 3 IP address. It forms the central vertex of our BFS star topology.</p>

<p><strong>Q2: Why does an IP address collision break network communication?</strong><br>
<em>Answer:</em> When two hosts share the same IPv4 address, both reply to ARP Request broadcasts with different MAC addresses. This causes ARP cache ambiguity in neighboring hosts and causes switch MAC address tables to flap, leading to dropped frames.</p>

<p><strong>Q3: How does your DHCP allocator ensure no overlapping IP addresses are assigned?</strong><br>
<em>Answer:</em> The DHCP engine queries both active static device allocations and existing unexpired leases. It iterates through the configured <code>[dhcp_start, dhcp_end]</code> pool and only grants an address if it is completely absent from the claimed set.</p>

<p><strong>Q4: Explain the BFS algorithm used in the Ping Simulator.</strong><br>
<em>Answer:</em> We build an undirected adjacency list from the <code>connections</code> table where edges exist between connected devices. BFS traverses the graph from the source device queue. If an intermediate switch is offline (<code>is_online == 0</code>), its edges are pruned. Reachability succeeds if the destination device is dequeued.</p>

<p><strong>Q5: Why did you choose Vanilla JavaScript and SVG over React or Canvas?</strong><br>
<em>Answer:</em> SVG represents connection links and devices as scalable DOM vector nodes with crisp rendering at any resolution. Vanilla JavaScript eliminates complex node_modules dependencies and npm build steps, keeping the complete project lightweight and startable with a single Python command.</p>

<!-- ========================================== -->
<!-- CONCLUSION & FUTURE SCOPE                  -->
<!-- ========================================== -->
<h2>8. Conclusion &amp; Future Scope</h2>
<p>
  NodeScope successfully achieves all stated engineering objectives. It provides a robust, educational, and visually engaging simulation platform for understanding computer networking fundamentals. By transforming abstract theoretical protocols into interactive visual workflows, NodeScope empowers students to experiment, make mistakes, observe failures, and resolve network problems safely on their own computers.
</p>

<h3>Future Enhancements</h3>
<ul>
  <li><strong>VLAN Tagging (802.1Q):</strong> Simulating virtual LAN trunking and access port isolation on the core switch.</li>
  <li><strong>Static Inter-LAN Routing:</strong> Introducing a dual-interface router allowing communication between separate subnets (e.g. <code>192.168.10.0/24</code> and <code>10.0.0.0/24</code>).</li>
  <li><strong>Network Performance Metrics:</strong> Simulating link bandwidth, transmission queueing delay, and packet loss ratios.</li>
</ul>

<hr style="margin-top: 30px; border: none; border-top: 1px solid #cbd5e1;">
<div style="text-align: center; font-size: 8.5pt; color: #64748b; margin-top: 10px;">
  NodeScope Project Report · Department of Computer Engineering · MIT License
</div>

</body>
</html>"""
    return html

def main():
    html_content = build_html()
    os.makedirs("docs", exist_ok=True)
    
    html_path = os.path.abspath("docs/NodeScope_Project_Report.html")
    pdf_path = os.path.abspath("docs/NodeScope_Project_Report.pdf")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML Report generated at: {html_path}")

    browser_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(browser_exe):
        browser_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

    print(f"Generating PDF with: {browser_exe} ...")
    cmd = [
        browser_exe,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--print-to-pdf={pdf_path}",
        html_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) // 1024
        print(f"PDF Successfully Generated: {pdf_path} ({size_kb} KB)")
    else:
        print(f"Failed to generate PDF: {res.stderr}")

if __name__ == '__main__':
    main()
