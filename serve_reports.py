"""
Simple local HTTP server to serve generated reports for easy download.
Run this in the project root and open the printed URL in your browser.

Usage:
    python serve_reports.py         # serves logs/reports on http://localhost:8000/
    python serve_reports.py --port 9000

It prints the latest PDF report URL so you can click/download it.
"""

import argparse
import http.server
import socketserver
import os
from pathlib import Path
import webbrowser


def find_latest_pdf(reports_dir: Path):
    if not reports_dir.exists():
        return None
    files = sorted([p for p in reports_dir.iterdir() if p.suffix.lower() == '.pdf'], key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def main():
    parser = argparse.ArgumentParser(description="Serve logs/reports for download")
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to serve on')
    parser.add_argument('--open', '-o', action='store_true', help='Open latest report in browser after starting')
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    reports_dir = project_root / 'logs' / 'reports'

    if not reports_dir.exists():
        print(f"No reports directory found at: {reports_dir}\nPlease generate a report first (see aggregator.save_weekly_report_pdf()).")
        return

    latest = find_latest_pdf(reports_dir)
    if latest:
        print(f"Latest PDF: {latest.name}")
    else:
        print("No PDF reports found in logs/reports/")

    os.chdir(str(reports_dir))

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", args.port), handler) as httpd:
        host = 'localhost'
        url = f'http://{host}:{args.port}/{latest.name if latest else ""}'
        print(f"Serving {reports_dir} at http://{host}:{args.port}/")
        if latest:
            print(f"Direct download URL for latest PDF: {url}")
            if args.open:
                webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")


if __name__ == '__main__':
    main()
