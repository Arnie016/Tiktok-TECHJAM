#!/usr/bin/env python3
"""
Simple HTTP server to serve the geo-compliance UI
This solves CORS issues when testing locally
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def serve_ui(port=8000):
    """Start a local HTTP server to serve the UI"""
    
    # Change to the directory containing the HTML file
    current_dir = Path.cwd()
    html_file = current_dir / "geo_compliance_ui.html"
    
    if not html_file.exists():
        print("❌ Error: geo_compliance_ui.html not found in current directory")
        return False
    
    print(f"🚀 Starting local server for Geo-Compliance UI")
    print(f"📁 Serving from: {current_dir}")
    print(f"🌐 Server URL: http://localhost:{port}")
    print(f"📄 UI File: {html_file.name}")
    
    # Custom handler to serve files with proper MIME types
    class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers for local development
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()
        
        def log_message(self, format, *args):
            # Custom logging to show which files are being served
            if args[0].endswith('.html'):
                print(f"📄 Serving: {args[0]}")
            elif args[0].endswith(('.css', '.js')):
                print(f"📦 Asset: {args[0]}")
    
    try:
        with socketserver.TCPServer(("", port), CustomHTTPRequestHandler) as httpd:
            print(f"\n✅ Server started successfully!")
            print(f"🔗 Open this URL in your browser:")
            print(f"   http://localhost:{port}/geo_compliance_ui.html")
            print(f"\n💡 Benefits of using local server:")
            print(f"   • ✅ Proper CORS origin (not 'null')")
            print(f"   • ✅ Real HTTP requests to Lambda")
            print(f"   • ✅ Better debugging capabilities")
            print(f"   • ✅ Production-like environment")
            
            # Automatically open browser
            try:
                webbrowser.open(f"http://localhost:{port}/geo_compliance_ui.html")
                print(f"\n🌐 Browser should open automatically...")
            except Exception as e:
                print(f"\n⚠️ Could not auto-open browser: {e}")
                print(f"Please manually open: http://localhost:{port}/geo_compliance_ui.html")
            
            print(f"\n⏹️  Press Ctrl+C to stop the server")
            print("=" * 60)
            
            httpd.serve_forever()
            
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {port} is already in use")
            print(f"💡 Try a different port: python3 serve_ui.py --port 8001")
            return False
        else:
            print(f"❌ Error starting server: {e}")
            return False
    except KeyboardInterrupt:
        print(f"\n\n🛑 Server stopped by user")
        print(f"✅ Geo-Compliance UI server shut down successfully")
        return True

def main():
    """Main function with command line argument support"""
    
    port = 8000
    
    # Simple argument parsing
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("🛡️ Geo-Compliance UI Server")
            print("Usage: python3 serve_ui.py [--port PORT]")
            print("Default port: 8000")
            return
        elif sys.argv[1] == '--port' and len(sys.argv) > 2:
            try:
                port = int(sys.argv[2])
            except ValueError:
                print("❌ Invalid port number")
                return
    
    print("🛡️ Geo-Compliance UI Server")
    print("=" * 40)
    
    serve_ui(port)

if __name__ == "__main__":
    main()
