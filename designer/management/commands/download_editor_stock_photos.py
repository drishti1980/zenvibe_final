"""Download local stock photos for the Zenvibe editor.

Usage:
  python manage.py download_editor_stock_photos
  python manage.py download_editor_stock_photos --replace

All resulting JPGs live in designer/static/designer/img/stock/.
Sources: Unsplash image CDN (where configured), Wikimedia Commons fallback.
Review individual image licenses and visual suitability before commercial publishing.
"""
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import time

from django.conf import settings
from django.core.management.base import BaseCommand

PHOTOS = [['sunflower.jpg','photo-1597848212624-e6e0a38a6e99','sunflower flower field'],['daisy.jpg','photo-1490750967868-88aa4486c946','white daisy flower meadow'],['cherry-blossom.jpg','photo-1522383225653-ed111181a951','cherry blossom'],['lotus.jpg','photo-1497250681960-ef046c08a56e','pink lotus flower'],['ocean-beach.jpg','photo-1507525428034-b723cf961d3e','ocean beach'],['sunset-sea.jpg','photo-1472120435266-53107fd0c44a','sunset sea'],['tropical-beach.jpg','photo-1514282401047-d79a71a590e8','tropical beach'],['underwater.jpg','photo-1544551763-46a013bb70d5','underwater'],['green-forest.jpg','photo-1448375240586-882707db888b','green forest'],['autumn-leaves.jpg','photo-1473448912268-2022ce9509d8','autumn leaves'],['snow-mountains.jpg','photo-1464822759023-fed622ff2c3b','snow mountains'],['blue-sky.jpg','photo-1534088568595-a066f410bcda','blue sky'],['tulip-garden.jpg','photo-1490750967868-88aa4486c946','pink tulip garden'],['jasmine.jpg','photo-1468327768560-75b778cbb551','white jasmine flower'],['misty-lake.jpg','photo-1501785888041-af3ef285b470','misty lake'],['red-roses.jpg','','red roses flower'],['white-roses.jpg','','white rose flower'],['peony-garden.jpg','','pink peony flowers'],['orchid-flowers.jpg','','orchid flower'],['hibiscus.jpg','','hibiscus flower'],['marigold.jpg','','marigold flowers'],['wildflowers.jpg','','wildflower meadow'],['waterfall.jpg','','waterfall nature'],['river-stream.jpg','','forest river stream'],['rainforest.jpg','','tropical rainforest'],['pine-trees.jpg','','pine forest'],['desert-dunes.jpg','','sand dunes desert'],['coral-reef.jpg','','coral reef underwater'],['sea-waves.jpg','','ocean waves'],['rocky-coast.jpg','','rocky ocean coast'],['countryside.jpg','','green countryside hills'],['wheat-field.jpg','','golden wheat field'],['bamboo-forest.jpg','','bamboo forest'],['northern-lights.jpg','','aurora borealis'],['starry-sky.jpg','','milky way stars']]
USER_AGENT = 'ZenVibePhotoImporter/1.1 (editor asset download; Wikimedia Commons)'


def fetch(url, timeout=22):
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'image/*,application/json;q=0.9'})
    with urlopen(request, timeout=timeout) as response:
        data = response.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise ValueError('File exceeds 10 MB')
        return data


def commons_candidates(query):
    params = urlencode({
        'action': 'query', 'generator': 'search', 'gsrsearch': 'filetype:bitmap ' + query,
        'gsrnamespace': 6, 'gsrlimit': 12, 'prop': 'imageinfo',
        'iiprop': 'url|mime|extmetadata', 'iiurlwidth': 1200, 'format': 'json',
    })
    payload = json.loads(fetch('https://commons.wikimedia.org/w/api.php?' + params).decode('utf-8'))
    pages = payload.get('query', {}).get('pages', {})
    results = []
    for page in sorted(pages.values(), key=lambda item: item.get('index', 999)):
        for info in page.get('imageinfo', []):
            mime = info.get('mime', '')
            if mime in ('image/jpeg', 'image/png', 'image/webp'):
                url = info.get('thumburl') or info.get('url')
                if url:
                    results.append((url, page.get('title', '')))
    return results


def as_jpeg(data):
    from PIL import Image, ImageOps
    with Image.open(BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image)
        if image.width < 250 or image.height < 180:
            raise ValueError('Image resolution too small')
        image.thumbnail((1400, 1400))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        out = BytesIO()
        image.save(out, format='JPEG', quality=86, optimize=True)
        return out.getvalue()


class Command(BaseCommand):
    help = 'Download editor stock photos locally; retry missing Unsplash photos via Wikimedia Commons'

    def add_arguments(self, parser):
        parser.add_argument('--replace', action='store_true', help='Re-download existing photos')

    def handle(self, *args, **options):
        root = Path(settings.BASE_DIR) / 'designer' / 'static' / 'designer' / 'img' / 'stock'
        root.mkdir(parents=True, exist_ok=True)
        successful, failed = 0, []
        for filename, unsplash_id, query in PHOTOS:
            target = root / filename
            if target.exists() and not options['replace']:
                self.stdout.write('Already exists: ' + filename)
                continue
            candidates = []
            if unsplash_id and filename != 'sunflower.jpg':
                candidates.append(('Unsplash', 'https://images.unsplash.com/' + unsplash_id + '?fit=crop&w=1200&q=82&fm=jpg'))
            try:
                candidates.extend(('Wikimedia Commons: ' + title, url) for url, title in commons_candidates(query))
            except Exception as exc:
                self.stderr.write('Wikimedia lookup failed for ' + filename + ': ' + str(exc))
            if unsplash_id and filename == 'sunflower.jpg':
                candidates.append(('Unsplash', 'https://images.unsplash.com/' + unsplash_id + '?fit=crop&w=1200&q=82&fm=jpg'))
            downloaded = False
            for source, url in candidates[:9]:
                try:
                    data = as_jpeg(fetch(url))
                    temporary = target.with_suffix('.jpg.tmp')
                    temporary.write_bytes(data)
                    temporary.replace(target)
                    self.stdout.write(self.style.SUCCESS('Saved ' + filename + ' (' + source + ')'))
                    successful += 1
                    downloaded = True
                    break
                except Exception:
                    continue
            if not downloaded:
                failed.append(filename)
                self.stderr.write(self.style.ERROR('Could not download: ' + filename))
            time.sleep(0.12)
        self.stdout.write('Downloaded: %s; missing: %s' % (successful, len(failed)))
        if failed:
            self.stderr.write('Missing files: ' + ', '.join(failed))
            self.stderr.write('Run again later, or manually save appropriately licensed JPGs under the exact filenames.')
        self.stdout.write('Image files are stored locally. Review licensing/attribution before publication.')
