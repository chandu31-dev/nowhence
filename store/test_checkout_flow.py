import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import Order, OrderItem, ShowcaseProduct


class CustomerCheckoutFlowTests(TestCase):
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_login_checkout_order_persistence_inventory_and_receipt(self):
        user = User.objects.create_user(
            username='order-customer',
            email='order-customer@example.com',
            password='order-test-password',
        )
        product = ShowcaseProduct.objects.create(
            name='Order Journey Tee',
            slug='order-journey-tee',
            price=Decimal('899.00'),
            image='showcase/order-journey-flow.gif',
            stock_quantity=3,
        )
        payload = {
            'items': [{
                'name': product.name,
                'slug': product.slug,
                'price': 899.0,
                'quantity': 1,
                'image': '',
                'size': 'M',
            }],
            'email': 'receipt@example.com',
            'save_address': False,
            'payment_method': 'cod',
            'coupon_code': '',
            'discount_amount': 0,
            'shipping': {
                'full_name': 'Order Customer',
                'phone': '9999999999',
                'address_line1': '123 Market Road',
                'city': 'Hyderabad',
                'state': 'Telangana',
                'pincode': '500001',
            },
        }

        unauthorized = self.client.post(
            reverse('place_order'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(Order.objects.count(), 0)

        invalid_login = self.client.post(
            reverse('checkout_login'),
            {'username': user.username, 'password': 'wrong-password'},
        )
        self.assertFalse(invalid_login.json()['ok'])

        valid_login = self.client.post(
            reverse('checkout_login'),
            {'username': user.username, 'password': 'order-test-password'},
        )
        self.assertTrue(valid_login.json()['ok'])

        placed = self.client.post(
            reverse('place_order'),
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(placed.status_code, 200)
        self.assertTrue(placed.json()['ok'])

        order = Order.objects.get(order_number=placed.json()['order_number'])
        item = OrderItem.objects.get(order=order)
        self.assertEqual(order.customer_email, 'receipt@example.com')
        self.assertEqual(item.product, product)
        self.assertEqual(item.quantity, 1)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['receipt@example.com'])
        self.assertIn(order.order_number, mail.outbox[0].subject)
