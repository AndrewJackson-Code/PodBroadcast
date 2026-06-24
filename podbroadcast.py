#!/usr/bin/env python3
"""
PodBroadcast - A tiny HTTP server for broadcasting podman container status.
Fetches container status on demand and requires key-based authentication.
"""

import json
import os
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8080
PODMAN_COMMAND_TIMEOUT_SECONDS = 10


class PodBroadcastHandler(BaseHTTPRequestHandler):
    """HTTP request handler that returns current podman container status."""
    
    def log_message(self, message_format, *message_args):
        """Keep BaseHTTPRequestHandler's stderr logging behavior explicit."""
        # BaseHTTPRequestHandler writes access logs to stderr by default.
        super().log_message(message_format, *message_args)
    
    def do_GET(self):
        """Authenticate the request and return podman container status as JSON."""
        provided_api_key = self._get_query_parameter('key')
        configured_api_key = os.environ.get('PODBROADCAST_KEY', '')
        
        if not configured_api_key:
            self.send_error(500, "Server not configured with API key")
            return
        
        if provided_api_key != configured_api_key:
            self.send_error(401, "Unauthorized - Invalid or missing API key")
            return
        
        try:
            container_statuses = self._fetch_podman_container_statuses()
            self._send_json_response(container_statuses)
        except subprocess.TimeoutExpired:
            self.send_error(504, "Timeout executing podman command")
        except subprocess.CalledProcessError as error:
            self.send_error(500, f"Error executing podman: {error}")
        except json.JSONDecodeError as error:
            self.send_error(500, f"Error parsing podman output: {error}")
        except FileNotFoundError:
            self.send_error(500, "podman command not found")
        except Exception as error:
            self.send_error(500, f"Internal server error: {error}")

    def _get_query_parameter(self, parameter_name):
        """Return the first value for a query parameter in the request URL."""
        parsed_request_url = urlparse(self.path)
        query_parameters = parse_qs(parsed_request_url.query)
        return query_parameters.get(parameter_name, [None])[0]

    def _fetch_podman_container_statuses(self):
        """Run podman and return parsed container status data."""
        # Query podman for every request so the response reflects current state.
        completed_podman_process = subprocess.run(
            ['podman', 'ps', '-a', '--format', 'json'],
            capture_output=True,
            text=True,
            check=True,
            timeout=PODMAN_COMMAND_TIMEOUT_SECONDS
        )
        return json.loads(completed_podman_process.stdout)

    def _send_json_response(self, response_payload):
        """Send a successful JSON response to the client."""
        # Pretty-printed JSON is easier to read when testing in a browser or curl.
        response_body = json.dumps(response_payload, indent=2).encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)


def run_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Start the HTTP server and serve requests until interrupted."""
    listen_address = (host, port)
    http_server = HTTPServer(listen_address, PodBroadcastHandler)
    
    print(f"PodBroadcast server running on {host}:{port}")
    print(f"Access with: http://{host}:{port}/?key=YOUR_KEY")
    print("Press Ctrl+C to stop")
    
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        # Give the server a chance to stop cleanly on Ctrl+C.
        print("\nShutting down the server...")
        http_server.shutdown()


if __name__ == '__main__':
    # Environment variables allow the same script to run locally or as a service.
    server_host = os.environ.get('PODBROADCAST_HOST', DEFAULT_HOST)
    server_port = int(os.environ.get('PODBROADCAST_PORT', str(DEFAULT_PORT)))
    
    # Fail fast rather than starting a server that rejects every request.
    if not os.environ.get('PODBROADCAST_KEY'):
        print("WARNING: PODBROADCAST_KEY environment variable not set!")
        print("Please set it before running the server:")
        print("  export PODBROADCAST_KEY='your-secret-key'")
        exit(1)
    
    run_server(server_host, server_port)
