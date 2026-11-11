"""Test the built site in a real browser before it is published.

    python -m http.server 8731 --directory .    # in another shell
    python test_site.py

Every page is loaded at three widths. A page fails on a broken internal link, sideways scrolling on a
phone, a stylesheet that did not apply, a console error, a missing title, more or fewer than one h1,
markdown that did not convert, or a table outside a scroll container.
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
    "/404.html",
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

                # no horizontal overflow
                overflow = page.evaluate(
                    "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
                )
                check(overflow <= 1,
                      f"{path} [{label}] page scrolls sideways by {overflow}px")

                # the stylesheet applied
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

            # Unconverted markdown left in the rendered prose. Code blocks are
            # skipped: a shell comment and a markdown heading both start "# ".
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
