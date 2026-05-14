"""Local ESC/POS printer agent for MKSOFT.

Usage: python printer_agent.py [--port 8765]

Requires: pip install pywin32 requests (Windows only)

This runs a small HTTP server on localhost that receives print jobs
from the MKSOFT web app and sends them to a thermal printer via
win32print (Windows print spooler).
"""

import argparse
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import win32print
except ImportError:
    win32print = None

try:
    import requests
except ImportError:
    requests = None


class PrintHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        origin = self.headers.get("Origin", "*")
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(body)
            pk = data.get("pk")
            site_url = data.get("site_url", "http://127.0.0.1:8000")
            printer_name = data.get("printer_name", None)

            if not pk:
                self._respond(400, {"error": "Missing pk"}, origin)
                return

            escpos_url = f"{site_url.rstrip('/')}/facturacion/{pk}/escpos/"
            if requests is None:
                import urllib.request
                resp = urllib.request.urlopen(escpos_url)
                raw = resp.read()
            else:
                resp = requests.get(escpos_url, timeout=10)
                resp.raise_for_status()
                raw = resp.content

            self._print_raw(raw, printer_name)
            self._respond(200, {"success": True, "message": f"Factura {pk} impresa"}, origin)

        except Exception as e:
            self._respond(500, {"error": str(e)}, origin)

    def _print_raw(self, data, printer_name=None):
        if win32print is None:
            raise RuntimeError("pywin32 no instalado. pip install pywin32")
        name = printer_name or win32print.GetDefaultPrinter()
        handle = win32print.OpenPrinter(name)
        try:
            win32print.StartDocPrinter(handle, 1, ("mksoft", None, "RAW"))
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, data)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
            win32print.ClosePrinter(handle)

    def _respond(self, code, body, origin):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[printer_agent] {args[0]}\n")


def list_printers():
    if win32print is None:
        return []
    return [p[2] for p in win32print.EnumPrinters(2)]


def main():
    parser = argparse.ArgumentParser(description="MKSOFT ESC/POS printer agent")
    parser.add_argument("--port", type=int, default=8765, help="Puerto local (default: 8765)")
    parser.add_argument("--list-printers", action="store_true", help="Listar impresoras disponibles")
    args = parser.parse_args()

    if args.list_printers:
        print("Impresoras disponibles:")
        for p in list_printers():
            print(f"  - {p}")
        return

    if win32print is None:
        print("ADVERTENCIA: pywin32 no instalado. La impresion solo funcionara via WebUSB/Serial.")
        print("  pip install pywin32")

    server = HTTPServer(("127.0.0.1", args.port), PrintHandler)
    print(f"MKSOFT Printer Agent corriendo en http://127.0.0.1:{args.port}")
    print("Configura en MKSOFT: Imprimir > Agente Local > http://127.0.0.1:8765")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo...")


if __name__ == "__main__":
    main()
