from django.urls import path, include
from djoser.views import TokenCreateView, TokenDestroyView

from .router import router_v1


app_name = 'api'

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/token/login/', TokenCreateView.as_view(), name='token_create'),
    path('auth/token/logout/', TokenDestroyView.as_view(), name='token_destroy'),
]


