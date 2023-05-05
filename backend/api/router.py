from rest_framework.routers import DefaultRouter
from .views import CustomUserViewSet, TagViewSet, IngredientViewSet, RecipeViewSet, ShoppingListViewSet

router_v1 = DefaultRouter()
router_v1.register(r'users', CustomUserViewSet)
router_v1.register(r'ingredients', IngredientViewSet)
router_v1.register(r'tags', TagViewSet)
router_v1.register(r'recipes', RecipeViewSet, basename='recipes')
router_v1.register(r'shopping-lists', ShoppingListViewSet)