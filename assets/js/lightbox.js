/* Gallery lightbox. Plain browser JavaScript, no dependencies, no build step.
 *
 * It enhances the gallery: each frame is an ordinary link to the full-size
 * image file, so if this script is missing or fails the page still works.
 * Frames and their captions are read from the DOM, so nothing here needs
 * touching when photographs are added to content/photos.yaml. */

(function () {
  "use strict";

  var gallery = document.getElementById("gallery");
  var box = document.getElementById("lightbox");
  var img = document.getElementById("lightbox-img");
  var caption = document.getElementById("lightbox-caption");
  var prevBtn = document.getElementById("lightbox-prev");
  var nextBtn = document.getElementById("lightbox-next");
  var closeBtn = document.getElementById("lightbox-close");

  if (!gallery || !box || !img || !caption) return;

  var frames = Array.prototype.slice.call(gallery.querySelectorAll(".tile"));
  if (!frames.length) return;

  var index = -1;
  var lastFocused = null;

  function show(i) {
    if (i < 0) i = frames.length - 1;
    if (i >= frames.length) i = 0;
    index = i;

    var link = frames[index];
    img.src = link.getAttribute("href");

    // Reuse the frame's own caption markup. In the grid, CSS hides the longer
    // note; here it is shown.
    var overlay = link.querySelector(".tile__overlay");
    caption.innerHTML = overlay ? overlay.innerHTML : "";
  }

  function open(i) {
    lastFocused = document.activeElement;
    show(i);
    box.classList.add("is-open");
    document.body.style.overflow = "hidden";
    if (closeBtn) closeBtn.focus();
  }

  function close() {
    box.classList.remove("is-open");
    document.body.style.overflow = "";
    img.removeAttribute("src");
    if (lastFocused && lastFocused.focus) lastFocused.focus();
  }

  function isOpen() {
    return box.classList.contains("is-open");
  }

  frames.forEach(function (link, i) {
    link.addEventListener("click", function (event) {
      // Let modifier-clicks and middle-clicks open the file normally.
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) {
        return;
      }
      event.preventDefault();
      open(i);
    });
  });

  if (prevBtn) {
    prevBtn.addEventListener("click", function () {
      show(index - 1);
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      show(index + 1);
    });
  }

  if (closeBtn) closeBtn.addEventListener("click", close);

  // Clicking the empty space around the photograph closes the viewer.
  box.addEventListener("click", function (event) {
    if (event.target === box || event.target.classList.contains("lightbox__stage")) {
      close();
    }
  });

  document.addEventListener("keydown", function (event) {
    if (!isOpen()) return;
    if (event.key === "Escape") close();
    else if (event.key === "ArrowLeft") show(index - 1);
    else if (event.key === "ArrowRight") show(index + 1);
  });
})();
