/**
 * workspace.js — Interactive Network Topology Workspace Engine for NodeScope.
 * 100% Vanilla JavaScript: Device dragging, SVG connection rendering,
 * real-time inspection, DHCP lifecycle, ping diagnostics, and IP conflict resolution.
 */

// Application State
const state = {
  networkId: null,
  network: null,
  devices: [],
  connections: [],
  conflicts: [],
  alerts: [],
  selectedDeviceId: null,
  isConnectMode: false,
  connectSourceId: null,
  draggedNode: null,
  dragOffset: { x: 0, y: 0 },
  hasUnsavedPositions: false,
};

// Node Dimensions for high-accuracy SVG anchoring & drag boundary checks
const NODE_SIZE = 86;
const NODE_HALF = 43;

// Device Icon Map
const DEVICE_ICONS = {
  router: 'bi-router text-primary',
  switch: 'bi-diagram-3-fill text-info',
  access_point: 'bi-wifi text-success',
  desktop: 'bi-pc-display text-primary',
  laptop: 'bi-laptop text-info',
  smartphone: 'bi-phone text-success',
  printer: 'bi-printer text-secondary',
  server: 'bi-hdd-network-fill text-warning'
};

document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('.ns-workspace-container');
  if (!container) return;
  state.networkId = parseInt(container.dataset.networkId, 10);
  initWorkspace();
});

/**
 * Initialize workspace state, events, and canvas
 */
async function initWorkspace() {
  await refreshTopology();
  initGlobalDragHandlers();
  initConsoleResizer();

  // Re-render SVG connections smoothly on window resizing
  window.addEventListener('resize', () => {
    renderSvgConnections();
  });
}

/**
 * Fetch full topology state from Flask API
 */
async function refreshTopology() {
  try {
    const res = await fetch(`/api/networks/${state.networkId}/topology`);
    const data = await res.json();
    if (!data.success) {
      console.error('Topology load failed:', data.error);
      return;
    }

    state.network = data.network;
    state.devices = data.devices;
    state.connections = data.connections;
    state.conflicts = data.conflicts;
    state.alerts = data.alerts;

    renderDeviceNodes();
    renderSvgConnections();
    updateConflictBadges();
    renderEventStream(data.recent_events || []);
    populatePingSelects();
    renderConflictsTab();

    // If selected device still exists, refresh inspector
    if (state.selectedDeviceId) {
      const dev = state.devices.find(d => d.id === state.selectedDeviceId);
      if (dev) {
        populateInspector(dev);
      } else {
        deselectDevice();
      }
    }
  } catch (err) {
    console.error('Error fetching topology:', err);
  }
}

/**
 * Render HTML draggable device nodes
 */
function renderDeviceNodes() {
  const layer = document.getElementById('device-nodes-layer');
  const emptyState = document.getElementById('canvas-empty-state');
  if (!layer) return;

  layer.innerHTML = '';

  if (state.devices.length === 0) {
    emptyState.classList.remove('d-none');
    return;
  }
  emptyState.classList.add('d-none');

  state.devices.forEach(dev => {
    const node = document.createElement('div');
    node.className = 'ns-device-node';
    node.id = `node-${dev.id}`;
    node.dataset.deviceId = dev.id;
    node.style.left = `${dev.pos_x}px`;
    node.style.top = `${dev.pos_y}px`;

    if (dev.id === state.selectedDeviceId) node.classList.add('selected');
    if (!dev.is_online) node.classList.add('offline');
    if (dev.in_conflict) node.classList.add('conflict-halo');
    if (!dev.is_approved) node.classList.add('unapproved-node');

    const iconClass = DEVICE_ICONS[dev.device_type] || 'bi-hdd text-secondary';

    node.innerHTML = `
      <div class="ns-node-status-dot ${dev.is_online ? 'online' : 'offline'}" title="${dev.is_online ? 'Device Online' : 'Device Powered Off'}"></div>
      ${dev.in_conflict ? '<div class="ns-node-conflict-badge" title="IP Conflict!"><i class="bi bi-exclamation-triangle-fill"></i></div>' : ''}
      ${!dev.is_approved ? '<div class="ns-node-unapproved-badge" title="Unapproved Rogue Device"><i class="bi bi-shield-x"></i></div>' : ''}
      <div class="ns-node-icon"><i class="bi ${iconClass}"></i></div>
      <div class="ns-node-label" title="${escapeHtml(dev.name)}">${escapeHtml(dev.name)}</div>
      <div class="ns-node-ip font-monospace">${dev.ip_address ? escapeHtml(dev.ip_address) : '<span class="text-muted">No IP</span>'}</div>
    `;

    // Click handler for selection or connection
    node.addEventListener('mousedown', (e) => handleNodeMouseDown(e, dev));
    node.addEventListener('click', (e) => handleNodeClick(e, dev));

    layer.appendChild(node);
  });
}

