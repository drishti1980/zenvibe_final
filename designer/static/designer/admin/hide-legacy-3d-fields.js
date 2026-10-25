/* Presentation-only: hide generated 3D metadata without changing stored product data. */
(function () {
  "use strict";
  const hidden = /^(generated_3d_model|generated_3d_method)$/i;
  const fieldSelectors = ".form-row,.field-box,.form-group,.mb-3,.field-wrapper,.form-field,.jsoneditor-field,.jsoneditor-tree tr,.row";
  function matches(text) {
    return hidden.test(String(text || "").trim().replace(/:$/, "").trim());
  }
  function conceal(node) {
    if (!node || !node.style) return;
    node.style.setProperty("display", "none", "important");
    node.setAttribute("aria-hidden", "true");
  }
  function fieldRow(el) {
    const row = el.closest(fieldSelectors);
    if (row && row !== document.body) return row;
    // A JSON editor often renders the key and value in one table row.
    const tr = el.closest("tr");
    if (tr) return tr;
    // Django admin commonly nests a label and input in one immediate wrapper.
    const parent = el.parentElement;
    if (parent && parent.querySelector("input,textarea,select,[contenteditable]")) return parent;
    if (parent && parent.parentElement &&
        parent.parentElement.querySelector("input,textarea,select,[contenteditable]") &&
        parent.parentElement.children.length <= 4) return parent.parentElement;
    return parent;
  }
  function scan() {
    document.querySelectorAll("label,.jsoneditor-field,[data-field],th,dt").forEach(function (el) {
      const name = el.getAttribute("data-field") || el.textContent;
      if (matches(name)) conceal(fieldRow(el));
    });
    document.querySelectorAll("input,textarea,select").forEach(function (el) {
      const name = el.name || el.id.replace(/^id_/, "");
      if (matches(name)) conceal(fieldRow(el));
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", scan);
  else scan();
  // Some admin JSON editors build their field rows after DOMContentLoaded.
  const observer = new MutationObserver(function () { scan(); });
  function observe() {
    if (document.body) observer.observe(document.body, {childList: true, subtree: true});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe);
  else observe();
})();
