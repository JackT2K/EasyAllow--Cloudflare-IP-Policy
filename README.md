# EasyAllow – Cloudflare Access IP Bypass Portal

EasyAllow is a self‑service web portal that allows administrators to temporarily add and remove IP addresses from Cloudflare Access *Bypass* policies.

It is intended for environments using Cloudflare Access with Entra ID (Azure AD) or other identy providors where admins need a fast, controlled way to bypass identity prompts from trusted locations without permanently modifying allowlists.

The application runs entirely behind Cloudflare Access via a Cloudflare Tunnel. TLS, authentication, and identity are enforced by Cloudflare.

---

## Features

- Protected by Cloudflare Access and Entra ID (Azure AD)
- Automatically detects the client’s current WAN IP
- Manually add or remove IP addresses
- Select from all reusable Cloudflare Access policies with decision = bypass
- Time‑limited access (minutes, hours, or unlimited)
- Automatic cleanup of expired IPs
- No public ports exposed
- No TLS or certificate management
- SQLite backend (no external database)

---

## Architecture Overview

Browser  
→ Cloudflare Access (Azure AD)  
→ Cloudflare Tunnel  
→ FastAPI app (127.0.0.1:8000)  
→ Cloudflare Access API (Reusable Bypass Policies)

The application does not validate Azure tokens itself. Cloudflare Access is treated as the trust boundary. Requests without Cloudflare headers are rejected.

---

## Cloudflare Access Model (Important)

EasyAllow relies on two separate policy types:

1. Bypass policies (IP‑based)
- Decision: bypass
- Rules: IP ranges only
- No identity requirements

EasyAllow dynamically edits these policies.

2. Allow policies (identity‑based)
- Decision: allow
- Rules: Entra ID users or groups

These remain unchanged and continue to enforce Azure login when no bypass applies.

Important: using an Allow policy will still trigger Azure authentication. To skip Azure AD entirely, IP rules must live in a Bypass policy with higher precedence.

---

## Requirements

### Platform
- Ubuntu 22.04 or newer
- Python 3.10+

### Cloudflare
- Cloudflare Tunnel already configured to route a hostname to http://127.0.0.1:8000
- Cloudflare Access application protecting that hostname
- At least one reusable Cloudflare Access policy with decision = bypass

### Cloudflare API Token
The API token must have the following permissions:

Account → Access: Apps and Policies → Read  
Account → Access: Apps and Policies → Edit  

---

## Deployment

These steps assume:
- Ubuntu is already installed
- Cloudflare Tunnel is already configured
- Cloudflare Access is already protecting the hostname

### 1. Clone the repository
git clone https://github.com/JackT2K/EasyAllow--Cloudflare-IP-Policy.git

cd EasyAllow--Cloudflare-IP-Policy

### 2. Install system dependencies

sudo apt update
sudo apt install -y python3 python3-venv python3-pip sqlite3 curl

### 3. Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

### 4. Install Python requirements
pip install -r requirements.txt

### 5. Configure environment variables

Edit the `.env` file and populate it with your Cloudflare details:

CF_API_TOKEN=your_cloudflare_api_token
CF_ACCOUNT_ID=your_account_id

Set permissions:

chmod 600 .env

### 6. Initialize the database

sqlite3 ip_allow.db <<EOF
CREATE TABLE IF NOT EXISTS ip_allowlist (
ip TEXT PRIMARY KEY,
expires_at INTEGER,
added_at INTEGER NOT NULL,
policy_id TEXT
);
EOF

### 7. Install systemd services
sudo cp systemd/.service systemd/.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ip-allow
sudo systemctl enable --now ip-allow-cleanup.timer

### 8. Validation

Local access (should be blocked):

curl http://127.0.0.1:8000

Expected response:
403 Forbidden

Browser access:
- Navigate to the hostname protected by Cloudflare Access
- Authenticate via Entra ID
- The EasyAllow UI should load
- Bypass policies should appear in the dropdown


## Security Notes

- The application only accepts requests containing Cloudflare headers
- No credentials are stored locally
- The Cloudflare API token is scoped only to Access policies
- The app should never be exposed without Cloudflare Access in front of it


## Common Pitfalls

- Using an Allow policy instead of a Bypass policy
- Placing the Bypass policy below identity‑based policies
- API token missing Access policy read permissions
- Expecting bypass behavior without policy precedence configured correctly
