"""
Generate dummy gallery images for each ShowcaseProduct.
Creates 3 extra views per product: Back View, Detail View, Close-up.
Usage: python manage.py generate_gallery
"""

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from store.models import ShowcaseProduct, ProductImage

PALETTES = {
    'essential': [
        {'bg': (38, 52, 58), 'accent': (196, 165, 123)},
        {'bg': (53, 64, 68), 'accent': (212, 180, 138)},
        {'bg': (38, 59, 55), 'accent': (224, 201, 160)},
    ],
    'graphic': [
        {'bg': (53, 45, 57), 'accent': (215, 173, 120)},
        {'bg': (43, 54, 71), 'accent': (208, 184, 136)},
        {'bg': (64, 49, 44), 'accent': (200, 168, 104)},
    ],
    'polo': [
        {'bg': (41, 56, 58), 'accent': (196, 165, 123)},
        {'bg': (59, 53, 48), 'accent': (208, 176, 112)},
        {'bg': (39, 57, 67), 'accent': (168, 208, 184)},
    ],
    'oversized': [
        {'bg': (52, 48, 56), 'accent': (196, 165, 123)},
        {'bg': (41, 56, 58), 'accent': (184, 160, 128)},
        {'bg': (66, 52, 58), 'accent': (208, 168, 160)},
    ],
    'limited': [
        {'bg': (41, 47, 62), 'accent': (212, 180, 138)},
        {'bg': (60, 48, 43), 'accent': (224, 201, 160)},
        {'bg': (44, 60, 57), 'accent': (200, 168, 104)},
    ],
}

VIEW_LABELS = ['Back View', 'Detail View', 'Close-up']


def create_gallery_image(product_name, view_label, bg_color, accent_color, width=600, height=800):
    """Create a styled placeholder gallery image."""
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    for i in range(-height, width + height, 40):
        draw.line([(i, 0), (i + height, height)], fill=accent_color, width=1)

    cx, cy = width // 2, height // 2
    shirt = [
        (cx - 26, cy - 120), (cx - 78, cy - 108), (cx - 158, cy - 58),
        (cx - 112, cy + 22), (cx - 78, cy + 2), (cx - 78, cy + 138),
        (cx + 78, cy + 138), (cx + 78, cy + 2), (cx + 112, cy + 22),
        (cx + 158, cy - 58), (cx + 78, cy - 108), (cx + 26, cy - 120),
    ]
    draw.polygon(shirt, fill=accent_color, outline=(255, 255, 255))
    draw.ellipse((cx - 28, cy - 132, cx + 28, cy - 88), fill=bg_color)
    draw.arc((cx - 28, cy - 132, cx + 28, cy - 88), 0, 180, fill=(255, 255, 255), width=2)

    try:
        font_large = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except (OSError, IOError):
        font_large = ImageFont.load_default()
        font_small = font_large

    bbox = draw.textbbox((0, 0), view_label, font=font_large)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 50), view_label, fill=(255, 255, 255), font=font_large)

    short_name = product_name[:30]
    bbox2 = draw.textbbox((0, 0), short_name, font=font_small)
    tw2 = bbox2[2] - bbox2[0]
    draw.text(((width - tw2) // 2, height - 60), short_name, fill=(255, 255, 255), font=font_small)

    draw.rectangle([(10, 10), (width - 11, height - 11)], outline=(255, 255, 255, 128), width=2)

    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return buffer


class Command(BaseCommand):
    help = 'Generate dummy gallery images for each ShowcaseProduct.'

    def handle(self, *args, **options):
        products = ShowcaseProduct.objects.filter(is_active=True)
        total_created = 0

        for product in products:
            existing = product.images.count()
            if existing > 0:
                self.stdout.write(f'  ⏭ {product.name} — already has {existing} gallery images, skipping')
                continue

            palette = PALETTES.get(product.category, PALETTES['essential'])

            for idx, (view_label, colors) in enumerate(zip(VIEW_LABELS, palette)):
                img_buffer = create_gallery_image(
                    product.name,
                    view_label,
                    colors['bg'],
                    colors['accent'],
                )
                filename = f"{product.slug}-{view_label.lower().replace(' ', '-')}.jpg"

                gallery_img = ProductImage(
                    product=product,
                    alt_text=f'{product.name} — {view_label}',
                    display_order=idx + 1,
                )
                gallery_img.image.save(filename, ContentFile(img_buffer.read()), save=True)
                total_created += 1

            self.stdout.write(f'  ✓ {product.name} — 3 gallery images created')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {total_created} gallery images for {products.count()} products.'
        ))
