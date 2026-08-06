from __future__ import annotations

import http.server
from pathlib import Path
import socket
import socketserver
import webbrowser

START_PORT = 8501
MAX_ATTEMPTS = 20
DEMO_DIR = Path(__file__).resolve().parents[1] / "demo"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DEMO_DIR), **kwargs)


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def find_free_port(start_port: int, max_attempts: int) -> tuple[ReusableTCPServer, int]:
    for port in range(start_port, start_port + max_attempts):
        try:
            server = ReusableTCPServer(("", port), Handler)
            return server, port
        except OSError:
            continue
    raise RuntimeError(f"Could not find any available port in range {start_port} - {start_port + max_attempts}")


def main():
    try:
        httpd, port = find_free_port(START_PORT, MAX_ATTEMPTS)
    except Exception as exc:
        print(f"Error starting server: {exc}")
        return

    url = f"http://localhost:{port}/index.html"
    print(f"=== LAUNCHING SHOWCASE DEMO DASHBOARD ON PORT {port} ===")
    print(f"Dashboard URL: {url}")

    try:
        webbrowser.open(url)
    except Exception as exc:
        print(f"Could not open browser automatically: {exc}")

    print(f"Server active at {url}. Press Ctrl+C to stop.")
    try:
        with httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShowcase Demo server stopped cleanly.")


if __name__ == "__main__":
    main()