/**
 * Render SVG connection links between devices
 */
function renderSvgConnections() {
  const g = document.getElementById('svg-links-group');
  if (!g) return;
  g.innerHTML = '';

  state.connections.forEach(conn => {
    const devA = state.devices.find(d => d.id === conn.device_a_id);
    const devB = state.devices.find(d => d.id === conn.device_b_id);
    if (!devA || !devB) return;

    // Accurate center coordinates based on NODE_HALF (86px / 2 = 43px)
    const x1 = devA.pos_x + NODE_HALF;
    const y1 = devA.pos_y + NODE_HALF;
    const x2 = devB.pos_x + NODE_HALF;
    const y2 = devB.pos_y + NODE_HALF;

    const isBothOnline = devA.is_online && devB.is_online && conn.status === 'active';
    const isWireless = conn.link_type === 'wireless';

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    line.id = `link-${conn.id}`;
    line.className.baseVal = `ns-topology-link ${isBothOnline ? 'active' : 'inactive'} ${isWireless ? 'wireless' : 'wired'}`;
    
    // Clicking connection gives delete option
    line.addEventListener('click', (e) => {
      e.stopPropagation();
      if (confirm(`Remove network connection between '${devA.name}' and '${devB.name}'?`)) {
        removeConnection(conn.id);
      }
    });

    g.appendChild(line);
  });
}

/**
 * Dynamic SVG line update during drag (high performance)
 */
function updateSvgLinesForDraggedNode(devId, newX, newY) {
  state.connections.forEach(conn => {
    if (conn.device_a_id === devId || conn.device_b_id === devId) {
      const line = document.getElementById(`link-${conn.id}`);
      if (!line) return;
      if (conn.device_a_id === devId) {
        line.setAttribute('x1', newX + NODE_HALF);
        line.setAttribute('y1', newY + NODE_HALF);
      }
      if (conn.device_b_id === devId) {
        line.setAttribute('x2', newX + NODE_HALF);
        line.setAttribute('y2', newY + NODE_HALF);
      }
    }
  });
}

/**
 * Global Drag & Drop Handler
 */
function initGlobalDragHandlers() {
  const wrapper = document.getElementById('canvas-wrapper');
  if (!wrapper) return;

  document.addEventListener('mousemove', (e) => {
    if (!state.draggedNode) return;
    e.preventDefault();

    const rect = wrapper.getBoundingClientRect();
    let x = e.clientX - rect.left - state.dragOffset.x;
    let y = e.clientY - rect.top - state.dragOffset.y;

    // Boundaries accounting for 86px node width/height
    x = Math.max(8, Math.min(x, rect.width - NODE_SIZE - 8));
    y = Math.max(8, Math.min(y, rect.height - NODE_SIZE - 8));

    state.draggedNode.style.left = `${x}px`;
    state.draggedNode.style.top = `${y}px`;

    const devId = parseInt(state.draggedNode.dataset.deviceId, 10);
    const dev = state.devices.find(d => d.id === devId);
    if (dev) {
      dev.pos_x = x;
      dev.pos_y = y;
      updateSvgLinesForDraggedNode(devId, x, y);
    }
    state.hasUnsavedPositions = true;
  });

  document.addEventListener('mouseup', () => {
    if (state.draggedNode) {
      state.draggedNode = null;
    }
  });

  // Deselect on empty canvas click
  wrapper.addEventListener('click', (e) => {
    if (e.target.id === 'canvas-wrapper' || e.target.id === 'topology-svg') {
      if (state.isConnectMode) {
        toggleConnectMode(false);
      } else {
        deselectDevice();
      }
    }
  });
}

function handleNodeMouseDown(e, dev) {
  if (e.button !== 0) return; // Only left-click
  if (state.isConnectMode) return;

  const nodeEl = document.getElementById(`node-${dev.id}`);
  const rect = nodeEl.getBoundingClientRect();
  state.draggedNode = nodeEl;
  state.dragOffset = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  };
}

function handleNodeClick(e, dev) {
  e.stopPropagation();

  // If in connection mode
  if (state.isConnectMode) {
    if (!state.connectSourceId) {
      // Picked source
      state.connectSourceId = dev.id;
      document.getElementById(`node-${dev.id}`).classList.add('connect-source-pulse');
      document.getElementById('connect-mode-hint').textContent = `Source: '${dev.name}'. Now click destination device.`;
    } else {
      // Picked destination
      if (state.connectSourceId === dev.id) {
        alert("Cannot connect a device to itself.");
        return;
      }
      createConnection(state.connectSourceId, dev.id);
      toggleConnectMode(false);
    }
    return;
  }

  // Normal mode: select device
  selectDevice(dev.id);
}

