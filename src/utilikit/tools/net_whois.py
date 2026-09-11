"""WHOIS / RDAP, ASN lookups and a combined IP-info endpoint."""

from __future__ import annotations

import ipaddress
import socket

import dns.resolver
import httpx
from fastapi import APIRouter, Query

from ..cache import cached
from ..config import get_settings
from ..errors import ToolError, UpstreamError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["whois"])

_RDAP = "https://rdap.org"


@cached(ttl=1800)
def _rdap_get(path: str) -> dict:
    try:
        r = httpx.get(f"{_RDAP}{path}", follow_redirects=True, timeout=15, headers={"accept": "application/rdap+json"})
    except httpx.HTTPError as exc:
        raise UpstreamError(f"RDAP request failed: {exc}") from exc
    if r.status_code == 404:
        raise ToolError(
            "Not found in RDAP (registry may not publish RDAP for this).", status_code=404, type="not_found"
        )
    if r.status_code >= 400:
        raise UpstreamError(f"RDAP returned HTTP {r.status_code}.")
    return r.json()


def _events(obj: dict) -> dict[str, str]:
    return {e.get("eventAction", "?"): e.get("eventDate", "") for e in obj.get("events", [])}


def _vcard_name(entity: dict) -> str:
    try:
        for item in entity.get("vcardArray", [None, []])[1]:
            if item[0] == "fn":
                return item[3]
    except (IndexError, TypeError):
        pass
    return ""


def _entities(obj: dict) -> list[dict]:
    out = []
    for e in obj.get("entities", []):
        out.append(
            {
                "handle": e.get("handle", ""),
                "roles": e.get("roles", []),
                "name": _vcard_name(e),
            }
        )
    return out


@cached(ttl=900)
def _whois43(query: str, server: str = "whois.iana.org") -> str:
    try:
        with socket.create_connection((server, 43), timeout=10) as sock:
            sock.sendall((query + "\r\n").encode())
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
        return b"".join(chunks).decode("utf-8", "replace")
    except OSError as exc:
        raise UpstreamError(f"WHOIS ({server}:43) failed: {exc}") from exc


@router.get("/whois/domain", summary="Domain registration data (RDAP, with a port-43 fallback)")
def whois_domain(domain: str) -> dict:
    domain = domain.strip().lower().strip(".")
    if "." not in domain or " " in domain:
        raise ToolError("Give a bare domain, e.g. example.com")
    try:
        data = _rdap_get(f"/domain/{domain}")
        ev = _events(data)
        return {
            "source": "rdap",
            "domain": data.get("ldhName", domain),
            "status": data.get("status", []),
            "created": ev.get("registration", ""),
            "updated": ev.get("last changed", ev.get("last update of RDAP database", "")),
            "expires": ev.get("expiration", ""),
            "nameservers": sorted(ns.get("ldhName", "") for ns in data.get("nameservers", [])),
            "entities": _entities(data),
            "dnssec": bool(data.get("secureDNS", {}).get("delegationSigned")),
        }
    except (ToolError, UpstreamError):
        # ccTLDs frequently lack RDAP - fall back to classic WHOIS via IANA referral.
        iana = _whois43(domain, "whois.iana.org")
        refer = next(
            (ln.split(":", 1)[1].strip() for ln in iana.splitlines() if ln.lower().startswith("refer:")),
            "",
        )
        text = _whois43(domain, refer) if refer else iana
        return {"source": f"whois43 ({refer or 'iana'})", "domain": domain, "raw": text}


@router.get("/whois/ip", summary="IP allocation data (RDAP)")
def whois_ip(ip: str) -> dict:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ToolError(f"{ip!r} is not an IP address.") from exc
    data = _rdap_get(f"/ip/{addr}")
    ev = _events(data)
    return {
        "source": "rdap",
        "ip": ip,
        "handle": data.get("handle", ""),
        "name": data.get("name", ""),
        "type": data.get("type", ""),
        "country": data.get("country", ""),
        "cidr": [f"{c.get('v4prefix') or c.get('v6prefix')}/{c.get('length')}" for c in data.get("cidr0_cidrs", [])],
        "start_address": data.get("startAddress", ""),
        "end_address": data.get("endAddress", ""),
        "registered": ev.get("registration", ""),
        "updated": ev.get("last changed", ""),
        "entities": _entities(data),
    }


