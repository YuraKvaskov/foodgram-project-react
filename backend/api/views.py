from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from djoser.views import UserViewSet

from api.Serializers import TagSerializer, RecipeSerializer, IngredientSerializer, ShoppingListSerializer
from api.Serializers import	ChangePasswordSerializer, CustomUserSerializer
from api.Serializers import CustomUserCreateSerializer
from recipes.models import Recipe, Subscription, Ingredient, Tag, ShoppingList

User = get_user_model()


class ShoppingListViewSet(viewsets.ModelViewSet):

    queryset = ShoppingList.objects.all()
    serializer_class = ShoppingListSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def download_shopping_cart(self, request, pk=None):
        shopping_list = self.get_object()
        ingredients = shopping_list.recipes.values(
            'ingredients__name').annotate(
            total_amount=Sum('ingredients_amount__amount'))
        filename = f'shopping_list_{timezone.now().strftime("%Y%m%d%H%M%S")}.txt'
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        for ingredient in ingredients:
            response.write(
                f"{ingredient['ingredients__name']} — {ingredient['total_amount']}\n")

        return response

    @action(detail=True, methods=['post'])
    def add_to_shopping_cart(self, request, pk=None):
        shopping_list = self.get_object()
        recipe = Recipe.objects.get(
            pk=request.data.get('recipe_id'))

        if shopping_list.recipes.filter(
                pk=recipe.pk).exists():
            return Response(
                {'detail': 'Этот рецепт уже есть в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST)

        shopping_list.recipes.add(recipe)
        return Response(
            RecipeSerializer(recipe).data,
            status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def remove_from_shopping_cart(self, request, pk=None):
        shopping_list = self.get_object()
        recipe = Recipe.objects.get(
            pk=request.data.get('recipe_id'))

        if not shopping_list.recipes.filter(pk=recipe.pk).exists():
            return Response(
                {'detail': 'Этот рецепт не найден в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST)

        shopping_list.recipes.remove(recipe)
        return Response(
            {'detail': 'Рецепт успешно удален из списка покупок.'},
            status=status.HTTP_204_NO_CONTENT)


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        elif self.action == 'set_password':
            return ChangePasswordSerializer
        return CustomUserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    permission_classes = [IsAuthenticated]
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

    @action(detail=True, methods=['post'], url_path='subscribe')
    def subscribe(self, request, pk):
        user = request.user
        author = get_object_or_404(User, id=pk)
        if user != author:
            subscription = Subscription.objects.get_or_create(user=user, author=author)
            return Response({'success': True})
        return Response({'success': False, 'message': 'Вы не можете подписаться на самого себя.'})

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        subscriptions = Subscription.objects.filter(user=request.user)
        authors = [subscription.author for subscription in subscriptions]
        recipes = Recipe.objects.filter(author__in=authors)
        serializer = RecipeSerializer(recipes, many=True)
        results = []
        for subscription in subscriptions:
            author = subscription.author
            result = {
                'id': author.id,
                'email': author.email,
                'username': author.username,
                'first_name': author.first_name,
                'last_name': author.last_name,
                'recipes': [],
            }
            author_recipes = recipes.filter(author=author)
            serializer = RecipeSerializer(author_recipes, many=True)
            result['recipes'] = serializer.data
            results.append(result)
        return Response(results)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    serializer_class = RecipeSerializer

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

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        recipe.favorites.add(user)
        recipe.save()
        serializer = RecipeSerializer(recipe)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'])
    def unfavorite(self, request, pk=None):
        recipe = self.get_object()
        user = request.user
        recipe.favorites.remove(user)
        recipe.save()
        serializer = RecipeSerializer(recipe)
        return Response(serializer.data)

