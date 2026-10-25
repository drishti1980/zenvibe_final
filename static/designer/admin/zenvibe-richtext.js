(function () {
    'use strict';

    const FIELD_SELECTOR = 'textarea.zenvibe-richtext-source';

    function syncEditor(editor, textarea) {
        textarea.value = editor.innerHTML;
    }

    function focusEditor(editor) {
        editor.focus();
    }

    function execute(editor, textarea, command, value = null) {
        focusEditor(editor);

        try {
            document.execCommand(command, false, value);
        } catch (error) {
            console.error('ZenVibe rich-text command failed:', command, error);
        }

        syncEditor(editor, textarea);
    }

    function createButton(label, title, handler) {
        const button = document.createElement('button');

        button.type = 'button';
        button.className = 'zv-rt-btn';
        button.innerHTML = label;
        button.title = title;

        /*
         * Prevent the toolbar button from stealing the current
         * text selection from the contenteditable editor.
         */
        button.addEventListener('mousedown', function (event) {
            event.preventDefault();
        });

        button.addEventListener('click', function (event) {
            event.preventDefault();
            handler();
        });

        return button;
    }

    function init(textarea) {
        if (!textarea || textarea.dataset.zvReady === '1') {
            return;
        }

        textarea.dataset.zvReady = '1';

        /* ---------------------------------------------------------
           WRAPPER
        --------------------------------------------------------- */

        const wrap = document.createElement('div');
        wrap.className = 'zv-rt-wrap';

        const toolbar = document.createElement('div');
        toolbar.className = 'zv-rt-toolbar';

        const editor = document.createElement('div');
        editor.className = 'zv-rt-editor';
        editor.contentEditable = 'true';
        editor.setAttribute('role', 'textbox');
        editor.setAttribute('aria-multiline', 'true');
        editor.spellcheck = true;

        editor.innerHTML = textarea.value || '';

        /* ---------------------------------------------------------
           BASIC FORMATTING
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('<b>B</b>', 'Bold', function () {
                execute(editor, textarea, 'bold');
            })
        );

        toolbar.appendChild(
            createButton('<i>I</i>', 'Italic', function () {
                execute(editor, textarea, 'italic');
            })
        );

        toolbar.appendChild(
            createButton('<u>U</u>', 'Underline', function () {
                execute(editor, textarea, 'underline');
            })
        );

        toolbar.appendChild(
            createButton('<s>S</s>', 'Strikethrough', function () {
                execute(editor, textarea, 'strikeThrough');
            })
        );

        /* ---------------------------------------------------------
           BULLET LIST
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('• List', 'Bulleted List', function () {
                execute(
                    editor,
                    textarea,
                    'insertUnorderedList'
                );
            })
        );

        /* ---------------------------------------------------------
           NUMBERED LIST
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('1. List', 'Numbered List', function () {
                execute(
                    editor,
                    textarea,
                    'insertOrderedList'
                );
            })
        );

        /* ---------------------------------------------------------
           UNDO / REDO
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('↶', 'Undo', function () {
                execute(editor, textarea, 'undo');
            })
        );

        toolbar.appendChild(
            createButton('↷', 'Redo', function () {
                execute(editor, textarea, 'redo');
            })
        );

        /* ---------------------------------------------------------
           PARAGRAPH / HEADINGS
        --------------------------------------------------------- */

        const format = document.createElement('select');
        format.className = 'zv-rt-select';
        format.title = 'Text format';

        [
            ['p', 'Paragraph'],
            ['h2', 'Heading 2'],
            ['h3', 'Heading 3'],
            ['h4', 'Heading 4']
        ].forEach(function (item) {
            const option = document.createElement('option');

            option.value = item[0];
            option.textContent = item[1];

            format.appendChild(option);
        });

        /*
         * Keep the current editor selection when clicking
         * the format dropdown.
         */
        format.addEventListener('mousedown', function () {
            // Do not prevent default because select still needs to open.
        });

        format.addEventListener('change', function () {
            focusEditor(editor);

            document.execCommand(
                'formatBlock',
                false,
                '<' + format.value + '>'
            );

            syncEditor(editor, textarea);
        });

        toolbar.appendChild(format);

        /* ---------------------------------------------------------
           LINK
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('Link', 'Insert Link', function () {
                const url = window.prompt('Enter link URL');

                if (!url) {
                    return;
                }

                execute(
                    editor,
                    textarea,
                    'createLink',
                    url.trim()
                );
            })
        );

        /* ---------------------------------------------------------
           UNLINK
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('Unlink', 'Remove Link', function () {
                execute(editor, textarea, 'unlink');
            })
        );

        /* ---------------------------------------------------------
           CLEAR FORMATTING
        --------------------------------------------------------- */

        toolbar.appendChild(
            createButton('Clear', 'Clear Formatting', function () {
                execute(editor, textarea, 'removeFormat');
            })
        );

        /* ---------------------------------------------------------
           SYNCHRONIZATION
        --------------------------------------------------------- */

        function sync() {
            syncEditor(editor, textarea);
        }

        editor.addEventListener('input', sync);
        editor.addEventListener('blur', sync);
        editor.addEventListener('keyup', sync);
        editor.addEventListener('paste', function () {
            /*
             * Browser updates the content after the paste event,
             * therefore sync on the next event loop.
             */
            setTimeout(sync, 0);
        });

        /* ---------------------------------------------------------
           FORM SUBMISSION
        --------------------------------------------------------- */

        const form = textarea.closest('form');

        if (form) {
            form.addEventListener('submit', function () {
                sync();
            });
        }

        /* ---------------------------------------------------------
           BUILD EDITOR
        --------------------------------------------------------- */

        textarea.style.display = 'none';

        textarea.parentNode.insertBefore(wrap, textarea);

        wrap.appendChild(toolbar);
        wrap.appendChild(editor);

        /*
         * Keep the original Django textarea inside the wrapper.
         * Django still receives the original model field normally.
         */
        wrap.appendChild(textarea);
    }

    function boot(root) {
        const scope = root || document;

        if (
            scope.matches &&
            scope.matches(FIELD_SELECTOR)
        ) {
            init(scope);
        }

        scope
            .querySelectorAll(FIELD_SELECTOR)
            .forEach(init);
    }

    document.addEventListener('DOMContentLoaded', function () {
        boot(document);
    });

    /*
     * Django admin inline/formset support.
     */
    document.addEventListener('formset:added', function (event) {
        boot(event.target || document);
    });

})();