# ZenVibe Corporate Gifts

ZenVibe storefront and administration portal for ZenVibe Corporate Gifts.

## Local setup

1. Create and activate a Python virtual environment.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Run `python manage.py migrate`.
4. Run `python manage.py seed_demo` when demo catalogue data is required.
5. Create an administrator with `python manage.py createsuperuser`.
6. Start the site with `python manage.py runserver`.

## Main areas

- Customer storefront and product catalogue
- Product customizers and editable design templates
- Orders, customers, blog and chatbot administration
- ZenVibe-branded ZenVibe Admin using the bundled Multikart assets
- Responsive admin list filters rendered as dropdowns beside search
- Optional light/dark mode in the admin header

Run commands from the directory containing `manage.py`. Included migrations are ready to apply.
