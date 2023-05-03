from django.urls import include, path
from rest_framework import routers

from api.views import RecipesViewSet

# from rest_framework.authtoken.views import obtain_auth_token


app_name = 'api'
router_v1 = routers.DefaultRouter()
router_v1.register(r'recipes', RecipesViewSet)


urlpatterns = [
    path(r'auth/', include('djoser.urls.authtoken')),
    path(r'', include(router_v1.urls))
    # path('auth/token', obtain_auth_token, name= 'token'),
]

