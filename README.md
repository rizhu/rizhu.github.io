# richardhu.org

My personal site: a resume and a photography portfolio, plus occasional writing.

**You edit YAML in `content/`. You never edit HTML.**

```bash
vim content/photos.yaml     # or resume.yaml, site.yaml, posts.yaml
./build.py                  # regenerate the pages
./serve.sh                  # look at it: http://localhost:4000
./check.py                  # sanity check before pushing
git commit -am "new photo"  # commit the YAML and the generated HTML together
git push                    # live in a minute or so
```

There is nothing to install. `build.py` and `check.py` need only Python 3, and
`serve.sh` uses Python's built-in web server.

## Why it is built this way

The previous version of this site was a Jekyll site built on a third-party
remote theme, and it broke completely the day that theme stopped resolving.

So: **no package manager, no framework, no static site generator, no CDN.** The
`.html` files that GitHub Pages serves are committed to this repository, which
means the live site does not depend on `build.py` working, or on Python
existing, or on any network fetch at page load. `build.py` is a convenience for
whoever is editing; it is not a runtime dependency. If it ever broke, the site
would keep serving exactly as it is.

The two libraries this repo does use are committed into it rather than installed:

| Library | Location              | Needed for                                   |
| ------- | --------------------- | -------------------------------------------- |
| KaTeX   | `assets/vendor/katex` | rendering math in blog posts, in the browser  |
| PyYAML  | `tools/vendor/yaml`   | letting `build.py` read the YAML in `content/` |

## Common jobs

### Add a photograph

1. Drop the image into `assets/gallery/`.
2. Add four lines to `content/photos.yaml`, in the position you want it on the
   page:

```yaml
  - file: new_photo.jpg
    title: Some Lake
    place: Sierra Nevada, CA
    alt: A description for screen readers
```

3. `./build.py`

You do not need to look up the image's dimensions — `build.py` reads them out of
the file. Photographs are shown three per row, cropped to a 4:3 window; hovering
one darkens it and reveals the title.

### Update the resume

Edit `content/resume.yaml`. One job is one block:

```yaml
      - org: Some Company
        url: https://example.com/
        role: Job Title
        dates: March 2026 – Present
        location: Chicago, IL
        body:
          - >-
            What the work was. **Bold** and [links](https://example.com) work.
        stack: [Python, Kubernetes]
```

Then `./build.py`. Sections appear in the order they are listed.

### Change the headshot

Replace `assets/logo.jpg`, or point `logo:` in `content/site.yaml` at a
different file. Then `./build.py`.

### Add a tab to the top nav

In `content/site.yaml`, add to `tabs`:

```yaml
tabs:
  - label: Resume
    url: /
  - label: Photography
    url: /photography/
  - label: Blog
    url: /blog/
  - label: Notes          # new
    url: /notes/
```

Then create the page it points at and add it to `pages` in the same file. Run
`./build.py`; the nav updates on **every** page at once, including old blog
posts. There is no per-page nav to keep in sync.

### Add a blog post

1. Write the body as HTML in `content/posts/<slug>.html` — just the article, no
   `<head>` and no navigation. Copy an existing file for the house style.
2. Add an entry to `content/posts.yaml` with the slug, title, date, summary, and
   tags. Set `math: true` if it contains LaTeX.
3. `./build.py` creates `/blog/<slug>/` and lists it on the blog index.

Post bodies are the one place you write HTML, because prose with code samples,
diagrams, and equations does not fit neatly into YAML.

### Move or rename a page

Add the old address to `redirects` in `content/site.yaml` so existing links keep
working:

```yaml
redirects:
  - from: /old-address/
    to: /new-address/
```

## Setup

After cloning, run:

```bash
./bootstrap.sh
```

This installs the pre-commit hook (which runs `check.py` before every commit, so
you cannot accidentally commit stale HTML) and any other one-time setup.

## Deploy

Push to `master`. GitHub Pages serves the repository root as-is.

Repository settings must stay as **Settings → Pages → Source: Deploy from a
branch → `master` / `(root)`**.

Two files make that work, and neither should be deleted:

| File        | Why it matters                                                        |
| ----------- | --------------------------------------------------------------------- |
| `.nojekyll` | Tells GitHub Pages to skip Jekyll and serve these files byte-for-byte. |
| `CNAME`     | Points the custom domain `richardhu.org` at this site.                 |

## What `check.py` checks

Run it before pushing. It fails if:

- the generated HTML is out of date with `content/` (you forgot `./build.py`),
- any internal link or image points at a file that does not exist,
- a filename's capitalisation does not match the file on disk — this works on
  your Mac and 404s on GitHub Pages, so it is worth catching before you push,
- a page loads a stylesheet or script from another domain,
- a page is missing the shared stylesheet or a nav tab,
- `.nojekyll` has gone missing.

`build.py` explains mistakes in plain language rather than printing a Python
traceback. For example, misspelling a photo's filename tells you which entry is
wrong and suggests the file you probably meant.

## Layout of the repository

```
content/                 EVERYTHING YOU EDIT
  site.yaml              name, domain, nav tabs, headshot, redirects
  resume.yaml            the landing page
  photos.yaml            the photography page
  posts.yaml             blog post list
  posts/*.html           blog post bodies

build.py                 content/ -> HTML. Run after every edit.
check.py                 pre-push sanity check
serve.sh                 local preview
bootstrap.sh             one-time setup after cloning

index.html               generated
photography/index.html   generated
blog/                    generated
404.html, sitemap.xml    generated
gallery.html, blog.html  generated redirect stubs

assets/css/site.css      the entire design system, hand-maintained
assets/js/lightbox.js    click-to-enlarge for the gallery
assets/js/math.js        LaTeX rendering
assets/vendor/katex/     committed copy of KaTeX 0.18.4
assets/gallery/          photographs
assets/logo.jpg          headshot
tools/hooks/pre-commit   version-controlled pre-commit hook
tools/vendor/yaml/       committed copy of PyYAML 6.0.3

CNAME, .nojekyll         GitHub Pages configuration
robots.txt               hand-maintained
```

Generated files carry a comment at the top saying so. If you edit one by hand,
the next `./build.py` will overwrite it.

## Design

Four colours, and only four, defined at the top of `assets/css/site.css`:

| Colour | Light     | Dark      | Used for                                          |
| ------ | --------- | --------- | ------------------------------------------------- |
| Paper  | `#ffffff` | `#161616` | All backgrounds                                   |
| Ink    | `#000000` | `#e8e8e8` | All text, and — at reduced alpha — every grey      |
| Polemonium    | `#7a7eb9` | `#9da1d4` | Sparingly: wordmark accent, selection, callouts    |
| Range of Light | `#ff9f6a` | `#ff9f6a` | Sparingly: active tab, link hover, accents         |

A dark-mode toggle sits in the header bar. The saved preference lives in
`localStorage`; if nothing is saved the system preference wins. Greys are
always the ink colour at reduced alpha via the `--ink-*` variables, never a
new hue. Type is the system sans-serif stack, so there are no web fonts to
load and no font host to depend on.

Styling is the one part of this site that is not driven by YAML. If you want to
change how something looks, it is in `assets/css/site.css`.

## A note on image sizes

The originals are large: the headshot is about 3 MB and the gallery is around
20 MB. Everything is served at full resolution on purpose, so the photographs
stay sharp. If pages ever feel slow, generate smaller copies with the `sips`
tool that ships with macOS and point `content/photos.yaml` at those instead:

```bash
sips -Z 2400 assets/gallery/sierra.jpg --out assets/gallery/web/sierra.jpg
```

## For agents

See [AGENTS.md](AGENTS.md).