@cached(ttl=1800)
def _cymru_asn(ip: str) -> dict:
    addr = ipaddress.ip_address(ip)
    if addr.version == 4:
        rev = ".".join(reversed(ip.split("."))) + ".origin.asn.cymru.com"
    else:
        nibbles = addr.exploded.replace(":", "")
        rev = ".".join(reversed(nibbles)) + ".origin6.asn.cymru.com"
    try:
        txt = dns.resolver.resolve(rev, "TXT", lifetime=5).rrset[0].to_text().strip('"')
    except Exception as exc:  # NXDOMAIN etc.
        raise UpstreamError(f"Team Cymru ASN lookup failed: {exc}") from exc
    # "13335 | 1.1.1.0/24 | US | arin | 2010-07-14"
    asn, prefix, cc, registry, allocated = (p.strip() for p in txt.split("|"))
    name = ""
    try:
        nm = dns.resolver.resolve(f"AS{asn}.asn.cymru.com", "TXT", lifetime=5).rrset[0].to_text().strip('"')
        name = nm.split("|")[-1].strip()
    except Exception:
        pass
    return {
        "asn": int(asn.split()[0]),
        "prefix": prefix,
        "country": cc,
        "registry": registry,
        "allocated": allocated,
        "as_name": name,
    }


@router.get("/asn", summary="Origin ASN for an IP (Team Cymru)")
def asn_lookup(ip: str) -> dict:
    try:
        ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ToolError(f"{ip!r} is not an IP address.") from exc
    return {"ip": ip, **_cymru_asn(ip)}


@router.get("/ip/info", summary="Everything about an IP: RDAP + reverse DNS + ASN + optional geo")
def ip_info(ip: str, geo: bool = Query(True)) -> dict:
    try:
        ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ToolError(f"{ip!r} is not an IP address.") from exc

    out: dict = {"ip": ip}
    try:
        out["rdap"] = whois_ip(ip)
    except (ToolError, UpstreamError) as exc:
        out["rdap"] = {"error": exc.message}
    try:
        import dns.reversename

        rev = dns.reversename.from_address(ip)
        ptr = dns.resolver.resolve(rev, "PTR", lifetime=5)
        out["reverse_dns"] = [r.to_text().rstrip(".") for r in ptr.rrset]
    except Exception:
        out["reverse_dns"] = []
    try:
        out["asn"] = _cymru_asn(ip)
    except UpstreamError as exc:
        out["asn"] = {"error": exc.message}

    if geo:
        out["geo"] = _geo(ip)
    return out


def _geo(ip: str) -> dict:
    path = get_settings().geoip_mmdb_path
    if not path.exists():
        return {"available": False, "hint": f"put a MaxMind/DB-IP .mmdb at {path} and pip install 'utilikit[geo]'"}
    try:
        import geoip2.database

        with geoip2.database.Reader(str(path)) as reader:
            r = reader.city(ip)
            return {
                "available": True,
                "country": r.country.iso_code,
                "country_name": r.country.name,
                "city": r.city.name,
                "subdivision": r.subdivisions.most_specific.name if r.subdivisions else None,
                "latitude": r.location.latitude,
                "longitude": r.location.longitude,
                "timezone": r.location.time_zone,
            }
    except Exception as exc:  # geoip2 missing, or IP not in DB
        return {"available": False, "error": str(exc)}


register(
    ToolInfo(
        key="whois",
        title="WHOIS / RDAP / ASN",
        category="Network & OSINT",
        description=(
            "Domain & IP registration data via RDAP (port-43 fallback for ccTLDs), "
            "origin-ASN, and a combined IP dossier with optional offline geolocation."
        ),
        router=router,
        requires=["geo (optional, for /v1/ip/info geo)"],
        endpoints=[
            Endpoint("GET", "/v1/whois/domain", "Domain WHOIS", "?domain=example.com"),
            Endpoint("GET", "/v1/whois/ip", "IP WHOIS", "?ip=1.1.1.1"),
            Endpoint("GET", "/v1/asn", "Origin ASN", "?ip=8.8.8.8"),
            Endpoint("GET", "/v1/ip/info", "Full IP dossier", "?ip=8.8.8.8"),
        ],
    )
)
