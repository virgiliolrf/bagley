"""Browser tool via playwright — Bagley pesquisa em sources públicas.

Sources allowlist (sem login):
    exploit-db.com, hacktricks.xyz, portswigger.net/research, github.com (public search),
    stackoverflow.com, reddit.com/r/netsec, web.archive.org, subdomainfinder.c99.nl,
    bgp.he.net, nvd.nist.gov, cve.mitre.org

Uso via tool_call do modelo:
    <tool_call>{"name":"web_research","arguments":{"query":"CVE-2024-X exploit PoC"}}</tool_call>
    <tool_call>{"name":"browse","arguments":{"url":"https://exploit-db.com/..."}}</tool_call>

Instalação:
    pip install playwright
    playwright install chromium  # ~250MB
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable
from urllib.parse import urlparse


ALLOWED_DOMAINS = frozenset({
    "exploit-db.com", "hacktricks.xyz", "book.hacktricks.xyz",
    "portswigger.net", "stackoverflow.com", "security.stackexchange.com",
    "github.com", "raw.githubusercontent.com", "gist.github.com",
    "reddit.com", "old.reddit.com", "www.reddit.com",
    "web.archive.org", "subdomainfinder.c99.nl",
    "bgp.he.net", "nvd.nist.gov", "cve.mitre.org", "cve.org",
    "attack.mitre.org", "capec.mitre.org",
    "owasp.org", "cwe.mitre.org", "kb.cert.org",
    "google.com", "duckduckgo.com",  # search engines (used in research mode)
})


def _host_allowed(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    host = host.lower().lstrip("www.")
    for allowed in ALLOWED_DOMAINS:
        if host == allowed or host.endswith("." + allowed):
            return True
    return False


@dataclass
class BrowseResult:
    url: str
    status: int
    title: str
    text: str                # extracted readable content
    screenshot_path: str = ""
    blocked: bool = False
    error: str = ""


@dataclass
class BrowserTool:
    headless: bool = True
    timeout_ms: int = 20000
    max_text_chars: int = 8000

    def browse(self, url: str, screenshot: bool = False) -> BrowseResult:
        if not _host_allowed(url):
            return BrowseResult(url=url, status=0, title="", text="",
                                blocked=True, error="domain not in allowlist")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return BrowseResult(url=url, status=0, title="", text="",
                                error="playwright not installed — `pip install playwright && playwright install chromium`")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            try:
                page = browser.new_page()
                page.set_default_timeout(self.timeout_ms)
                resp = page.goto(url, wait_until="domcontentloaded")
                status = resp.status if resp else 0
                title = page.title()
                text = page.inner_text("body")[:self.max_text_chars]
                shot_path = ""
                if screenshot:
                    import time
                    shot_path = f"/tmp/bagley_browse_{int(time.time())}.png"
                    page.screenshot(path=shot_path, full_page=False)
                return BrowseResult(url=url, status=status, title=title, text=text,
                                    screenshot_path=shot_path)
            finally:
                browser.close()

    def research(self, query: str, max_pages: int = 3) -> list[BrowseResult]:
        """Research mode — busca + navega nos top results.

        Usa DuckDuckGo HTML search (sem tracking, sem captcha agressiva).
        Segue apenas links dentro do allowlist.
        """
        from urllib.parse import quote_plus
        search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
        sr = self.browse(search_url)
        if sr.blocked or sr.error:
            return [sr]

        # Extrai URLs do resultado
        candidate_urls = re.findall(r'https?://[^\s<>"]+', sr.text)
        # Filtra: apenas allowlist, dedupe, top N
        seen: set[str] = set()
        filtered: list[str] = []
        for u in candidate_urls:
            if u in seen:
                continue
            seen.add(u)
            if _host_allowed(u):
                filtered.append(u)
            if len(filtered) >= max_pages:
                break

        results = [sr]
        for u in filtered:
            results.append(self.browse(u))
        return results
