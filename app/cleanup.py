import time
from app.db import db
from app.cloudflare import get_policy, put_policy

now = int(time.time())

with db() as conn:
    expired = conn.execute(
        "SELECT ip, policy_id FROM ip_allowlist WHERE expires_at IS NOT NULL AND expires_at < ?",
        (now,)
    ).fetchall()

if expired:
    by_policy = {}
    for r in expired:
        by_policy.setdefault(r["policy_id"], set()).add(r["ip"])

    for policy_id, ips in by_policy.items():
        policy = get_policy(policy_id)
        policy["include"] = [
            r for r in policy.get("include", [])
            if r.get("ip", {}).get("ip") not in ips
        ]
        put_policy(policy_id, policy)

    with db() as conn:
        conn.execute(
            "DELETE FROM ip_allowlist WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,)
        )
        conn.commit()
