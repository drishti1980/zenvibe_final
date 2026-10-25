"""Import selected Our Work images from the supplied 2026.zip into admin-managed blocks.

Usage: python manage.py seed_our_work --zip "C:\\path\\to\\2026.zip"
Only imports a small explicit allowlist; never extracts the entire archive.
Images are saved via PageContentBlock.image to media/page-content/our-work/.\nExisting content is preserved unless --replace is supplied.
"""
import hashlib
from pathlib import Path
from zipfile import ZipFile

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from designer.models import PageContentBlock

BLOCKS = [
    ("hero", "OUR WORKS", "Explore our recent work in apparel, banners, promotional products, awards, and more.", "our-works-hero-image.webp", 0),
    ("banners-heading", "BANNERS & DISPLAYS", "", None, 10),
    ("banners-image-01", "", "", "Banners_displays_ZenVibe.webp", 11),
    ("banners-image-02", "", "", "Banners-Display-Post.webp", 12),
    ("banners-image-03", "", "", "Custom-Roll-Up-Banners.webp", 13),
    ("banners-image-04", "", "", "Banners-Displays.webp", 14),
    ("promotional-heading", "PROMOTIONAL PRODUCTS", "", None, 20),
    ("promotional-image-01", "", "", "20oz-Stainless-Steel-Tumbler.webp", 21),
    ("promotional-image-02", "", "", "corporate-gift-set-1.png", 22),
    ("promotional-image-03", "", "", "Premium-Executive-Gift-Set-e1779996317242.webp", 23),
    ("promotional-image-04", "", "", "Custom-Apparel.webp", 24),
    ("corporate-heading", "CORPORATE GIFT SETS", "", None, 30),
    ("corporate-image-01", "", "", "corporate-gift-set-canada.webp", 31),
    ("corporate-image-02", "", "", "executive-office-black-gift-set.jpg", 32),
    ("corporate-image-03", "", "", "Premium-Corporate-Gift-Set.jpg", 33),
    ("corporate-image-04", "", "", "Customized-Bamboo-Corporate-Gift-Set.png", 34),
    ("awards-heading", "AWARDS", "", None, 40),
    ("awards-image-01", "", "", "Crystal-Award-e1779991079248.webp", 41),
    ("awards-image-02", "", "", "EDCL-Award-e1781543269563.webp", 42),
    ("awards-image-03", "", "", "Purple-Mirror-Finishing-Award.webp", 43),
    ("awards-image-04", "", "", "Custom-Awards.webp", 44),
    ("marketing-heading", "MARKETING MATERIALS", "", None, 50),
    ("marketing-image-01", "", "", "Free-Mockup-for-our-works.webp", 51),
    ("marketing-image-02", "", "", "Bulk-Discount-for-our-works.webp", 52),
    ("marketing-image-03", "", "", "metal-ballpoint-pen.jpg", 53),
    ("apparel-heading", "CUSTOM APPAREL", "", None, 60),
    ("apparel-image-01", "", "", "Custom-Apparel-canada.webp", 61),
    ("apparel-image-02", "", "", "Apparel-.webp", 62),
    ("apparel-image-03", "", "", "custom-apparel-for-small-businesses-brand-recognition.webp", 63),
    ("apparel-image-04", "", "", "Custom-Apparel-image-box.webp", 64),
]


class Command(BaseCommand):
    help = "Seed Our Work content from selected images in 2026.zip without changing other pages."

    def add_arguments(self, parser):
        parser.add_argument("--zip", required=True, help="Path to 2026.zip")
        parser.add_argument("--replace", action="store_true", help="Update existing blocks and images")
        parser.add_argument("--sync-images", action="store_true", help="Update only reference images; preserve admin-edited text, links and ordering")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        source = Path(options["zip"])
        if not source.is_file():
            raise CommandError(f"Archive not found: {source}")
        with ZipFile(source) as archive:
            files = {Path(name).name: name for name in archive.namelist()
                     if name.startswith("2026/") and not name.endswith("/")}
            missing = [filename for _, _, _, filename, _ in BLOCKS if filename and filename not in files]
            if missing:
                raise CommandError("Reference images missing from archive: " + ", ".join(missing))
            for key, heading, body, filename, order in BLOCKS:
                existing = PageContentBlock.objects.filter(page="our_work", section_key=key).first()
                if existing and not (options["replace"] or (options["sync_images"] and filename)):
                    self.stdout.write(f"Preserved existing: {key}")
                    continue
                if options["dry_run"]:
                    self.stdout.write(f"Would seed {key}: {filename or 'text only'}")
                    continue
                block = existing or PageContentBlock(page="our_work", section_key=key)
                if not existing or options["replace"]:
                    block.heading = heading
                    block.body = body
                    block.sort_order = order
                    block.is_active = True
                if filename and filename in files:
                    entry = archive.getinfo(files[filename])
                    if entry.file_size > 12 * 1024 * 1024:
                        raise CommandError(f"Image exceeds 12 MB: {filename}")
                    data = archive.read(files[filename])
                    # Avoid duplicate media files when the exact reference image is already installed.
                    same_image = False
                    if block.image:
                        try:
                            with block.image.open("rb") as previous:
                                same_image = hashlib.sha256(previous.read()).digest() == hashlib.sha256(data).digest()
                        except (OSError, ValueError):
                            pass
                    if not same_image:
                        block.image.save(f"our-work/{filename}", ContentFile(data), save=False)
                block.save()
                self.stdout.write(self.style.SUCCESS(f"Ready: {key}"))
        self.stdout.write(self.style.SUCCESS("Our Work content import complete."))
