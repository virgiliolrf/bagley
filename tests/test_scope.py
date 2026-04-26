from bagley.agent.safeguards import Scope, check_scope, check_all


def test_in_scope_cidr():
    s = Scope(cidrs=("10.10.0.0/16",))
    assert check_scope("nmap 10.10.45.22", s).allowed


def test_out_of_scope_cidr():
    s = Scope(cidrs=("10.10.0.0/16",))
    assert not check_scope("nmap 10.0.0.5", s).allowed


def test_allow_rfc1918_convenience():
    s = Scope(allow_any_rfc1918=True)
    assert check_scope("nmap 192.168.1.50", s).allowed


def test_public_ip_blocked_even_with_rfc1918():
    s = Scope(allow_any_rfc1918=True)
    assert not check_scope("nmap 8.8.8.8", s).allowed


def test_hostname_allowlist():
    s = Scope(hostnames=frozenset({"megacorp.thm"}))
    assert check_scope("curl http://megacorp.thm", s).allowed
    assert check_scope("curl http://sub.megacorp.thm", s).allowed


def test_hostname_out_of_scope():
    s = Scope(hostnames=frozenset({"megacorp.thm"}))
    assert not check_scope("curl http://other.com", s).allowed


def test_github_always_allowed():
    s = Scope()
    assert check_scope("wget https://raw.githubusercontent.com/x/y/z.sh", s).allowed


def test_check_all_destructive_blocks_first():
    s = Scope(cidrs=("10.10.0.0/16",))
    assert not check_all("rm -rf /", s).allowed


def test_check_all_scope_applies_when_destructive_passes():
    s = Scope(cidrs=("10.10.0.0/16",))
    assert not check_all("nmap 192.168.1.1", s).allowed
    assert check_all("nmap 10.10.45.22", s).allowed


def test_empty_scope_blocks_any_ip():
    s = Scope()
    assert not check_scope("nmap 10.10.45.22", s).allowed


def test_localhost_always_allowed():
    s = Scope()
    assert check_scope("nc 127.0.0.1 4444", s).allowed
