"""DNS + WHOIS with the upstreams monkeypatched (no real network in CI)."""

from __future__ import annotations

import pytest


@pytest.fixture
def fake_dns(monkeypatch):
    table = {
        ("example.com", "A", None): ["93.184.216.34"],
        ("example.com", "MX", None): ["0 ."],
        ("example.com", "TXT", None): ['"v=spf1 -all"'],
        ("example.com", "A", "1.1.1.1"): ["93.184.216.34"],
        ("example.com", "A", "8.8.8.8"): ["93.184.216.34"],
        ("example.com", "A", "9.9.9.9"): ["93.184.216.34"],
        ("example.com", "A", "208.67.222.222"): ["93.184.216.34"],
        ("example.com", "A", "94.140.14.14"): ["203.0.113.9"],  # one odd one out
        ("4.4.8.8.in-addr.arpa.", "PTR", None): ["dns.google"],
    }

    def fake_query(name, rtype, resolver):
        return table.get((name, rtype, resolver), [])

    monkeypatch.setattr("utilikit.tools.net_dns._query", fake_query)


def test_dns_records(client, fake_dns):
    r = client.get("/v1/dns/records", params={"name": "example.com", "types": "A,MX,TXT"}).json()
    assert r["records"]["A"] == ["93.184.216.34"]
    assert r["records"]["TXT"] == ['"v=spf1 -all"']
    assert r["nxdomain"] is False


def test_dns_reverse(client, fake_dns):
    r = client.get("/v1/dns/reverse", params={"ip": "8.8.4.4"}).json()
    assert r["ptr"] == ["dns.google"]


def test_dns_propagation_detects_mismatch(client, fake_dns):
    r = client.get("/v1/dns/propagation", params={"name": "example.com", "type": "A"}).json()
    assert r["consistent"] is False
    assert r["by_resolver"]["adguard"] == ["203.0.113.9"]


def test_dns_reverse_rejects_bad_ip(client):
    assert client.get("/v1/dns/reverse", params={"ip": "not-an-ip"}).status_code == 400


@pytest.fixture
def fake_rdap(monkeypatch):
    domain_doc = {
        "ldhName": "example.com",
        "status": ["client transfer prohibited"],
        "events": [
            {"eventAction": "registration", "eventDate": "1995-08-14T04:00:00Z"},
            {"eventAction": "expiration", "eventDate": "2027-08-13T04:00:00Z"},
        ],
        "nameservers": [{"ldhName": "a.iana-servers.net"}, {"ldhName": "b.iana-servers.net"}],
        "entities": [{"handle": "376", "roles": ["registrar"], "vcardArray": [None, [["fn", {}, "text", "RESERVED"]]]}],
        "secureDNS": {"delegationSigned": True},
    }
    ip_doc = {
        "handle": "NET-93-184-216-0-1",
        "name": "EDGECAST-NETBLK",
        "type": "DIRECT ALLOCATION",
        "country": "US",
        "startAddress": "93.184.216.0",
        "endAddress": "93.184.216.255",
        "events": [{"eventAction": "registration", "eventDate": "2008-01-01T00:00:00Z"}],
        "cidr0_cidrs": [{"v4prefix": "93.184.216.0", "length": 24}],
        "entities": [],
    }

    def fake_get(path: str):
        if path.startswith("/domain/"):
            return domain_doc
        if path.startswith("/ip/"):
            return ip_doc
        raise AssertionError(path)

    monkeypatch.setattr("utilikit.tools.net_whois._rdap_get", fake_get)


def test_whois_domain(client, fake_rdap):
    r = client.get("/v1/whois/domain", params={"domain": "example.com"}).json()
    assert r["source"] == "rdap"
    assert r["expires"].startswith("2027")
    assert r["dnssec"] is True
    assert "a.iana-servers.net" in r["nameservers"]


def test_whois_ip(client, fake_rdap):
    r = client.get("/v1/whois/ip", params={"ip": "93.184.216.34"}).json()
    assert r["country"] == "US" and r["cidr"] == ["93.184.216.0/24"]


def test_whois_domain_rejects_garbage(client):
    assert client.get("/v1/whois/domain", params={"domain": "not a domain"}).status_code == 400
