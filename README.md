# mahdi-al-hakim.github.io

Source for [mahdi-al-hakim.github.io](https://mahdi-al-hakim.github.io). Plain HTML and one stylesheet,
no framework, no build step at serve time. `.nojekyll` is present because the pages ship finished.

## Layout

```
index.html                      the landing page
style.css                       the only stylesheet
writeups/<slug>/index.html      one writeup per directory
resume.pdf
```

Writeups live at directory URLs (`/writeups/netcdf-c/`) rather than at `.md` paths. That is deliberate:
GitHub Pages runs Jekyll by default, which rewrites `.md` to `.html`, so a link to a `.md` file 404s the
moment the site goes live. Finished HTML at a directory path does not depend on any of that.

## Build and test

`build.py` converts the writeups from markdown. The prose it reads is kept in a separate working tree, so
the script will not run as-is from a fresh clone; it is here because it is the thing that produced these
files, and because it records why the output is shaped the way it is.

`test_site.py` is self-contained and does run from a clone:

```bash
python -m http.server 8731 --directory .
python test_site.py
```

It loads every page in headless Chromium at three viewport widths and checks the things that actually
break a text site: dead internal links, horizontal overflow on a phone, a stylesheet that failed to
apply, console errors, missing or duplicated `h1`, markdown that silently failed to convert, and tables
that are not inside a scroll container.

Two of its checks were wrong when first written. It flagged three bash comments inside fenced code blocks
as unconverted markdown headings, because it searched rendered text where `# comment` and `# Heading` look
identical, and it flagged a table header cell containing `#`. Both were corrected by narrowing the check,
not by changing the content it had misjudged. That failure mode is also the subject of the writeups.