/**
 * Device Selection & Property Inspector
 */
function selectDevice(devId) {
  state.selectedDeviceId = devId;
  const dev = state.devices.find(d => d.id === devId);
  if (!dev) return;

  // Highlight selected node
  document.querySelectorAll('.ns-device-node').forEach(n => n.classList.remove('selected'));
  const nodeEl = document.getElementById(`node-${devId}`);
  if (nodeEl) nodeEl.classList.add('selected');

  populateInspector(dev);
}

function deselectDevice() {
  state.selectedDeviceId = null;
  document.querySelectorAll('.ns-device-node').forEach(n => n.classList.remove('selected'));
  document.getElementById('inspector-empty').classList.remove('d-none');
  document.getElementById('inspector-form-container').classList.add('d-none');
}

function populateInspector(dev) {
  document.getElementById('inspector-empty').classList.add('d-none');
  const form = document.getElementById('inspector-form-container');
  form.classList.remove('d-none');

  document.getElementById('prop-name').value = dev.name;
  document.getElementById('prop-type-label').textContent = `${dev.device_type.replace('_', ' ')}`;
  
  // Power State & Approval State with Dynamic Descriptive Subtext
  const onlineCheck = document.getElementById('prop-online');
  const onlineSubtext = document.getElementById('prop-online-subtext');
  if (onlineCheck) onlineCheck.checked = Boolean(dev.is_online);
  if (onlineSubtext) {
    onlineSubtext.textContent = dev.is_online ? 'Online (Active on LAN)' : 'Powered Off (Offline)';
    onlineSubtext.className = dev.is_online ? 'text-success d-block' : 'text-muted d-block';
  }

  const approvedCheck = document.getElementById('prop-approved');
  const approvedSubtext = document.getElementById('prop-approved-subtext');
  if (approvedCheck) approvedCheck.checked = Boolean(dev.is_approved);
  if (approvedSubtext) {
    approvedSubtext.textContent = dev.is_approved ? 'Approved LAN host' : 'Unapproved (Rogue Alert)';
    approvedSubtext.className = dev.is_approved ? 'text-muted d-block' : 'text-danger fw-semibold d-block';
  }

  // IP Mode Tag
  const ipModeTag = document.getElementById('ip-mode-tag');
  if (ipModeTag) {
    const isDhcp = dev.ip_mode === 'dhcp';
    ipModeTag.textContent = isDhcp ? 'DHCP' : 'STATIC';
    ipModeTag.className = `badge ${isDhcp ? 'bg-info text-dark' : 'bg-secondary'} font-monospace`;
  }

  const iconClass = DEVICE_ICONS[dev.device_type] || 'bi-hdd text-secondary';
  document.getElementById('dev-icon-badge').innerHTML = `<i class="bi ${iconClass} fs-4"></i>`;

  // Network configs
  const netSection = document.getElementById('prop-network-section');
  if (dev.device_type === 'switch' || dev.device_type === 'access_point') {
    netSection.classList.add('d-none');
  } else {
    netSection.classList.remove('d-none');
    document.getElementById('prop-ip').value = dev.ip_address || '';
    document.getElementById('prop-netmask').value = dev.subnet_mask || (state.network ? state.network.netmask : '');
    document.getElementById('prop-gateway').value = dev.gateway || (state.network ? state.network.gateway : '');
    document.getElementById('prop-mac').value = dev.mac_address;

    const isDhcp = dev.ip_mode === 'dhcp';
    document.getElementById('mode-dhcp').checked = isDhcp;
    document.getElementById('mode-static').checked = !isDhcp;
    document.getElementById('prop-ip').readOnly = isDhcp;
    document.getElementById('btn-save-ip').classList.toggle('d-none', isDhcp);
    document.getElementById('dhcp-controls').classList.toggle('d-none', !isDhcp);
  }

  // Conflict alert in inspector
  const conflictBanner = document.getElementById('inspector-conflict-alert');
  if (dev.in_conflict) {
    conflictBanner.classList.remove('d-none');
  } else {
    conflictBanner.classList.add('d-none');
  }

  // Name change handler
  const nameInput = document.getElementById('prop-name');
  nameInput.onblur = () => {
    const val = nameInput.value.trim();
    if (val && val !== dev.name) {
      updateDeviceProperty('name', val);
    }
  };
}

/**
 * Update a device property via PUT /api/devices/:id
 */
