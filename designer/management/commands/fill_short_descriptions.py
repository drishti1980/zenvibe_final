import html
import re

from django.core.management.base import BaseCommand
from django.utils.html import strip_tags

from designer.models import Product


def clean_text(value):
    if not value:
        return ""

    text = strip_tags(value)
    text = html.unescape(text)

    # Normalize whitespace / NBSP
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()

    return text


def remove_title_prefix(text, product_name):
    """
    Many ZenVibe descriptions begin with the product name as a heading.
    Remove it so the short description starts with useful copy.
    """
    if not text or not product_name:
        return text

    name = clean_text(product_name)

    # Exact title at beginning
    if text.lower().startswith(name.lower()):
        text = text[len(name):].strip(" :-–—|")

    return text.strip()


def make_short_description(description, product_name, max_chars=320):
    text = clean_text(description)

    if not text:
        return ""

    text = remove_title_prefix(text, product_name)

    if not text:
        return ""

    # Get complete sentences.
    sentences = re.split(r"(?<=[.!?])\s+", text)

    selected = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        new_length = (
            current_length
            + len(sentence)
            + (1 if selected else 0)
        )

        # Prefer complete sentences rather than cutting words.
        if selected and new_length > max_chars:
            break

        # If first sentence itself is long, still keep the whole sentence.
        selected.append(sentence)
        current_length = new_length

        if current_length >= 180:
            break

    result = " ".join(selected).strip()

    # Absolute safety limit, but never chop through a word.
    if len(result) > 450:
        result = result[:450]
        result = result.rsplit(" ", 1)[0].rstrip(" ,;:-")
        result += "."

    return result


class Command(BaseCommand):
    help = "Populate missing ZenVibe product short descriptions from full descriptions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate existing short descriptions as well.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]

        products = Product.objects.all().order_by("id")

        updated = 0
        skipped = 0
        missing_description = 0

        for product in products:

            if product.short_description and not force:
                skipped += 1
                continue

            short = make_short_description(
                product.description,
                product.name,
            )

            if not short:
                missing_description += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"[{product.id}] No usable description: {product.name}"
                    )
                )
                continue

            self.stdout.write(
                f"\n[{product.id}] {product.name}\n"
                f"SHORT: {short}\n"
            )

            if not dry_run:
                product.short_description = short
                product.save(update_fields=["short_description"])

            updated += 1

        self.stdout.write("")
        self.stdout.write("=" * 60)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — database was NOT changed.")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Short descriptions updated successfully.")
            )

        self.stdout.write(f"Updated: {updated}")
        self.stdout.write(f"Already populated/skipped: {skipped}")
        self.stdout.write(
            f"Products without usable full description: {missing_description}"
        )