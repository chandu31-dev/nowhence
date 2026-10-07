import json
import os
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from mysite.settings.base import get_media_root
from mysite.views.helpers import get_otp, store_otp
from mysite.views.features import review_submit
from store.models import (
    Address, ContactInfo, ContactMessage, Coupon, FeaturedCollection, HeroSection, Order, OrderItem,
    ProductVariant, Review, ShowcaseProduct, UserProfile,
)


def _test_image():
    return SimpleUploadedFile(
        'test.gif',
        (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00'
            b'\x00\x00\x00\xff\xff\xff!\xf9\x04\x01'
            b'\x00\x00\x00\x00,\x00\x00\x00\x00\x01'
            b'\x00\x01\x00\x00\x02\x02D\x01\x00;'
        ),
        content_type='image/gif',
    )


class ReviewApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', password='secret123')
        self.other_user = User.objects.create_user(username='bob', password='secret123')
        self.factory = RequestFactory()
        self.product = ShowcaseProduct.objects.create(
            name='Essential Tee',
            slug='essential-tee',
            category='essential',
            price=Decimal('9999.00'),
            image=_test_image(),
            stock_quantity=10,
            is_active=True,
        )
        order = Order.objects.create(
            user=self.user,
            status='delivered',
            payment_status='paid',
            payment_method='cod',
            shipping_full_name='Alice',
            shipping_phone='9999999999',
            shipping_address='123 Street',
            shipping_city='Delhi',
            shipping_state='Delhi',
            shipping_pincode='110001',
            subtotal=Decimal('9999.00'),
            total=Decimal('9999.00'),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            price=Decimal('9999.00'),
            total=Decimal('9999.00'),
        )
        Review.objects.create(
            product=self.product,
            user=self.other_user,
            rating=4,
            title='Lovely work',
            comment='Great finish',
            is_approved=True,
        )

    def test_review_submit_accepts_form_posts(self):
        request = self.factory.post(
            reverse('review_submit'),
            data={
                'product_id': self.product.id,
                'rating': 5,
                'title': 'Perfect',
                'comment': 'Beautiful craftsmanship',
            },
        )
        request.user = self.user
        response = review_submit(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['review']['rating'], 5)
        self.assertEqual(
            Review.objects.get(product=self.product, user=self.user).title,
            'Perfect',
        )

    def test_review_list_returns_summary_and_frontend_keys(self):
        response = self.client.get(reverse('review_list'), {'product_id': self.product.id})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['average'], 4.0)
        self.assertEqual(payload['reviews'][0]['date'], payload['reviews'][0]['created_at'])
        self.assertFalse(payload['reviews'][0]['verified'])


class MediaRootTests(TestCase):
    def test_get_media_root_uses_environment_override(self):
        with mock.patch.dict(os.environ, {'MEDIA_ROOT': '/tmp/custom-media'}, clear=False):
            self.assertEqual(get_media_root(Path('/tmp/base')), Path('/tmp/custom-media'))


