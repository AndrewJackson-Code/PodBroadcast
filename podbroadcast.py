#!/usr/bin/env python3
"""
PodBroadcast - A tiny HTTP server for broadcasting podman container status.
Stores all data in RAM and requires key-based authentication.
"""

import json
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


class PodBroadcastHandler(BaseHTTPRequestHandler):
    """HTTP request handler for broadcasting podman container status."""
    
    def log_message(self, format, *args):
        """Override to log to stderr (RAM-based logging)."""
        # Logs go to stderr by default, not to disk
        super().log_message(format, *args)
    
    def do_GET(self):
        """Handle GET requests."""
        # Parse the URL and query parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        # Check for API key
        provided_key = query_params.get('key', [None])[0]
        expected_key = os.environ.get('PODBROADCAST_KEY', '')
        
        if not expected_key:
            self.send_error(500, "Server not configured with API key")
            return
        
        if provided_key != expected_key:
            self.send_error(401, "Unauthorized - Invalid or missing API key")
            return
        
        # Get podman container status
        # Support different actions via 'action' query param. Default is 'podman'.
        action = query_params.get('action', ['podman'])[0]

        try:
            if action == 'mpstat':
                # Run mpstat 1 1 and pipe to jc mpstat, returning JSON output
                # We'll run mpstat first and pipe its stdout to jc
                mpstat_proc = subprocess.run(
                    ['mpstat', '1', '1'],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=15
                )

                jc_proc = subprocess.run(
                    ['jc', 'mpstat'],
                    input=mpstat_proc.stdout,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )

                # Validate JSON
                parsed = json.loads(jc_proc.stdout)
                response_data = json.dumps(parsed, indent=2)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_data)))
                self.end_headers()
                self.wfile.write(response_data.encode('utf-8'))

            else:
                # Default: podman
                result = subprocess.run(
                    ['podman', 'ps','-a', '--format', 'json'],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )

                # Parse and re-serialize to ensure valid JSON
                container_data = json.loads(result.stdout)
                response_data = json.dumps(container_data, indent=2)

                # Send successful response
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(response_data)))
                self.end_headers()
                self.wfile.write(response_data.encode('utf-8'))

        except subprocess.TimeoutExpired:
            self.send_error(504, "Timeout executing command")
        except subprocess.CalledProcessError as e:
            self.send_error(500, f"Error executing command: {e}")
        except json.JSONDecodeError as e:
            self.send_error(500, f"Error parsing output JSON: {e}")
        except FileNotFoundError as e:
            # Include which command was missing if possible
            missing = str(e)
            self.send_error(500, f"Command not found: {missing}")
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")


def run_server(host='0.0.0.0', port=8080):
    """Run the HTTP server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, PodBroadcastHandler)
    
    print(f"PodBroadcast server running on {host}:{port}")
    print(f"Access with: http://{host}:{port}/?key=YOUR_KEY")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()


if __name__ == '__main__':
    # Get configuration from environment variables
    host = os.environ.get('PODBROADCAST_HOST', '0.0.0.0')
    port = int(os.environ.get('PODBROADCAST_PORT', '8080'))
    
    # Check if API key is set
    if not os.environ.get('PODBROADCAST_KEY'):
        print("WARNING: PODBROADCAST_KEY environment variable not set!")
        print("Please set it before running the server:")
        print("  export PODBROADCAST_KEY='your-secret-key'")
        exit(1)
    
    run_server(host, port)
