# mahdi-al-hakim.github.io

Source for [mahdi-al-hakim.github.io](https://mahdi-al-hakim.github.io): plain HTML and one stylesheet,
built from markdown and served as is. `.nojekyll` turns off GitHub's Jekyll step.

## Layout

```
index.html                      the landing page
style.css                       the stylesheet
writeups/<slug>/index.html      one writeup per directory
404.html
resume.pdf
```

Writeups live at directory URLs such as `/writeups/netcdf-c/`, so links don't depend on Jekyll
rewriting `.md` to `.html`.

## Build and test

`build.py` turns the markdown sources into these files:

```bash
python build.py --src <markdown folder> --resume <resume.pdf>
```

The markdown sources aren't in this repository, so a clone can serve and test the site but can't
rebuild it.

`test_site.py` loads every page in headless Chromium at three widths and fails on a broken internal link,
sideways scrolling on a phone, a stylesheet that didn't apply, a console error, a missing title, more or
fewer than one `h1`, markdown that didn't convert, or a table outside a scroll container:

```bash
python -m http.server 8731 --directory .
python test_site.py
```
