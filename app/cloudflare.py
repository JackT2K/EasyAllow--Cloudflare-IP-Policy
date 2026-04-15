import os
import requests
from dotenv import load_dotenv

load_dotenv("/opt/ip-allow/.env")

API_BASE = "https://api.cloudflare.com/client/v4"
ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")

HEADERS = {
    "Authorization": f"Bearer {os.getenv('CF_API_TOKEN')}",
    "Content-Type": "application/json",
}

def list_policies():
    url = f"{API_BASE}/accounts/{ACCOUNT_ID}/access/policies"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()["result"]

def get_policy(policy_id: str):
    url = f"{API_BASE}/accounts/{ACCOUNT_ID}/access/policies/{policy_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()["result"]

def put_policy(policy_id: str, policy_obj: dict):
    url = f"{API_BASE}/accounts/{ACCOUNT_ID}/access/policies/{policy_id}"
    r = requests.put(url, headers=HEADERS, json=policy_obj, timeout=20)
    r.raise_for_status()
    return r.json()
