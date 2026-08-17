/* Renders the LaTeX in a post using the vendored copy of KaTeX.
 *
 * Loaded with `defer` after katex.min.js and contrib/auto-render.min.js, so the
 * document is fully parsed and both globals exist by the time this runs. If
 * KaTeX is somehow missing, the page still reads fine with raw LaTeX visible.
 *
 * Write inline math as \( ... \) and display math as $$ ... $$ or \[ ... \]. */

(function () {
  "use strict";

  if (typeof window.renderMathInElement !== "function") return;

  window.renderMathInElement(document.body, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false }
    ],
    ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option"],
    throwOnError: false
  });
})();
