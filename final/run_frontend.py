"""
Start the web frontend on your own computer (localhost).

Run:   python run_frontend.py            -> opens http://localhost:8000 in your browser
       python run_frontend.py 8080       -> use a different port
Stop:  press Ctrl + C in this terminal.

How it works:
  * The browser shows index.html. The page only displays results; it does no maths.
  * When the page needs results it asks this server, which runs the Python scripts
    (through frontend_api.py) and sends the answers back.

  GET  /api/data         read Table9_Data.xlsx from this folder
  POST /api/upload       read an Excel file chosen with "Import Excel..."
  POST /api/compute      weights, the six rankings and the final ranking for the table on the page
  POST /api/sensitivity  sensitivity analysis for the six rankings and the best alternative
                         (about a minute; runs in a separate Python process)
"""
import http.server
import json
import os
import sys
import tempfile
import threading
import traceback
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))                    # this folder holds index.html and the data file
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000                # port number (default 8000)
MAX_UPLOAD = 10 * 1024 * 1024                                         # largest Excel file accepted (10 MB)

print("Loading the Python scripts...")
import frontend_api as api                                            # all calculations live here (and in the scripts)


class Handler(http.server.SimpleHTTPRequestHandler):
    """Serve the page's files, and answer the page's requests for results."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=HERE, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")                  # always load the latest files after edits
        super().end_headers()

    def log_message(self, *args):
        pass                                                           # silence the per-request log lines

    def send_json(self, obj, status=200):
        body = json.dumps(obj, allow_nan=False).encode("utf-8")        # results as JSON text
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_UPLOAD:
            raise ValueError("the file is larger than 10 MB")
        return self.rfile.read(length)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/data":                     # the data file in this folder
            try:
                result = api.read_table(api.DATA_FILE)
                result["file"] = os.path.basename(api.DATA_FILE)
                self.send_json(result)
            except Exception as err:
                self.send_json({"error": f"Could not read {os.path.basename(api.DATA_FILE)}: {err}"}, 400)
            return
        super().do_GET()                                               # any other path: send the file (index.html etc.)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/upload":                                  # an Excel file chosen on the page
                name = os.path.basename(self.headers.get("X-Filename", "upload.xlsx"))
                suffix = os.path.splitext(name)[1].lower() or ".xlsx"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(self.read_body())                        # save it to a temporary file for pandas
                try:
                    result = api.read_table(tmp.name)
                finally:
                    os.remove(tmp.name)
                result["file"] = name
                self.send_json(result)
            elif path == "/api/compute":                               # weights and the four rankings
                self.send_json(api.compute(json.loads(self.read_body())))
            elif path == "/api/sensitivity":                           # sensitivity analysis
                self.send_json(api.run_sensitivity(json.loads(self.read_body())))
            else:
                self.send_json({"error": "unknown request"}, 404)
        except Exception as err:
            traceback.print_exc()                                      # show the full error in the terminal
            self.send_json({"error": str(err)}, 400)


if __name__ == "__main__":
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)  # localhost only: not visible to other computers
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
