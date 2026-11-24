// Filters the implementations listing by text and profile. Without
// JavaScript the full listing shows and the filter controls stay hidden.
(() => {
  const filters = document.querySelector("[data-filters]");
  const rows = Array.from(document.querySelectorAll("[data-entry]"));
  if (!filters || rows.length === 0) return;

  const search = filters.querySelector("[data-search]");
  const buttons = Array.from(filters.querySelectorAll("[data-profile]"));
  const count = document.querySelector("[data-count]");
  const noMatch = document.querySelector("[data-no-match]");
  const table = document.querySelector("[data-table]");
  const plural = (n) => `${n} ${n === 1 ? "entry" : "entries"}`;
  let profile = "";

  function apply() {
    const query = search.value.trim().toLowerCase();
    let shown = 0;
    for (const row of rows) {
      const match =
        (!profile || row.dataset.entryProfile === profile) &&
        (!query || row.dataset.entry.includes(query));
      row.hidden = !match;
      if (match) shown += 1;
    }
    noMatch.hidden = shown > 0;
    table.hidden = shown === 0;
    count.textContent = shown === rows.length ? plural(rows.length) : `${shown} of ${plural(rows.length)}`;
  }

  search.addEventListener("input", apply);
  for (const button of buttons) {
    button.addEventListener("click", () => {
      profile = button.dataset.profile;
      for (const other of buttons) other.setAttribute("aria-pressed", String(other === button));
      apply();
    });
  }
  filters.hidden = false;
})();
