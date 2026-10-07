"""
Populate the shop with dummy products and generate placeholder images via Pillow.
Usage: python manage.py populate_shop
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.core.management.base import BaseCommand
from store.models import ShowcaseProduct

# Colour palettes per category (bg, accent)
PALETTES = {
    'essential': [('#26343a', '#c4a57b'), ('#354044', '#d4b48a'), ('#263b37', '#e0c9a0')],
    'graphic':   [('#352d39', '#d7ad78'), ('#2b3647', '#d0b888'), ('#40312c', '#c8a868')],
    'polo':      [('#29383a', '#c4a57b'), ('#3b3530', '#d0b070'), ('#273943', '#a8d0b8')],
    'oversized': [('#343038', '#c4a57b'), ('#29383a', '#b8a080'), ('#42343a', '#d0a8a0')],
    'limited':   [('#292f3e', '#d4b48a'), ('#3c302b', '#e0c9a0'), ('#2c3c39', '#c8a868')],
}

PRODUCTS = [
    {'name': 'The Essential Tee - Chalk',       'category': 'essential', 'price': 1890, 'discount': 0},
    {'name': 'Pima Cotton Tee - Ivory',          'category': 'essential', 'price': 2290, 'discount': 10},
    {'name': 'Everyday Crew Tee - Moss',         'category': 'essential', 'price': 1990, 'discount': 0},
    {'name': 'Studio Mark Tee - Black',          'category': 'graphic',   'price': 2490, 'discount': 0},
    {'name': 'After Hours Graphic Tee',          'category': 'graphic',   'price': 2890, 'discount': 10},
    {'name': 'Archive Print Tee - Ecru',         'category': 'graphic',   'price': 2690, 'discount': 0},
    {'name': 'Signature Pique Polo - Navy',      'category': 'polo',      'price': 3290, 'discount': 0},
    {'name': 'Cotton Polo - Soft White',          'category': 'polo',      'price': 3190, 'discount': 10},
    {'name': 'Mercerised Polo - Forest',          'category': 'polo',      'price': 3590, 'discount': 0},
    {'name': 'Relaxed Box Tee - Slate',           'category': 'oversized', 'price': 2490, 'discount': 0},
    {'name': 'Heavyweight Oversized Tee',         'category': 'oversized', 'price': 2990, 'discount': 10},
    {'name': 'Drop Shoulder Tee - Clay',          'category': 'oversized', 'price': 2790, 'discount': 0},
    {'name': 'Atelier No. 01 - Limited Tee',       'category': 'limited',   'price': 4290, 'discount': 0},
    {'name': 'Hand-Finished Monogram Tee',         'category': 'limited',   'price': 4590, 'discount': 10},
    {'name': 'Season One Artist Tee',              'category': 'limited',   'price': 3990, 'discount': 0},
]


def make_placeholder(media_dir, filename, label, category, w=600, h=800):
    """Generate an elegant placeholder image."""
    palette = PALETTES.get(category, PALETTES['essential'])
    idx = hash(filename) % len(palette)
    bg, accent = palette[idx]
    img = Image.new('RGB', (w, h), bg)
    draw = ImageDraw.Draw(img)

    accent_rgb = tuple(int(accent.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
    light = tuple(min(c + 40, 255) for c in accent_rgb)

    for i in range(3):
        offset = 20 + i * 8
        draw.rectangle([offset, offset, w - offset, h - offset],
                       outline=(*accent_rgb, 60), width=1)

    cx, cy = w // 2, h // 2 - 30
    shirt = [
        (cx - 26, cy - 105), (cx - 75, cy - 95), (cx - 145, cy - 52),
        (cx - 105, cy + 20), (cx - 74, cy + 2), (cx - 74, cy + 118),
        (cx + 74, cy + 118), (cx + 74, cy + 2), (cx + 105, cy + 20),
        (cx + 145, cy - 52), (cx + 75, cy - 95), (cx + 26, cy - 105),
    ]
    draw.polygon(shirt, outline=light, fill=accent_rgb)
    draw.ellipse((cx - 27, cy - 117, cx + 27, cy - 78), fill=bg)
    draw.arc((cx - 27, cy - 117, cx + 27, cy - 78), 0, 180, fill=light, width=2)
    draw.line([(cx - 120, cy - 18), (cx - 105, cy + 8)], fill=light, width=2)
    draw.line([(cx + 120, cy - 18), (cx + 105, cy + 8)], fill=light, width=2)

    try:
        font_sm = ImageFont.truetype("arial.ttf", 14)
        font_lg = ImageFont.truetype("arial.ttf", 20)
    except OSError:
        font_sm = ImageFont.load_default()
        font_lg = font_sm

    cat_text = category.upper()
    cat_bbox = draw.textbbox((0, 0), cat_text, font=font_sm)
    cat_w = cat_bbox[2] - cat_bbox[0]
    draw.text(((w - cat_w) // 2, cy + 145), cat_text, fill=accent_rgb, font=font_sm)

    words = label.split()
    line1 = ' '.join(words[:3])
    line2 = ' '.join(words[3:]) if len(words) > 3 else ''
    bbox1 = draw.textbbox((0, 0), line1, font=font_lg)
    draw.text(((w - (bbox1[2] - bbox1[0])) // 2, cy + 175), line1, fill=light, font=font_lg)
    if line2:
        bbox2 = draw.textbbox((0, 0), line2, font=font_lg)
        draw.text(((w - (bbox2[2] - bbox2[0])) // 2, cy + 203), line2, fill=light, font=font_lg)

    wm = 'Nowhence Clothings'
    wm_bbox = draw.textbbox((0, 0), wm, font=font_sm)
    draw.text(((w - (wm_bbox[2] - wm_bbox[0])) // 2, h - 50), wm, fill=(*accent_rgb, 80), font=font_sm)

    path = media_dir / filename
    img.save(path, 'JPEG', quality=90)
    return f'showcase/{filename}'


class Command(BaseCommand):
    help = 'Populate the shop with dummy products and placeholder images.'

    def handle(self, *args, **options):
        media_dir = Path(settings.MEDIA_ROOT) / 'showcase'
        media_dir.mkdir(parents=True, exist_ok=True)

        ShowcaseProduct.objects.all().delete()
        self.stdout.write('Cleared existing showcase products.')

        for i, p in enumerate(PRODUCTS):
            filename = f"product_{i + 1}.jpg"
            rel_path = make_placeholder(media_dir, filename, p['name'], p['category'])
            disc_price = round(p['price'] * (1 - p['discount'] / 100), 2) if p['discount'] > 0 else None
            ShowcaseProduct.objects.create(
                name=p['name'],
                category=p['category'],
                price=p['price'],
                discount_percent=p['discount'],
                discounted_price=disc_price,
                image=rel_path,
                display_order=i,
                is_active=True,
            )
            self.stdout.write(f"  ✓ {p['name']} ({p['category']})")

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! {ShowcaseProduct.objects.count()} products created.'
        ))
