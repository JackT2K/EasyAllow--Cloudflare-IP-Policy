import time
from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.db import db
from app.utils import normalize_ip
from app.cloudflare import list_policies, get_policy, put_policy

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


def require_cloudflare(request: Request):
    # Only allow requests that come through Cloudflare (Tunnel/Access)
    if "CF-Ray" not in request.headers:
        raise HTTPException(status_code=403)


@app.get("/")
def index(request: Request, policy_id: str | None = Query(default=None)):
    require_cloudflare(request)
    now = int(time.time())
    wan_ip = request.headers.get("CF-Connecting-IP")

    # Pull all reusable policies and filter to bypass
    policies = list_policies()
    bypass_policies = [
        {"id": p.get("id"), "name": p.get("name")}
        for p in policies
        if p.get("decision") == "bypass"
    ]

    # Build lookup for display
    policy_name_by_id = {p.get("id"): p.get("name") for p in policies}

    # Default selection: first bypass policy (if any)
    if not policy_id and bypass_policies:
        policy_id = bypass_policies[0]["id"]

    # Query items filtered to selected policy_id
    with db() as conn:
        if policy_id:
            rows = conn.execute(
                "SELECT ip, expires_at, added_at, policy_id FROM ip_allowlist "
                "WHERE policy_id = ? ORDER BY added_at DESC",
                (policy_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ip, expires_at, added_at, policy_id FROM ip_allowlist "
                "ORDER BY added_at DESC"
            ).fetchall()

    items = []
    for r in rows:
        expires_at = r["expires_at"]
        remaining = None if expires_at is None else max(0, int(expires_at) - now)
        items.append(
            {
                "ip": r["ip"],
                "expires_at": expires_at,
                "remaining": remaining,
                "policy_id": r["policy_id"],
                "policy_name": policy_name_by_id.get(r["policy_id"], r["policy_id"] or "Unknown"),
            }
        )

    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "wan_ip": wan_ip,
            "items": items,
            "bypass_policies": bypass_policies,
            "selected_policy_id": policy_id,
        },
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
    expires = None if duration == 0 else now + int(duration)

    # Store in DB (include policy_id)
    with db() as conn:
        conn.execute(
            "INSERT INTO ip_allowlist (ip, expires_at, added_at, policy_id) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(ip) DO UPDATE SET "
            "expires_at=excluded.expires_at, "
            "policy_id=excluded.policy_id",
            (ip, expires, now, policy_id),
        )
        conn.commit()

    # Add to Cloudflare policy include rules (if not already there)
    policy = get_policy(policy_id)
    policy.setdefault("include", [])
    if not any(rule.get("ip", {}).get("ip") == ip for rule in policy["include"]):
        policy["include"].append({"ip": {"ip": ip}})
        put_policy(policy_id, policy)

    return RedirectResponse(f"/?policy_id={policy_id}", status_code=303)


@app.post("/remove")
def remove_ip(
    request: Request,
    ip: str = Form(...),
    policy_id: str = Form(...),
):
    require_cloudflare(request)
    ip = normalize_ip(ip)

    # Remove from DB
    with db() as conn:
        conn.execute("DELETE FROM ip_allowlist WHERE ip = ?", (ip,))
        conn.commit()

    # Remove from Cloudflare policy include rules
    policy = get_policy(policy_id)
    policy["include"] = [
        r for r in policy.get("include", [])
        if r.get("ip", {}).get("ip") != ip
    ]
    put_policy(policy_id, policy)

    return RedirectResponse(f"/?policy_id={policy_id}", status_code=303)