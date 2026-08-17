/* Dark-mode toggle. The saved preference lives in localStorage so it
 * persists across visits. If nothing is saved the system preference wins. */

(function () {
  "use strict";

  var btn = document.getElementById("theme-toggle");
  if (!btn) return;

  function isDark() {
    return document.documentElement.getAttribute("data-theme") === "dark";
  }

  function apply(dark) {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("theme", dark ? "dark" : "light");
  }

  btn.addEventListener("click", function () {
    apply(!isDark());
  });
})();
