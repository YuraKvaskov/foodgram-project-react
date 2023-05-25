from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from djoser.views import UserViewSet

from api.filters import CustomRecipeFilter, CustomIngredientFilter
from api.pagination import CustomPagination
from api.Serializers import (
    TagSerializer,
    RecipeSerializer,
    IngredientSerializer,
    SubscriptionListSerializer,
    UserReadSerializer,
    ChangePasswordSerializer,
    UserCreateSerializer,
    RecipeCreateSerializer,
    FavoriteSerializer,
    ShoppingListSerializer,
)
from api.permissions import IsAdminOrReadOnly, IsOwnerOrReadOnly
from recipes.models import (
    Recipe,
    Subscription,
    Ingredient,
    Tag,
    ShoppingList,
    Favorite,
    IngredientRecipe,
)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all().order_by('id')
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action == 'set_password':
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
        serializer.is_valid(
            raise_exception=True)
        user = self.request.user
        user.set_password(
            serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'detail': 'Пароль успешно изменен'},
            status=status.HTTP_204_NO_CONTENT)

    @action(methods=['get'],
            detail=False,
            permission_classes=[IsAuthenticated]
            )
    def subscriptions(self, request):
        queryset = Subscription.objects.filter(
            user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionListSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['post', 'delete'],
            detail=True,
            permission_classes=[IsAuthenticated]
            )
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        user = self.request.user

        if request.method == 'POST' and user != author:
            subscription, created = Subscription.objects.get_or_create(
                author=author, user=user)
            if created:
                return Response(
                    {"message": "Подписка успешно создана."},
                    status=status.HTTP_201_CREATED)
            return Response(
                {"message": "Вы уже подписаны на этого автора."},
                status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            subscription = get_object_or_404(
                Subscription, author=author, user=user)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = CustomIngredientFilter
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get('name')
        queryset = super().get_queryset().filter(name__icontains=name)
        start_queryset = list(queryset.filter(name__istartswith=name))
        queryset = (
                start_queryset +
                [ing for ing in queryset if ing not in start_queryset]
        )
        return queryset


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = CustomRecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update']:
            return RecipeCreateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        if not self.request.user.is_authenticated:
            raise PermissionDenied('Пользователь не авторизован.')
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action in ['delete', 'partial_update']:
            permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def favorites(self, request, *args, **kwargs):
        queryset = Favorite.objects.filter(user=self.request.user)
        page = self.paginate_queryset(queryset)
        serializer = FavoriteSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def handle_action(self, request, pk, model, serializer):
        try:
            recipe = get_object_or_404(Recipe, id=pk)
            user = request.user
            if request.method == 'POST':
                if model == Favorite:
                    obj, created = model.objects.get_or_create(
                        user=user, recipe=recipe)
                elif model == ShoppingList:
                    obj, created = model.objects.get_or_create(
                        user=user)
                    obj.recipe.add(recipe)
                status_code = status.HTTP_201_CREATED
            elif request.method == 'DELETE':
                obj = model.objects.get(
                    user=user, recipe__id=pk)
                if model == ShoppingList:
                    obj.recipe.remove(recipe)
                    if not obj.recipe.exists():
                        obj.delete()
                else:
                    obj.delete()
                status_code = status.HTTP_204_NO_CONTENT

            serializer = self.get_serializer(recipe)
            return Response(serializer.data, status=status_code)

        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post', 'delete'],
            detail=True,
            permission_classes=[IsAuthenticated]
            )
    def favorite(self, request, pk=None):
        return self.handle_action(
            request, pk, Favorite, FavoriteSerializer)

    @action(methods=['post', 'delete'],
            detail=True,
            permission_classes=[IsAuthenticated]
            )
    def shopping_cart(self, request, pk=None):
        return self.handle_action(
            request, pk, ShoppingList, ShoppingListSerializer)

    @action(detail=False,
            methods=['get'],
            permission_classes=[IsAuthenticated]
            )
    def download_shopping_cart(self, request):
        shopping_list = ShoppingList.objects.filter(
            user=request.user)
        recipe_ids = shopping_list.values_list(
            'recipe', flat=True)
        ingredients = IngredientRecipe.objects.filter(
            recipe__in=recipe_ids).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        )
        ingredients_dict = {}
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
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
        response['Content-Disposition'] = ('attachment;'
                                           'filename="shopping_list.txt"')
        return response
