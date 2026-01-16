# Connect to Server

## Quick SSH Connection

### From Terminal (Mac/Linux):
```bash
ssh root@167.88.36.83
```

When prompted, enter the password:
```
ElNeneNunito135#
```

### One-liner with password (using sshpass if installed):
```bash
sshpass -p 'ElNeneNunito135#' ssh root@167.88.36.83
```

**Note:** `sshpass` may need to be installed first:
- Mac: `brew install sshpass`
- Linux: `sudo apt-get install sshpass` or `sudo yum install sshpass`

### After connecting, navigate to project:
```bash
cd /opt/schicchi
```

## Setup SSH Key (Recommended - No Password Needed)

To avoid entering password each time:

1. **Generate SSH key (if you don't have one):**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   # Press Enter to accept default location
   # Enter passphrase (optional)
   ```

2. **Copy public key to server:**
   ```bash
   ssh-copy-id root@167.88.36.83
   ```
   Enter password when prompted: `ElNeneNunito135#`

3. **Now you can connect without password:**
   ```bash
   ssh root@167.88.36.83
   ```

## Quick Setup Script

Save this as `connect.sh` and make it executable:

```bash
#!/bin/bash
ssh root@167.88.36.83 << 'EOF'
cd /opt/schicchi/schicchi
pwd
ls -la
EOF
```

Make executable:
```bash
chmod +x connect.sh
./connect.sh
```

## Server Details

- **IP Address:** 167.88.36.83
- **Username:** root
- **Password:** ElNeneNunito135#
- **Project Path:** /opt/schicchi

## Common Commands After Connection

```bash
# Navigate to project
cd /opt/schicchi

# Check if webhook server is running
ps aux | grep webhook_server

# Start webhook server
source venv/bin/activate
python webhook_server.py

# Check logs (if using systemd)
sudo systemctl status schicchi-webhook

# View webhook server logs
sudo journalctl -u schicchi-webhook -f
```

