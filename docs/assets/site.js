"use strict";

(() => {
  const select = document.querySelector("#calendar-select");
  const feed = document.querySelector("#feed-url");
  const status = document.querySelector("#copy-status");
  const copy = document.querySelector("#copy-feed");
  const tabList = document.querySelector(".platform-tabs");
  const tabs = Array.from(document.querySelectorAll("[data-platform]"));
  if (!select || !feed || !status || !copy || !tabList) return;

  document.querySelectorAll("[data-js-only]").forEach((element) => {
    element.hidden = false;
  });

  function updateFeed() {
    feed.value = select.value;
    document.querySelectorAll(".guide-apple-link").forEach((link) => {
      link.href = select.value.replace(/^https:/, "webcal:");
    });
    status.textContent = "Select the full link to copy it manually.";
  }

  function showPlatform(platform, focus = false) {
    tabs.forEach((tab) => {
      const selected = tab.dataset.platform === platform;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      document.querySelector(`#panel-${tab.dataset.platform}`).hidden = !selected;
      if (selected && focus) tab.focus();
    });
  }

  tabList.setAttribute("role", "tablist");
  tabs.forEach((tab, index) => {
    const panel = document.querySelector(`#panel-${tab.dataset.platform}`);
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", panel.id);
    panel.setAttribute("role", "tabpanel");
    panel.setAttribute("aria-labelledby", tab.id);
    panel.tabIndex = 0;
    tab.addEventListener("click", () => showPlatform(tab.dataset.platform));
    tab.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) {
        event.preventDefault();
        showPlatform(tabs[next].dataset.platform, true);
      }
    });
  });

  const userAgent = navigator.userAgent;
  const initialPlatform = /Android/i.test(userAgent)
    ? "android"
    : /Macintosh/i.test(userAgent) && navigator.maxTouchPoints < 2 ? "mac" : "iphone";
  showPlatform(initialPlatform);
  select.addEventListener("change", updateFeed);
  feed.addEventListener("click", () => feed.select());

  copy.addEventListener("click", async () => {
    const copiedFeed = feed.value;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(copiedFeed);
      if (feed.value === copiedFeed) status.textContent = "Link copied. Paste it into your calendar subscription settings.";
    } catch {
      feed.focus();
      feed.select();
      feed.setSelectionRange(0, feed.value.length);
      status.textContent = "The link is selected. Choose Copy from your device's text menu, or press Ctrl+C / Command+C.";
    }
  });

  document.querySelectorAll("[data-setup-feed]").forEach((link) => {
    link.addEventListener("click", () => {
      select.value = link.dataset.setupFeed;
      updateFeed();
      showPlatform("android");
      document.querySelector("#instructions").focus({ preventScroll: true });
    });
  });
})();
