(function () {
  "use strict";
  function init() {
    const field = document.getElementById("id_faqs");
    if (!field || field.dataset.faqUi) return;
    field.dataset.faqUi = "1";
    const root = document.createElement("div");
    root.className = "zv-faq-admin";
    field.parentNode.insertBefore(root, field);
    const heading = document.createElement("h3");
    heading.textContent = "FAQ Questions & Answers";
    root.appendChild(heading);
    const hint = document.createElement("p");
    hint.textContent = "Add, edit, remove or reorder FAQs here. Save the product to publish changes.";
    root.appendChild(hint);
    const list = document.createElement("div");
    root.appendChild(list);
    const add = document.createElement("button");
    add.type = "button"; add.className = "button";
    add.textContent = "+ Add FAQ";
    root.appendChild(add);
    const original = field.value.trim();
    const doc = new DOMParser().parseFromString(original, "text/html");
    const details = Array.from(doc.querySelectorAll("details"));
    const remainder = doc.body.cloneNode(true);
    remainder.querySelectorAll("details").forEach(el => el.remove());
    const remainingText = (remainder.textContent || "").trim();
    // Never silently overwrite existing unstructured FAQ HTML.
    if (original && (!details.length || remainingText)) {
      const warning = document.createElement("p");
      warning.textContent = "Existing FAQ content is not in accordion format. It is preserved below. To convert it, first copy its questions and answers into the new FAQ rows, then remove the old content manually.";
      warning.style.color = "#a35c00";
      root.insertBefore(warning, list);
      field.style.display = "";
      field.style.minHeight = "130px";
      add.disabled = true;
      return;
    }
    const rows = details.map(d => ({
      q: (d.querySelector("summary")?.textContent || "").trim().replace(/\s*[+−]\s*$/, ""),
      a: Array.from(d.children).filter(e => e.tagName !== "SUMMARY").map(e => e.textContent).join("\n").trim()
    }));
    field.style.display = "none";
    function serialize() {
      const escape = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      field.value = rows.filter(x => x.q.trim()).map(x =>
        '<details class="zv-product-faq"><summary>' + escape(x.q.trim()) + '</summary><p>' + escape(x.a.trim()).replace(/\n/g, "<br>") + '</p></details>'
      ).join("\n");
      field.dispatchEvent(new Event("change", {bubbles:true}));
    }
    function render() {
      list.replaceChildren();
      rows.forEach((row, i) => {
        const card = document.createElement("div"); card.className = "zv-faq-admin-row";
        const top = document.createElement("div"); top.className = "zv-faq-admin-actions";
        const label = document.createElement("strong"); label.textContent = "FAQ " + (i + 1); top.appendChild(label);
        [["↑", () => swap(i, i-1)], ["↓", () => swap(i, i+1)], ["Remove", () => {rows.splice(i,1);serialize();render();}]].forEach(([name,fn],k) => {
          const btn=document.createElement("button"); btn.type="button";btn.textContent=name;
          btn.disabled=(k===0&&i===0)||(k===1&&i===rows.length-1);
          btn.addEventListener("click",fn);top.appendChild(btn);
        });
        card.appendChild(top);
        const q=document.createElement("input");q.type="text";q.placeholder="Question";q.value=row.q;q.setAttribute("aria-label","FAQ question "+(i+1));
        q.addEventListener("input",()=>{row.q=q.value;serialize();});card.appendChild(q);
        const a=document.createElement("textarea");a.rows=3;a.placeholder="Answer";a.value=row.a;a.setAttribute("aria-label","FAQ answer "+(i+1));
        a.addEventListener("input",()=>{row.a=a.value;serialize();});card.appendChild(a);
        list.appendChild(card);
      });
    }
    function swap(i,j){if(j<0||j>=rows.length)return;[rows[i],rows[j]]=[rows[j],rows[i]];serialize();render();}
    add.addEventListener("click",()=>{rows.push({q:"",a:""});render();list.lastElementChild?.querySelector("input")?.focus();});
    render();
    // Preserve existing data on load; only write on edits.
  }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",init);
  else init();
})();