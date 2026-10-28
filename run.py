"""
run.py — NodeScope application runner.
"""
from app import app

if __name__ == '__main__':
    print("=================================================================")
    print("  NodeScope: Interactive LAN Simulator & Troubleshooting Lab")
    print("  Server running at: http://127.0.0.1:5000/")
    print("=================================================================")
    app.run(debug=True, host='127.0.0.1', port=5000)
