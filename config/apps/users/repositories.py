from django.contrib.auth import get_user_model

User = get_user_model()

class UserRepository:
    @staticmethod
    def create_user(username, email, password, **extra_fields):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields
        )
        return user

    @staticmethod
    def get_user_by_username(username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
