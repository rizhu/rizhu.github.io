#!/usr/bin/env python3
"""Sanity-check the site before committing.

    ./check.py

Uses only the Python 3 standard library, on purpose: this repository has no
dependencies and this script must not introduce any.

It verifies the invariants that keep the site working forever:

  1. The generated HTML matches content/, i.e. somebody ran ./build.py.
  2. Every internal link, image, stylesheet, and script resolves to a real file.
  3. No page loads a stylesheet or script from another domain (a CDN going away
     must never be able to break this site).
  4. Every page includes the shared stylesheet and the nav tabs.
  5. .nojekyll exists, so GitHub Pages serves these files verbatim.
"""

import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.abspath(__file__))

problems = []
checked_links = 0
NAV_URLS = []


def report(path, message):
    problems.append("%s: %s" % (os.path.relpath(path, ROOT), message))


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []            # (attr_value, tag)
        self.remote_resources = []  # (tag, url)
        self.nav_targets = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)

        # rel values that make a <link> actually load a file, as opposed to
        # merely declaring metadata such as rel="canonical".
        loading_rels = {"stylesheet", "icon", "apple-touch-icon", "preload", "manifest"}
        rels = set((a.get("rel") or "").lower().split())

        for attr in ("href", "src"):
            value = a.get(attr)
            if not value:
                continue
            loads_a_file = tag == "script" or (tag == "link" and rels & loading_rels)
            if loads_a_file and re.match(r"https?://", value):
                # Stylesheets, icons, and scripts must be local. Ordinary
                # <a href> links to other websites are of course fine.
                self.remote_resources.append((tag, value))
            self.refs.append((value, tag))

        if tag == "a" and a.get("href") in NAV_URLS:
            self.nav_targets.append(a["href"])


def exists_exactly(path):
    """Like os.path.exists, but capitalisation must match.

    macOS filesystems are case-insensitive; the Linux servers behind GitHub
    Pages are not. Without this, a link to /assets/gallery/photo.jpg would work
    perfectly on a Mac and 404 on the live site.
    """
    path = os.path.normpath(path)
    if not os.path.exists(path):
        return False

    current = path
    while current != ROOT and len(current) > len(ROOT):
        parent, name = os.path.split(current)
        try:
            if name not in os.listdir(parent):
                return False
        except OSError:
            return False
        current = parent
    return True


def resolve(page_path, ref):
    """Map an href/src to the file GitHub Pages would serve, or None to skip."""
    if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", ref):  # http:, mailto:, data: ...
        return None
    ref = ref.split("#")[0].split("?")[0]
    if not ref:
        return None

    if ref.startswith("/"):
        target = os.path.join(ROOT, ref.lstrip("/"))
    else:
        target = os.path.join(os.path.dirname(page_path), ref)

    target = os.path.normpath(target)
    if ref.endswith("/") or os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target


def check_page(path):
    global checked_links

    with open(path, encoding="utf-8") as handle:
        source = handle.read()

    parser = PageParser()
    parser.feed(source)

    # Files under content/ are article fragments, not whole pages: their links
    # are worth checking, but they have no <head> or navigation of their own.
    is_fragment = os.path.relpath(path, ROOT).startswith("content" + os.sep)
    is_redirect = "http-equiv=\"refresh\"" in source

    for ref, tag in parser.refs:
        target = resolve(path, ref)
        if target is None:
            continue
        checked_links += 1
        if not os.path.exists(target):
            report(path, "<%s> points at missing %s" % (tag, ref))
        elif not exists_exactly(target):
            report(path, "<%s> points at %s, whose capitalisation does not match "
                         "the file on disk. This works on macOS but 404s on "
                         "GitHub Pages." % (tag, ref))

    for tag, url in parser.remote_resources:
        report(path, "<%s> loads a remote resource: %s" % (tag, url))

    if is_fragment:
        return

    if not source.lstrip().startswith("<!DOCTYPE html>"):
        report(path, "missing <!DOCTYPE html>")

    if is_redirect:
        return

    if "/assets/css/site.css" not in source:
        report(path, "does not include /assets/css/site.css")

    for target in NAV_URLS:
        if target not in parser.nav_targets:
            report(path, "nav is missing a link to %s" % target)


def nav_urls():
    """The tabs every page must link to, read from content/site.yaml."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "vendor"))
    import yaml

    with open(os.path.join(ROOT, "content", "site.yaml"), encoding="utf-8") as handle:
        site = yaml.safe_load(handle)
    return [tab["url"] for tab in site["tabs"]]


def check_build_is_current():
    """Fail if somebody edited content/ but forgot to run ./build.py."""
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, "build.py"), "--check"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        problems.append(
            "the generated HTML is out of date with content/ — run ./build.py\n"
            + "\n".join("      " + line
                        for line in result.stdout.strip().split("\n"))
        )


def main():
    global NAV_URLS
    NAV_URLS = nav_urls()

    check_build_is_current()

    pages = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if name.endswith(".html"):
                pages.append(os.path.join(dirpath, name))

    if not pages:
        print("No HTML files found. Are you running this from the repo root?")
        return 1

    for path in sorted(pages):
        check_page(path)

    if not os.path.exists(os.path.join(ROOT, ".nojekyll")):
        problems.append(
            ".nojekyll is missing: GitHub Pages would try to build this with "
            "Jekyll instead of serving the files as-is"
        )

    print("Checked %d pages and %d references." % (len(pages), checked_links))

    if problems:
        print("\n%d problem(s):\n" % len(problems))
        for problem in problems:
            print("  - " + problem)
        return 1

    print("Everything looks good.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
