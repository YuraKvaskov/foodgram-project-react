from django.urls import path, include
from djoser.views import TokenCreateView, TokenDestroyView

from .router import router_v1
from .views import SubscriptionViewSet, SubscriptionListAPIView,DownloadShoppingCartView, RecipeViewSet

app_name = 'api'

urlpatterns = [
    path('auth/token/login/', TokenCreateView.as_view(), name='token_create'),
    path('auth/token/logout/', TokenDestroyView.as_view(), name='token_destroy'),
    path('users/<int:user_id>/subscribe/', SubscriptionViewSet.as_view(
        {'post': 'subscribe', 'delete': 'unsubscribe'}),
         name='subscribe'),
    path('users/subscriptions/', SubscriptionListAPIView.as_view(), name='subscription-list'),
    path('recipes/<int:pk>/favorite/', RecipeViewSet.as_view(
        {'post': 'add_to_favorite', 'delete': 'remove_from_favorite'})),
    path('recipes/download_shopping_cart/', DownloadShoppingCartView.as_view(), name='download_shopping_cart'),
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),

]
