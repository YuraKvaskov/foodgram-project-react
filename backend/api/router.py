from rest_framework.routers import DefaultRouter
from .views import RecipesViewSet, CustomUserViewSet

router_v1 = DefaultRouter()
router_v1.register(r'recipes', RecipesViewSet)
router_v1.register(r'users', CustomUserViewSet)