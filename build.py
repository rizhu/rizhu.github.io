#!/usr/bin/env python3
"""Generate the website's HTML from the YAML files in content/.

    ./build.py            regenerate the site
    ./build.py --check    fail if the HTML on disk is out of date (no writes)

Everything you normally edit lives in content/. This script turns it into the
.html files that GitHub Pages serves. Those .html files are committed, so the
live site never depends on this script working — if Python vanished tomorrow the
website would keep serving exactly as it is now.

Only the Python standard library is used, plus the copy of PyYAML committed at
tools/vendor/. There is nothing to install.
"""

import os
import re
import struct
import sys
import textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")

sys.path.insert(0, os.path.join(ROOT, "tools", "vendor"))
import yaml  # noqa: E402  (vendored, see tools/vendor/yaml/VERSION)


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

def fail(message):
    """Stop with an explanation instead of a Python traceback."""
    raise SystemExit("\nbuild.py stopped:\n\n  " + message.replace("\n", "\n  ") + "\n")


def need(mapping, key, where):
    if not isinstance(mapping, dict) or mapping.get(key) in (None, ""):
        fail("%s is missing the required '%s:' field.\n"
             "Got: %r" % (where, key, mapping))
    return mapping[key]


def esc(text):
    """Escape text for HTML. Content files hold plain text, never markup."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def inline(text):
    """Render the small amount of formatting allowed in content files.

    **bold**, *italic*, `code`, and [link text](https://example.com).
    """
    text = esc(text)

    # Park code spans so their contents are not treated as other markup.
    spans = []

    def park(match):
        spans.append(match.group(1))
        return "\x00%d\x00" % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", park, text)

    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)

    for i, span in enumerate(spans):
        text = text.replace("\x00%d\x00" % i, "<code>%s</code>" % span)

    return " ".join(text.split())


def wrap(text, indent):
    """Soft-wrap generated prose so the committed HTML stays readable.

    Tags are treated as single unbreakable words, so a line never breaks in the
    middle of <a href="..."> and the generated markup stays easy to read.
    """
    pad = " " * indent
    protected = re.sub(r"<[^>]*>", lambda m: m.group(0).replace(" ", "\x01"), text)
    lines = textwrap.wrap(
        protected, width=78 - indent, break_long_words=False, break_on_hyphens=False
    )
    lines = [line.replace("\x01", " ") for line in lines]
    return "\n".join(pad + line for line in lines) or pad + text


def paragraph(text, indent=2):
    body = inline(text)
    if len(body) + indent < 76 and "\n" not in body:
        return "%s<p>%s</p>" % (" " * indent, body)
    return "%s<p>\n%s\n%s</p>" % (" " * indent, wrap(body, indent + 2), " " * indent)


def paragraphs(value, indent=2):
    """Accept either a single string or a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    return [paragraph(item, indent) for item in value]


def format_date(value):
    if not hasattr(value, "strftime"):
        fail("'date: %s' is not a date. Write it as YYYY-MM-DD, "
             "for example 2026-08-11." % value)
    return "%s %d, %d" % (value.strftime("%B"), value.day, value.year)


# --------------------------------------------------------------------------- #
# Image dimensions, read straight out of the file
# --------------------------------------------------------------------------- #

_JPEG_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
             0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def image_size(path):
    """Return (width, height) for a PNG or JPEG, so pages can reserve space."""
    with open(path, "rb") as handle:
        head = handle.read(26)

        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])

        if head[:2] == b"\xff\xd8":
            handle.seek(2)
            while True:
                byte = handle.read(1)
                if not byte:
                    break
                if byte != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if not marker:
                    break
                code = marker[0]
                if code == 0x01 or 0xD0 <= code <= 0xD9:
                    continue
                length_bytes = handle.read(2)
                if len(length_bytes) < 2:
                    break
                length = struct.unpack(">H", length_bytes)[0]
                if code in _JPEG_SOF:
                    frame = handle.read(5)
                    height, width = struct.unpack(">HH", frame[1:5])
                    return width, height
                handle.seek(length - 2, 1)

    raise SystemExit(
        "build.py cannot read the dimensions of %s.\n"
        "Only PNG and JPEG are supported; convert the file or add width and "
        "height by hand." % os.path.relpath(path, ROOT)
    )


# --------------------------------------------------------------------------- #
# Page shell
# --------------------------------------------------------------------------- #

def nav(current_url):
    out = []
    for tab in SITE["tabs"]:
        current = ' aria-current="page"' if tab["url"] == current_url else ""
        out.append('      <a href="%s"%s>%s</a>'
                   % (tab["url"], current, esc(tab["label"])))
    return "\n".join(out)


