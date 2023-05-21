from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum, Q
from django.http import HttpResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets, mixins, generics, permissions, serializers
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from djoser.views import UserViewSet
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import CustomRecipeFilter, CustomIngredientFilter
from api.pagination import LimitPagination
from api.Serializers import (
    TagSerializer,
    RecipeSerializer,
    IngredientSerializer,
    # FavoriteSerializer,
    SubscriptionListSerializer,
    # SubscriptionCreateSerializer,
    UserReadSerializer,
    # ShoppingListSerializer,
    ChangePasswordSerializer,
    UserCreateSerializer,
    RecipeCreateSerializer, FavoriteSerializer, ShoppingListSerializer,
)
from api.permissions import IsOwnerOrReadOnly, IsAdminOrReadOnly
from recipes.models import (
    Recipe,
    Subscription,
    Ingredient,
    Tag,
    ShoppingList,
    Favorite, IngredientRecipe
)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all().order_by('id')
    pagination_class = LimitPagination

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

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = Subscription.objects.filter(user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = SubscriptionListSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['post', 'delete'], detail=True, permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = get_object_or_404(User, id=id)
        user = self.request.user

        if request.method == 'POST' and user != author:
            subscription, created = Subscription.objects.get_or_create(author=author, user=user)
            if created:
                return Response({"message": "Подписка успешно создана."}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "Вы уже подписаны на этого автора."}, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            subscription = get_object_or_404(Subscription, author=author, user=user)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = [DjangoFilterBackend]
    filterset_class = CustomIngredientFilter
    pagination_class = None


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = LimitPagination
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
                    obj, created = model.objects.get_or_create(user=user, recipe=recipe)
                elif model == ShoppingList:
                    obj, created = model.objects.get_or_create(user=user)
                    obj.recipe.add(recipe)
                status_code = status.HTTP_201_CREATED
            elif request.method == 'DELETE':
                obj = model.objects.get(user=user, recipe__id=pk)
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

    @action(methods=['post', 'delete'], detail=True, permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.handle_action(request, pk, Favorite, FavoriteSerializer)

    @action(methods=['post', 'delete'], detail=True, permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self.handle_action(request, pk, ShoppingList, ShoppingListSerializer)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        shopping_list = ShoppingList.objects.filter(user=request.user)
        recipe_ids = shopping_list.values_list('recipe', flat=True)
        ingredients = IngredientRecipe.objects.filter(recipe__in=recipe_ids).values(
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
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

#
# class SubscriptionViewSet(viewsets.GenericViewSet,
#                           mixins.ListModelMixin,
#                           mixins.CreateModelMixin,
#                           mixins.DestroyModelMixin):
#     serializer_class = SubscriptionCreateSerializer
#     permission_classes = [IsAuthenticated]
#     queryset = Subscription.objects.all()
#
#     def get_queryset(self):
#         return self.queryset.filter(user=self.request.user)
#
#     @action(detail=True, methods=['POST'])
#     def subscribe(self, request, user_id=None):
#         user = get_object_or_404(User, id=user_id)
#         if user == request.user:
#             return Response(
#                 {'error': 'Нельзя подписаться на самого себя'},
#                 status=status.HTTP_400_BAD_REQUEST)
#         subscription = Subscription.objects.filter(
#             user=request.user, author=user).first()
#         if subscription:
#             return Response(
#                 {'error': 'Вы уже подписаны на данного пользователя'},
#                 status=status.HTTP_400_BAD_REQUEST)
#         subscription = Subscription.objects.create(
#             user=request.user, author=user)
#         serializer = self.get_serializer(subscription)
#         user_serializer = UserReadSerializer(
#             user, context={'request': request})
#         return Response({
#             'user': user_serializer.data,
#             'recipes_count': user.recipes.count(),
#             'message': 'Подписка успешно создана'
#         }, status=status.HTTP_201_CREATED)
#
#     @subscribe.mapping.delete
#     def unsubscribe(self, request, user_id=None):
#         user = get_object_or_404(User, id=user_id)
#         try:
#             subscription = Subscription.objects.get(
#                 user=request.user, author=user)
#         except Subscription.DoesNotExist:
#             return Response(
#                 {'error': 'Вы не подписаны на этого автора.'},
#                 status=status.HTTP_400_BAD_REQUEST)
#         else:
#             subscription.delete()
#             return Response(
#                 {'Успешная отписка'},
#                 status=status.HTTP_204_NO_CONTENT)
#
#
# class SubscriptionListAPIView(generics.ListAPIView):
#     serializer_class = SubscriptionListSerializer
#     permission_classes = [IsAuthenticated]
#     pagination_class = LimitPagination
#
#     def get_queryset(self):
#         user = self.request.user
#         subscriptions = Subscription.objects.filter(user=user).order_by('-created_at')
#         return subscriptions.prefetch_related('author__recipes')
#
#     def get(self, request, *args, **kwargs):
#         queryset = self.paginate_queryset(self.get_queryset())
#         serializer = self.get_serializer(queryset, many=True, context={'request': request})
#         return self.get_paginated_response(serializer.data)


# class DownloadShoppingCartView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get(self, request):
#         shopping_list = ShoppingList.objects.filter(user=request.user)
#         recipe_ids = shopping_list.values_list('recipe', flat=True)
#         ingredients = IngredientRecipe.objects.filter(recipe__in=recipe_ids).values(
#             'ingredient__name',
#             'ingredient__measurement_unit'
#         ).annotate(
#             total_amount=Sum('amount')
#         )
#         ingredients_dict = {}
#         for ingredient in ingredients:
#             name = ingredient['ingredient__name']
#             unit = ingredient['ingredient__measurement_unit']
#             amount = ingredient['total_amount']
#             if name not in ingredients_dict:
#                 ingredients_dict[name] = {
#                     'unit': unit,
#                     'amount': amount
#                 }
#             else:
#                 ingredients_dict[name]['amount'] += amount
#         content = '\n'.join([
#             f"{name} - {data['amount']} {data['unit']}"
#             for name, data in ingredients_dict.items()
#         ])
#         response = HttpResponse(content, content_type='text/plain')
#         response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
#         return response

# class ShoppingListViewSet(viewsets.ModelViewSet):
#     serializer_class = ShoppingListSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_queryset(self):
#         return ShoppingList.objects.filter(user=self.request.user)
#
#     @action(detail=True, methods=['post'])
#     def add_to_cart(self, request, *args, **kwargs):
#         recipe_pk = self.kwargs.get('recipe_pk')
#         shopping_list = self.get_object()
#
#         try:
#             recipe = Recipe.objects.get(pk=recipe_pk)
#             shopping_list.recipes.add(recipe)
#             serializer = self.get_serializer(shopping_list)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except ObjectDoesNotExist:
#             raise serializers.ValidationError('Указанный рецепт не существует.')
#
#     @action(detail=True, methods=['delete'])
#     def remove_from_cart(self, request, *args, **kwargs):
#         recipe_id = request.data.get('recipe_id')
#         shopping_list = self.get_object()
#
#         try:
#             recipe = Recipe.objects.get(id=recipe_id)
#             shopping_list.recipes.remove(recipe)
#
#             if not shopping_list.recipes.exists():
#                 shopping_list.delete()
#
#             return Response(status=status.HTTP_204_NO_CONTENT)
#         except Recipe.DoesNotExist:
#             raise serializers.ValidationError('Указанный рецепт не существует')