async function updateDeviceProperty(property, value) {
  if (!state.selectedDeviceId) return;
  const dev = state.devices.find(d => d.id === state.selectedDeviceId);
  if (!dev) return;

  const payload = {
    name: dev.name,
    is_online: dev.is_online,
    is_approved: dev.is_approved,
    pos_x: dev.pos_x,
    pos_y: dev.pos_y,
    ip_mode: dev.ip_mode,
    ip_address: dev.ip_address,
    [property]: value
  };

  try {
    const res = await fetch(`/api/devices/${dev.id}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
    } else {
      alert(data.error || 'Failed to update device.');
      await refreshTopology();
    }
  } catch (err) {
    console.error('Update error:', err);
  }
}

/**
 * Apply Static IP change
 */
async function applyDeviceIpChange() {
  const ipInput = document.getElementById('prop-ip');
  const errBox = document.getElementById('prop-ip-error');
  errBox.classList.add('d-none');

  const newIp = ipInput.value.trim();
  if (!state.selectedDeviceId) return;

  const dev = state.devices.find(d => d.id === state.selectedDeviceId);
  if (!dev) return;

  const payload = {
    name: dev.name,
    is_online: dev.is_online,
    is_approved: dev.is_approved,
    pos_x: dev.pos_x,
    pos_y: dev.pos_y,
    ip_mode: 'static',
    ip_address: newIp
  };

  try {
    const res = await fetch(`/api/devices/${dev.id}`, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
    } else {
      errBox.textContent = data.error || 'Invalid IP address.';
      errBox.classList.remove('d-none');
    }
  } catch (err) {
    errBox.textContent = err.message;
    errBox.classList.remove('d-none');
  }
}

async function changeDeviceIpMode(mode) {
  if (!state.selectedDeviceId) return;
  const dev = state.devices.find(d => d.id === state.selectedDeviceId);
  if (!dev) return;

  if (mode === 'dhcp') {
    await requestDhcpLease();
  } else {
    await updateDeviceProperty('ip_mode', 'static');
  }
}

async function requestDhcpLease() {
  if (!state.selectedDeviceId) return;
  try {
    const res = await fetch(`/api/devices/${state.selectedDeviceId}/dhcp`, {method: 'POST'});
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
    } else {
      alert(data.error || 'DHCP lease allocation failed.');
      await refreshTopology();
    }
  } catch (err) {
    alert('DHCP Request error: ' + err.message);
  }
}

async function releaseDhcpLease() {
  if (!state.selectedDeviceId) return;
  try {
    const res = await fetch(`/api/devices/${state.selectedDeviceId}/dhcp/release`, {method: 'POST'});
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
    }
  } catch (err) {
    alert('DHCP release error: ' + err.message);
  }
}

async function deleteSelectedDevice() {
  if (!state.selectedDeviceId) return;
  const dev = state.devices.find(d => d.id === state.selectedDeviceId);
  if (!dev) return;

  if (!confirm(`Permanently delete device '${dev.name}' from the virtual network?`)) return;

  try {
    const res = await fetch(`/api/devices/${dev.id}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) {
      deselectDevice();
      await refreshTopology();
    }
  } catch (err) {
    alert('Delete error: ' + err.message);
  }
}

/**
 * Add a new device from palette
 */
async function createDevice(type) {
  const existingCount = state.devices.filter(d => d.device_type === type).length;
  const name = `${type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())} ${existingCount + 1}`;

  // Stagger positions across canvas
  const posX = 120 + (state.devices.length % 5) * 110;
  const posY = 100 + Math.floor(state.devices.length / 5) * 120;

  try {
    const res = await fetch(`/api/networks/${state.networkId}/devices`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        name: name,
        device_type: type,
        pos_x: posX,
        pos_y: posY,
        ip_mode: state.network.dhcp_enabled ? 'dhcp' : 'static',
        is_approved: 1
      })
    });
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
      selectDevice(data.device.id);
    } else {
      alert(data.error || 'Failed to add device.');
    }
  } catch (err) {
    alert('Error adding device: ' + err.message);
  }
}

/**
 * Toggle Connection Mode
 */
function toggleConnectMode(forceState) {
  state.isConnectMode = forceState !== undefined ? forceState : !state.isConnectMode;
  state.connectSourceId = null;

  const btn = document.getElementById('btn-toggle-connect-mode');
  const label = document.getElementById('connect-mode-label');
  const hint = document.getElementById('connect-mode-hint');

  document.querySelectorAll('.ns-device-node').forEach(n => n.classList.remove('connect-source-pulse'));

  if (state.isConnectMode) {
    btn.classList.remove('btn-outline-primary');
    btn.classList.add('btn-primary');
    label.textContent = 'Cancel Connecting';
    hint.classList.remove('d-none');
    hint.textContent = 'Click source device, then click destination.';
  } else {
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-outline-primary');
    label.textContent = 'Connect Link';
    hint.classList.add('d-none');
  }
}

