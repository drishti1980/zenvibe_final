(function () {
  "use strict";

  const fields = [
    "short_description",
    "description",
    "product_information",
    "printing_method",
    "design_guidelines",
    "printing_guidelines",
    "body"
  ];

  function cmd(name, value) {
    document.execCommand(name, false, value == null ? null : value);
  }

  function button(label, title, command, value) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "zv-rt-btn";
    b.innerHTML = label;
    b.title = title;
    b.setAttribute("aria-label", title);
    b.addEventListener("mousedown", function (e) { e.preventDefault(); });
    b.addEventListener("click", function (e) {
      e.preventDefault();
      command && cmd(command, value);
    });
    return b;
  }

  function separator() {
    const s = document.createElement("span");
    s.className = "zv-rt-separator";
    return s;
  }

  function enhance(textarea) {
    if (!textarea || textarea.dataset.zvRich === "1") return;
    textarea.dataset.zvRich = "1";

    const shell = document.createElement("div");
    shell.className = "zv-rich-shell" + (textarea.id === "id_short_description" ? " zv-rich-short" : "");

    // Insert the complete editor exactly where Django put the textarea.
    textarea.parentNode.insertBefore(shell, textarea);

    const toolbar = document.createElement("div");
    toolbar.className = "zv-rt-toolbar";

    const format = document.createElement("select");
    format.className = "zv-rt-format";
    [["Paragraph", "p"], ["Heading 2", "h2"], ["Heading 3", "h3"], ["Heading 4", "h4"]].forEach(function (x) {
      const o = document.createElement("option");
      o.value = x[1]; o.textContent = x[0]; format.appendChild(o);
    });
    format.addEventListener("mousedown", function (e) { e.stopPropagation(); });
    format.addEventListener("change", function () {
      editor.focus(); cmd("formatBlock", "<" + format.value + ">"); sync();
    });
    toolbar.appendChild(format);
    toolbar.appendChild(separator());
    toolbar.appendChild(button("<b>B</b>", "Bold", "bold"));
    toolbar.appendChild(button("<i>I</i>", "Italic", "italic"));
    toolbar.appendChild(button("<u>U</u>", "Underline", "underline"));
    toolbar.appendChild(button("<s>S</s>", "Strikethrough", "strikeThrough"));
    toolbar.appendChild(separator());
    toolbar.appendChild(button("• Bullets", "Bullet list", "insertUnorderedList"));
    toolbar.appendChild(button("1. Numbered", "Numbered list", "insertOrderedList"));
    toolbar.appendChild(separator());
    toolbar.appendChild(button("⇤", "Align left", "justifyLeft"));
    toolbar.appendChild(button("↔", "Align center", "justifyCenter"));
    toolbar.appendChild(button("⇥", "Align right", "justifyRight"));
    toolbar.appendChild(separator());

    const link = button("🔗 Link", "Insert link");
    link.addEventListener("click", function () {
      const url = window.prompt("Enter link URL");
      if (url) { cmd("createLink", url); sync(); }
    });
    toolbar.appendChild(link);
    if (textarea.id === "id_description") {
      // A small on-page form avoids blocked prompt dialogs and unreliable
      // execCommand insertion when the cursor is inside a <details> element.
      const faq = button("＋ Add FAQ", "Add a question and answer to Description");
      const faqPanel = document.createElement("div");
      faqPanel.className = "zv-inline-faq-form";
      faqPanel.hidden = true;
      const question = document.createElement("input");
      question.type = "text"; question.placeholder = "Question (e.g. Can I add engraving?)";
      question.setAttribute("aria-label", "New FAQ question");
      const answer = document.createElement("textarea");
      answer.rows = 3; answer.placeholder = "Write the answer here";
      answer.setAttribute("aria-label", "New FAQ answer");
      const saveFaq = document.createElement("button");
      saveFaq.type = "button"; saveFaq.className = "button default";
      saveFaq.textContent = "Add question to description";
      const cancelFaq = document.createElement("button");
      cancelFaq.type = "button"; cancelFaq.className = "button";
      cancelFaq.textContent = "Cancel";
      const error = document.createElement("p");
      error.className = "zv-faq-error";error.setAttribute("role", "alert");
      cancelFaq.addEventListener("click", () => { faqPanel.hidden = true;error.textContent = ""; });
      faq.addEventListener("click", function () {
        faqPanel.hidden = !faqPanel.hidden;
        if (!faqPanel.hidden) question.focus();
      });
      saveFaq.addEventListener("click", function () {
        const q = question.value.trim(), a = answer.value.trim();
        if (!q || !a) { error.textContent = "Enter both a question and an answer.";return; }
        const details = document.createElement("details");
        details.className = "zv-description-faq";
        const summary = document.createElement("summary");
        const prior = editor.querySelectorAll("details").length;
        summary.textContent = (prior + 1) + ". " + q;
        const paragraph = document.createElement("p");
        paragraph.textContent = a;
        details.append(summary, paragraph);
        // Append after existing FAQ accordions; never nest a FAQ inside another.
        const all = Array.from(editor.querySelectorAll("details"));
        const last = all[all.length - 1];
        if (last) last.insertAdjacentElement("afterend", details);
        else editor.appendChild(details);
        question.value = "";answer.value = "";
        faqPanel.hidden = true;error.textContent = "";
        sync();
      });
      faqPanel.append(question, answer, error, saveFaq, cancelFaq);
      toolbar.appendChild(faq);
      // The panel is mounted after the toolbar in the editor shell below.
      toolbar.dataset.hasFaqPanel = "1";
      toolbar._zvFaqPanel = faqPanel;
    }
    if (textarea.id === "id_body") {
      const photo = button("Image", "Insert hosted image");
      photo.addEventListener("click", function () {
        const url = window.prompt("Enter a public HTTPS image URL (upload images to your media library first):");
        if (url && /^https:\/\//i.test(url.trim())) {
          editor.focus();
          cmd("insertHTML", '<img src="' + url.trim().replace(/["<>]/g, "") + '" alt="Email image" style="max-width:100%;height:auto">');
          sync();
        }
      });
      toolbar.appendChild(photo);
    }
    toolbar.appendChild(separator());
    toolbar.appendChild(button("↶", "Undo", "undo"));
    toolbar.appendChild(button("↷", "Redo", "redo"));
    toolbar.appendChild(button("Clear", "Clear formatting", "removeFormat"));

    const editor = document.createElement("div");
    editor.className = "zv-rich-editor";
    editor.contentEditable = "true";
    editor.spellcheck = true;
    editor.setAttribute("role", "textbox");
    editor.setAttribute("aria-multiline", "true");
    editor.dataset.placeholder = "Type content here…";
    editor.innerHTML = textarea.value || "";

    function sync() { textarea.value = editor.innerHTML; }
    editor.addEventListener("input", sync);
    editor.addEventListener("blur", sync);
    editor.addEventListener("keydown", function (e) {
      if (e.key !== "Tab") return;
      let n = window.getSelection() && window.getSelection().anchorNode;
      if (n && n.nodeType === 3) n = n.parentElement;
      if (n && n.closest && n.closest("li")) {
        e.preventDefault(); cmd(e.shiftKey ? "outdent" : "indent"); sync();
      }
    });

    // The real textarea remains inside the same shell for Django form submission,
    // but is visually hidden so there is never a second giant box beside the toolbar.
    textarea.classList.add("zv-rich-source");
    shell.appendChild(toolbar);
    if (toolbar._zvFaqPanel) shell.appendChild(toolbar._zvFaqPanel);
    shell.appendChild(editor);
    shell.appendChild(textarea);
    if (textarea.form) textarea.form.addEventListener("submit", sync);
  }

  function init() {
    fields.forEach(function (name) { enhance(document.getElementById("id_" + name)); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
