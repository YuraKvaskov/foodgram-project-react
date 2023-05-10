from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets, mixins, generics, permissions
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from djoser.views import UserViewSet
from rest_framework.views import APIView

from api.Serializers import TagSerializer, RecipeSerializer, IngredientSerializer, ShoppingListSerializer, \
    FavoriteSerializer, SubscriptionListSerializer, SubscriptionCreateSerializer, UserReadSerializer
from api.Serializers import	ChangePasswordSerializer
from api.Serializers import UserCreateSerializer, RecipeCreateSerializer
from recipes.models import Recipe, Subscription, Ingredient, Tag, ShoppingList, Favorite

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action == 'set_password':
            return ChangePasswordSerializer
        return UserReadSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


    @action(detail=False, methods=['post'])
    def set_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response(
            {'detail': 'Пароль успешно изменен'},
            status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer

    def get_serializer_class(self):
        if self.action == 'create' or 'update':
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all()
        tag = self.request.query_params.get('tag')
        author = self.request.query_params.get('author')
        favorites = self.request.query_params.get('favorites')

        if tag:
            queryset = queryset.filter(tags__slug=tag)
        if author:
            queryset = queryset.filter(author__username=author)
        if favorites:
            queryset = queryset.filter(favorites__user=self.request.user)

        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'])
    def ingredients(self, request, pk=None):
        recipe = self.get_object()
        ingredients = recipe.ingredients.all()
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def tags(self, request, pk=None):
        recipe = self.get_object()
        tags = recipe.tags.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def add_to_favorite(self, request, pk=None):
        recipe = self.get_object()
        if Favorite.objects.filter(recipe=recipe, user=request.user).exists():
            return Response(
                {'error': 'This recipe is already in your favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite = Favorite.objects.create(recipe=recipe, user=request.user)
        serializer = FavoriteSerializer(favorite.recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_from_favorite(self, request, pk=None):
        recipe = self.get_object()
        try:
            favorite = Favorite.objects.get(recipe=recipe, user=request.user)
        except Favorite.DoesNotExist:
            return Response(
                {'error': 'This recipe is not in your favorites'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionViewSet(viewsets.GenericViewSet,
                          mixins.ListModelMixin,
                          mixins.CreateModelMixin,
                          mixins.DestroyModelMixin):
    serializer_class = SubscriptionCreateSerializer
    # permission_classes = [IsAuthenticated]
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
        subscription, created = Subscription.objects.get_or_create(user=request.user, author=user)
        serializer = self.get_serializer(subscription)

        user_serializer = UserReadSerializer(user, context={'request': request})
        return Response({
            'user': user_serializer.data,
            'recipes_count': user.recipes.count(),
            'message': 'Подписка успешно создана'
        }, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, user_id=None):
        user = get_object_or_404(User, id=user_id)
        try:
            subscription = Subscription.objects.get(user=request.user, author=user)
        except Subscription.DoesNotExist:
            return Response({'error': 'Вы не подписаны на этого автора.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            subscription.delete()
            return Response({'Успешная отписка'}, status=status.HTTP_204_NO_CONTENT)


class SubscriptionListAPIView(generics.ListAPIView):
    serializer_class = SubscriptionListSerializer

    def get_queryset(self):
        user = self.request.user
        subscriptions = Subscription.objects.filter(user=user)
        return subscriptions.prefetch_related('author__recipes')

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            results = {
                'count': self.paginator.count,
                'results': serializer.data
            }
            return self.get_paginated_response(results)
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        results = {
            'count': len(serializer.data),
            'results': serializer.data
        }
        return Response(results)


class DownloadShoppingCartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        shopping_list = ShoppingList.objects.filter(user=request.user)
        ingredients = shopping_list.values('recipes__ingredients__name', 'recipes__ingredients__measurement_unit').annotate(total_amount=Sum('recipes__ingredient_recipes__amount'))
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

        content = '\n'.join([f"{name} - {data['amount']} {data['unit']}" for name, data in ingredients_dict.items()])
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response


class ShoppingListViewSet(viewsets.ModelViewSet):
    serializer_class = ShoppingListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ShoppingList.objects.filter(user=self.request.user)

    def create(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
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
        try:
            shopping_list = self.get_queryset().get(recipes=recipe_id)
        except ShoppingList.DoesNotExist:
            return Response({'error': 'Такого рецепта нет в списке покупок'}, status=status.HTTP_400_BAD_REQUEST)
        shopping_list.recipes.remove(recipe_id)
        if not shopping_list.recipes.all():
            shopping_list.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, *args, **kwargs):
        return self.shopping_cart(request, *args, **kwargs)




