from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.http import HttpResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, mixins, generics, permissions
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from djoser.views import UserViewSet
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import CustomRecipeFilter, CustomIngredientFilter
from api.pagination import SubscriptionListPagination
from api.Serializers import (
    TagSerializer,
    RecipeSerializer,
    IngredientSerializer,
    FavoriteSerializer,
    SubscriptionListSerializer,
    SubscriptionCreateSerializer,
    UserReadSerializer,
    ShoppingListSerializer,
    ChangePasswordSerializer,
    UserCreateSerializer,
    RecipeCreateSerializer,
)
from api.permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from recipes.models import (
    Recipe,
    Subscription,
    Ingredient,
    Tag,
    ShoppingList,
    Favorite
)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all().order_by('id')

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'set_password':
            return ChangePasswordSerializer
        return UserReadSerializer

    def get_permissions(self):
        if self.action == 'set_password' and self.request.method == 'POST':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers)

    @action(detail=False,
            methods=['post'],
            permission_classes=[IsAuthenticated]
            )
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'detail': 'Пароль успешно изменен'},
            status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    # filter_backends = [DjangoFilterBackend]
    # filterset_class = CustomIngredientFilter
    pagination_class = None


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all().order_by('id')
    pagination_class = PageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CustomRecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all()
        tag_slugs = self.request.query_params.getlist('tag')

        if tag_slugs:
            query = Q(tags__slug=tag_slugs[0])
            for tag_slug in tag_slugs[1:]:
                query |= Q(tags__slug=tag_slug)
            queryset = queryset.filter(query)
        author = self.request.query_params.get('author')
        favorites = self.request.query_params.get('favorites')
        if author:
            queryset = queryset.filter(author__username=author)
        if favorites:
            queryset = queryset.filter(favorites__user=self.request.user)

        return queryset

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Пользователь не авторизован.')
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['POST'])
    def add_to_favorite(self, request, pk=None):
        recipe = self.get_object()
        if Favorite.objects.filter(
                recipe=recipe, user=request.user).exists():
            return Response(
                {'error': 'Этот рецепт уже в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite = Favorite.objects.create(
            recipe=recipe, user=request.user)
        serializer = FavoriteSerializer(favorite.recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['POST'])
    def remove_from_favorite(self, request, pk=None):
        if not request.user.is_authenticated:
            raise PermissionDenied('Пользователь не авторизован.')
        recipe = self.get_object()
        try:
            favorite = Favorite.objects.get(
                recipe=recipe, user=request.user)
        except Favorite.DoesNotExist:
            return Response(
                {'error': 'Рецепт не находится в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.GenericViewSet,
                          mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          mixins.DestroyModelMixin):
    serializer_class = SubscriptionCreateSerializer
    permission_classes = [IsAuthenticated]
    queryset = Subscription.objects.all()

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=['POST'])
    def subscribe(self, request, user_id=None):
        user = get_object_or_404(User, id=user_id)
        if user == request.user:
            return Response(
                {'error': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscription.objects.filter(
            user=request.user, author=user).first()
        if subscription:
            return Response(
                {'error': 'Вы уже подписаны на данного пользователя'},
                status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscription.objects.create(
            user=request.user, author=user)
        serializer = self.get_serializer(subscription)
        user_serializer = UserReadSerializer(
            user, context={'request': request})
        return Response({
            'user': user_serializer.data,
            'recipes_count': user.recipes.count(),
            'message': 'Подписка успешно создана'
        }, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, user_id=None):
        user = get_object_or_404(User, id=user_id)
        try:
            subscription = Subscription.objects.get(
                user=request.user, author=user)
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'Вы не подписаны на этого автора.'},
                status=status.HTTP_400_BAD_REQUEST)
        else:
            subscription.delete()
            return Response(
                {'Успешная отписка'},
                status=status.HTTP_204_NO_CONTENT)


class SubscriptionListAPIView(generics.ListAPIView):
    serializer_class = SubscriptionListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = SubscriptionListPagination

    def get_queryset(self):
        user = self.request.user
        subscriptions = Subscription.objects.filter(user=user).order_by('-created_at')
        return subscriptions.prefetch_related('author__recipes')

    def get(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class DownloadShoppingCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        shopping_list = ShoppingList.objects.filter(
            user=request.user)
        ingredients = shopping_list.values(
            'recipes__ingredients__name',
            'recipes__ingredients__measurement_unit').annotate(
            total_amount=Sum('recipes__ingredient_recipes__amount'))
        ingredients_dict = {}
        for ingredient in ingredients:
            name = ingredient['recipes__ingredients__name']
            unit = ingredient['recipes__ingredients__measurement_unit']
            amount = ingredient['total_amount']
            if name not in ingredients_dict:
                ingredients_dict[name] = {
                    'unit': unit,
                    'amount': amount
                }
            else:
                ingredients_dict[name]['amount'] += amount
        content = '\n'.join([
            f"{name} - {data['amount']} {data['unit']}"
            for name, data in ingredients_dict.items()
        ])
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response


class ShoppingListViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)

    def create(self, request, recipe_id):
        recipe = Recipe.objects.filter(id=recipe_id).first()
        if not recipe:
            raise Http404('Рецепт не найден')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, recipe=recipe)
        response_data = {
            'id': recipe.id,
            'name': recipe.name,
            'image': request.build_absolute_uri(recipe.image.url),
            'cooking_time': recipe.cooking_time
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def shopping_cart(self, request, recipe_id=None, pk=None):
        shopping_lists = self.get_queryset().filter(
            recipes__id=recipe_id
        )
        if not shopping_lists.exists():
            return Response(
                {'error': 'Такого рецепта нет в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST
            )
        for shopping_list in shopping_lists:
            if recipe_id in shopping_list.recipes.values_list('id', flat=True):
                shopping_list.recipes.remove(recipe_id)
                if not shopping_list.recipes.all():
                    shopping_list.delete()
            else:
                return Response(
                    {'error': 'Такого рецепта нет в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        return self.shopping_cart(request, *args, **kwargs)

