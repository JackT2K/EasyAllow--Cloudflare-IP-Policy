import ipaddress

def normalize_ip(ip: str) -> str:
    ip = ip.strip()
    if "/" not in ip:
        addr = ipaddress.ip_address(ip)
        return f"{ip}/32" if addr.version == 4 else f"{ip}/128"
    ipaddress.ip_network(ip, strict=False)
    return ip
