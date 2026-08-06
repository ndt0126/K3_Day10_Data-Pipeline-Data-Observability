from __future__ import annotations

import http.server
from pathlib import Path
import socketserver
import webbrowser

PORT = 8501
DEMO_DIR = Path(__file__).resolve().parents[1] / "demo"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_DIR), **kwargs)


def main():
    print(f"=== LAUNCHING SHOWCASE DEMO DASHBOARD ON PORT {PORT} ===")
    url = f"http://localhost:{PORT}/index.html"
    print(f"Opening dashboard at: {url}")

    try:
        webbrowser.open(url)
    except Exception as exc:
        print(f"Could not open browser automatically: {exc}")

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server active. Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShowcase Demo server stopped.")


if __name__ == "__main__":
    main()
