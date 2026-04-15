import time
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import db
from app.utils import normalize_ip
from app.cloudflare import list_policies, get_policy, put_policy

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

def require_cloudflare(request: Request):
    if "CF-Ray" not in request.headers:
        raise HTTPException(status_code=403)

@app.get("/")
def index(request: Request):
    require_cloudflare(request)
    now = int(time.time())
    wan_ip = request.headers.get("CF-Connecting-IP")

    with db() as conn:
        rows = conn.execute(
            "SELECT ip, expires_at, policy_id FROM ip_allowlist ORDER BY added_at DESC"
        ).fetchall()

    items = []
    for r in rows:
        remaining = None if r["expires_at"] is None else max(0, r["expires_at"] - now)
        items.append({
            "ip": r["ip"],
            "remaining": remaining,
            "expires_at": r["expires_at"],
            "policy_id": r["policy_id"],
        })

    policies = list_policies()
    bypass_policies = [
        {"id": p["id"], "name": p["name"]}
        for p in policies if p.get("decision") == "bypass"
    ]

    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "wan_ip": wan_ip,
            "items": items,
            "bypass_policies": bypass_policies,
        }
    )

@app.post("/add")
def add_ip(
    request: Request,
    ip: str = Form(...),
    duration: int = Form(...),
    policy_id: str = Form(...),
):
    require_cloudflare(request)
    ip = normalize_ip(ip)
    now = int(time.time())
    expires = None if duration == 0 else now + duration

    with db() as conn:
        conn.execute(
            "INSERT INTO ip_allowlist (ip, expires_at, added_at, policy_id) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ip) DO UPDATE SET expires_at=excluded.expires_at, policy_id=excluded.policy_id",
            (ip, expires, now, policy_id)
        )
        conn.commit()

    policy = get_policy(policy_id)
    policy.setdefault("include", [])

    if not any(r.get("ip", {}).get("ip") == ip for r in policy["include"]):
        policy["include"].append({"ip": {"ip": ip}})
        put_policy(policy_id, policy)

    return RedirectResponse("/", status_code=303)

@app.post("/remove")
def remove_ip(request: Request, ip: str = Form(...), policy_id: str = Form(...)):
    require_cloudflare(request)
    ip = normalize_ip(ip)

    with db() as conn:
        conn.execute("DELETE FROM ip_allowlist WHERE ip = ?", (ip,))
        conn.commit()

    policy = get_policy(policy_id)
    policy["include"] = [
        r for r in policy.get("include", [])
        if r.get("ip", {}).get("ip") != ip
    ]
    put_policy(policy_id, policy)

    return RedirectResponse("/", status_code=303)