async function createConnection(sourceId, destId) {
  try {
    const res = await fetch(`/api/networks/${state.networkId}/connections`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        device_a_id: sourceId,
        device_b_id: destId,
        link_type: 'wired'
      })
    });
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
    } else {
      alert(data.error || 'Failed to connect devices.');
    }
  } catch (err) {
    alert('Connection error: ' + err.message);
  }
}

async function removeConnection(connId) {
  try {
    const res = await fetch(`/api/connections/${connId}`, {method: 'DELETE'});
    const data = await res.json();
    if (data.success) {
      await refreshTopology();
    }
  } catch (err) {
    alert('Disconnect error: ' + err.message);
  }
}

/**
 * Save all device positions to SQLite
 */
async function saveDevicePositions() {
  const btn = document.getElementById('save-layout-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

  try {
    for (const dev of state.devices) {
      await fetch(`/api/devices/${dev.id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          name: dev.name,
          is_online: dev.is_online,
          is_approved: dev.is_approved,
          pos_x: dev.pos_x,
          pos_y: dev.pos_y,
          ip_mode: dev.ip_mode,
          ip_address: dev.ip_address
        })
      });
    }
    state.hasUnsavedPositions = false;
    btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Saved!';
    setTimeout(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-floppy me-1"></i>Save Layout';
    }, 1500);
  } catch (err) {
    alert('Save error: ' + err.message);
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-floppy me-1"></i>Save Layout';
  }
}

/**
 * Center / Fit Topology View
 */
function centerTopologyView() {
  if (state.devices.length === 0) return;
  const minX = Math.min(...state.devices.map(d => d.pos_x));
  const minY = Math.min(...state.devices.map(d => d.pos_y));
  const offsetX = Math.max(50, 100 - minX);
  const offsetY = Math.max(50, 70 - minY);

  state.devices.forEach(d => {
    d.pos_x += offsetX;
    d.pos_y += offsetY;
  });
  renderDeviceNodes();
  renderSvgConnections();
  saveDevicePositions();
}

/**
 * Update Nav and Tab Conflict Badges
 */
function updateConflictBadges() {
  const count = state.conflicts.length;
  const navBadge = document.getElementById('nav-conflict-badge');
  const navCount = document.getElementById('nav-conflict-count');
  const tabBadge = document.getElementById('tab-conflict-badge');

  if (count > 0) {
    navBadge.classList.remove('d-none');
    navCount.textContent = count;
    tabBadge.classList.remove('d-none');
    tabBadge.textContent = count;
  } else {
    navBadge.classList.add('d-none');
    tabBadge.classList.add('d-none');
  }
}

/**
 * Render Live Simulation Event Stream in Tab 1
 */
function renderEventStream(events) {
  const container = document.getElementById('simulation-event-stream');
  if (!container) return;

  if (events.length === 0) {
    container.innerHTML = '<div class="text-muted p-2">Ready. Simulation events will stream here.</div>';
    return;
  }

  container.innerHTML = events.map(e => {
    const time = e.created_at ? e.created_at.substring(11, 19) : '';
    let badgeClass = 'text-primary';
    if (e.level === 'danger') badgeClass = 'text-danger fw-bold';
    if (e.level === 'warning') badgeClass = 'text-warning';
    if (e.level === 'success') badgeClass = 'text-success';

    return `
      <div class="ns-event-line">
        <span class="text-muted">[${time}]</span>
        <span class="text-uppercase fw-bold text-secondary" style="font-size:0.7rem;">[${e.category}]</span>
        <span class="${badgeClass}">${escapeHtml(e.message)}</span>
      </div>
    `;
  }).join('');
}

async function clearConsoleLog() {
  try {
    await fetch(`/api/networks/${state.networkId}/events/clear`, {method: 'POST'});
    await refreshTopology();
  } catch (err) {
    console.error('Clear log error:', err);
  }
}

/**
 * Ping Simulator (Tab 2)
 */
function populatePingSelects() {
  const src = document.getElementById('ping-src-select');
  const dst = document.getElementById('ping-dst-select');
  if (!src || !dst) return;

  const prevSrc = src.value;
  const prevDst = dst.value;

  src.innerHTML = '';
  dst.innerHTML = '';

  // Layer 3 Endpoints & Routers (devices with IP capability)
  const l3Devices = state.devices.filter(d => d.device_type !== 'switch' && d.device_type !== 'access_point');
  // Layer 2 Infrastructure (transparent multi-port forwarders)
  const l2Devices = state.devices.filter(d => d.device_type === 'switch' || d.device_type === 'access_point');

  l3Devices.forEach(d => {
    const optA = document.createElement('option');
    optA.value = d.id;
    optA.textContent = `${d.name} (${d.ip_address || 'No IP'})`;
    src.appendChild(optA);

    const optB = document.createElement('option');
    optB.value = d.id;
    optB.textContent = `${d.name} (${d.ip_address || 'No IP'})`;
    dst.appendChild(optB);
  });

  // Show Layer 2 switches/APs in a disabled optgroup for clarity
  if (l2Devices.length > 0) {
    const grpA = document.createElement('optgroup');
    grpA.label = 'Layer 2 Transparent Devices (No IP)';
    const grpB = document.createElement('optgroup');
    grpB.label = 'Layer 2 Transparent Devices (No IP)';

    l2Devices.forEach(d => {
      const optA = document.createElement('option');
      optA.value = d.id;
      optA.disabled = true;
      optA.textContent = `${d.name} [L2 Forwarding Hub]`;
      grpA.appendChild(optA);

      const optB = document.createElement('option');
      optB.value = d.id;
      optB.disabled = true;
      optB.textContent = `${d.name} [L2 Forwarding Hub]`;
      grpB.appendChild(optB);
    });

    src.appendChild(grpA);
    dst.appendChild(grpB);
  }

  // Preserve previous selection if valid
  if (prevSrc && src.querySelector(`option[value="${prevSrc}"]:not([disabled])`)) {
    src.value = prevSrc;
  }
  if (prevDst && dst.querySelector(`option[value="${prevDst}"]:not([disabled])`)) {
    dst.value = prevDst;
  } else {
    const validDstOptions = dst.querySelectorAll('option:not([disabled])');
    if (validDstOptions.length > 1) {
      validDstOptions[1].selected = true;
    }
  }
}

function openPingTab() {
  const pingTabBtn = document.getElementById('tab-ping-btn');
  const tab = new bootstrap.Tab(pingTabBtn);
  tab.show();
}

async function executePingSimulation() {
  const srcId = document.getElementById('ping-src-select').value;
  const dstId = document.getElementById('ping-dst-select').value;
  const resultBox = document.getElementById('ping-result-box');
  const statusBadge = document.getElementById('ping-status-badge');
  const rttLabel = document.getElementById('ping-rtt-label');
  const summaryMsg = document.getElementById('ping-summary-message');
  const stepsList = document.getElementById('ping-steps-list');
  const btn = document.getElementById('btn-run-ping');

  if (!srcId || !dstId) {
    alert("Please select both a source and destination device.");
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Probing Path...';

  try {
    const res = await fetch(`/api/networks/${state.networkId}/ping`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({source_id: srcId, destination_id: dstId})
    });
    const data = await res.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-send-fill me-1"></i>Simulate Ping';

    if (!data.success) {
      alert(data.error || 'Simulation error.');
      return;
    }

    const r = data.result;
    resultBox.classList.remove('d-none');

    if (r.status === 'success') {
      statusBadge.className = 'badge bg-success';
      statusBadge.textContent = 'PING SUCCESSFUL (ICMP REPLY)';
      rttLabel.textContent = `RTT: ${r.rtt_ms}ms · TTL: 64`;
    } else {
      statusBadge.className = 'badge bg-danger';
      statusBadge.textContent = 'PING FAILED (DESTINATION UNREACHABLE)';
      rttLabel.textContent = 'Loss: 100%';
    }

    summaryMsg.textContent = r.message;
    stepsList.innerHTML = r.steps.map(s => `
      <div class="d-flex align-items-center gap-2">
        <i class="bi ${s.passed ? 'bi-check-circle-fill text-success' : 'bi-x-circle-fill text-danger'}"></i>
        <span class="fw-semibold">${escapeHtml(s.check)}:</span>
        <span class="text-muted">${escapeHtml(s.detail)}</span>
      </div>
    `).join('');

    await refreshTopology();
  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-send-fill me-1"></i>Simulate Ping';
    alert('Ping error: ' + err.message);
  }
}

/**
 * Virtual ARP Table (Tab 3)
 */
async function loadArpTable() {
  const tbody = document.getElementById('arp-table-body');
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Refreshing ARP entries...</td></tr>';

  try {
    const res = await fetch(`/api/networks/${state.networkId}/arp`);
    const data = await res.json();
    if (!data.success || data.arp_table.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No ARP bindings found. Configure device IP addresses to populate.</td></tr>';
      return;
    }

    tbody.innerHTML = data.arp_table.map(row => `
      <tr class="${row.is_conflict ? 'table-danger' : ''}">
        <td class="fw-bold">${escapeHtml(row.ip_address)}</td>
        <td><code>${escapeHtml(row.mac_address)}</code></td>
        <td>${escapeHtml(row.device_name)}</td>
        <td><span class="badge bg-light text-dark border">${escapeHtml(row.device_type)}</span></td>
        <td>
          <span class="badge ${row.is_conflict ? 'bg-danger' : 'bg-success'}">
            ${escapeHtml(row.status)}
          </span>
        </td>
        <td class="small text-muted">${escapeHtml(row.notes)}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">Error: ${err.message}</td></tr>`;
  }
}

/**
 * IP Conflicts & Guided Resolution (Tab 4)
 */
function renderConflictsTab() {
  const container = document.getElementById('conflicts-container');
  if (!container) return;

  if (state.conflicts.length === 0) {
    container.innerHTML = `
      <div class="text-center p-3 text-muted">
        <i class="bi bi-shield-check text-success fs-3 d-block mb-1"></i>
        <strong>All Network IP Addresses are Unique</strong>
        <div class="small">No active IPv4 collisions detected on this virtual LAN.</div>
      </div>
    `;
    return;
  }

  container.innerHTML = state.conflicts.map(c => `
    <div class="card border-danger mb-3 shadow-sm">
      <div class="card-header bg-danger text-white d-flex justify-content-between align-items-center py-2">
        <span><i class="bi bi-exclamation-triangle-fill me-1"></i>Active IP Address Conflict</span>
        <span class="badge bg-white text-danger font-monospace fs-6">${escapeHtml(c.ip_address)}</span>
      </div>
      <div class="card-body p-3">
        <p class="small text-muted mb-2">
          The following active interfaces are responding to the identical IP address <code>${escapeHtml(c.ip_address)}</code>:
        </p>
        <ul class="list-group list-group-flush mb-3">
          ${(c.devices || []).map(d => `
            <li class="list-group-item d-flex justify-content-between align-items-center py-2 px-0">
              <div>
                <strong>${escapeHtml(d.name)}</strong>
                <span class="badge bg-light text-dark border ms-1 font-monospace">${escapeHtml(d.mac_address)}</span>
              </div>
              <span class="badge ${d.ip_mode === 'dhcp' ? 'bg-info text-dark' : 'bg-secondary'}">${d.ip_mode.toUpperCase()}</span>
            </li>
          `).join('')}
        </ul>
        <button type="button" class="btn btn-danger btn-sm shadow-sm" onclick="openConflictResolutionModal(${c.id})">
          <i class="bi bi-wrench me-1"></i>Launch Guided Conflict Resolution
        </button>
      </div>
    </div>
  `).join('');
}

let activeResolvingConflictId = null;

async function openConflictResolutionModal(conflictId) {
  activeResolvingConflictId = conflictId;
  const modalEl = document.getElementById('conflictResolveModal');
  const modal = new bootstrap.Modal(modalEl);
  const errBox = document.getElementById('modal-resolve-error');
  errBox.classList.add('d-none');

  try {
    const res = await fetch(`/api/conflicts/${conflictId}`);
    const data = await res.json();
    if (!data.success) {
      alert(data.error || 'Failed to load conflict details.');
      return;
    }

    const diag = data.diagnostic;
    document.getElementById('modal-conflict-ip').textContent = diag.ip_address;
    document.getElementById('modal-candidate-ip').textContent = diag.suggested_ip || 'None available';
    document.getElementById('modal-proposed-ip').value = diag.suggested_ip || '';

    // Device choices
    const choices = document.getElementById('modal-conflict-device-choices');
    choices.innerHTML = diag.devices.map((d, idx) => `
      <div class="form-check card p-2 bg-light border-0">
        <input class="form-check-input" type="radio" name="conflict_target_device" id="choice-dev-${d.id}" value="${d.id}" ${idx === 0 ? 'checked' : ''}>
        <label class="form-check-label small fw-semibold" for="choice-dev-${d.id}">
          ${escapeHtml(d.name)} <span class="text-muted font-monospace">(${d.mac_address})</span>
        </label>
      </div>
    `).join('');

    modal.show();
  } catch (err) {
    alert('Resolution modal error: ' + err.message);
  }
}

function openConflictResolutionModalForSelected() {
  if (!state.selectedDeviceId) return;
  const dev = state.devices.find(d => d.id === state.selectedDeviceId);
  if (!dev || !dev.ip_address) return;

  const conflict = state.conflicts.find(c => c.ip_address === dev.ip_address);
  if (conflict) {
    openConflictResolutionModal(conflict.id);
  }
}

function toggleModalResolveMode(mode) {
  const manualRow = document.getElementById('modal-manual-ip-row');
  manualRow.classList.toggle('d-none', mode === 'dhcp');
}

async function applyConflictResolution() {
  if (!activeResolvingConflictId) return;

  const btn = document.getElementById('btn-apply-resolution');
  const errBox = document.getElementById('modal-resolve-error');
  errBox.classList.add('d-none');

  const selectedDevRadio = document.querySelector('input[name="conflict_target_device"]:checked');
  if (!selectedDevRadio) {
    errBox.textContent = 'Please choose a device to reconfigure.';
    errBox.classList.remove('d-none');
    return;
  }

  const targetDeviceId = selectedDevRadio.value;
  const mode = document.querySelector('input[name="resolve_mode"]:checked').value;
  const newIp = document.getElementById('modal-proposed-ip').value.trim();

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Applying Changes...';

  try {
    const res = await fetch(`/api/conflicts/${activeResolvingConflictId}/resolve`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        target_device_id: targetDeviceId,
        mode: mode,
        new_ip: newIp
      })
    });
    const data = await res.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Apply Resolution &amp; Verify';

    if (data.success) {
      const modalEl = document.getElementById('conflictResolveModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if (modal) modal.hide();

      await refreshTopology();
      alert(`Resolution Applied! ${data.message}`);
    } else {
      errBox.textContent = data.error || 'Resolution failed.';
      errBox.classList.remove('d-none');
    }
  } catch (err) {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Apply Resolution &amp; Verify';
    errBox.textContent = 'Error: ' + err.message;
    errBox.classList.remove('d-none');
  }
}

/**
 * Bottom Console Controls: Collapsible, Maximizable, and Drag Resizable
 */
let currentConsoleHeight = 190;
let lastExpandedHeight = 190;
let isConsoleCollapsed = false;

function setConsoleHeight(height) {
  const container = document.querySelector('.ns-workspace-container');
  if (!container) return;

  const minHeight = 38;
  const maxHeight = Math.max(250, window.innerHeight - 180);
  currentConsoleHeight = Math.max(minHeight, Math.min(height, maxHeight));

  container.style.setProperty('--console-height', `${currentConsoleHeight}px`);

  const collapseIcon = document.getElementById('panel-collapse-icon');
  const maxIcon = document.getElementById('panel-maximize-icon');

  if (currentConsoleHeight <= 42) {
    isConsoleCollapsed = true;
    if (collapseIcon) collapseIcon.className = 'bi bi-chevron-up';
  } else {
    isConsoleCollapsed = false;
    lastExpandedHeight = currentConsoleHeight;
    if (collapseIcon) collapseIcon.className = 'bi bi-chevron-down';
  }

  if (maxIcon) {
    maxIcon.className = (currentConsoleHeight >= 330) ? 'bi bi-arrows-collapse' : 'bi bi-arrows-expand';
  }
}

function toggleBottomPanelCollapse() {
  if (isConsoleCollapsed || currentConsoleHeight <= 42) {
    const target = (lastExpandedHeight > 42) ? lastExpandedHeight : 190;
    setConsoleHeight(target);
  } else {
    lastExpandedHeight = currentConsoleHeight;
    setConsoleHeight(38);
  }
}

function toggleBottomPanelMaximize() {
  if (currentConsoleHeight >= 330) {
    setConsoleHeight(190);
  } else {
    setConsoleHeight(360);
  }
}

// Backwards compatibility alias
function toggleBottomPanelSize() {
  toggleBottomPanelMaximize();
}

/**
 * Console Vertical Drag Resizer
 */
function initConsoleResizer() {
  const resizer = document.getElementById('console-resizer');
  if (!resizer) return;

  let isResizing = false;
  let startY = 0;
  let startHeight = 0;

  resizer.addEventListener('mousedown', (e) => {
    isResizing = true;
    startY = e.clientY;
    startHeight = currentConsoleHeight;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;
    const deltaY = startY - e.clientY; // dragging upwards increases height
    const newHeight = startHeight + deltaY;
    setConsoleHeight(newHeight);
  });

  document.addEventListener('mouseup', () => {
    if (isResizing) {
      isResizing = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    }
  });

  // Clicking any tab automatically expands the console if currently collapsed
  const tabs = document.querySelectorAll('#consoleTabs .nav-link');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      if (isConsoleCollapsed || currentConsoleHeight <= 42) {
        const target = (lastExpandedHeight > 42) ? lastExpandedHeight : 190;
        setConsoleHeight(target);
      }
    });
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
