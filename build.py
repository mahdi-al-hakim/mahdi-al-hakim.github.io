"""Build the site from the published prose. Run from the SITE/ directory.

    python build.py

The source of truth is PUBLISH/prose/. Nothing here edits prose; it only
converts it. The file list is explicit rather than a directory glob, because
PUBLISH/prose/ also holds internal working files (CLAIM-LEDGER.md and
resume-deltas.md) that must never be published. A glob would ship them.

Every writeup lands at the path the resume and profile already link:
/writeups/<slug>/ served by writeups/<slug>/index.html. That form does not
depend on Jekyll, which would otherwise rewrite .md to .html and break every
link the moment the site went live.
"""

from __future__ import annotations

import html
import pathlib
import re
import shutil
import sys

import markdown

HERE = pathlib.Path(__file__).resolve().parent
PROSE = HERE.parent / "PUBLISH" / "prose"
RESUME = HERE.parent / "mahdi_apply" / "resume_security.pdf"

#: slug -> (source file, browser title, one-line description for the tab)
WRITEUPS = {
    "github-mcp-lockdown": (
        "writeup-github-mcp-lockdown.md",
        "An incomplete content filter in github-mcp-server lockdown mode",
    ),
    "netcdf-c": (
        "writeup-netcdf-c.md",
        "A one-byte differential in netcdf-c",
    ),
    "keycloak-caep": (
        "writeup-keycloak-caep.md",
        "Three reports to one vendor inside two weeks",
    ),
}

NAME = "Mahdi Alhakim"

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{name}">
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
    """Markdown to HTML, with tables and fenced code."""
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )


def wrap_tables(body: str) -> str:
    """Put every table in a horizontally scrollable box.

    These writeups carry 36 tables, several of them wide. Without this a
    phone gets a page that scrolls sideways as a whole, which is the single
    most common way a text site breaks on mobile.
    """
    return re.sub(
        r"(<table>.*?</table>)",
        r'<div class="scroll">\1</div>',
        body,
        flags=re.DOTALL,
    )


def strip_leading_h1(body: str) -> tuple[str, str]:
    """Return (title_text, body_without_that_h1)."""
    m = re.match(r"\s*<h1>(.*?)</h1>", body, flags=re.DOTALL)
    if not m:
        return "", body
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return title, body[m.end() :]


def build_writeup(slug: str, src: str, short: str) -> pathlib.Path:
    md_text = (PROSE / src).read_text(encoding="utf-8")
    body = wrap_tables(convert(md_text))
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
    page = PAGE.format(
        title=html.escape(f"{title} | {NAME}"),
        desc=html.escape(short),
        name=html.escape(NAME),
        css="/style.css",
        body=head + body,
        foot=foot,
    )
    out = HERE / "writeups" / slug / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return out


def build_index() -> pathlib.Path:
    md_text = (PROSE / "index.md").read_text(encoding="utf-8")
    # The index's relative links already point at writeups/<slug>/.
    body = wrap_tables(convert(md_text))
    title, body = strip_leading_h1(body)

    foot = (
        '<a href="https://github.com/mahdi-al-hakim">GitHub</a> &middot; '
        '<a href="https://www.linkedin.com/in/mahdi-alhakim-ab75731b9">LinkedIn</a> &middot; '
        '<a href="/resume.pdf">Resume</a> &middot; '
        '<a href="mailto:mahdi.a.alhakim@gmail.com">mahdi.a.alhakim@gmail.com</a>'
    )
    page = PAGE.format(
        title=html.escape(f"{NAME}"),
        desc="Security research on AI agents, authentication systems and file parsers.",
        name=html.escape(NAME),
        css="style.css",
        body=f'<div class="masthead"><h1>{html.escape(title or NAME)}</h1></div>\n' + body,
        foot=foot,
    )
    out = HERE / "index.html"
    out.write_text(page, encoding="utf-8")
    return out


def main() -> int:
    built = [build_index()]
    for slug, (src, short) in WRITEUPS.items():
        built.append(build_writeup(slug, src, short))

    # .nojekyll: we ship finished HTML. Without it GitHub Pages runs Jekyll,
    # which has its own opinions about files starting with an underscore and
    # adds a build step that can only break things.
    (HERE / ".nojekyll").write_text("", encoding="utf-8")

    if RESUME.exists():
        shutil.copy2(RESUME, HERE / "resume.pdf")
        built.append(HERE / "resume.pdf")
    else:
        print(f"WARNING: {RESUME} not found; /resume.pdf will 404", file=sys.stderr)

    for p in built:
        print(f"  {p.stat().st_size:>8,} B  {p.relative_to(HERE).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
