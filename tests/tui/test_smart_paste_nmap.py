"""Tests for nmap text output parser."""

from bagley.tui.parsers.nmap import parse_nmap_output, Host

NMAP_OUTPUT = """
Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for 10.10.14.5
Host is up (0.045s latency).

PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 8.9p1 Ubuntu
80/tcp   open  http     Apache httpd 2.4.52
443/tcp  closed https
3306/tcp open  mysql    MySQL 8.0.32

Nmap scan report for 10.10.14.6
Host is up (0.030s latency).

PORT   STATE SERVICE
22/tcp open  ssh

Nmap done: 2 IP addresses (2 hosts up) scanned
""".strip()


def test_parse_returns_hosts():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    assert len(hosts) == 2


def test_parse_first_host_ip():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    assert hosts[0].ip == "10.10.14.5"


def test_parse_first_host_ports():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    ports = {p.number for p in hosts[0].ports}
    assert 22 in ports
    assert 80 in ports
    assert 443 in ports
    assert 3306 in ports


def test_parse_open_ports_only_flag():
    hosts = parse_nmap_output(NMAP_OUTPUT, open_only=True)
    ports = {p.number for p in hosts[0].ports}
    assert 22 in ports
    assert 443 not in ports


def test_parse_service_version():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    ssh_port = next(p for p in hosts[0].ports if p.number == 22)
    assert ssh_port.service == "ssh"
    assert "OpenSSH" in ssh_port.version


def test_parse_empty_returns_empty():
    assert parse_nmap_output("") == []
