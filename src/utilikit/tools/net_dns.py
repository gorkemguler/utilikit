"""DNS lookups: records, reverse DNS, cross-resolver propagation check."""

from __future__ import annotations

import ipaddress

import dns.exception
import dns.rdatatype
import dns.resolver
import dns.reversename
from fastapi import APIRouter, Query

from ..cache import cached
from ..errors import ToolError, UpstreamError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["dns"])

_DEFAULT_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]
_PUBLIC_RESOLVERS = {
    "cloudflare": "1.1.1.1",
    "google": "8.8.8.8",
    "quad9": "9.9.9.9",
    "opendns": "208.67.222.222",
    "adguard": "94.140.14.14",
}


def _rdata_str(rtype: str, rdata) -> str:
    return rdata.to_text()


@cached(ttl=120)
def _query(name: str, rtype: str, resolver_ip: str | None) -> list[str]:
    res = dns.resolver.Resolver(configure=resolver_ip is None)
    if resolver_ip:
        res.nameservers = [resolver_ip]
    res.lifetime = 5.0
    res.timeout = 5.0
    try:
        answer = res.resolve(name, rtype, raise_on_no_answer=False)
    except dns.resolver.NXDOMAIN:
        return ["__NXDOMAIN__"]
    except (dns.resolver.NoNameservers, dns.exception.Timeout) as exc:
        raise UpstreamError(f"DNS query for {name}/{rtype} failed: {exc}") from exc
    if answer.rrset is None:
        return []
    return sorted(_rdata_str(rtype, r) for r in answer.rrset)


@router.get("/dns/records", summary="Look up DNS records for a name")
def dns_records(
    name: str,
    types: str = Query("", description="Comma-separated, e.g. A,AAAA,MX. Empty = a sensible default set."),
    resolver: str | None = Query(None, description="Resolver IP; default = the server's."),
) -> dict:
    name = name.strip().rstrip(".")
    if not name:
        raise ToolError("name is required.")
    want = [t.strip().upper() for t in types.split(",") if t.strip()] or _DEFAULT_TYPES
    for t in want:
        if not hasattr(dns.rdatatype, t):
            raise ToolError(f"Unknown record type {t!r}.")
    out: dict[str, list[str]] = {}
    nxdomain = False
    for t in want:
        recs = _query(name, t, resolver)
        if recs == ["__NXDOMAIN__"]:
            nxdomain = True
            out[t] = []
        else:
            out[t] = recs
    return {"name": name, "resolver": resolver or "system", "nxdomain": nxdomain, "records": out}


@router.get("/dns/reverse", summary="Reverse DNS (PTR) for an IP address")
def dns_reverse(ip: str) -> dict:
    try:
        ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ToolError(f"{ip!r} is not an IP address.") from exc
    rev = dns.reversename.from_address(ip)
    ptr = _query(str(rev), "PTR", None)
    return {"ip": ip, "ptr": [] if ptr == ["__NXDOMAIN__"] else ptr}


@router.get("/dns/propagation", summary="Query several public resolvers and compare answers")
def dns_propagation(
    name: str,
    type: str = Query("A"),
) -> dict:
    name, rtype = name.strip().rstrip("."), type.strip().upper()
    if not hasattr(dns.rdatatype, rtype):
        raise ToolError(f"Unknown record type {rtype!r}.")
    per_resolver: dict[str, list[str] | str] = {}
    seen: set[tuple[str, ...]] = set()
    for label, ip in _PUBLIC_RESOLVERS.items():
        try:
            recs = _query(name, rtype, ip)
            if recs == ["__NXDOMAIN__"]:
                per_resolver[label] = "NXDOMAIN"
            else:
                per_resolver[label] = recs
                seen.add(tuple(recs))
        except UpstreamError as exc:
            per_resolver[label] = f"error: {exc.message}"
    return {
        "name": name,
        "type": rtype,
        "consistent": len(seen) <= 1,
        "distinct_answers": [list(s) for s in seen],
        "by_resolver": per_resolver,
    }


register(
    ToolInfo(
        key="dns",
        title="DNS lookups",
        category="Network & OSINT",
        description="Resolve any record type, reverse DNS, and a propagation check across 5 public resolvers.",
        router=router,
        endpoints=[
            Endpoint("GET", "/v1/dns/records", "Records for a name", "?name=example.com&types=A,MX,TXT"),
            Endpoint("GET", "/v1/dns/reverse", "PTR for an IP", "?ip=1.1.1.1"),
            Endpoint("GET", "/v1/dns/propagation", "Compare resolvers", "?name=example.com&type=A"),
        ],
    )
)