def page(*, title, description, url, body, current_url=None,
         og_type="website", image=None, head="", scripts="", wrap_class="wrap",
         footer_left=None, top_anchor="#main", robots=None, extra=""):
    """Assemble a complete page. Every page on the site goes through here."""
    image = image or SITE["logo"]
    absolute_image = SITE["domain"] + image
    card = "summary" if image == SITE["logo"] else "summary_large_image"
    footer_left = footer_left or "<span>%s</span>" % esc(SITE["footer"])

    meta_robots = '\n<meta name="robots" content="%s">' % robots if robots else ""

    name_parts = SITE["name"].rsplit(" ", 1)
    if len(name_parts) == 2:
        wordmark = '%s <span class="wordmark__accent">%s</span>' % (
            esc(name_parts[0]), esc(name_parts[1]))
    else:
        wordmark = esc(SITE["name"])

    return """<!DOCTYPE html>
<html lang="en">
<head>
<!-- Generated by build.py from content/. Edit the content files, not this. -->
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="author" content="{author}">{robots}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{image}">
<meta name="twitter:card" content="{card}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{logo}">
<link rel="stylesheet" href="/assets/css/site.css">
<script>/* Apply saved theme before first paint */
(function(){{var t=localStorage.getItem("theme");if(t)document.documentElement.setAttribute("data-theme",t);else if(matchMedia("(prefers-color-scheme:dark)").matches)document.documentElement.setAttribute("data-theme","dark")}})();
</script>{head}
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>

<header class="site-header">
  <div class="site-header__inner">
    <a class="wordmark" href="/">{wordmark}</a>
    <nav class="nav" aria-label="Primary">
{nav}
    </nav>
    <button class="theme-toggle" type="button" id="theme-toggle" aria-label="Toggle dark mode">
      <svg class="icon-sun" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      <svg class="icon-moon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
    </button>
  </div>
</header>

<main class="{wrap_class}" id="main">
{body}
</main>

<footer class="site-footer">
  <div class="site-footer__inner">
    {footer_left}
    <a class="backtotop" href="{top_anchor}">Back to top &uarr;</a>
  </div>
</footer>
{extra}<script src="/assets/js/theme.js" defer></script>
{scripts}
</body>
</html>
""".format(
        title=esc(title),
        description=esc(" ".join(str(description).split())),
        author=esc(SITE["name"]),
        wordmark=wordmark,
        robots=meta_robots,
        canonical=SITE["domain"] + url,
        og_type=og_type,
        image=absolute_image,
        card=card,
        logo=SITE["logo"],
        head=head,
        nav=nav(current_url if current_url is not None else url),
        wrap_class=wrap_class,
        body=body,
        footer_left=footer_left,
        top_anchor=top_anchor,
        extra=extra,
        scripts=scripts,
    )


# --------------------------------------------------------------------------- #
# Resume page
# --------------------------------------------------------------------------- #

def render_entry(entry):
    out = ['    <div class="entry">']

    org = esc(entry["org"])
    if entry.get("url"):
        org = '<a href="%s">%s</a>' % (esc(entry["url"]), org)

    out.append('      <div class="entry__head">')
    out.append('        <div class="entry__org">%s</div>' % org)
    out.append("      </div>")

    for role in entry.get("roles", []):
        parts = [part for part in (role.get("title"), role.get("dates")) if part]
        subtitle = " &middot; ".join(inline(part) for part in parts)
        if role.get("location"):
            out.append('      <div class="entry__head">')
            out.append('        <div class="entry__title">%s</div>' % subtitle)
            out.append('        <div class="entry__meta">%s</div>'
                       % esc(role["location"]))
            out.append("      </div>")
        else:
            out.append('      <div class="entry__title">%s</div>' % subtitle)

    out.extend(paragraphs(entry.get("body"), indent=6))

    if entry.get("bullets"):
        out.append(render_bullets(entry["bullets"], indent=6))

    if entry.get("stack"):
        items = (" <span>&bull;</span> ").join(esc(x) for x in entry["stack"])
        out.append('      <p class="stack">\n%s\n      </p>' % wrap(items, 8))

    out.append("    </div>")
    return "\n".join(out)


def render_bullets(bullets, indent, css_class="list"):
    pad = " " * indent
    out = ['%s<ul class="%s">' % (pad, css_class) if css_class
           else "%s<ul>" % pad]
    for bullet in bullets:
        if isinstance(bullet, str):
            bullet = {"text": bullet}
        out.append("%s  <li>" % pad)
        out.append(wrap(inline(bullet["text"]), indent + 4))
        if bullet.get("bullets"):
            out.append(render_bullets(bullet["bullets"], indent + 4, css_class=""))
        out.append("%s  </li>" % pad)
    out.append("%s</ul>" % pad)
    return "\n".join(out)


