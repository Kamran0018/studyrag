from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class AccountsModelTests(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            username='scholar1',
            email='scholar1@example.com',
            password='Password123!',
            first_name='Alex',
            last_name='Morgan',
            learning_goals='Python, Machine Learning'
        )
        self.assertEqual(user.username, 'scholar1')
        self.assertEqual(user.email, 'scholar1@example.com')
        self.assertTrue(user.check_password('Password123!'))


class AccountsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='SecretPassword99!',
            first_name='Jane',
            last_name='Doe'
        )

    def test_signup_view_get(self):
        response = self.client.get(reverse('accounts:signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")

    def test_signup_view_post_success(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'ComplexPass1234!',
            'password2': 'ComplexPass1234!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_view_get(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome Back")

    def test_login_view_post_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'SecretPassword99!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_home_view_requires_login(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_home_view_authenticated(self):
        self.client.login(username='testuser', password='SecretPassword99!')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back, Jane!")

    def test_logout_view(self):
        self.client.login(username='testuser', password='SecretPassword99!')
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))
