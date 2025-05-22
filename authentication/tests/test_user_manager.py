from authentication.models import User
from django.test import TestCase

class UserManagerTests(TestCase):
    def test_create_user_without_email(self):
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email="", password="password")
        self.assertEqual(str(context.exception), "The Email must be set")

    def test_create_superuser(self):
        superuser = User.objects.create_superuser(
            email="superuser@example.com",
            password="password",
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertEqual(superuser.email, "superuser@example.com")

    