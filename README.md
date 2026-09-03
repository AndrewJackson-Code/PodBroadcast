# PodBroadcast
A tiny HTTP server for broadcasting the status of podman containers on the local machine. Uses JSON format.

## Features

- **Minimal SSD Wear**: All data is stored exclusively in RAM - no writes to disk
- **Secure Access**: Requires API key authentication for all requests
- **JSON Format**: Uses `podman ps --format json` for container status
- **Host Metrics**: Reports aggregate CPU usage and CPU temperature when available
- **Flexible Deployment**: Can run as a systemd service or via cron job
- **No Dependencies**: Uses only Python standard library

## Requirements

- Python 3.6 or higher
- Podman installed and accessible
- Linux system with systemd (for service mode)

## Installation

1. Clone the repository or download the script:
```bash
git clone https://github.com/AndrewJackson-Code/PodBroadcast.git
cd PodBroadcast
```

2. Make the script executable:
```bash
chmod +x podbroadcast.py
```

3. (Optional) Copy to a system directory:
```bash
sudo cp podbroadcast.py /usr/local/bin/
```

## Usage

### Running Manually

Set your API key and run the server:

```bash
export PODBROADCAST_KEY='your-secret-key-here'
python3 podbroadcast.py
```

The server will start on `http://0.0.0.0:8080` by default.

### Environment Variables

- `PODBROADCAST_KEY` (required): API key for authentication
- `PODBROADCAST_HOST` (optional): Host to bind to (default: `0.0.0.0`)
- `PODBROADCAST_PORT` (optional): Port to listen on (default: `8080`)

### Running as a systemd Service

1. Create an environment file for security:
```bash
sudo mkdir -p /etc/podbroadcast
sudo bash -c 'cat > /etc/podbroadcast/podbroadcast.env << EOF
PODBROADCAST_KEY=your-secret-key-here
PODBROADCAST_HOST=0.0.0.0
PODBROADCAST_PORT=8080
EOF'
sudo chmod 600 /etc/podbroadcast/podbroadcast.env
```

2. Copy the service file:
```bash
sudo cp podbroadcast.service /etc/systemd/system/
```

3. Edit the service file to use the environment file:
```bash
sudo nano /etc/systemd/system/podbroadcast.service
# Uncomment the EnvironmentFile line and comment out the Environment lines
```

4. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable podbroadcast.service
sudo systemctl start podbroadcast.service
```

5. Check the status:
```bash
sudo systemctl status podbroadcast.service
```

### Running as a Cron Job

For periodic status broadcasts, you can run the server for a limited time via cron:

1. Create a wrapper script `/usr/local/bin/podbroadcast-cron.sh`:
```bash
#!/bin/bash
export PODBROADCAST_KEY='your-secret-key-here'
timeout 5m /usr/local/bin/podbroadcast.py
```

2. Make it executable:
```bash
chmod +x /usr/local/bin/podbroadcast-cron.sh
```

3. Add to crontab (e.g., run every hour):
```bash
crontab -e
# Add:
0 * * * * /usr/local/bin/podbroadcast-cron.sh
```

**Note**: Running as a continuous service (systemd) is recommended for LAN broadcasting. The cron approach is better suited for scheduled status checks.

## Accessing the API

Once the server is running, access it with your API key:

```bash
curl "http://localhost:8080/?key=your-secret-key-here"
```

Or from another machine on the LAN:

```bash
curl "http://192.168.1.100:8080/?key=your-secret-key-here"
```

The response will be JSON-formatted podman container status:

```json
[
  {
    "Id": "abc123...",
    "Names": ["my-container"],
    "Image": "docker.io/library/nginx:latest",
    "Status": "Up 2 hours",
    "State": "running",
    ...
  }
]
```

The original endpoint remains unchanged for existing clients. To include host CPU
metrics with the container status, use the `/metrics` endpoint:

```bash
curl "http://localhost:8080/metrics?key=your-secret-key-here"
```

```json
{
  "containers": [
    {
      "Id": "abc123...",
      "Names": ["my-container"],
      "State": "running"
    }
  ],
  "system": {
    "cpu_usage_percent": 14.2,
    "cpu_temperature_celsius": 52.0
  }
}
```

CPU metrics are read from Linux `/proc` and `/sys` without external dependencies.
Temperature is `null` when the machine, VM, or kernel does not expose a recognized
CPU sensor.

## Security Considerations

1. **API Key**: Always use a strong, random API key. Generate one with:
   ```bash
   openssl rand -hex 32
   ```

2. **Network Access**: Consider using a firewall to restrict access to trusted IPs:
   ```bash
   sudo ufw allow from 192.168.1.0/24 to any port 8080
   ```

3. **HTTPS**: For production use, consider placing the server behind a reverse proxy with TLS (e.g., nginx, Caddy).

4. **Non-Root User**: Run the service as a non-root user for additional security.

## Troubleshooting

### Server won't start
- Ensure the `PODBROADCAST_KEY` environment variable is set
- Check if the port is already in use: `sudo netstat -tulpn | grep 8080`
- Verify podman is installed: `which podman`

### Getting 401 Unauthorized
- Verify you're using the correct API key
- Ensure the key is properly URL-encoded in the query string

### Getting 500 Internal Server Error
- Check if podman is accessible: `podman ps --format json`
- Review server logs: `sudo journalctl -u podbroadcast.service -n 50`
- If running as systemd service with exit code 125: Ensure the service file doesn't have `ReadOnlyPaths=/` set, as podman needs write access to `/run`, `/var/lib/containers`, and other directories

## License

This project is licensed under the GNU General Public License v2.0 - see the LICENSE file for details.