def render_trips(trips, indent=4):
    pad = " " * indent
    out = ['%s<ul class="trips">' % pad]
    for trip in trips:
        party = trip.get("party")
        if party:
            prefix = "" if "solo" in party.lower() else "with "
            party_html = (' <span class="trips__party"><strong>%s%s</strong></span>'
                          % (prefix, esc(party)))
        else:
            party_html = ""
        out.append("%s  <li>" % pad)
        out.append(wrap(inline(trip["what"]) + party_html, indent + 4))
        out.append('%s    <span class="trips__where">%s</span>'
                   % (pad, inline(trip["where"])))
        out.append("%s  </li>" % pad)
    out.append("%s</ul>" % pad)
    return "\n".join(out)


def build_resume(data, url):
    body = ['  <div class="hero">']
    body.append('    <img class="hero__portrait" src="%s" width="132" height="132"'
                % SITE["logo"])
    body.append('         alt="" fetchpriority="high">')
    body.append('    <div class="hero__body">')
    heading_parts = data["heading"].rsplit(" ", 1)
    if len(heading_parts) == 2:
        heading_html = '%s <span class="wordmark__accent">%s</span>' % (
            esc(heading_parts[0]), esc(heading_parts[1]))
    else:
        heading_html = esc(data["heading"])
    body.append("      <h1>%s</h1>" % heading_html)
    body.append('      <p class="hero__role">')
    body.append(wrap(inline(data["intro"]), 8))
    body.append("      </p>")

    if data.get("links"):
        body.append('      <ul class="linkrow">')
        for link in data["links"]:
            body.append('        <li><a href="%s">%s</a></li>'
                        % (esc(link["url"]), esc(link["label"])))
        body.append("      </ul>")

    body.append("    </div>")
    body.append("  </div>")

    for section in data.get("sections", []):
        body.append("")
        body.append('  <section class="section">')
        body.append("    <h2>%s</h2>" % esc(section["heading"]))
        body.extend(paragraphs(section.get("intro"), indent=4))
        for entry in section.get("entries", []):
            body.append(render_entry(entry))
        if section.get("trips"):
            body.append(render_trips(section["trips"]))
        body.append("  </section>")

    return page(
        title=data["title"],
        description=data["description"],
        url=url,
        body="\n".join(body),
    )


# --------------------------------------------------------------------------- #
# Photography page
# --------------------------------------------------------------------------- #

def build_photos(data, url):
    body = ["  <h1>%s</h1>" % esc(data["title"])]
    body.append('  <p class="page-intro">')
    body.append(wrap(inline(data["intro"]), 4))
    body.append("  </p>")
    body.append("")
    body.append("  <!-- Generated from content/photos.yaml -->")
    body.append('  <div class="grid" id="gallery">')

    first = True
    for position, photo in enumerate(data["photos"], start=1):
        where = "photo #%d in content/photos.yaml" % position
        filename = need(photo, "file", where)
        title = need(photo, "title", where)
        place = need(photo, "place", where)

        src = "/assets/gallery/" + filename
        path = os.path.join(ROOT, src.lstrip("/"))

        # Compared against the real directory listing rather than with
        # os.path.exists, because macOS ignores capitalisation and the Linux
        # servers behind GitHub Pages do not. "sierra2.jpg" would work here and
        # 404 on the live site.
        available = sorted(os.listdir(os.path.join(ROOT, "assets", "gallery")))
        if filename not in available:
            close = [name for name in available if name.lower() == filename.lower()]
            hint = ("\n\nDid you mean '%s'? Capitalisation matters on the live "
                    "site, even though it does not on your Mac." % close[0]
                    if close else
                    "\n\nFiles in assets/gallery:\n    %s" % "\n    ".join(available))
            fail("%s refers to '%s', which is not in assets/gallery.%s"
                 % (where, filename, hint))

        width, height = image_size(path)
        loading = "" if first else ' loading="lazy"'

        body.append('    <a class="tile" href="%s">' % src)
        body.append('      <img src="%s" width="%d" height="%d"' % (src, width, height))
        body.append('           alt=""%s decoding="async">' % loading)

        # The lightbox reuses this markup verbatim, which is why the note lives
        # here even though CSS hides it until the photograph is opened.
        body.append('      <span class="tile__overlay">')
        body.append('        <span class="tile__title">%s</span>' % inline(title))
        body.append('        <span class="tile__place">%s</span>' % inline(place))
        if photo.get("note"):
            note = inline(photo["note"])
            if photo.get("note_by"):
                note += "<cite>&mdash; %s</cite>" % inline(photo["note_by"])
            body.append('        <span class="tile__note">%s</span>' % note)
        body.append("      </span>")
        body.append("    </a>")
        first = False

    body.append("  </div>")

    lightbox = """
<!-- Full-screen viewer. Hidden until a photograph is clicked; without
     JavaScript the frames above are ordinary links to the image files. -->
<div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="Photograph viewer">
  <div class="lightbox__stage">
    <img class="lightbox__img" id="lightbox-img" alt="">
  </div>

  <div class="lightbox__bar">
    <p class="lightbox__caption" id="lightbox-caption"></p>
    <div class="lightbox__controls">
      <button class="iconbtn" type="button" id="lightbox-prev" aria-label="Previous photograph">&larr;</button>
      <button class="iconbtn" type="button" id="lightbox-next" aria-label="Next photograph">&rarr;</button>
    </div>
  </div>
  <button class="iconbtn lightbox__close" type="button" id="lightbox-close" aria-label="Close viewer">&times;</button>
</div>
"""

    return page(
        title="%s &mdash; %s" % (data["title"], SITE["name"]),
        description=data["description"],
        url=url,
        body="\n".join(body),
        image="/assets/gallery/" + data["photos"][0]["file"],
        wrap_class="wrap wrap--gallery",
        extra=lightbox,
        scripts='<script src="/assets/js/lightbox.js" defer></script>',
    )


