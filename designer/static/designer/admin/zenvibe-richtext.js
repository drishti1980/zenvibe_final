(function () {
  "use strict";

  const fields = [
    "short_description",
    "description",
    "product_information",
    "printing_method",
    "design_guidelines",
    "printing_guidelines",
    "faqs",
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
