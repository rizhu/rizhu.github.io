# Working on this site

A static website with content in YAML and a small generator. Read
[README.md](README.md) first if you have not.

**Content lives in `content/*.yaml`. The `.html` files at the repository root are
generated output — never edit them by hand.** Change the YAML, then run
`./build.py`. Commit the YAML change and the regenerated HTML together.

```bash
./build.py     # content/ -> HTML
./check.py     # must print "Everything looks good." before you finish
./serve.sh     # local preview at http://localhost:4000
```

`check.py` fails if the HTML is out of date with `content/`, so a forgotten
`./build.py` cannot slip through.

## Rules

Do not break these. They are the point of how this site is built.

1. **Never edit generated HTML.** `index.html`, `photography/index.html`,
   `blog/*/index.html`, `404.html`, `sitemap.xml`, and the redirect stubs all
   come from `content/`. Your change will be silently overwritten. The only
   hand-written HTML is `content/posts/*.html` (post bodies).
2. **Never introduce a build dependency.** No npm, no `package.json`, no pip
   install, no bundler, no Jekyll, no framework, no CSS preprocessor. `build.py`
   and `check.py` use only the Python standard library plus the vendored PyYAML
   at `tools/vendor/`.
3. **Never load anything from another domain.** No CDN links, no Google Fonts, no
   analytics. Every stylesheet, script, font, and image must live in this
   repository. `check.py` enforces this.
4. **Never delete `.nojekyll` or `CNAME`.** The site breaks without them.
5. **Never add `vendor/` to `.gitignore`.** It would exclude the vendored KaTeX
   and PyYAML.
6. **Stay inside the four-colour palette.** `#ffffff`, `#000000`, `#7a7eb9`,
   `#ff9f6a`, plus ink at reduced alpha for greys and hairlines. Dark mode has
   its own values for each variable. Use the CSS variables (`--paper`, `--ink`,
   `--polemonium`, `--range-of-light`, `--ink-55`, …); do not introduce new
   hex values. The accents stay sparing.
7. **All styling goes in `assets/css/site.css`.** No `<style>` blocks, no
   `style="…"` attributes.
8. **Prefer extending the content schema over hard-coding.** If a task needs a
   new field, add it to the YAML and teach `build.py` to render it, rather than
   writing one-off HTML.

## How the generator works

`build.py` reads `content/site.yaml`, which lists `pages`: each entry names a
content file, a `kind`, and an output path. `kind` selects a builder function
(`about-me`, `photos`, `posts`). Every page goes through the single `page()`
function, which owns the `<head>`, the header, the nav, and the footer — so
shared chrome is defined in exactly one place.

Text fields in YAML support a small inline syntax, handled by `inline()`:
`**bold**`, `*italic*`, `` `code` ``, and `[text](url)`. Everything is
HTML-escaped first, so **raw HTML in a YAML field will not work** — it will be
shown as literal text. Type real Unicode punctuation (– — ’ ′ ·) directly into
the YAML; do not use HTML entities there.

`build.py --check` exits non-zero if any output would change, without writing.

## Recipe: add or reorder photographs

Edit the `photos` list in `content/photos.yaml`. Order in the file is order on
the page. `file`, `title`, and `place` are required; `alt`, `note`, and `note_by`
are optional. `build.py` reads pixel dimensions from the image itself.

Do not add width, height, or `loading` attributes by hand — the generator emits
them, and lazy-loads everything except the first frame.

## Recipe: change the gallery layout or hover behaviour

The grid is `.grid` / `.tile` / `.tile__overlay` in `assets/css/site.css`. Three
columns, dropping to two below 62rem and one below 30rem. Hover fades in a black
scrim and the caption together over 420ms; `@media (hover: none)` shows the
caption permanently over a gradient instead, because touch screens cannot hover.

`.tile__note` is hidden inside `.grid` and shown inside `.lightbox__caption`:
`assets/js/lightbox.js` reuses the frame's own overlay markup as the viewer
caption, so there is one source for each caption.

## Recipe: add a blog post

1. Write the body as HTML in `content/posts/<slug>.html`. Just the article
   content — no `<head>`, no header, no `<h1>`, no tag list. `build.py` adds the
   date, title, and tags around it.
2. Add an entry to `posts` in `content/posts.yaml`: `slug`, `title`, `date`
   (`YYYY-MM-DD`), `description`, `summary`, `tags`, optional `image`, and
   `math: true` if it contains LaTeX. Order in the file does not matter; posts
   sort newest first.
3. `./build.py`

Conventions inside a post body:

- Section headings are `<h3 id="slug">` with a back-to-top anchor:
  `<a class="anchor" href="#top" aria-label="Back to top">&#8689;</a>`
- Code goes in `<pre><code>…</code></pre>` and **must be escaped**: `<` becomes
  `&lt;`, `>` becomes `&gt;`, `&` becomes `&amp;`. This matters in C++ examples —
  `vector<int>` and `&&` will corrupt the page otherwise.
- Use `<div class="callout">` with a `<p class="callout__label">` for boxed
  algorithm or theorem statements.

### Math

Setting `math: true` makes `build.py` link the vendored KaTeX. Write inline math
as `\( x^2 \)` and display math as `$$ x^2 $$`. Inside math, write `&` as
`&amp;` (alignment in `align*`) and avoid literal `<` and `>` — use `\lt`,
`\gt`, `\leq`, `\geq`. To verify an expression parses:

```bash
node -e 'const k=require("./assets/vendor/katex/katex.min.js");
         k.renderToString("\\frac{1}{2}", {throwOnError:true}); console.log("ok")'
```

## Recipe: add a nav tab or a new page

1. Add the tab to `tabs` in `content/site.yaml`. This updates the nav on every
   page, including existing blog posts.
2. Add a `pages` entry pointing at a content file, a `kind`, an `output` path,
   and a `url`.
3. If the page needs a shape none of the existing kinds provide, add a builder
   function to `build.py` and register it in `BUILDERS`. Follow the existing
   ones: return `page(...)` so the new page inherits the shared chrome.
4. `./build.py && ./check.py`

## Recipe: move or rename a page

Add the old path to `redirects` in `content/site.yaml`. `build.py` generates the
redirect stub; `check.py` knows to skip the stylesheet and nav requirements for
those stubs.

## Verifying visually

`check.py` catches broken references and stale output, not ugly layout. For
layout work, check narrow widths too — headless Chrome enforces a 500px minimum
window, so `--window-size=390` will silently crop a screenshot rather than
render a 390px viewport. Load the page in a 390px-wide `<iframe>` on a scratch
page instead; media queries respond to the iframe's width. Delete any scratch
file when you are done.
