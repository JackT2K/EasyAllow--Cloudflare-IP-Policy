# EasyAllow--Cloudflare-IP-Policy
Simple Python powered website that is inteded to be used with a cloudflare tunnel. This when ran will allow you to access this site protected with an identity provider and easily add your current IP to a bypass policy. 


Cloudflare Access IP Bypass Portal – From-Scratch Deployment Guide 

✅ Secure self‑service web portal ✅ Protected by Cloudflare Access + Azure AD ✅ Allows adding/removing IPs to Bypass Access policies ✅ Automatic expiration (TTL cleanup) ✅ No hard‑coded policy IDs – live dropdown of Bypass policies ✅ Runs behind Cloudflare Tunnel (HTTPS handled by Cloudflare) 

1. Architecture Overview 

    Browser 
      ↓ 
    Cloudflare Access (Azure AD) 
      ↓ 
    Cloudflare Tunnel 
      ↓ 
    FastAPI app (127.0.0.1:8000) 
      ↓ 
    Cloudflare Access API (reusable policies) 

The app: 

Is never publicly exposed 
Trusts Cloudflare headers only 
Edits Reusable Access Policies with decision = bypass 

2. Prerequisites (Assumed Done) 

This guide does NOT cover: 
Ubuntu installation 
Cloudflare Tunnel setup 

You must already have: 
✅ Ubuntu 22.04+ 
✅ Working Cloudflare Tunnel mapping subdomain.domain.tld → http://127.0.0.1:8000 
✅ Cloudflare Access Application protecting subdomain.domain.tld
✅ At least one Reusable Access Policy with Decision = Bypass 

3. Cloudflare API Token 

Create an API token with these permissions: 
Scope    Permission 
Account  Access: Apps and Policies Read 
Account  Access: Apps and Policies Edit 

Save: 
API Token 
Account ID 

4. System Packages

sudo apt update 
sudo apt install -y python3 python3-venv python3-pip sqlite3 curl

5. Directory Layout 
    /opt/ip-allow 
    ├── app
    │   ├── main.py 
    │   ├── cloudflare.py 
    │   ├── cleanup.py 
    │   ├── db.py 
    │   ├── utils.py 
    │   └── templates 
    │       └── index.html 
    ├── ip_allow.db 
    ├── requirements.txt 
    ├── .env 
    └── systemd 
        ├── ip-allow.service 
        └── ip-allow-cleanup.timer

Create It
1     sudo mkdir -p /opt/ip-allow/app/templates /opt/ip-allow/systemd 
2     sudo chown -R $USER:$USER /opt/ip-allow 
3     cd /opt/ip-allow 

6. Python Virtual Environment 

1     python3 -m venv venv 
2     source venv/bin/activate 

7. Python Requirements 

nano /opt/ip-allow/requirements.txt 

fastapi 
uvicorn 
jinja2 
requests 
python-dotenv 
python-multipart 

Install: 

pip install -r requirements.txt 

8. Environment Variables 

nano /opt/ip-allow/.env 

CF_API_TOKEN=REDACTED 
CF_ACCOUNT_ID=REDACTED    

Permissions: 
chmod 600 .env 

9. Database Initialization 

sqlite3 ip_allow.db <<'SQL' 
CREATE TABLE IF NOT EXISTS ip_allowlist ( 
  ip TEXT PRIMARY KEY, 
  expires_at INTEGER, 
  added_at INTEGER NOT NULL, 
  policy_id TEXT 
); 
SQL 

Install and Enable

sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/ 
sudo systemctl daemon-reload 
sudo systemctl enable --now ip-allow ip-allow-cleanup.timer 

