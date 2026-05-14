"""Local ESC/POS printer agent for MKSOFT.

Usage: python printer_agent.py [--port 8765]
       python install_agent.bat  (one-time setup + auto-startup)

Requires: pywin32 (pip install pywin32)

Runs as a background HTTP server on localhost. The MKSOFT web app
sends print jobs here, and this agent sends them to the thermal
printer via Windows print spooler (win32print).
"""

import argparse
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    import win32print
except ImportError:
    win32print = None


def find_thermal_printer():
    if win32print is None:
        return None
    keywords = ["tm", "thermal", "pos", "ticket", "receipt", "epson", "star",
                "bixolon", "zebra", "datamax", "reci"]
    printers = [p[2] for p in win32print.EnumPrinters(2)]
    for kw in keywords:
        for p in printers:
            if kw in p.lower():
                return p
    return printers[0] if printers else None


class PrintHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        origin = self.headers.get("Origin", "*")
        if self.path == "/status":
            printer = find_thermal_printer()
            self._respond(200, {
                "running": True,
                "printer": printer,
                "win32print": win32print is not None,
            }, origin)
        elif self.path == "/printers":
            printers = []
            if win32print:
                printers = [p[2] for p in win32print.EnumPrinters(2)]
            self._respond(200, {"printers": printers}, origin)
        else:
            self._respond(404, {"error": "Not found"}, origin)

    def do_POST(self):
        origin = self.headers.get("Origin", "*")
        content_type = self.headers.get("Content-Type", "")
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length) if length > 0 else b""

            if "application/octet-stream" in content_type:
                self._print_raw(raw_body, None)
                self._respond(200, {"success": True}, origin)
                return

            data = json.loads(raw_body)
            pk = data.get("pk")
            site_url = data.get("site_url", "http://127.0.0.1:8000")
            printer_name = data.get("printer_name", None)

            if not pk:
                self._respond(400, {"error": "Missing pk"}, origin)
                return

            escpos_url = f"{site_url.rstrip('/')}/facturacion/{pk}/escpos/"
            import urllib.request
            resp = urllib.request.urlopen(escpos_url)
            raw = resp.read()

            self._print_raw(raw, printer_name)
            self._respond(200, {"success": True, "message": f"Factura {pk} impresa"}, origin)

        except Exception as e:
            self._respond(500, {"error": str(e)}, origin)

    def _print_raw(self, data, printer_name=None):
        if win32print is None:
            raise RuntimeError("pywin32 no instalado. pip install pywin32")
        name = printer_name or find_thermal_printer() or win32print.GetDefaultPrinter()
        handle = win32print.OpenPrinter(name)
        try:
            win32print.StartDocPrinter(handle, 1, ("mksoft", None, "RAW"))
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, data)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
            win32print.ClosePrinter(handle)
        sys.stderr.write(f"[printer_agent] Impreso en: {name}\n")

    def _respond(self, code, body, origin):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[printer_agent] {args[0]}\n")


def main():
    parser = argparse.ArgumentParser(description="MKSOFT ESC/POS printer agent")
    parser.add_argument("--port", type=int, default=8765, help="Puerto local (default: 8765)")
    parser.add_argument("--list-printers", action="store_true", help="Listar impresoras disponibles")
    args = parser.parse_args()

    if args.list_printers:
        print("Impresoras disponibles:")
        for p in win32print.EnumPrinters(2):
            print(f"  - {p[2]}")
        return

    if win32print is None:
        print("ADVERTENCIA: pywin32 no instalado.")
        print("  pip install pywin32")
    else:
        printer = find_thermal_printer()
        if printer:
            print(f"Impresora detectada: {printer}")
        else:
            print("ADVERTENCIA: No se detecto impresora termica.")

    server = HTTPServer(("127.0.0.1", args.port), PrintHandler)
    print(f"MKSOFT Printer Agent corriendo en http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo...")


if __name__ == "__main__":
    main()
