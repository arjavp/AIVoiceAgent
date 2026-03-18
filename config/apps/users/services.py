from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .repositories import UserRepository

class UserService:
    @staticmethod
    def register_user(username, email, password, **extra_fields):
        return UserRepository.create_user(username, email, password, **extra_fields)
    
    @staticmethod
    def authenticate_user(username, password):
        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': user
            }
        return None
    
    @staticmethod
    def blacklist_token(refresh_token):
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return True
        except Exception:
            return False
