"""Build the site from markdown sources.

    python build.py --src DIR --resume PATH

The list of writeups is explicit, so nothing else in the source folder is published. Each writeup is
written to writeups/<slug>/index.html, so its URL does not depend on Jekyll turning .md into .html.
"""

from __future__ import annotations

import argparse
import html
import os
import pathlib
import re
import shutil
import sys

import markdown

HERE = pathlib.Path(__file__).resolve().parent
SITE_URL = "https://mahdi-al-hakim.github.io"
NAME = "Mahdi Alhakim"

#: slug -> (markdown file, short description used for the page's description and preview)
WRITEUPS = {
    "github-mcp-lockdown": (
        "writeup-github-mcp-lockdown.md",
        "An incomplete content filter in github-mcp-server lockdown mode",
    ),
    "netcdf-c": (
        "writeup-netcdf-c.md",
        "An integer overflow in netcdf-c's classic-format length arithmetic",
    ),
    "keycloak-caep": (
        "writeup-keycloak-caep.md",
        "Three reports to one vendor inside two weeks",
    ),
}

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='6' fill='%231a1a1a'/%3E%3Ctext x='16' y='22.5' "
    "font-family='Georgia,serif' font-size='18' fill='%23fdfcfa' text-anchor='middle'%3EM%3C/text%3E"
    "%3C/svg%3E"
)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{name}">
<link rel="canonical" href="{url}">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="{css}">
</head>
<body>
<div class="wrap">
{body}
<div class="foot">
{foot}
</div>
</div>
</body>
</html>
"""


def convert(md_text: str) -> str:
    """Markdown to HTML, with tables, fenced code, and an id on every heading."""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list", "toc"],
        output_format="html5",
    )


def wrap_tables(body: str) -> str:
    """Put every table in a horizontally scrollable box, so a wide one never widens the page."""
    return re.sub(
        r"(<table>.*?</table>)",
        r'<div class="scroll">\1</div>',
        body,
        flags=re.DOTALL,
    )


def strip_leading_h1(body: str) -> tuple[str, str]:
    """Return (title_text, body_without_that_h1). The title comes back as plain text."""
    m = re.match(r"\s*<h1[^>]*>(.*?)</h1>", body, flags=re.DOTALL)
    if not m:
        return "", body
    title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    return title, body[m.end() :]


def page(*, title: str, og_title: str, desc: str, url: str, og_type: str, css: str, body: str,
         foot: str) -> str:
    return PAGE.format(
        title=html.escape(title),
        og_title=html.escape(og_title),
        desc=html.escape(desc),
        name=html.escape(NAME),
        url=url,
        favicon=FAVICON,
        og_type=og_type,
        css=css,
        body=body,
        foot=foot,
    )


def build_writeup(src_dir: pathlib.Path, slug: str, src: str, short: str) -> pathlib.Path:
    body = wrap_tables(convert((src_dir / src).read_text(encoding="utf-8")))
    title, body = strip_leading_h1(body)
    title = title or short
    head = (
        f'<div class="masthead">\n'
        f"<h1>{html.escape(title)}</h1>\n"
        f'<p class="meta"><a href="/">{html.escape(NAME)}</a></p>\n'
        f"</div>\n"
    )
    foot = (
        '<a href="/">Back to the index</a> &middot; '
        '<a href="https://github.com/mahdi-al-hakim">GitHub</a> &middot; '
        '<a href="mailto:mahdi.a.alhakim@gmail.com">mahdi.a.alhakim@gmail.com</a>'
    )
    out = HERE / "writeups" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        page(title=f"{title} | {NAME}", og_title=title, desc=short,
             url=f"{SITE_URL}/writeups/{slug}/", og_type="article", css="/style.css",
             body=head + body, foot=foot),
        encoding="utf-8", newline="\n",
    )
    return out


def build_index(src_dir: pathlib.Path) -> pathlib.Path:
    body = wrap_tables(convert((src_dir / "index.md").read_text(encoding="utf-8")))
    title, body = strip_leading_h1(body)
    foot = (
        '<a href="https://github.com/mahdi-al-hakim">GitHub</a> &middot; '
        '<a href="https://www.linkedin.com/in/mahdi-alhakim-ab75731b9">LinkedIn</a> &middot; '
        '<a href="/resume.pdf">Resume</a> &middot; '
        '<a href="mailto:mahdi.a.alhakim@gmail.com">mahdi.a.alhakim@gmail.com</a>'
    )
    desc = "Security research on AI agents, authentication systems and file parsers."
    out = HERE / "index.html"
    out.write_text(
        page(title=NAME, og_title=NAME, desc=desc, url=f"{SITE_URL}/", og_type="website",
             css="style.css",
             body=f'<div class="masthead"><h1>{html.escape(title or NAME)}</h1></div>\n' + body,
             foot=foot),
        encoding="utf-8", newline="\n",
    )
    return out


def build_404() -> pathlib.Path:
    out = HERE / "404.html"
    body = (
        '<div class="masthead"><h1>Not found</h1></div>\n'
        '<p>There is nothing at this address. <a href="/">Go to the index</a>.</p>\n'
    )
    out.write_text(
        page(title=f"Not found | {NAME}", og_title="Not found", desc="Page not found.",
             url=f"{SITE_URL}/404.html", og_type="website", css="/style.css", body=body,
             foot='<a href="/">Back to the index</a>'),
        encoding="utf-8", newline="\n",
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", default=os.getenv("SITE_SRC"), help="folder of markdown sources")
    parser.add_argument("--resume", default=os.getenv("SITE_RESUME"), help="resume PDF to publish")
    args = parser.parse_args()
    if not args.src or not args.resume:
        parser.error("--src and --resume are required (or set SITE_SRC and SITE_RESUME)")
    src_dir = pathlib.Path(args.src)

    built = [build_index(src_dir), build_404()]
    for slug, (src, short) in WRITEUPS.items():
        built.append(build_writeup(src_dir, slug, src, short))

    # Finished HTML ships as-is; without .nojekyll GitHub Pages would run Jekyll over it.
    (HERE / ".nojekyll").write_text("", encoding="utf-8")

    resume = pathlib.Path(args.resume)
    if not resume.exists():
        print(f"error: {resume} not found", file=sys.stderr)
        return 1
    shutil.copy2(resume, HERE / "resume.pdf")
    built.append(HERE / "resume.pdf")

    for p in built:
        print(f"  {p.stat().st_size:>8,} B  {p.relative_to(HERE).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
