"""
Update existing showcase products with descriptions, sizes, fabric, and slugs.
Usage: python manage.py update_products
"""

from django.core.management.base import BaseCommand
from store.models import ShowcaseProduct

PRODUCT_DETAILS = {
    'essential': {
        'description': 'A refined everyday T-shirt cut from exceptionally soft, breathable cotton jersey. Finished with a clean crew neck, considered proportions, and a smooth hand feel that improves with wear.',
        'fabric': 'Premium combed cotton jersey, 220 GSM',
        'sizes': 'XS,S,M,L,XL,XXL',
        'care': 'Machine wash cold inside out; line dry',
    },
    'graphic': {
        'description': 'A statement graphic T-shirt with a soft-touch print and a carefully balanced regular fit. Designed to hold its shape, feel easy against the skin, and bring a quiet point of view to everyday dressing.',
        'fabric': 'Compact cotton jersey, 240 GSM',
        'sizes': 'XS,S,M,L,XL,XXL',
        'care': 'Machine wash cold inside out; do not iron on print',
    },
    'polo': {
        'description': 'A polished polo made for everyday refinement, with a structured collar, tonal buttons, and a smooth finish. The breathable knit gives it an easy drape without losing its shape.',
        'fabric': 'Mercerised cotton pique',
        'sizes': 'XS,S,M,L,XL,XXL',
        'care': 'Machine wash cold; reshape and dry flat',
    },
    'oversized': {
        'description': 'A relaxed, generous silhouette with dropped shoulders and a substantial feel. Cut from premium heavyweight cotton for an effortless drape that works on its own or layered.',
        'fabric': 'Heavyweight organic cotton jersey, 280 GSM',
        'sizes': 'XS,S,M,L,XL,XXL',
        'care': 'Machine wash cold inside out; line dry',
    },
    'limited': {
        'description': 'A small-run T-shirt finished with elevated details and a considered, lasting fit. Made in limited quantities from premium cotton selected for its softness, durability, and rich surface.',
        'fabric': 'Long-staple cotton jersey, 240 GSM',
        'sizes': 'XS,S,M,L,XL,XXL',
        'care': 'Machine wash cold inside out; line dry',
    },
}


class Command(BaseCommand):
    help = 'Update existing showcase products with descriptions, sizes, fabric, and slugs.'

    def handle(self, *args, **options):
        updated = 0
        for product in ShowcaseProduct.objects.all():
            details = PRODUCT_DETAILS.get(product.category)
            if details:
                product.description = details['description']
                product.fabric = details['fabric']
                product.available_sizes = details['sizes']
                product.care_instructions = details['care']
                product.slug = ''  # Force slug regeneration
                product.save()
                updated += 1
                self.stdout.write(f'  ✓ Updated: {product.name}  →  /shop/{product.slug}/')

        self.stdout.write(self.style.SUCCESS(f'\nDone! Updated {updated} products.'))