# --------------------------------------------------------------------------- #
# Blog index and posts
# --------------------------------------------------------------------------- #

KATEX_HEAD = '\n<link rel="stylesheet" href="/assets/vendor/katex/katex.min.css">'

KATEX_SCRIPTS = """<!-- Math is rendered by the copy of KaTeX committed at
     /assets/vendor/katex. No CDN, so these pages render the same forever. -->
<script defer src="/assets/vendor/katex/katex.min.js"></script>
<script defer src="/assets/vendor/katex/contrib/auto-render.min.js"></script>
<script defer src="/assets/js/math.js"></script>"""


def tag_list(tags, indent=2):
    pad = " " * indent
    out = ['%s<ul class="tags">' % pad]
    out += ["%s  <li>%s</li>" % (pad, esc(tag)) for tag in tags]
    out.append("%s</ul>" % pad)
    return "\n".join(out)


def sorted_posts(data):
    for post in data["posts"]:
        format_date(need(post, "date", "a post in content/posts.yaml"))
    return sorted(data["posts"], key=lambda post: post["date"], reverse=True)


def build_posts_index(data, url):
    body = ["  <h1>%s</h1>" % esc(data["title"])]
    body.append('  <p class="page-intro">')
    body.append(wrap(inline(data["intro"]), 4))
    body.append("  </p>")
    body.append("")
    body.append("  <!-- Generated from content/posts.yaml, newest first -->")
    body.append('  <ol class="postlist">')

    for post in sorted_posts(data):
        body.append("")
        body.append("    <li>")
        body.append('      <p class="dateline">%s</p>' % format_date(post["date"]))
        body.append('      <h2><a href="/blog/%s/">%s</a></h2>'
                    % (post["slug"], esc(post["title"])))
        body.append(paragraph(post["summary"], indent=6))
        if post.get("tags"):
            body.append(tag_list(post["tags"], indent=6))
        body.append("    </li>")

    body.append("")
    body.append("  </ol>")

    return page(
        title="%s &mdash; %s" % (data["title"], SITE["name"]),
        description=data["description"],
        url=url,
        body="\n".join(body),
    )


def build_post(post, blog_url):
    where = "a post in content/posts.yaml"
    slug = need(post, "slug", where)
    for key in ("title", "date", "summary", "description"):
        need(post, key, "post '%s' in content/posts.yaml" % slug)

    fragment_path = os.path.join(CONTENT, "posts", slug + ".html")
    if not os.path.exists(fragment_path):
        fail("content/posts.yaml lists the post '%s', but its body file\n"
             "content/posts/%s.html does not exist. Create it, or remove the\n"
             "entry from content/posts.yaml." % (slug, slug))

    with open(fragment_path, encoding="utf-8") as handle:
        fragment = handle.read().strip()

    body = ['<article class="post">', ""]
    body.append("  <header>")
    body.append('    <p class="dateline">%s</p>' % format_date(post["date"]))
    body.append('    <h1 id="top">%s</h1>' % esc(post["title"]))
    body.append("  </header>")
    body.append("")
    body.extend("  " + line if line.strip() else "" for line in fragment.split("\n"))
    if post.get("tags"):
        body.append("")
        body.append(tag_list(post["tags"], indent=2))
    body.append("")
    body.append("</article>")

    return page(
        title="%s &mdash; %s" % (post["title"], SITE["name"]),
        description=post["description"],
        url="/blog/%s/" % post["slug"],
        current_url=blog_url,
        og_type="article",
        image=post.get("image"),
        body="\n".join(body),
        head=KATEX_HEAD if post.get("math") else "",
        scripts=KATEX_SCRIPTS if post.get("math") else "",
        footer_left='<a href="%s">&larr; All posts</a>' % blog_url,
        top_anchor="#top",
    )


