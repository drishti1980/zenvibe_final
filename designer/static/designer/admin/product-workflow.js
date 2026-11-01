(function () {
  "use strict";
  function ready() {
    const form = document.getElementById("product_form");
    const tools = document.getElementById("zv-admin-tools");
    if (!form || !tools || form.dataset.zvWorkflow) return;
    form.dataset.zvWorkflow = "1";
    const search = document.getElementById("zv-product-search");
    const status = document.getElementById("zv-search-status");
    const groups = [...form.querySelectorAll("fieldset.module, .inline-group")].filter(el =>
      !el.parentElement.closest("fieldset.module, .inline-group, .inline-related"));
    const heading = el => el.querySelector("h2, h3");
    function category(el) {
      if (el.matches("#price_tiers-group")) return "Price tiers";
      if (el.matches("#size_variants-group, #color_variants-group") || el.querySelector('[name="shape_variant_options"], [name="material_variant_options"]')) return "Variants";
      const text = heading(el)?.textContent || "";
      if (/price|quantity/i.test(text)) return "Price tiers";
      if (/delivery/i.test(text)) return "Delivery";
      if (/information|description|content|faq|guideline|printing method/i.test(text)) return "Product information";
      if (/print|editor|editable|surface/i.test(text)) return "Editor & print areas";
      if (/images|photos/i.test(text) || el.id === "angle_images-group") return "Images";
      if (/sale|availability/i.test(text)) return "Visibility & sale";
      if (/source/i.test(text)) return "Advanced";
      return "Product details";
    }
    const sections = groups.map((el, index) => {
      const details = document.createElement("details");
      details.className = "zv-config-section";
      const summary = document.createElement("summary");
      summary.textContent = heading(el)?.textContent.trim() || "Product settings";
      el.parentNode.insertBefore(details, el); details.append(summary, el);
      details.open = index === 0 || !!el.querySelector(".errorlist, .errors");
      return {el, details, group: category(el)};
    });
    const nav = document.createElement("div"); nav.className = "zv-product-nav";
    nav.setAttribute("aria-label", "Product settings sections"); tools.after(nav);
    const names = ["Product details", "Product information", "Variants", "Price tiers", "Images", "Delivery", "Visibility & sale", "Editor & print areas", "Advanced"];
    let selected = sections.find(s => s.el.querySelector(".errorlist, .errors"))?.group || "Product details";
    const buttons = [];
    function apply() {
      const term = search.value.trim().toLowerCase(); let count = 0;
      sections.forEach(s => {
        const labels = [...s.el.querySelectorAll("label, input, select, textarea")].map(e => e.tagName === "LABEL" ? e.textContent : e.name + " " + (e.type === "file" ? "" : e.value)).join(" ");
        const show = term ? (s.group + " " + s.details.querySelector("summary").textContent + " " + labels).toLowerCase().includes(term) : s.group === selected;
        s.details.hidden = !show;
        if (show) { count++; if (term) s.details.open = true; }
      });
      buttons.forEach(b => {const active = !term && b.textContent === selected; b.classList.toggle("active", active); b.setAttribute("aria-pressed", String(active));});
      status.textContent = term ? (count ? count + " matching sections" : "No matching settings") : "";
    }
    names.filter(name => sections.some(s => s.group === name)).forEach(name => {
      const b = document.createElement("button"); b.type = "button"; b.textContent = name;
      b.addEventListener("click", () => { selected = name; search.value = ""; sections.filter(s => s.group === name).forEach(s => s.details.open = true); apply(); });
      nav.append(b); buttons.push(b);
    });
    document.getElementById("zv-discard").addEventListener("click", () => {
      if (window.confirm("Discard unsaved changes and reload the saved product?")) window.location.reload();
    });
    document.getElementById("zv-expand-all").addEventListener("click", e => {
      const visible = sections.filter(s => !s.details.hidden); const open = visible.some(s => !s.details.open);
      visible.forEach(s => s.details.open = open); e.currentTarget.textContent = open ? "Collapse sections" : "Expand sections";
    });
    search.addEventListener("input", apply);
    function cards(root) {
      root.querySelectorAll(".inline-related:not(.empty-form)").forEach(card => {
        if (card.dataset.zvCompact) return;
        const h = card.querySelector("h3"); if (!h) return;
        card.dataset.zvCompact = "1";
        const button = document.createElement("button"); button.type = "button"; button.className = "zv-inline-toggle";
        const saved = card.querySelector('input[name$="-id"]')?.value;
        card.classList.toggle("zv-inline-collapsed", !!saved && !card.querySelector(".errorlist"));
        function update() { const collapsed = card.classList.contains("zv-inline-collapsed");button.textContent = collapsed ? "Edit / expand" : "Collapse";button.setAttribute("aria-expanded", String(!collapsed)); }
        update(); h.append(button); button.addEventListener("click", () => {card.classList.toggle("zv-inline-collapsed");update();});
      });
    }
    cards(form);
    document.addEventListener("formset:added", () => cards(form));
    form.addEventListener("invalid", e => {
      const s = sections.find(s => s.el.contains(e.target));
      if (s) { search.value = ""; selected = s.group; apply(); s.details.open = true; e.target.closest(".inline-related")?.classList.remove("zv-inline-collapsed"); }
    }, true);
    form.addEventListener("submit", () => sections.forEach(s => {s.details.hidden = false;s.details.open = true;}));
    apply();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready); else ready();
})();
