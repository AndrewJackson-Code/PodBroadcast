#!/usr/bin/env python3
"""
PodBroadcast - A tiny HTTP server for broadcasting podman container status.
Fetches container status on demand and requires key-based authentication.

"""

import json
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


class PodBroadcastHandler(BaseHTTPRequestHandler):
    """HTTP request handler that returns current podman container status."""
    
    def log_message(self, format, *args):
        """Keep BaseHTTPRequestHandler's stderr logging behavior explicit."""
        # BaseHTTPRequestHandler writes access logs to stderr, not to a file.
        super().log_message(format, *args)
    
    def do_GET(self):
        """Authenticate the request and return podman container status as JSON."""
        # API keys are supplied as query parameters, so parse them before auth.
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Refuse all requests if the server was started without a configured key.
        provided_key = query_params.get('key', [None])[0]
        expected_key = os.environ.get('PODBROADCAST_KEY', '')
        
        if not expected_key:
            self.send_error(500, "Server not configured with API key")
            return
        
        if provided_key != expected_key:
            self.send_error(401, "Unauthorized - Invalid or missing API key")
            return
        
        try:
            # Query podman for every request so responses reflect current state.
            result = subprocess.run(
                ['podman', 'ps','-a', '--format', 'json'],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            # Validate podman's output and pretty-print it for clients.
            container_data = json.loads(result.stdout)
            response_data = json.dumps(container_data, indent=2)
            
            # Content-Length is measured from the response string, which is ASCII
            # for the JSON emitted by json.dumps with default ensure_ascii=True.
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_data)))
            self.end_headers()
            self.wfile.write(response_data.encode('utf-8'))
            
        except subprocess.TimeoutExpired:
            self.send_error(504, "Timeout executing podman command")
        except subprocess.CalledProcessError as e:
            self.send_error(500, f"Error executing podman: {e}")
        except json.JSONDecodeError as e:
            self.send_error(500, f"Error parsing podman output: {e}")
        except FileNotFoundError:
            self.send_error(500, "podman command not found")
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")


def run_server(host='0.0.0.0', port=8080):
    """Start the HTTP server and serve requests until interrupted."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, PodBroadcastHandler)
    
    print(f"PodBroadcast server running on {host}:{port}")
    print(f"Access with: http://{host}:{port}/?key=YOUR_KEY")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        # Give the server a chance to stop cleanly on Ctrl+C.
        print("\nShutting down the server...")
        httpd.shutdown()


if __name__ == '__main__':
    # Environment variables allow the same script to run locally or as a service.
    host = os.environ.get('PODBROADCAST_HOST', '0.0.0.0')
    port = int(os.environ.get('PODBROADCAST_PORT', '8080'))
    
    # Fail fast rather than starting a server that rejects every request.
    if not os.environ.get('PODBROADCAST_KEY'):
        print("WARNING: PODBROADCAST_KEY environment variable not set!")
        print("Please set it before running the server:")
        print("  export PODBROADCAST_KEY='your-secret-key'")
        exit(1)
    
    run_server(host, port)
