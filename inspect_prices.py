from designer.models import Product

ids = [391, 411, 413]

for pid in ids:
    p = Product.objects.get(id=pid)

    print()
    print("=" * 80)
    print("PRODUCT:", p.id, "|", p.name)
    print("BASE:", p.price)
    print("RANGE:", p.min_price, "-", p.max_price)

    for rel in p._meta.related_objects:
        accessor = rel.get_accessor_name()

        try:
            rows = list(getattr(p, accessor).all())
        except Exception:
            continue

        if not rows:
            continue

        print()
        print("RELATION:", accessor, "|", rel.related_model.__name__)

        for row in rows[:30]:
            values = {}

            for field in row._meta.fields:
                name = field.name

                if any(
                    key in name.lower()
                    for key in [
                        "price",
                        "quantity",
                        "qty",
                        "size",
                        "variant",
                        "name",
                    ]
                ):
                    try:
                        values[name] = getattr(row, name)
                    except Exception:
                        pass

            print(row.pk, values)
