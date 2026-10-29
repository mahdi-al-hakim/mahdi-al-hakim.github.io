"""Test the built site in a real browser before it is published.

    python -m http.server 8731 --directory .    # in another shell
    python test_site.py

Checks the things that actually break a text site for a reviewer: dead links,
horizontal overflow on a phone, unreadable contrast, missing titles, and
content that silently failed to convert. A build that "looks fine" in a file
listing is not evidence, which is the whole point of the project this site
is advertising.
"""

from __future__ import annotations

import re
import sys
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8731"

PAGES = [
    "/",
    "/writeups/github-mcp-lockdown/",
    "/writeups/netcdf-c/",
    "/writeups/keycloak-caep/",
]

VIEWPORTS = [
    ("phone", 360, 740),
    ("tablet", 768, 1024),
    ("laptop", 1440, 900),
]

failures: list[str] = []
notes: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ---------- per page, per viewport ----------
        for path in PAGES:
            for label, w, h in VIEWPORTS:
                page = browser.new_page(viewport={"width": w, "height": h})
                errors: list[str] = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on(
                    "console",
                    lambda m: errors.append(m.text) if m.type == "error" else None,
                )
                resp = page.goto(BASE + path, wait_until="load")

                check(resp is not None and resp.status == 200,
                      f"{path} [{label}] HTTP {resp.status if resp else 'none'}")

                # no horizontal overflow: the single most common mobile break
                overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
                )
                check(overflow <= 1,
                      f"{path} [{label}] page scrolls sideways by {overflow}px")

                # the stylesheet actually applied
                bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
                check(bg not in ("rgba(0, 0, 0, 0)", "rgb(255, 255, 255)"),
                      f"{path} [{label}] stylesheet did not apply (body bg {bg})")

                check(not errors, f"{path} [{label}] console/page errors: {errors[:3]}")
                page.close()

            # ---------- content checks, once per page ----------
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(BASE + path, wait_until="load")

            title = page.title()
            check(bool(title) and "Mahdi Alhakim" in title,
                  f"{path} title missing or wrong: {title!r}")

            h1s = page.locator("h1").count()
            check(h1s == 1, f"{path} has {h1s} h1 elements, expected exactly 1")

            text = page.inner_text("body")

            # Unconverted markdown left in the rendered prose. This must skip
            # code blocks: a shell comment is "# something" and a markdown
            # heading is "# something", and inner_text cannot tell them apart.
            # The first version of this check flagged three bash comments as
            # broken conversion, which would have had me "fix" correct output.
            prose = page.evaluate(
                """() => {
                    const clone = document.body.cloneNode(true);
                    clone.querySelectorAll('pre, code').forEach(e => e.remove());
                    return clone.innerText;
                }"""
            )
            for pat, what in (
                (r"^#{1,6}[ 	]+\S", "raw markdown heading"),  # needs text after: a lone "#" is a table header
                (r"\]\(http", "raw markdown link"),
                (r"\|\s*-{3,}\s*\|", "raw markdown table rule"),
                (r"\*\*\w", "raw markdown bold"),
            ):
                m = re.search(pat, prose, flags=re.M)
                check(m is None, f"{path} contains {what}: {(m.group(0)[:40] if m else '')!r}")

            # AI-typography must not have crept in through conversion
            for ch, name in ((0x2014, "em dash"), (0x2013, "en dash")):
                if chr(ch) in text:
                    n = text.count(chr(ch))
                    if ch == 0x2014:
                        failures.append(f"{path} rendered text contains {n} em dash(es)")
                    else:
                        notes.append(f"{path}: {n} en dash(es) (ranges, expected)")

            # tables must be inside a scroll container
            tables = page.locator("table").count()
            wrapped = page.locator("div.scroll > table").count()
            check(tables == wrapped,
                  f"{path} has {tables} tables but {wrapped} wrapped for scrolling")
            if tables:
                notes.append(f"{path}: {tables} tables, all scroll-wrapped")

            # internal links must resolve
            hrefs = page.eval_on_selector_all(
                "a[href]", "els => els.map(e => e.getAttribute('href'))"
            )
            for href in hrefs:
                if href.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target = href if href.startswith("/") else path.rstrip("/") + "/" + href
                r = page.request.get(BASE + target)
                check(r.status == 200, f"{path} internal link {href} -> HTTP {r.status}")

            page.close()

        browser.close()

    for n in notes:
        print(f"  note: {n}")
    if failures:
        print(f"\nFAILED: {len(failures)} problem(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\nPASS: {len(PAGES)} pages x {len(VIEWPORTS)} viewports, no problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
