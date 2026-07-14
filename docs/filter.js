(function () {
  "use strict";

  var hero = document.getElementById("hero-search");
  var list = document.getElementById("all-items-list");
  var areaSelect = document.getElementById("filter-area");
  var industrySelect = document.getElementById("filter-industry");
  var keywordInput = document.getElementById("filter-keyword");
  var countLabel = document.getElementById("filter-count");
  var clearBtn = document.getElementById("filter-clear-btn");
  var noMatch = document.getElementById("filter-no-match");
  if (!hero || !list || !areaSelect || !industrySelect || !keywordInput || !countLabel) return;

  var cards = Array.prototype.slice.call(list.querySelectorAll("[data-filter-card]"));
  var cardsByDeadline = cards.slice();

  function trackFilterUse(filterType, value, extraParams) {
    if (typeof window.gtag !== "function" || !value) return;
    var params = { filter_type: filterType, filter_value: value };
    if (extraParams) {
      for (var key in extraParams) params[key] = extraParams[key];
    }
    window.gtag("event", "filter_use", params);
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

  function buildFeedbackText(labels, visibleCount) {
    if (labels.length === 0) {
      return "全" + cards.length + "件を表示中";
    }
    return labels.join(" × ") + "：" + visibleCount + "件";
  }

  function applyFilters() {
    var area = areaSelect.value;
    var industry = industrySelect.value;
    var keyword = keywordInput.value.trim();
    var keywordLower = keyword.toLowerCase();

    var visibleCount = 0;
    cards.forEach(function (card) {
      var visible =
        matchesArea(card, area) &&
        matchesIndustry(card, industry) &&
        matchesKeyword(card, keywordLower);
      card.hidden = !visible;
      if (visible) visibleCount++;
    });

    var labels = [];
    if (area) labels.push(area);
    if (keyword) labels.push(keyword);
    if (industry) labels.push(industry);

    countLabel.textContent = buildFeedbackText(labels, visibleCount);
    if (noMatch) noMatch.hidden = visibleCount !== 0;
    if (clearBtn) clearBtn.hidden = labels.length === 0;
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
  keywordInput.addEventListener("input", function () {
    debouncedApplyFilters();
    updateChipPressedStates();
  });
  keywordInput.addEventListener("change", function () {
    trackFilterUse("keyword", keywordInput.value.trim());
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      areaSelect.value = "";
      industrySelect.value = "";
      keywordInput.value = "";
      applyFilters();
      updateChipPressedStates();
      trackFilterUse("clear", "all");
      // クリアボタンはこの後 hidden になるため、フォーカスが行方不明にならないよう
      // 絞り込み条件欄の先頭（キーワード入力）へ移す。
      keywordInput.focus();
    });
  }

  // 並び替え: 締切が近い順（サーバー生成時点の既定順）/ 新着順（first_seen降順）。
  // カードのDOMノードを実際に並べ替える（複製はしない）ため、hidden属性は
  // ノードに紐づいたまま移動し、絞り込み状態を壊さない。
  var sortToggle = document.getElementById("sort-toggle");
  if (sortToggle) {
    var sortButtons = Array.prototype.slice.call(sortToggle.querySelectorAll(".sort-btn"));

    function cardsSortedByNew() {
      return cards.slice().sort(function (a, b) {
        var aDate = a.getAttribute("data-first-seen") || "0000-00-00";
        var bDate = b.getAttribute("data-first-seen") || "0000-00-00";
        return bDate.localeCompare(aDate);
      });
    }

    function applySort(sortKey) {
      var ordered = sortKey === "new" ? cardsSortedByNew() : cardsByDeadline;
      var fragment = document.createDocumentFragment();
      ordered.forEach(function (card) {
        fragment.appendChild(card);
      });
      if (noMatch) fragment.appendChild(noMatch);
      list.appendChild(fragment);
      sortButtons.forEach(function (btn) {
        btn.setAttribute("aria-pressed", String(btn.getAttribute("data-sort") === sortKey));
      });
    }

    sortButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var sortKey = btn.getAttribute("data-sort");
        if (btn.getAttribute("aria-pressed") === "true") return;
        applySort(sortKey);
        trackFilterUse("sort", sortKey);
      });
    });
  }

  // 目的・キーワードチップ: クリックでキーワード検索欄に反映し、既存の
  // キーワード絞り込みロジック（matchesKeyword）をそのまま利用する。
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));

  function updateChipPressedStates() {
    var current = keywordInput.value.trim();
    chips.forEach(function (chip) {
      chip.setAttribute("aria-pressed", String(chip.getAttribute("data-keyword") === current));
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var keyword = chip.getAttribute("data-keyword");
      var isActive = chip.getAttribute("aria-pressed") === "true";
      keywordInput.value = isActive ? "" : keyword;
      applyFilters();
      updateChipPressedStates();
      trackFilterUse("keyword_chip", keyword, { filter_action: isActive ? "clear" : "apply" });
    });
  });

  var chipMoreToggle = document.getElementById("chip-more-toggle");
  if (chipMoreToggle) {
    chipMoreToggle.addEventListener("click", function () {
      var expanded = chipMoreToggle.getAttribute("aria-expanded") === "true";
      document.querySelectorAll(".chip-extra").forEach(function (chip) {
        chip.hidden = expanded;
      });
      chipMoreToggle.setAttribute("aria-expanded", String(!expanded));
      chipMoreToggle.textContent = expanded ? "もっと見る" : "閉じる";
    });
  }

  applyFilters();
  updateChipPressedStates();
})();
