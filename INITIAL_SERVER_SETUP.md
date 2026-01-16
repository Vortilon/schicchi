# Initial Server Setup

The `/opt/schicchi` directory doesn't exist yet. Here's how to set it up:

## Option 1: Copy Files from Local Machine (Recommended)

**From your LOCAL machine** (where you have the code):

1. **Make sure you're in the project directory:**
   ```bash
   cd /Users/carolynlepper/schicchi/schicchi
   ```

2. **Run the copy script:**
   ```bash
   ./COPY_TO_SERVER.sh
   ```

   OR manually with rsync:
   ```bash
   rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
     --exclude 'schicchi.db' --exclude '*.log' \
     ./ root@167.88.36.83:/opt/schicchi/
   ```

   OR with scp (if rsync not available):
   ```bash
   scp -r . root@167.88.36.83:/opt/schicchi/schicchi/
   ```

3. **SSH to server and set up:**
   ```bash
   ssh root@167.88.36.83
   cd /opt/schicchi
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Option 2: Create Directory and Clone from GitHub

**On the SERVER:**

1. **Create directory:**
   ```bash
   mkdir -p /opt/schicchi
   cd /opt/schicchi
   ```

2. **Clone repository (if you've pushed to GitHub):**
   ```bash
   git clone git@github.com:Vortilon/schicchi.git
   cd schicchi/schicchi
   ```

3. **Set up virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Option 3: Manual Setup on Server

**On the SERVER, run these commands:**

```bash
# Create directory
mkdir -p /opt/schicchi
cd /opt/schicchi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Create requirements.txt (you'll need to copy the file or create it)
# Then install dependencies
pip install -r requirements.txt
```

## Quick Setup Command (Run on Server)

Once you have files on the server, run this:

```bash
cd /opt/schicchi/schicchi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export ALPACA_API_KEY="PK2GOVNPOKMT4BXY3OFFWOVHBS"
export ALPACA_SECRET_KEY="3QtrLXygY7ztrP5am1gr6FBUCDq1QAJizvqCP2BuEME2"

# Test webhook server
python webhook_server.py
```

