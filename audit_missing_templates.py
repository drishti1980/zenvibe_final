from designer.models import Category, Product
from django.db.models import Count, Q

categories = list(Category.objects.all())

keywords = (
    "promotional products",
    "banners & displays",
    "marketing materials",
)

selected = {
    c.id for c in categories
    if any(k in c.name.lower() for k in keywords)
}

while True:
    new_ids = {
        c.id for c in categories
        if c.parent_id in selected
    }

    if new_ids.issubset(selected):
        break

    selected.update(new_ids)

products = (
    Product.objects
    .filter(category_id__in=selected, is_active=True)
    .select_related("category")
    .annotate(
        template_count=Count(
            "templates",
            filter=Q(templates__is_active=True)
        )
    )
    .order_by("category__name", "name")
)

missing = [p for p in products if p.template_count < 100]

print("\nID | CATEGORY | PRODUCT | EXISTING | MISSING")
print("-" * 100)

for p in missing:
    print(
        f"{p.id} | {p.category.name} | {p.name} | "
        f"{p.template_count} | {100 - p.template_count}"
    )

print("\nTotal products checked:", products.count())
print("Products requiring templates:", len(missing))
print(
    "Total additional templates needed:",
    sum(100 - p.template_count for p in missing)
)
