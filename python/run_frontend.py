"""
Start the web frontend on your own computer (localhost).

Run:   python run_frontend.py            -> opens http://localhost:8000 in your browser
       python run_frontend.py 8080       -> use a different port
Stop:  press Ctrl + C in this terminal.

The page (index.html) loads Sample_Table9_Prototype_Data.xlsx from this folder, the same
data file the Python scripts use, and runs all calculations in the browser.
Only Python's standard library is needed for this script.
"""
import http.server
import os
import socketserver
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))                    # this folder holds index.html and the data file
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000                # port number (default 8000)


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve files from this folder and keep the terminal output short."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")                  # always load the latest data file after edits
        super().end_headers()

    def log_message(self, *args):
        pass                                                           # silence the per-request log lines


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    try:
        server = socketserver.TCPServer(("127.0.0.1", PORT), Handler)  # localhost only: not visible to other computers
    except OSError:
        sys.exit(f"Port {PORT} is busy. Try another one, e.g.  python run_frontend.py 8080")
    url = f"http://localhost:{PORT}/"
    print(f"Frontend running at {url}")
    print("Press Ctrl + C to stop.")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()          # open the browser once the server is up
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()