class HeroSectionTests(TestCase):
    def test_homepage_does_not_show_unverified_customer_or_design_counts(self):
        response = self.client.get(reverse('home'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '10K+')
        self.assertNotContains(response, '25+')
        self.assertContains(response, 'OPEN FOR PRE-ORDERS')

    def test_about_fallback_uses_tshirt_content_and_brand_image(self):
        response = self.client.get(reverse('about'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'T-shirts for Everyday Wear')
        self.assertContains(response, 'home-background.')
        self.assertNotContains(response, 'Ambava')
        self.assertNotContains(response, 'Add image from admin')

    def test_homepage_fallback_product_uses_launch_visual_settings(self):
        product = ShowcaseProduct.objects.create(
            name='Coming Soon Tee',
            image=_test_image(),
            price=Decimal('1200.00'),
            blur_image=True,
            show_coming_soon=True,
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'alt="{product.name}" loading="lazy" decoding="async" class="is-blurred"')
        self.assertContains(response, 'class="coming-soon-ribbon"')

    def test_homepage_featured_collection_uses_linked_product_launch_visual_settings(self):
        product = ShowcaseProduct.objects.create(
            name='Featured Coming Soon Tee',
            image=_test_image(),
            price=Decimal('1200.00'),
            blur_image=True,
            show_coming_soon=True,
        )
        FeaturedCollection.objects.create(
            name=product.name,
            description='A featured tee',
            price=Decimal('1200.00'),
            image=_test_image(),
        )

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="is-blurred"')
        self.assertContains(response, 'class="coming-soon-ribbon"')
        self.assertContains(response, reverse('product_detail', args=[product.slug]))

    def test_homepage_uses_new_default_contact_phone(self):
        response = self.client.get(reverse('home'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '+91 9014352958')

    def test_homepage_uses_new_default_contact_email(self):
        response = self.client.get(reverse('home'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'nowhenceclothings@gmail.com')
        self.assertNotContains(response, 'info@NowhenceClothings.com')

    def test_homepage_displays_active_contact_email(self):
        ContactInfo.objects.create(email='nowhenceclothings@gmail.com')

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'nowhenceclothings@gmail.com')

    def test_homepage_uses_default_background_image_without_active_hero(self):
        response = self.client.get(reverse('home'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'src="/static/images/home-background.')
        self.assertNotContains(response, 'class="hero-content"')
        self.assertNotContains(response, 'class="hero-overlay"')
        self.assertNotContains(response, 'class="hero-background"')
        self.assertNotContains(response, 'class="scroll-indicator"')
        self.assertNotContains(response, 'Luxury T-Shirts, Considered for Everyday Wear')

    def test_homepage_uses_video_background_when_hero_has_video_file(self):
        HeroSection.objects.create(
            title='Video Hero',
            subtitle='Animated launch',
            media_type='image',
            background_video=SimpleUploadedFile(
                'hero.mp4',
                b'fake-video-bytes',
                content_type='video/mp4',
            ),
            is_active=True,
        )

        response = self.client.get(reverse('home'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<video class="hero-media"')
        self.assertContains(response, 'type="video/mp4"')


class StoreAdminDashboardTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='store-admin',
            email='admin@example.com',
            password='secure-test-password',
        )
        self.client.force_login(self.admin_user)

    def test_dashboard_groups_store_tasks_and_omits_duplicate_model_directory(self):
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Products &amp; inventory')
        self.assertContains(response, 'Orders')
        self.assertContains(response, 'Returns &amp; exchanges')
        self.assertContains(response, 'Customer care')
        self.assertContains(response, 'Promotions')
        self.assertContains(response, 'Storefront &amp; settings')
        self.assertContains(response, 'More store tools')
        self.assertContains(response, reverse('admin:store_showcaseproduct_changelist'))
        self.assertContains(response, reverse('admin:store_order_changelist'))
        self.assertNotContains(response, 'Select an app to change')
        self.assertNotContains(response, 'Recent actions')

    def test_orders_can_be_bulk_marked_shipped_from_admin(self):
        order = Order.objects.create(
            user=User.objects.create_user(
                username='tracking-customer',
                email='tracking@example.com',
                password='secret123',
            ),
            status='confirmed',
        )

        with mock.patch('store.emails.send_shipping_notification') as notify_customer:
            response = self.client.post(
                reverse('admin:store_order_changelist'),
                {
                    'action': 'mark_orders_shipped',
                    '_selected_action': [str(order.pk)],
                },
                follow=True,
            )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, 'shipped')
        notify_customer.assert_called_once_with(order)

    def test_marking_order_delivered_records_delivery_time_and_notifies_customer(self):
        order = Order.objects.create(
            user=User.objects.create_user(
                username='delivered-customer',
                email='delivered@example.com',
                password='secret123',
            ),
            status='out_for_delivery',
        )

        with mock.patch('store.emails.send_shipping_notification') as notify_customer:
            response = self.client.post(
                reverse('admin:store_order_changelist'),
                {
                    'action': 'mark_orders_delivered',
                    '_selected_action': [str(order.pk)],
                },
                follow=True,
            )

        order.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.status, 'delivered')
        self.assertIsNotNone(order.delivered_at)
        notify_customer.assert_called_once_with(order)

    def test_admin_login_and_dashboard_load_store_brand_styles(self):
        self.client.logout()
        login_response = self.client.get(reverse('admin:login'))
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, '/static/css/admin.')

        self.client.force_login(self.admin_user)
        dashboard_response = self.client.get(reverse('admin:index'))
        self.assertContains(dashboard_response, '/static/css/admin.')


class ProductMerchandisingTests(TestCase):
    def setUp(self):
        self.product = ShowcaseProduct.objects.create(
            name='Preview Tee',
            slug='preview-tee',
            category='graphic',
            price=Decimal('1999.00'),
            image=_test_image(),
            stock_quantity=5,
            is_active=True,
            blur_image=True,
            show_coming_soon=True,
        )

    def test_shop_card_renders_product_blur_and_coming_soon_ribbon(self):
        response = self.client.get(reverse('shop'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="is-blurred"')
        self.assertContains(response, 'aria-label="Coming soon"')
        self.assertContains(response, 'COMING SOON')

    def test_product_detail_renders_blur_for_gallery_images_and_coming_soon_ribbon(self):
        response = self.client.get(reverse('product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pdp-main-image is-blurred')
        self.assertContains(response, 'aria-label="Coming soon"')
        self.assertContains(response, 'COMING SOON')

    def test_product_admin_exposes_both_optional_visual_settings(self):
        admin_user = User.objects.create_superuser(
            username='merch-admin',
            email='merch-admin@example.com',
            password='secure-test-password',
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('admin:store_showcaseproduct_add'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="blur_image"')
        self.assertContains(response, 'name="show_coming_soon"')


class ContactAndAuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.victim = User.objects.create_user(
            username='9999999999',
            email='victim@example.com',
            password='secret123',
        )
        self.phone = '+919999999999'
        self.raw_phone = '9999999999'

    def test_login_page_hides_google_and_facebook_sign_in_options(self):
        response = self.client.get(reverse('customer_login'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'google_login')
        self.assertNotContains(response, 'facebook_login')
        self.assertNotContains(response, 'phone_login')
        self.assertNotContains(response, 'phoneNumber')
        self.assertNotContains(response, 'Use phone number instead')
        self.assertNotContains(response, 'socialDivider')
        self.assertNotContains(response, 'socialButtons')

    def test_contact_submit_accepts_form_posts(self):
        response = self.client.post(
            reverse('contact_submit'),
            data={
                'name': 'Asha',
                'email': 'asha@example.com',
                'phone': '9999999999',
                'subject': 'Need help',
                'message': 'Please share delivery details.',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(ContactMessage.objects.count(), 1)
        saved_message = ContactMessage.objects.get()
        self.assertEqual(saved_message.name, 'Asha')
        self.assertEqual(saved_message.subject, 'Need help')

    @override_settings(DEBUG=True)
    def test_send_otp_requires_csrf_and_succeeds_with_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        blocked = csrf_client.post(
            reverse('send_otp'),
            data=json.dumps({'phone': self.raw_phone}),
            content_type='application/json',
        )
        self.assertEqual(blocked.status_code, 403)

        csrf_token = 'b' * 32
        csrf_client.cookies['csrftoken'] = csrf_token
        allowed = csrf_client.post(
            reverse('send_otp'),
            data=json.dumps({'phone': self.raw_phone}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()['ok'])

    @override_settings(DEBUG=False, AWS_SMS_ENABLED=True, AWS_REGION='us-east-1')
    def test_production_send_otp_uses_sns_without_returning_the_code(self):
        with mock.patch('mysite.views.api.boto3.client') as sns_client:
            response = self.client.post(
                reverse('send_otp'),
                data=json.dumps({'phone': self.raw_phone}),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertNotIn('demo_otp', payload)
        sns_client.return_value.publish.assert_called_once()
        sent_message = sns_client.return_value.publish.call_args.kwargs['Message']
        otp = sent_message.split('code is ')[1].split('.')[0]
        self.assertEqual(get_otp(self.phone, self.raw_phone), otp)

    def test_customer_phone_login_does_not_take_over_existing_numeric_username(self):
        store_otp(self.phone, '123456', self.raw_phone)

        response = self.client.post(
            reverse('customer_login'),
            data={
                'action': 'phone_login',
                'phone': self.raw_phone,
                'otp': '123456',
                '_ajax': '1',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])

        self.assertNotEqual(int(self.client.session['_auth_user_id']), self.victim.pk)
        profile = UserProfile.objects.get(phone=self.phone)
        self.assertNotEqual(profile.user_id, self.victim.pk)
        self.assertTrue(profile.user.username.startswith('phone_'))

    def test_checkout_phone_login_does_not_take_over_existing_numeric_username(self):
        store_otp(self.phone, '654321', self.raw_phone)

        response = self.client.post(
            reverse('checkout_login'),
            data={
                'action': 'phone_login',
                'phone': self.raw_phone,
                'otp': '654321',
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertNotEqual(payload['user']['username'], self.victim.username)
        self.assertNotEqual(int(self.client.session['_auth_user_id']), self.victim.pk)


class CheckoutApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='checkout-user',
            email='checkout@example.com',
            password='secret123',
        )
        self.client.force_login(self.user)
        self.product = ShowcaseProduct.objects.create(
            name='Pima Cotton Tee',
            slug='pima-cotton-tee',
            category='essential',
            price=Decimal('8999.00'),
            image=_test_image(),
            stock_quantity=5,
            is_active=True,
        )

    def test_product_detail_exposes_size_and_color_inventory(self):
        ProductVariant.objects.create(
            product=self.product,
            size='m',
            color='Black',
            color_hex='#111111',
            stock_quantity=2,
        )
        ProductVariant.objects.create(
            product=self.product,
            size='L',
            color='Black',
            stock_quantity=0,
        )
        ProductVariant.objects.create(
            product=self.product,
            size='L',
            color='White',
            stock_quantity=3,
        )

        response = self.client.get(reverse('product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select Color')
        self.assertContains(response, 'data-color="Black"')
        self.assertContains(response, 'data-size="M"')
        self.assertContains(response, 'data-size="L"')
        self.assertContains(response, '"stock_quantity": 0')

    def test_checkout_login_hides_phone_otp_but_keeps_shipping_phone(self):
        response = self.client.get(reverse('checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Phone OTP')
        self.assertNotContains(response, 'phoneForm')
        self.assertNotContains(response, 'sendOtpBtn')
        self.assertNotContains(response, "fd.append('action', 'phone_login')")
        self.assertContains(response, 'id="shipPhone"')

    def test_coming_soon_product_detail_disables_ordering(self):
        self.product.show_coming_soon = True
        self.product.save(update_fields=['show_coming_soon'])

        response = self.client.get(reverse('product_detail', args=[self.product.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Coming Soon')
        self.assertContains(response, 'disabled aria-disabled="true"')
        self.assertContains(response, 'class="btn-text">')

    def test_coming_soon_product_shop_card_disables_add_to_cart(self):
        self.product.show_coming_soon = True
        self.product.save(update_fields=['show_coming_soon'])

        response = self.client.get(reverse('shop'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-product="{self.product.name}"')
        self.assertContains(response, 'disabled aria-disabled="true"')
        self.assertContains(response, '<span>Coming Soon</span>', html=False)

    def test_place_order_rejects_coming_soon_product(self):
        self.product.show_coming_soon = True
        self.product.save(update_fields=['show_coming_soon'])

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])
        self.assertIn('coming soon', response.json()['error'].lower())
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_place_order_requires_a_configured_color_and_size_variant(self):
        ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Black',
            stock_quantity=2,
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload()),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('color', response.json()['error'].lower())
        self.assertEqual(Order.objects.count(), 0)

    def test_place_order_records_variant_and_decrements_only_selected_stock(self):
        black_medium = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Black',
            stock_quantity=2,
        )
        white_medium = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='White',
            stock_quantity=4,
        )
        payload = self._payload(items=[{
            'name': self.product.name,
            'slug': self.product.slug,
            'price': float(self.product.price),
            'quantity': 2,
            'image': '',
            'size': 'm',
            'color': 'black',
        }])

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        item = Order.objects.get(order_number=response.json()['order_number']).items.get()
        self.assertEqual(item.variant, black_medium)
        self.assertEqual(item.size, 'M')
        self.assertEqual(item.color, 'Black')
        black_medium.refresh_from_db()
        white_medium.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(black_medium.stock_quantity, 0)
        self.assertEqual(white_medium.stock_quantity, 4)
        self.assertEqual(self.product.stock_quantity, 5)

    def test_place_order_rejects_insufficient_selected_variant_stock(self):
        ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Black',
            stock_quantity=1,
        )
        payload = self._payload(items=[{
            'name': self.product.name,
            'slug': self.product.slug,
            'price': float(self.product.price),
            'quantity': 2,
            'image': '',
            'size': 'M',
            'color': 'Black',
        }])

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['ok'])
        self.assertIn('insufficient stock', response.json()['error'].lower())
        self.assertEqual(Order.objects.count(), 0)

    def _payload(self, **overrides):
        payload = {
            'items': [{
                'name': self.product.name,
                'slug': self.product.slug,
                'price': float(self.product.price),
                'quantity': 1,
                'image': '',
                'size': 'M',
            }],
            'email': 'checkout@example.com',
            'save_address': False,
            'payment_method': 'cod',
            'coupon_code': '',
            'discount_amount': 0,
            'shipping': {
                'full_name': 'Checkout User',
                'phone': '9999999999',
                'address_line1': '123 Market Road',
                'address_line2': '',
                'city': 'Delhi',
                'state': 'Delhi',
                'pincode': '110001',
            },
        }
        payload.update(overrides)
        return payload

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_place_order_emails_complete_receipt_to_checkout_email(self):
        Coupon.objects.create(
            code='SAVE500',
            discount_type='fixed',
            discount_value=Decimal('500.00'),
            is_active=True,
        )
        payload = self._payload(
            email='receipt@example.com',
            coupon_code='SAVE500',
            items=[{
                'name': self.product.name,
                'slug': self.product.slug,
                'price': float(self.product.price),
                'quantity': 1,
                'image': '',
                'size': 'M',
                'color': 'Black',
            }],
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(len(mail.outbox), 1)

        order = Order.objects.get(order_number=response.json()['order_number'])
        self.assertEqual(order.customer_email, 'receipt@example.com')
        self.assertEqual(mail.outbox[0].to, ['receipt@example.com'])
        self.assertIn(order.order_number, mail.outbox[0].subject)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertEqual(mail.outbox[0].alternatives[0][1], 'text/html')

        receipt = mail.outbox[0].body
        for detail in (
            order.order_number,
            'Pima Cotton Tee',
            'Color: Black, Size: M',
            'Quantity: 1 × ₹8,999.00 = ₹8,999.00',
            'Subtotal: ₹8,999.00',
            'Discount (SAVE500): -₹500.00',
            'Shipping: Free',
            'Total: ₹8,499.00',
            'Checkout User',
            '9999999999',
            '123 Market Road',
            'Delhi, Delhi 110001',
        ):
            with self.subTest(detail=detail):
                self.assertIn(detail, receipt)

        html_receipt = mail.outbox[0].alternatives[0][0]
        self.assertIn('Track your order', html_receipt)
        self.assertIn('/account/track-order/', html_receipt)

    def test_place_order_rejects_invalid_customer_email(self):
        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(email='not-an-email')),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['ok'])
        self.assertIn('email', response.json()['errors'])
        self.assertEqual(Order.objects.count(), 0)

    def test_place_order_rejects_invalid_coupon_instead_of_silently_ignoring_it(self):
        Coupon.objects.create(
            code='EXPIRED50',
            discount_type='fixed',
            discount_value=Decimal('500.00'),
            is_active=False,
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(coupon_code='EXPIRED50')),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload['ok'])
        self.assertIn('coupon', payload['error'].lower())
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_place_order_rejects_items_missing_required_size(self):
        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(items=[{
                'name': self.product.name,
                'slug': self.product.slug,
                'price': float(self.product.price),
                'quantity': 1,
                'image': '',
                'size': '',
            }])),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload['ok'])
        self.assertIn('size', payload['error'].lower())
        self.assertEqual(Order.objects.count(), 0)

    @override_settings(DEBUG=True, RAZORPAY_KEY_ID='', RAZORPAY_KEY_SECRET='')
    def test_razorpay_fallback_to_cod_finalizes_order_side_effects(self):
        coupon = Coupon.objects.create(
            code='WELCOME10',
            discount_type='percent',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('1000.00'),
            per_user_limit=1,
            is_active=True,
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(payment_method='razorpay', coupon_code='WELCOME10')),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['payment_method'], 'cod')

        order = Order.objects.get(order_number=payload['order_number'])
        self.product.refresh_from_db()
        coupon.refresh_from_db()

        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(self.product.stock_quantity, 4)
        self.assertEqual(coupon.used_count, 1)

    def test_pending_online_order_does_not_consume_per_user_coupon_limit(self):
        Coupon.objects.create(
            code='WELCOME10',
            discount_type='percent',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('1000.00'),
            per_user_limit=1,
            is_active=True,
        )
        Order.objects.create(
            user=self.user,
            status='pending',
            payment_status='pending',
            payment_method='razorpay',
            coupon_code='welcome10',
            subtotal=Decimal('8999.00'),
            total=Decimal('8099.10'),
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(coupon_code='WELCOME10')),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(Order.objects.filter(coupon_code__iexact='WELCOME10').count(), 2)

    def test_place_order_uses_cart_slug_to_resolve_the_correct_product(self):
        alternate_product = ShowcaseProduct.objects.create(
            name=self.product.name,
            slug='pima-cotton-tee-alt',
            category='essential',
            price=Decimal('12999.00'),
            image=_test_image(),
            stock_quantity=2,
            is_active=True,
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(items=[{
                'name': self.product.name,
                'slug': alternate_product.slug,
                'price': float(alternate_product.price),
                'quantity': 1,
                'image': '',
                'size': 'M',
            }])),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])

        order = Order.objects.get(order_number=payload['order_number'])
        order_item = order.items.get()

        self.assertEqual(order_item.product, alternate_product)
        self.assertEqual(order_item.product_name, alternate_product.name)
        self.assertEqual(order.total, alternate_product.price)

    def test_place_order_saves_address_when_requested(self):
        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(save_address=True)),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])

        saved_address = Address.objects.get(user=self.user)
        self.assertEqual(saved_address.full_name, 'Checkout User')
        self.assertEqual(saved_address.address_line1, '123 Market Road')
        self.assertTrue(saved_address.is_default)

    def test_place_order_updates_existing_saved_address_instead_of_creating_duplicate(self):
        existing_address = Address.objects.create(
            user=self.user,
            label='work',
            full_name='Old Name',
            phone='8888888888',
            address_line1='Old Address',
            address_line2='',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            is_default=True,
        )

        response = self.client.post(
            reverse('place_order'),
            data=json.dumps(self._payload(
                save_address=True,
                address_id=str(existing_address.pk),
                shipping={
                    'full_name': 'Updated User',
                    'phone': '9999999999',
                    'address_line1': '456 Updated Road',
                    'address_line2': 'Suite 9',
                    'city': 'Gurugram',
                    'state': 'Haryana',
                    'pincode': '122001',
                },
            )),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)

        existing_address.refresh_from_db()
        self.assertEqual(existing_address.label, 'work')
        self.assertEqual(existing_address.full_name, 'Updated User')
        self.assertEqual(existing_address.address_line1, '456 Updated Road')
        self.assertEqual(existing_address.city, 'Gurugram')
        self.assertTrue(existing_address.is_default)

    def test_address_save_keeps_only_one_default_address(self):
        original_default = Address.objects.create(
            user=self.user,
            label='home',
            full_name='Original Default',
            phone='9999999999',
            address_line1='1 First Lane',
            address_line2='',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            is_default=True,
        )

        response = self.client.post(
            reverse('address_save'),
            data={
                'full_name': 'New Default',
                'phone': '9999999999',
                'address_line1': '2 Second Lane',
                'address_line2': '',
                'city': 'Noida',
                'state': 'UP',
                'pincode': '201301',
                'label': 'work',
                'is_default': 'on',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

        original_default.refresh_from_db()
        new_default = Address.objects.get(pk=response.json()['address']['id'])

        self.assertFalse(original_default.is_default)
        self.assertTrue(new_default.is_default)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)

    def test_checkout_login_requires_csrf_and_succeeds_with_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        blocked = csrf_client.post(
            reverse('checkout_login'),
            data={
                'action': 'login',
                'username': self.user.username,
                'password': 'secret123',
            },
        )
        self.assertEqual(blocked.status_code, 403)

        csrf_token = 'a' * 32
        csrf_client.cookies['csrftoken'] = csrf_token
        allowed = csrf_client.post(
            reverse('checkout_login'),
            data={
                'action': 'login',
                'username': self.user.username,
                'password': 'secret123',
            },
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(allowed.status_code, 200)
        payload = allowed.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['user']['username'], self.user.username)

    def test_cancel_confirmed_order_restocks_and_releases_coupon(self):
        coupon = Coupon.objects.create(
            code='WELCOME10',
            discount_type='percent',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('1000.00'),
            usage_limit=5,
            per_user_limit=1,
            used_count=1,
            is_active=True,
        )
        self.product.stock_quantity = 4
        self.product.save(update_fields=['stock_quantity'])
        order = Order.objects.create(
            user=self.user,
            status='confirmed',
            payment_status='paid',
            payment_method='razorpay',
            shipping_full_name='Checkout User',
            shipping_phone='9999999999',
            shipping_address='123 Market Road',
            shipping_city='Delhi',
            shipping_state='Delhi',
            shipping_pincode='110001',
            subtotal=Decimal('8999.00'),
            discount_amount=Decimal('900.00'),
            total=Decimal('8099.00'),
            coupon_code=coupon.code,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            price=Decimal('8999.00'),
            total=Decimal('8999.00'),
            size='M',
        )

        response = self.client.post(
            reverse('cancel_order'),
            data={'order_id': str(order.pk), 'reason': 'Changed my mind'},
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.product.refresh_from_db()
        coupon.refresh_from_db()

        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.payment_status, 'refunded')
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(coupon.used_count, 0)
        self.assertTrue(response.json()['refund'])

    def test_cancel_confirmed_variant_order_restocks_selected_size_and_color(self):
        variant = ProductVariant.objects.create(
            product=self.product,
            size='M',
            color='Black',
            stock_quantity=2,
        )
        order = Order.objects.create(
            user=self.user,
            status='confirmed',
            payment_status='paid',
            payment_method='cod',
            shipping_full_name='Checkout User',
            shipping_phone='9999999999',
            shipping_address='123 Market Road',
            shipping_city='Delhi',
            shipping_state='Delhi',
            shipping_pincode='110001',
            subtotal=Decimal('8999.00'),
            total=Decimal('8999.00'),
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            variant=variant,
            product_name=self.product.name,
            quantity=1,
            price=Decimal('8999.00'),
            size='M',
            color='Black',
        )
        variant.stock_quantity = 1
        variant.save(update_fields=['stock_quantity'])

        response = self.client.post(
            reverse('cancel_order'),
            data={'order_id': str(order.pk), 'reason': 'Changed my mind'},
        )

        self.assertEqual(response.status_code, 200)
        variant.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(variant.stock_quantity, 2)

    def test_cancel_pending_online_order_marks_payment_failed_without_side_effects(self):
        coupon = Coupon.objects.create(
            code='WELCOME10',
            discount_type='percent',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('1000.00'),
            usage_limit=5,
            per_user_limit=1,
            used_count=0,
            is_active=True,
        )
        order = Order.objects.create(
            user=self.user,
            status='pending',
            payment_status='pending',
            payment_method='razorpay',
            shipping_full_name='Checkout User',
            shipping_phone='9999999999',
            shipping_address='123 Market Road',
            shipping_city='Delhi',
            shipping_state='Delhi',
            shipping_pincode='110001',
            subtotal=Decimal('8999.00'),
            discount_amount=Decimal('900.00'),
            total=Decimal('8099.00'),
            coupon_code=coupon.code,
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            price=Decimal('8999.00'),
            total=Decimal('8999.00'),
            size='M',
        )

        response = self.client.post(
            reverse('cancel_order'),
            data={'order_id': str(order.pk), 'reason': 'Payment cancelled'},
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.product.refresh_from_db()
        coupon.refresh_from_db()

        self.assertEqual(order.status, 'cancelled')
        self.assertEqual(order.payment_status, 'failed')
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(coupon.used_count, 0)
        self.assertFalse(response.json()['refund'])

    def test_address_delete_promotes_another_saved_address_to_default(self):
        original_default = Address.objects.create(
            user=self.user,
            label='home',
            full_name='Original Default',
            phone='9999999999',
            address_line1='1 First Lane',
            address_line2='',
            city='Delhi',
            state='Delhi',
            pincode='110001',
            is_default=True,
        )
        replacement = Address.objects.create(
            user=self.user,
            label='work',
            full_name='Replacement',
            phone='8888888888',
            address_line1='2 Second Lane',
            address_line2='Suite 4',
            city='Noida',
            state='UP',
            pincode='201301',
            is_default=False,
        )

        response = self.client.post(
            reverse('address_delete'),
            data={'address_id': str(original_default.pk)},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['new_default_id'], replacement.pk)

        replacement.refresh_from_db()
        self.assertTrue(replacement.is_default)
        self.assertFalse(Address.objects.filter(pk=original_default.pk).exists())
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)


@override_settings(GOOGLE_CLIENT_ID='google-client-id', GOOGLE_CLIENT_SECRET='google-client-secret')
class GoogleOAuthTests(TestCase):
    def _response(self, payload):
        response = mock.Mock()
        response.read.return_value = json.dumps(payload).encode()
        return response

    def test_google_login_sets_encoded_callback_and_session_state(self):
        response = self.client.get(reverse('google_login'), {'next': '/checkout/'})

        self.assertEqual(response.status_code, 302)
        params = parse_qs(urlsplit(response['Location']).query)
        self.assertEqual(params['client_id'], ['google-client-id'])
        self.assertEqual(params['redirect_uri'], ['http://testserver/account/google/callback/'])
        self.assertEqual(params['state'][0], self.client.session['google_oauth_state'])
        self.assertEqual(self.client.session['google_oauth_next'], '/checkout/')

    def test_callback_rejects_state_mismatch_without_network_request(self):
        with mock.patch('mysite.views.auth.urllib.request.urlopen') as urlopen:
            response = self.client.get(
                reverse('google_callback'),
                {'code': 'authorization-code', 'state': 'unexpected-state'},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('customer_login'))
        urlopen.assert_not_called()

    def test_verified_google_identity_creates_and_logs_in_customer(self):
        session = self.client.session
        session['google_oauth_state'] = 'expected-state'
        session['google_oauth_next'] = '/checkout/'
        session.save()
        responses = [
            self._response({'access_token': 'access-token'}),
            self._response({
                'sub': 'google-subject-123',
                'email': 'customer@example.com',
                'email_verified': True,
                'given_name': 'Taylor',
                'family_name': 'Customer',
            }),
        ]

        with mock.patch('mysite.views.auth.urllib.request.urlopen', side_effect=responses):
            response = self.client.get(
                reverse('google_callback'),
                {'code': 'authorization-code', 'state': 'expected-state'},
            )

        user = User.objects.get(email='customer@example.com')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/checkout/')
        self.assertEqual(str(self.client.session['_auth_user_id']), str(user.pk))
        self.assertEqual(user.profile.google_id, 'google-subject-123')

    def test_callback_rejects_unverified_email(self):
        session = self.client.session
        session['google_oauth_state'] = 'expected-state'
        session.save()
        responses = [
            self._response({'access_token': 'access-token'}),
            self._response({
                'sub': 'google-subject-123',
                'email': 'customer@example.com',
                'email_verified': False,
            }),
        ]

        with mock.patch('mysite.views.auth.urllib.request.urlopen', side_effect=responses):
            response = self.client.get(
                reverse('google_callback'),
                {'code': 'authorization-code', 'state': 'expected-state'},
            )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(email='customer@example.com').exists())


class ShowcaseProductCatalogTests(TestCase):
    def test_discounted_price_uses_decimal_arithmetic(self):
        product = ShowcaseProduct.objects.create(
            name='Pima Cotton Tee',
            category='essential',
            price=Decimal('2290.00'),
            discount_percent=10,
            image=_test_image(),
        )

        self.assertEqual(product.discounted_price, Decimal('2061.00'))


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PASSWORD_RESET_TIMEOUT=3600,
)
class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='reset-customer',
            email='customer@example.com',
            password='old-password-123',
        )

    def test_email_link_opens_reset_form_and_changes_password(self):
        response = self.client.post(
            reverse('password_reset_request'),
            {'email': self.user.email},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertEqual(len(mail.outbox), 1)

        reset_url = mail.outbox[0].body.split(
            'Click the link below to reset your password:\n',
            1,
        )[1].splitlines()[0]
        reset_params = parse_qs(urlsplit(reset_url).query)
        reset_path = urlsplit(reset_url).path
        reset_page = self.client.get(reset_path, {
            'uid': reset_params['uid'][0],
            'token': reset_params['token'][0],
        })

        self.assertEqual(reset_page.status_code, 200)
        self.assertContains(reset_page, 'Update password')

        completed = self.client.post(reset_path, {
            'uid': reset_params['uid'][0],
            'token': reset_params['token'][0],
            'password': 'new-strong-password-456',
            'confirm_password': 'new-strong-password-456',
        })

        self.assertEqual(completed.status_code, 200)
        self.assertContains(completed, 'Password updated')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new-strong-password-456'))

    def test_unknown_email_has_same_response_without_sending_mail(self):
        registered = self.client.post(
            reverse('password_reset_request'),
            {'email': self.user.email},
        )
        cache.clear()
        unknown = self.client.post(
            reverse('password_reset_request'),
            {'email': 'unknown@example.com'},
        )

        self.assertEqual(registered.status_code, unknown.status_code)
        self.assertEqual(registered.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)
