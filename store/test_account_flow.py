from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class CustomerAccountFlowTests(TestCase):
    def test_invalid_login_then_valid_login_and_profile_readback(self):
        user = User.objects.create_user(
            username='flow-customer',
            email='flow-customer@example.com',
            password='correct-test-password',
        )

        login_page = self.client.get(reverse('customer_login'))
        self.assertEqual(login_page.status_code, 200)

        invalid_login = self.client.post(
            reverse('customer_login'),
            {
                'action': 'login',
                'username': user.username,
                'password': 'incorrect-password',
                '_ajax': '1',
            },
        )
        self.assertEqual(invalid_login.status_code, 200)
        self.assertFalse(invalid_login.json()['ok'])

        valid_login = self.client.post(
            reverse('customer_login'),
            {
                'action': 'login',
                'username': user.username,
                'password': 'correct-test-password',
                '_ajax': '1',
            },
        )
        self.assertEqual(valid_login.status_code, 200)
        self.assertTrue(valid_login.json()['ok'])

        profile = self.client.get(reverse('profile'))
        self.assertEqual(profile.status_code, 200)
        self.assertContains(profile, user.username)
        self.assertTrue(User.objects.filter(pk=user.pk, email='flow-customer@example.com').exists())
