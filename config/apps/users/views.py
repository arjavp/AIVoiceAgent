import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import RegisterSerializer, LoginSerializer, LogoutSerializer, UserSerializer
from .services import UserService

logger = logging.getLogger(__name__)

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        logger.info(f"User registration attempt: {request.data.get('username')}")
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = UserService.register_user(**serializer.validated_data)
            logger.info(f"User registered successfully: {user.username}")
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        logger.warning(f"Registration failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            logger.info(f"User login attempt: {username}")
            result = UserService.authenticate_user(
                username=username,
                password=serializer.validated_data['password']
            )
            if result:
                logger.info(f"User logged in successfully: {username}")
                response_data = {
                    'access': result['access'],
                    'refresh': result['refresh'],
                    'user': UserSerializer(result['user']).data
                }
                return Response(response_data, status=status.HTTP_200_OK)
            logger.warning(f"Invalid login credentials for {username}")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logger.info(f"User logout attempt: {request.user.username}")
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            success = UserService.blacklist_token(serializer.validated_data['refresh'])
            if success:
                logger.info(f"User logged out successfully: {request.user.username}")
                return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
