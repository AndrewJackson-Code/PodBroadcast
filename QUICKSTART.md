# Quick Start Guide

## Fastest Way to Get Started

1. **Generate an API key:**
   ```bash
   export PODBROADCAST_KEY=$(openssl rand -hex 32)
   echo "Your API key: $PODBROADCAST_KEY"
   ```

2. **Run the server:**
   ```bash
   python3 podbroadcast.py
   ```

3. **Test it:**
   ```bash
   curl "http://localhost:8080/?key=$PODBROADCAST_KEY"
   ```

## Install as systemd Service

```bash
# 1. Copy script to system location
sudo cp podbroadcast.py /usr/local/bin/
sudo chmod +x /usr/local/bin/podbroadcast.py

# 2. Create config directory and environment file
sudo mkdir -p /etc/podbroadcast
sudo bash -c "echo 'PODBROADCAST_KEY=$(openssl rand -hex 32)' > /etc/podbroadcast/podbroadcast.env"
sudo chmod 600 /etc/podbroadcast/podbroadcast.env

# 3. Install and configure service
sudo cp podbroadcast.service /etc/systemd/system/
sudo nano /etc/systemd/system/podbroadcast.service
# Uncomment: EnvironmentFile=/etc/podbroadcast/podbroadcast.env
# Comment out: Environment="PODBROADCAST_KEY=..."

# 4. Start service
sudo systemctl daemon-reload
sudo systemctl enable --now podbroadcast.service

# 5. Check status
sudo systemctl status podbroadcast.service

# 6. View your API key and test
sudo cat /etc/podbroadcast/podbroadcast.env
curl "http://localhost:8080/?key=YOUR_KEY_FROM_ABOVE"
```

## Security Tips

- **Never commit your API key to version control**
- **Use a strong, random API key** (at least 32 characters)
- **Restrict network access** with firewall rules
- **Run as non-root user** in production
- **Use HTTPS** with a reverse proxy for production

## Troubleshooting

```bash
# Check if podman is working
podman ps --format json

# Check server logs
sudo journalctl -u podbroadcast.service -f

# Test with verbose curl
curl -v "http://localhost:8080/?key=YOUR_KEY"

# Check what's using port 8080
sudo netstat -tulpn | grep 8080
```
