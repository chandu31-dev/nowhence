from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from store.models import ShowcaseProduct


class CustomerBrowseFlowTests(TestCase):
    def test_customer_browses_catalog_and_product_details(self):
        product = ShowcaseProduct.objects.create(
            name='Journey Tee',
            slug='journey-tee',
            price=Decimal('899.00'),
            image='showcase/journey-flow.gif',
            stock_quantity=4,
        )

        home = self.client.get(reverse('home'))
        shop = self.client.get(reverse('shop'))
        detail = self.client.get(reverse('product_detail', args=[product.slug]))

        self.assertEqual(home.status_code, 200)
        self.assertEqual(shop.status_code, 200)
        self.assertContains(shop, product.name)
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, product.name)

        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 4)
