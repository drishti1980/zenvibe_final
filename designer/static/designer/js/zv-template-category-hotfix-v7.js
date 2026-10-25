
(function () {
    "use strict";

    const norm = value =>
        String(value || "")
            .trim()
            .toLowerCase()
            .replace(/\s+/g, " ");

    function removeBadUI() {

        /*
         * Remove the visible blue dotted print/edit area.
         * Actual editor dimensions/ruler configuration remains intact.
         */
        document.querySelectorAll(
            ".zv-live-print-area," +
            ".zv-print-area-overlay," +
            ".editable-print-area"
        ).forEach(el => el.remove());


        /*
         * Remove generic template filters everywhere.
         */
        document.querySelectorAll(
            ".template-category-chips," +
            ".template-filters," +
            ".template-filter-chips," +
            ".template-chip-row," +
            "[data-template-filter]"
        ).forEach(el => el.remove());


        /*
         * Remove Corporate / Creative / Minimal / Luxury buttons
         * even if generated dynamically.
         */
        document.querySelectorAll(
            "button,.chip,.filter-chip,.template-chip"
        ).forEach(el => {

            const text = norm(el.textContent);

            if (
                text === "corporate" ||
                text === "creative" ||
                text === "minimal" ||
                text === "luxury"
            ) {
                el.remove();
            }
        });


        /*
         * Remove:
         *
         * This template doesn't have editable text yet
         * Add text
         *
         * wherever it appears.
         */
        document.querySelectorAll(
            ".template-card," +
            ".design-card," +
            ".template-item," +
            ".template-tile," +
            ".template-preview-card"
        ).forEach(el => {

            const text = norm(el.textContent);

            if (
                text.includes(
                    "this template doesn't have editable text yet"
                ) ||
                text.includes(
                    "this template doesn’t have editable text yet"
                )
            ) {
                el.remove();
            }
        });
    }


    function getSelectedSize() {

        const sizeSelect = document.querySelector(
            "#sizeSelect," +
            "#zvProductSize," +
            "#productSize," +
            '[name="size"],' +
            '[name="size_key"]'
        );

        if (sizeSelect && sizeSelect.value) {
            return norm(sizeSelect.value);
        }

        if (
            window.ZV_EDITOR_PROFILE &&
            window.ZV_EDITOR_PROFILE.sizeKey
        ) {
            return norm(
                window.ZV_EDITOR_PROFILE.sizeKey
            );
        }

        return "";
    }


    function isolateTemplates() {

        if (!Array.isArray(window.TEMPLATE_CATALOG)) {
            return;
        }

        const currentProductId =
            String(
                window.PRODUCT &&
                window.PRODUCT.id || ""
            );

        const currentCategory =
            norm(
                window.PRODUCT &&
                window.PRODUCT.category ||
                window.ZV_PRODUCT_CATEGORY ||
                ""
            );

        const currentSize = getSelectedSize();


        window.TEMPLATE_CATALOG =
            window.TEMPLATE_CATALOG.filter(template => {

                /*
                 * PRODUCT
                 */
                const templateProduct =
                    String(
                        template.product_id ||
                        template.productId ||
                        ""
                    );

                if (
                    templateProduct &&
                    currentProductId &&
                    templateProduct !== currentProductId
                ) {
                    return false;
                }


                /*
                 * CATEGORY
                 */
                const templateCategory =
                    norm(
                        template.category ||
                        template.category_name ||
                        ""
                    );

                if (
                    templateCategory &&
                    currentCategory &&
                    templateCategory !== currentCategory
                ) {
                    return false;
                }


                /*
                 * SIZE
                 */
                const templateSize =
                    norm(
                        template.size_key ||
                        template.sizeKey ||
                        (
                            template.json_data &&
                            template.json_data.sizeKey
                        ) ||
                        ""
                    );

                if (
                    templateSize &&
                    currentSize &&
                    templateSize !== currentSize
                ) {
                    return false;
                }

                return true;
            });
    }


    function runFix() {
        isolateTemplates();
        removeBadUI();
    }


    if (document.readyState === "loading") {

        document.addEventListener(
            "DOMContentLoaded",
            () => setTimeout(runFix, 0)
        );

    } else {

        setTimeout(runFix, 0);
    }


    /*
     * Editor dynamically rebuilds the template rail.
     * Therefore remove bad controls/cards again whenever
     * the DOM changes.
     */
    const observer = new MutationObserver(() => {
        removeBadUI();
    });

    observer.observe(
        document.documentElement,
        {
            childList: true,
            subtree: true
        }
    );


    /*
     * Re-filter when product size changes.
     */
    document.addEventListener(
        "change",
        event => {

            if (!event.target) {
                return;
            }

            const identity =
                (
                    (event.target.id || "") +
                    " " +
                    (event.target.name || "")
                ).toLowerCase();

            if (identity.includes("size")) {
                setTimeout(runFix, 0);
            }
        }
    );

})();
