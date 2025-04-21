from authentication.tests.test import *

class TestAuthBearer(TestCase):
    def setUp(self):
        self.auth = AuthBearer()

    def test_valid_token_with_user_id(self):
        payload = {"user_id": 123}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        user_id = self.auth.authenticate(request=None, token=token)
        self.assertEqual(user_id, 123)

    def test_invalid_token(self):
        invalid_token = "invalid.token.value"

        result = self.auth.authenticate(request=None, token=invalid_token)
        self.assertIsNone(result)

    def test_token_without_user_id(self):
        payload = {"something_else": "value"}
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        result = self.auth.authenticate(request=None, token=token)
        self.assertIsNone(result)