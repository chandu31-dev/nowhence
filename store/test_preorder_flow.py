import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from store.models import Coupon, Order, ProductVariant, ShowcaseProduct


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PreorderCheckoutFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='preorder-customer',
            email='preorder@example.com',
            password='preorder-test-password',
        )
        self.client.force_login(self.user)
        self.product = ShowcaseProduct.objects.create(
            name='Pre-order Tee',
            slug='preorder-tee',
            price=Decimal('8999.00'),
            image='showcase/preorder-tee.gif',
            stock_quantity=0,
            show_coming_soon=True,
            preorder_enabled=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Black',
            color_hex='#111111',
            stock_quantity=0,
        )

    def _payload(self, *, items=None, payment_method='razorpay', coupon_code=''):
        return {
            'items': items or [{
                'name': self.product.name,
                'slug': self.product.slug,
                'price': 1,
                'quantity': 1,
                'image': '',
                'size': 'M',
                'color': 'Black',
                'preorder': False,
            }],
            'email': 'receipt@example.com',
            'save_address': False,
            'payment_method': payment_method,
            'coupon_code': coupon_code,
            'discount_amount': 0,
            'shipping': {
                'full_name': 'Preorder Customer',
                'phone': '9999999999',
                'address_line1': '123 Market Road',
                'address_line2': '',
                'city': 'Delhi',
                'state': 'Delhi',
                'pincode': '110001',
            },
        }

    def _place_preorder(self, *, coupon_code=''):
        client = mock.Mock()
        client.order.create.return_value = {'id': 'order_test_123'}
        with override_settings(
            RAZORPAY_KEY_ID='test-key',
            RAZORPAY_KEY_SECRET='test-secret',
        ), mock.patch('razorpay.Client', return_value=client):
            response = self.client.post(
                reverse('place_order'),
                data=json.dumps(self._payload(coupon_code=coupon_code)),
                content_type='application/json',
            )
        return response, client

    def _verify_payment(self, order_number):
        client = mock.Mock()
        with mock.patch('razorpay.Client', return_value=client):
            response = self.client.post(
                reverse('verify_razorpay_payment'),
                data=json.dumps({
                    'razorpay_order_id': 'order_test_123',
                    'razorpay_payment_id': 'pay_test_123',
                    'razorpay_signature': 'test-signature',
                    'order_number': order_number,
                }),
                content_type='application/json',
            )
        return response, client

    def test_product_detail_offers_preorder_for_zero_stock_coming_soon_variant(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pre-order')
        self.assertContains(response, 'data-size="M"')
        self.assertContains(response, 'data-color="Black"')
        self.assertEqual(self.product.size_list, ['M'])
        self.assertEqual(self.product.color_options, [{'name': 'Black', 'hex': '#111111'}])

    def test_preorder_uses_fixed_advance_and_confirms_partial_payment(self):
        mail.outbox.clear()
        response, gateway = self._place_preorder()

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['is_preorder'])
        self.assertEqual(payload['amount_due_now'], '500.00')
        self.assertEqual(payload['balance_due'], '8499.00')
        self.assertEqual(payload['razorpay']['amount'], 50000)
        gateway.order.create.assert_called_once()
        self.assertEqual(gateway.order.create.call_args.args[0]['amount'], 50000)

        order = Order.objects.get(order_number=payload['order_number'])
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.payment_status, 'pending')
        self.assertTrue(order.is_preorder)
        self.assertEqual(order.items.get().variant, self.variant)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 0)

        verified, verification_gateway = self._verify_payment(order.order_number)
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.json()['ok'])
        self.assertTrue(verified.json()['is_preorder'])
        self.assertEqual(verified.json()['amount_paid'], '500.00')
        self.assertEqual(verified.json()['balance_due'], '8499.00')
        verification_gateway.utility.verify_payment_signature.assert_called_once()

        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.payment_status, 'partially_paid')
        self.assertEqual(order.amount_paid, Decimal('500.00'))
        self.assertEqual(order.balance_due, Decimal('8499.00'))
        confirmation_emails = [
            email for email in mail.outbox
            if email.subject.startswith('Order confirmed — #')
        ]
        self.assertEqual(len(confirmation_emails), 1)

        duplicate, _ = self._verify_payment(order.order_number)
        self.assertEqual(duplicate.status_code, 200)
        confirmation_emails = [
            email for email in mail.outbox
            if email.subject.startswith('Order confirmed — #')
        ]
        self.assertEqual(len(confirmation_emails), 1)
        self.assertIn('Advance paid: ₹500.00', confirmation_emails[0].body)
        self.assertIn('Balance due later: ₹8,499.00', confirmation_emails[0].body)

        history = self.client.get(reverse('order_history'))
        tracking = self.client.get(
            reverse('track_order'),
            {'order_number': order.order_number},
        )
        checkout = self.client.get(reverse('checkout'))
        self.assertEqual(history.status_code, 200)
        self.assertContains(history, 'Pre-order · Paid ₹500.00 · Balance due ₹8,499.00')
        self.assertEqual(tracking.status_code, 200)
        self.assertContains(tracking, 'Advance paid: ₹500.00')
        self.assertContains(tracking, 'Balance due later: ₹8,499.00')
        self.assertEqual(checkout.status_code, 200)
        self.assertContains(checkout, 'Remaining amount to pay:')
        self.assertContains(checkout, 'successPreorderBalance')

    def test_preorder_requires_razorpay_and_rejects_mixed_cart(self):
        cod_response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(payment_method='cod')),
            content_type='application/json',
        )
        self.assertEqual(cod_response.status_code, 400)
        self.assertIn('razorpay', cod_response.json()['error'].lower())

        regular = ShowcaseProduct.objects.create(
            name='Regular Tee',
            slug='regular-tee',
            price=Decimal('899.00'),
            image='showcase/regular-tee.gif',
            stock_quantity=5,
        )
        mixed_response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(items=[
                self._payload()['items'][0],
                {
                    'name': regular.name,
                    'slug': regular.slug,
                    'price': 899,
                    'quantity': 1,
                    'size': 'M',
                },
            ])),
            content_type='application/json',
        )
        self.assertEqual(mixed_response.status_code, 400)
        self.assertIn('separately', mixed_response.json()['error'].lower())
        self.assertEqual(Order.objects.count(), 0)

    @override_settings(RAZORPAY_KEY_ID='', RAZORPAY_KEY_SECRET='')
    def test_preorder_is_rejected_when_razorpay_is_not_configured(self):
        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn('temporarily unavailable', response.json()['error'].lower())
        self.assertEqual(Order.objects.count(), 0)

    def test_preorder_rejects_total_below_the_fixed_advance(self):
        self.product.price = Decimal('8999.00')
        self.product.save()
        Coupon.objects.create(
            code='LOWER-ORDER',
            discount_type='fixed',
            discount_value=Decimal('8500.00'),
            is_active=True,
        )

        response, _ = self._place_preorder(coupon_code='LOWER-ORDER')

        self.assertEqual(response.status_code, 400)
        self.assertIn('at least ₹500', response.json()['error'])
        self.assertEqual(Order.objects.count(), 0)

    def test_cancelling_preorder_does_not_change_inventory(self):
        response, _ = self._place_preorder()
        order_number = response.json()['order_number']
        verified, _ = self._verify_payment(order_number)
        self.assertTrue(verified.json()['ok'])
        order = Order.objects.get(order_number=order_number)

        cancelled = self.client.post(
            reverse('cancel_order'),
            {'order_id': str(order.pk), 'reason': 'Changed my mind'},
        )

        self.assertEqual(cancelled.status_code, 200)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 0)
