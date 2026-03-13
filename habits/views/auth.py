from django.contrib.auth import authenticate, login, logout
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from ..serializers import RegisterSerializer, LoginSerializer, UserSerializer


class RegisterView(GenericAPIView):
    permission_classes = []
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        from ..models import User

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already taken."}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({"detail": "Email already registered."}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)

        login(request, user)

        return Response(UserSerializer(user).data, status=201)


class LoginView(GenericAPIView):
    permission_classes = []
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            return Response({"detail": "Invalid credentials."}, status=401)

        login(request, user)

        return Response(UserSerializer(user).data)

class LogoutView(APIView):

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=204)

class MeView(APIView):

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        user = request.user
        return Response(UserSerializer(user).data)
