import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from djoser.serializers import UserCreateSerializer

from recipes.models import (
    Recipe,
    Ingredient,
    Tag,
    ShoppingList,
    Favorite,
    IngredientRecipe,
    Subscription,
)

User = get_user_model()


class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(
        style={'input_type': 'password'})
    current_password = serializers.CharField(
        style={'input_type': 'password'})

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Текущий пароль неверен.")
        return value


class UserCreateSerializer(UserCreateSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'password')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            'email': data['email'],
            'id': data['id'],
            'username': data['username'],
            'first_name': data['first_name'],
            'last_name': data['last_name'],
        }


class UserReadSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed')

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.following.filter(
            author=obj).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'color',
            'slug')
        read_only_fields = '__all__',


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'
        read_only_fields = '__all__',


class IngredientsEditSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserReadSerializer(read_only=True)
    ingredients = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)
    is_favorite = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id',
                  'tags',
                  'author',
                  'ingredients',
                  'is_favorite',
                  'is_in_shopping_cart',
                  'name',
                  'image',
                  'text',
                  'cooking_time',
                  )

    def get_ingredients(self, obj):
        recipe = obj
        ingredients = recipe.ingredients.values(
            'id',
            'name',
            'measurement_unit',
            amount=F('recipe_ingredients__amount')
        )
        return ingredients

    def get_is_favorite(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.favorites.filter(user=user).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.shopping_list.filter(user=user).exists()
        return False


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class RecipeCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(
        required=False,
        allow_null=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        required=True,
        write_only=True)
    ingredients = IngredientsEditSerializer(
        many=True)

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ('author',)

    def validate(self, data):
        ingredients = data['ingredients']
        ingredient_list = []
        for items in ingredients:
            ingredient = get_object_or_404(
                Ingredient, id=items['id'])
            if ingredient in ingredient_list:
                raise serializers.ValidationError(
                    'Ингредиент должен быть уникальным!')
            ingredient_list.append(ingredient)
        tags = data['tags']
        if not tags:
            raise serializers.ValidationError(
                'Нужен хотя бы один тэг для рецепта!')
        tag_ids = [
            tag.id if isinstance(tag, Tag) else tag for tag in tags]
        tags = Tag.objects.filter(id__in=tag_ids)
        if len(tag_ids) != len(tags):
            invalid_tags = [
                tag_id
                for tag_id in tag_ids
                if tag_id not in tags.values_list('id', flat=True)
            ]
            error_message = (
                'Недопустимые данные. Некоторые теги не найдены: '
                f'{invalid_tags}.'
            )
            raise serializers.ValidationError(error_message)
        data['tags'] = tags
        return data

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) < 1:
            raise serializers.ValidationError(
                'Время приготовления >= 1!')
        return cooking_time

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Минимум 1 ингредиент должен быть указан.')
        ingredient_ids = []
        for ingredient in ingredients:
            ingredient_id = ingredient.get('id')
            amount = ingredient.get('amount')
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    'Ингредиенты должны быть уникальными.')
            ingredient_ids.append(ingredient_id)
            if amount < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше или равно 1.')
        return ingredients

    def create_ingredients(self, ingredients, recipe):
        ingredient_instances = []
        for ingredient in ingredients:
            ingredient_instances.append(
                IngredientRecipe(
                    recipe=recipe,
                    ingredient_id=ingredient.get('id'),
                    amount=ingredient.get('amount')
                )
            )
        IngredientRecipe.objects.bulk_create(ingredient_instances)

    @transaction.atomic()
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    @transaction.atomic()
    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)
        if 'tags' in validated_data:
            tag_ids = validated_data.pop('tags')
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = 'id', 'name', 'image', 'cooking_time'
        read_only_fields = '__all__',


class SubscriptionListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='author.id')
    email = serializers.EmailField(source='author.email')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id',
                  'email',
                  'username',
                  'first_name',
                  'last_name',
                  'is_subscribed',
                  'recipes',
                  'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            author = obj.author
            if user.following.filter(author=author).exists():
                return True
        return False

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = int(request.GET.get('recipes_limit', 0))
        queryset = Recipe.objects.filter(author=obj.author)
        if recipes_limit > 0:
            queryset = queryset[:recipes_limit]
        return RecipeSerializer(
            queryset, many=True, context={'request': request}).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['recipes'] = self.get_recipes(instance)
        return representation


class FavoriteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all())
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all())

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')


class ShoppingListSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all())
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all())

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe')
