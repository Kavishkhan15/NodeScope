/* ============================================================
   NodeScope — Frontend JavaScript
   Vanilla JS only. No frameworks.
   ============================================================ */

document.addEventListener('DOMContentLoaded', function () {

  // ----------------------------------------------------------
  // 1. Auto-dismiss flash messages after 5 seconds
  // ----------------------------------------------------------
  document.querySelectorAll('.ns-flash').forEach(function (el) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ----------------------------------------------------------
  // 2. Mobile sidebar toggle
  // ----------------------------------------------------------
  var toggleBtn = document.getElementById('sidebarToggle');
  var sidebar   = document.getElementById('sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('open');
    });
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function (e) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // ----------------------------------------------------------
  // 3. Client-side table search for device inventory
  // ----------------------------------------------------------
  var searchInput = document.getElementById('table-search');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      var query = this.value.toLowerCase();
      document.querySelectorAll('#device-table tbody tr').forEach(function (row) {
        var text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  }

  // ----------------------------------------------------------
  // 4. CIDR subnet validation on the scan form
  // ----------------------------------------------------------
  var scanForm   = document.getElementById('scan-form');
  var subnetInput = document.getElementById('subnet');
  if (scanForm && subnetInput) {
    scanForm.addEventListener('submit', function (e) {
      var val = subnetInput.value.trim();
      var cidrPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;
      if (!cidrPattern.test(val)) {
        e.preventDefault();
        subnetInput.classList.add('is-invalid');
        var fb = subnetInput.parentElement.querySelector('.invalid-feedback');
        if (!fb) {
          fb = document.createElement('div');
          fb.className = 'invalid-feedback';
          subnetInput.parentElement.appendChild(fb);
        }
        fb.textContent = 'Enter a valid CIDR subnet, e.g. 192.168.1.0/24';
        return;
      }
      subnetInput.classList.remove('is-invalid');
    });

    subnetInput.addEventListener('input', function () {
      this.classList.remove('is-invalid');
    });
  }

  // ----------------------------------------------------------
  // 5. Confirm dialogs for destructive buttons
  // ----------------------------------------------------------
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(this.getAttribute('data-confirm'))) {
        e.preventDefault();
      }
    });
  });

  // ----------------------------------------------------------
  // 6. Highlight active nav link (fallback for dynamic paths)
  // ----------------------------------------------------------
  var currentPath = window.location.pathname;
  document.querySelectorAll('.ns-nav-link').forEach(function (link) {
    var href = link.getAttribute('href');
    if (href && href !== '/' && currentPath.startsWith(href)) {
      link.classList.add('active');
    }
  });

});
