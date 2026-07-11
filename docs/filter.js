(function () {
  "use strict";

  var panel = document.getElementById("filter-panel");
  var list = document.getElementById("all-items-list");
  var areaSelect = document.getElementById("filter-area");
  var industrySelect = document.getElementById("filter-industry");
  var keywordInput = document.getElementById("filter-keyword");
  var countLabel = document.getElementById("filter-count");
  var noMatch = document.getElementById("filter-no-match");
  if (!panel || !list || !areaSelect || !industrySelect || !keywordInput || !countLabel) return;

  var cards = Array.prototype.slice.call(list.querySelectorAll("[data-filter-card]"));

  function trackFilterUse(filterType, value) {
    if (typeof window.gtag !== "function" || !value) return;
    window.gtag("event", "filter_use", { filter_type: filterType, filter_value: value });
  }

  function matchesArea(card, area) {
    if (!area) return true;
    var cardArea = card.getAttribute("data-area") || "";
    if (cardArea === "全国") return true;
    return cardArea.split("/").indexOf(area) !== -1;
  }

  function matchesIndustry(card, industry) {
    if (!industry) return true;
    var industries = (card.getAttribute("data-industries") || "").split("|");
    return industries.indexOf(industry) !== -1;
  }

  function matchesKeyword(card, keyword) {
    if (!keyword) return true;
    var haystack = card.getAttribute("data-search") || "";
    return haystack.indexOf(keyword) !== -1;
  }

  function applyFilters() {
    var area = areaSelect.value;
    var industry = industrySelect.value;
    var keyword = keywordInput.value.trim().toLowerCase();

    var visibleCount = 0;
    cards.forEach(function (card) {
      var visible =
        matchesArea(card, area) &&
        matchesIndustry(card, industry) &&
        matchesKeyword(card, keyword);
      card.hidden = !visible;
      if (visible) visibleCount++;
    });

    countLabel.textContent = "該当: " + visibleCount + "件 / 全" + cards.length + "件";
    if (noMatch) noMatch.hidden = visibleCount !== 0;
  }

  function debounce(fn, waitMs) {
    var timerId = null;
    return function () {
      clearTimeout(timerId);
      timerId = setTimeout(fn, waitMs);
    };
  }

  var debouncedApplyFilters = debounce(applyFilters, 150);

  areaSelect.addEventListener("change", function () {
    applyFilters();
    trackFilterUse("area", areaSelect.value);
  });
  industrySelect.addEventListener("change", function () {
    applyFilters();
    trackFilterUse("industry", industrySelect.value);
  });
  keywordInput.addEventListener("input", debouncedApplyFilters);
  keywordInput.addEventListener("change", function () {
    trackFilterUse("keyword", keywordInput.value.trim());
  });

  applyFilters();
})();
