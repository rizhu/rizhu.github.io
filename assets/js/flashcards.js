/* Dutch flashcards: a typed-answer drill in the spirit of Quizlet's Learn.
 * Plain browser JavaScript, no dependencies, no build step.
 *
 * build.py embeds every set from content/flashcards/*.csv in the page as JSON.
 * The selected cards are shuffled once into a fixed order. Each round serves
 * that order; a missed card is slipped back in a few cards later, and the round
 * ends only when every card has been answered correctly. The next round then
 * replays the same order, forever. */

(function () {
  "use strict";

  var dataEl = document.getElementById("flashcard-data");
  var form = document.getElementById("fc-card");
  if (!dataEl || !form) return;

  var SETS = JSON.parse(dataEl.textContent).sets;

  // A missed card comes back after this many other cards (when that many are
  // left in the round).
  var RETRY_MIN = 3;
  var RETRY_MAX = 6;

  // How long "Correct" stays up before the next card, in milliseconds.
  var CORRECT_PAUSE = 650;

  var DIRECTION_LABELS = { mixed: "Mixed", nl: "NL \u2192 EN", en: "EN \u2192 NL" };

  var options = document.getElementById("fc-options");
  var summary = document.getElementById("fc-summary");
  var setBoxes = [].slice.call(document.querySelectorAll('#fc-options input[name="set"]'));
  var dirRadios = [].slice.call(document.querySelectorAll('#fc-options input[name="direction"]'));
  var quickBtns = [].slice.call(document.querySelectorAll("#fc-options [data-select]"));
  var directionEl = document.getElementById("fc-direction");
  var setEl = document.getElementById("fc-set");
  var promptEl = document.getElementById("fc-prompt");
  var input = document.getElementById("fc-answer");
  var feedback = document.getElementById("fc-feedback");
  var submitBtn = document.getElementById("fc-submit");
  var altBtn = document.getElementById("fc-alt");
  var empty = document.getElementById("fc-empty");
  var progress = document.getElementById("fc-progress");
  var bar = document.getElementById("fc-bar");
  var roundEl = document.getElementById("fc-round");
  var countEl = document.getElementById("fc-count");

  var deck = [];     // this session's shuffled order; every round replays it
  var queue = [];    // cards still to answer correctly this round, next first
  var round = 1;
  var card = null;   // { nl, en, set }
  var askDutch = true;
  var phase = "ask"; // "ask", "right" or "wrong"
  var timer = null;

  // ------------------------------------------------------------- storage

  function load(key) {
    try {
      return JSON.parse(localStorage.getItem("flashcards." + key));
    } catch (e) {
      return null;
    }
  }

  function save(key, value) {
    try {
      localStorage.setItem("flashcards." + key, JSON.stringify(value));
    } catch (e) {
      // Private browsing can refuse storage; the session still works.
    }
  }

  // ------------------------------------------------------------- helpers

  // Answers are compared stripped and lowercased. Phone keyboards also swap
  // ' for ’ and may send accented letters decomposed, so fold those first.
  function normalise(text) {
    return text
      .normalize("NFC")
      .replace(/[\u2018\u2019]/g, "'")
      .replace(/[\u201C\u201D]/g, '"')
      .trim()
      .toLowerCase();
  }

  function shuffle(list) {
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var swap = list[i];
      list[i] = list[j];
      list[j] = swap;
    }
    return list;
  }

  function direction() {
    for (var i = 0; i < dirRadios.length; i++) {
      if (dirRadios[i].checked) return dirRadios[i].value;
    }
    return "mixed";
  }

  function pickSide() {
    var mode = direction();
    askDutch = mode === "nl" || (mode === "mixed" && Math.random() < 0.5);
  }

  // ---------------------------------------------------------------- deck

  function start() {
    clearTimeout(timer);

    var on = {};
    setBoxes.forEach(function (box) {
      on[box.value] = box.checked;
    });

    var seen = {};
    deck = [];
    SETS.forEach(function (set) {
      if (!on[set.id]) return;
      set.cards.forEach(function (pair) {
        var key = normalise(pair[0]) + "\n" + normalise(pair[1]);
        if (seen[key]) return;
        seen[key] = true;
        deck.push({ nl: pair[0], en: pair[1], set: set.name });
      });
    });

    shuffle(deck);
    queue = deck.slice();
    round = 1;
    card = null;
    updateSummary();

    var hasCards = deck.length > 0;
    form.hidden = !hasCards;
    progress.hidden = !hasCards;
    empty.hidden = hasCards;
    if (hasCards) next();
    else options.open = true;
  }

  function next() {
    clearTimeout(timer);
    var note = "";

    if (!queue.length) {
      note = "Round " + round + " done \u2014 every card right. Round " +
        (round + 1) + " starts now.";
      round += 1;
      queue = deck.slice();
      // Never serve the card that was just answered twice in a row.
      if (queue.length > 1 && queue[0] === card) {
        queue[0] = queue[1];
        queue[1] = card;
      }
    }

    card = queue.shift();
    pickSide();
    phase = "ask";
    input.value = "";
    showCard();
    setFeedback(note ? "note" : "", note);
    render();
  }

  function showCard() {
    promptEl.textContent = askDutch ? card.nl : card.en;
    promptEl.lang = askDutch ? "nl" : "en";
    input.lang = askDutch ? "en" : "nl";
    input.placeholder = askDutch ? "Type the English" : "Type the Dutch";
    directionEl.textContent = askDutch ? "Dutch \u2192 English" : "English \u2192 Dutch";
    setEl.textContent = card.set;
  }

  function check(given) {
    var answer = askDutch ? card.en : card.nl;

    if (given !== null && normalise(given) === normalise(answer)) {
      phase = "right";
      setFeedback("right", "Correct");
      timer = setTimeout(next, CORRECT_PAUSE);
    } else {
      phase = "wrong";
      var gap = RETRY_MIN + Math.floor(Math.random() * (RETRY_MAX - RETRY_MIN + 1));
      queue.splice(Math.min(gap, queue.length), 0, card);
      setFeedback("wrong", answer);
    }
    render();
  }

  // "I was right": count the miss as a hit and take the card back out of the
  // queue, for typos and for translations the card does not list.
  function override() {
    var at = queue.indexOf(card);
    if (at !== -1) queue.splice(at, 1);
    next();
  }

  // ------------------------------------------------------------ drawing

  function setFeedback(kind, text) {
    feedback.className = "fc-card__feedback" + (kind ? " is-" + kind : "");
    feedback.textContent = "";
    if (kind === "wrong") {
      var label = document.createElement("span");
      label.className = "fc-card__label";
      label.textContent = "Answer";
      var answer = document.createElement("strong");
      answer.lang = askDutch ? "en" : "nl";
      answer.textContent = text;
      feedback.appendChild(label);
      feedback.appendChild(answer);
    } else {
      feedback.textContent = text;
    }
  }

  function render() {
    form.classList.toggle("is-right", phase === "right");
    form.classList.toggle("is-wrong", phase === "wrong");
    submitBtn.textContent = phase === "ask" ? "Check" : "Next";
    altBtn.textContent = phase === "wrong" ? "I was right" : "Don\u2019t know";

    var learned = deck.length - queue.length - (phase === "ask" ? 1 : 0);
    roundEl.textContent = "Round " + round;
    countEl.textContent = learned + " / " + deck.length + " right";
    bar.style.transform = "scaleX(" + (deck.length ? learned / deck.length : 0) + ")";
  }

  function updateSummary() {
    var sets = setBoxes.filter(function (box) {
      return box.checked;
    }).length;
    summary.textContent = sets + (sets === 1 ? " set" : " sets") + " \u00b7 " +
      deck.length + (deck.length === 1 ? " card" : " cards") + " \u00b7 " +
      DIRECTION_LABELS[direction()];
  }

  // On a phone the keyboard takes half the screen, so bring the whole card up
  // under the header once it has opened.
  function revealCard() {
    if (!window.matchMedia("(max-width: 40rem)").matches) return;
    setTimeout(function () {
      form.scrollIntoView({ block: "start", behavior: "smooth" });
    }, 300);
  }

  // -------------------------------------------------------------- events

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (phase === "ask") {
      // An empty Enter is usually a double press, not a guess; ignore it.
      if (input.value.trim()) check(input.value);
    } else {
      next();
    }
    input.focus();
  });

  altBtn.addEventListener("click", function () {
    if (phase === "ask") check(null);
    else if (phase === "wrong") override();
    input.focus();
  });

  // Keep the input focused through button taps, so a phone keyboard stays up.
  [submitBtn, altBtn].forEach(function (button) {
    button.addEventListener("mousedown", function (event) {
      event.preventDefault();
    });
  });

  // Typing during the "Correct" pause starts the next card straight away,
  // and the keystroke lands in its empty input.
  input.addEventListener("keydown", function (event) {
    if (phase === "right" && event.key.length === 1 &&
        !event.metaKey && !event.ctrlKey && !event.altKey) {
      next();
    }
  });

  input.addEventListener("focus", revealCard);

  setBoxes.forEach(function (box) {
    box.addEventListener("change", saveSetsAndRestart);
  });

  quickBtns.forEach(function (button) {
    button.addEventListener("click", function () {
      var on = button.getAttribute("data-select") === "all";
      setBoxes.forEach(function (box) {
        box.checked = on;
      });
      saveSetsAndRestart();
    });
  });

  dirRadios.forEach(function (radio) {
    radio.addEventListener("change", function () {
      save("direction", direction());
      updateSummary();
      if (card && phase === "ask" && !input.value) {
        pickSide();
        showCard();
      }
    });
  });

  // Remember which sets are switched off rather than on, so a newly added
  // set starts out included.
  function saveSetsAndRestart() {
    save("off", setBoxes.filter(function (box) {
      return !box.checked;
    }).map(function (box) {
      return box.value;
    }));
    start();
  }

  // --------------------------------------------------------------- start

  var off = load("off") || [];
  setBoxes.forEach(function (box) {
    box.checked = off.indexOf(box.value) === -1;
  });

  var savedDirection = load("direction");
  if (DIRECTION_LABELS[savedDirection]) {
    dirRadios.forEach(function (radio) {
      radio.checked = radio.value === savedDirection;
    });
  }

  start();

  if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    input.focus({ preventScroll: true });
  }
})();
