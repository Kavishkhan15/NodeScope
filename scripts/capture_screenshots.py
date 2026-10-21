import subprocess
import time
import os
import sys
import threading
from app import create_app
from database.db import init_db, get_db
from simulator.scenarios import load_example_scenario

def run_server():
    app = create_app({
        'TESTING': False,
        'DATABASE': 'nodescope_demo.db',
        'SECRET_KEY': 'dev-secret-key-nodescope'
    })
    with app.app_context():
        init_db()
        db = get_db()
        # Ensure all 5 scenarios are loaded
        for s_id in range(1, 6):
            load_example_scenario(db, s_id)
    app.run(host='127.0.0.1', port=5005, debug=False, use_reloader=False)

def capture_screenshots():
    # Wait for server to start
    time.sleep(2)
    
    browser_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(browser_exe):
        browser_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    print(f"Using browser: {browser_exe}")
    
    os.makedirs(r"docs\screenshots", exist_ok=True)
    
    targets = [
        ("http://127.0.0.1:5005/", r"docs\screenshots\01-welcome-dashboard.png"),
        ("http://127.0.0.1:5005/workspace/1", r"docs\screenshots\02-workspace-topology.png"),
        ("http://127.0.0.1:5005/workspace/2", r"docs\screenshots\03-ip-conflict-detected.png"),
        ("http://127.0.0.1:5005/workspace/5", r"docs\screenshots\04-unapproved-rogue-device.png"),
        ("http://127.0.0.1:5005/history/2", r"docs\screenshots\05-activity-audit-history.png")
    ]
    
    for url, out_path in targets:
        abs_out = os.path.abspath(out_path)
        cmd = [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=1440,900",
            f"--screenshot={abs_out}",
            url
        ]
        print(f"Capturing {url} -> {abs_out} ...")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if os.path.exists(abs_out):
            print(f"  Successfully captured: {abs_out} ({os.path.getsize(abs_out)} bytes)")
        else:
            print(f"  Failed to capture: {res.stderr}")

if __name__ == '__main__':
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    capture_screenshots()
    print("Done capturing screenshots!")
    sys.exit(0)
