ZENVIBE UI / ADMIN FIELD ALIGNMENT

Replace these files in your project:
1. designer/views.py
2. designer/admin.py
3. templates/designer/choose_design.html

Then restart Django and press Ctrl+F5.

NO DATABASE RESET. NO MIGRATION. NO DRY RUN.

What this patch does:
- UI reads product name, short description, description, product information, printing guidelines and FAQs from DB/Admin.
- Blank Description/Printing Guidelines/Information/FAQ tabs are hidden automatically.
- Size controls appear only when active size variants exist.
- Colour swatches appear only when active colour variants exist.
- Arbitrary source_attributes such as Material, Printed Sides and Printing Method appear as selectors automatically.
- Quantity tiers show proper ranges (50-99, 100-249, 500+).
- Current unit price changes when quantity moves into a different tier.
- Minimum and optional maximum quantity are enforced/displayed.
- Existing editor/template/ruler/print-area data is untouched.

This is FIELD/UI ALIGNMENT ONLY. Populate ZenVibe.ca data after this structure is confirmed.