# --------------------------------------------------------------------------- #
# Not-found page, redirects, sitemap
# --------------------------------------------------------------------------- #

def build_404():
    tabs = SITE["tabs"]
    links = ", ".join('<a href="%s">%s</a>' % (tab["url"], esc(tab["label"]).lower())
                      for tab in tabs[:-1])
    links += ', or the <a href="%s">%s</a>' % (tabs[-1]["url"],
                                               esc(tabs[-1]["label"]).lower())

    body = "\n".join([
        '  <p class="notfound__code">Error 404</p>',
        "  <h1>Off trail</h1>",
        "  <p>",
        "    There&rsquo;s nothing at this address. Try the %s." % links,
        "  </p>",
    ])

    return page(
        title="Not Found &mdash; %s" % SITE["name"],
        description="That page does not exist.",
        url="/404.html",
        current_url=None,
        body=body,
        wrap_class="wrap notfound",
        robots="noindex",
    )


def build_redirect(target):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<!-- Generated by build.py from the `redirects` list in content/site.yaml. -->
<meta charset="utf-8">
<title>Redirecting</title>
<link rel="canonical" href="{domain}{target}">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={target}">
<script>location.replace("{target}");</script>
</head>
<body>
<p>This page moved to <a href="{target}">{target}</a>.</p>
</body>
</html>
""".format(domain=SITE["domain"], target=target)


def build_sitemap(urls):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           "<!-- Generated by build.py. -->",
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, priority in urls:
        out.append("  <url>")
        out.append("    <loc>%s%s</loc>" % (SITE["domain"], url))
        out.append("    <priority>%s</priority>" % priority)
        out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def load(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


BUILDERS = {
    "resume": build_resume,
    "photos": build_photos,
    "posts": build_posts_index,
}


def generate():
    """Return {output path: file contents} for the whole site."""
    files = {}
    sitemap = []

    for spec in SITE["pages"]:
        data = load(spec["content"])
        builder = BUILDERS.get(spec["kind"])
        if builder is None:
            raise SystemExit(
                "content/site.yaml asks for unknown page kind %r. Known kinds: %s"
                % (spec["kind"], ", ".join(sorted(BUILDERS)))
            )
        files[spec["output"]] = builder(data, spec["url"])
        sitemap.append((spec["url"], "1.0" if spec["url"] == "/" else "0.8"))

        if spec["kind"] == "posts":
            for post in sorted_posts(data):
                files["blog/%s/index.html" % post["slug"]] = build_post(
                    post, spec["url"]
                )
                sitemap.append(("/blog/%s/" % post["slug"], "0.6"))

    files["404.html"] = build_404()

    for redirect in SITE.get("redirects", []):
        source = redirect["from"].lstrip("/")
        if source.endswith("/") or source == "":
            source += "index.html"
        files[source] = build_redirect(redirect["to"])

    files["sitemap.xml"] = build_sitemap(sitemap)
    return files


def main(argv):
    check_only = "--check" in argv

    files = generate()
    changed = []

    for relative, contents in sorted(files.items()):
        path = os.path.join(ROOT, relative)
        existing = None
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                existing = handle.read()
        if existing == contents:
            continue
        changed.append(relative)
        if not check_only:
            os.makedirs(os.path.dirname(path) or ROOT, exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(contents)

    if check_only:
        if changed:
            print("These pages are out of date with content/:")
            for relative in changed:
                print("  - " + relative)
            print("\nRun ./build.py and commit the result.")
            return 1
        print("%d generated pages are up to date." % len(files))
        return 0

    if changed:
        print("Updated %d of %d pages:" % (len(changed), len(files)))
        for relative in changed:
            print("  " + relative)
    else:
        print("No changes; %d pages already up to date." % len(files))

    print("\nPreview with ./serve.sh, then check with ./check.py")
    return 0


SITE = load("site.yaml")

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
