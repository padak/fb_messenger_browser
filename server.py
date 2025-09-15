#!/usr/bin/env python3
import http.server
import socketserver
import os

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

PORT = 8000

os.chdir('/Users/padak/github/fb_mess')

with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}/")
    print(f"Open http://localhost:{PORT}/messenger_reader.html in your browser")
    httpd.serve_forever()