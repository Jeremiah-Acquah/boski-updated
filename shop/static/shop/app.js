// Small enhancements. The site still works without JavaScript.
(function () {
  "use strict";

  // Close the dropdown menus (desktop All Categories, phone hamburger) when clicking elsewhere,
  // pressing Escape, or tapping a link inside them
  var menus = document.querySelectorAll(".allcats, .mnav");
  menus.forEach(function (menu) {
    document.addEventListener("click", function (e) { if (!menu.contains(e.target)) menu.removeAttribute("open"); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") menu.removeAttribute("open"); });
    menu.addEventListener("click", function (e) {
      if (e.target.closest && e.target.closest("a")) menu.removeAttribute("open");
    });
  });

  // Save / unsave a product without reloading the page
  document.addEventListener("submit", function (e) {
    var form = e.target.closest ? e.target.closest(".wish-form") : null;
    if (!form || !window.fetch) return;
    e.preventDefault();
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin"
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (data) {
        var btn = form.querySelector(".wish-btn");
        btn.classList.toggle("is-on", data.saved);
        btn.setAttribute("aria-pressed", data.saved ? "true" : "false");
        document.querySelectorAll("[data-wish-count]").forEach(function (el) {
          el.textContent = data.count;
          el.hidden = data.count === 0;
        });
        if (!data.saved && document.body.dataset.page === "wishlist") {
          var card = form.closest(".product-card");
          if (card) card.remove();
        }
      })
      .catch(function () { form.submit(); });
  });

  // Quantity +/- buttons
  document.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("[data-step]") : null;
    if (!btn) return;
    var input = btn.parentElement.querySelector("input");
    var value = (parseInt(input.value, 10) || 1) + parseInt(btn.dataset.step, 10);
    input.value = Math.min(99, Math.max(parseInt(input.min || "1", 10), value));
  });

  // Copy product link
  document.addEventListener("click", function (e) {
    var btn = e.target.closest ? e.target.closest("[data-copy]") : null;
    if (!btn) return;
    var done = function () {
      var old = btn.textContent;
      btn.textContent = "Link copied";
      setTimeout(function () { btn.textContent = old; }, 1800);
    };
    if (navigator.clipboard) navigator.clipboard.writeText(btn.dataset.copy).then(done);
    else { window.prompt("Copy this link:", btn.dataset.copy); }
  });
})();
