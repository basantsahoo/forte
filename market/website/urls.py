from django.urls import include, re_path
from rest_framework_simplejwt.views import TokenVerifyView

from website.views import UserLoginView

urlpatterns = [
    re_path(r"^login$", UserLoginView.as_view(), name="login"),
    re_path(r"^verify-token", TokenVerifyView.as_view(), name="token_verify"),
]
