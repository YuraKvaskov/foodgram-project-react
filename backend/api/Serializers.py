from django.contrib.auth import get_user_model
from django.db.models import Count
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from drf_base64.fields import Base64ImageField
from rest_framework.generics import get_object_or_404

from recipes.models import Recipe, Ingredient, Tag, ShoppingList, IngredientRecipe, Subscription, Favorite

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
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'password')

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
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'is_subscribed']

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return user.following.filter(author=obj).exists()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


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
                  'tags',
                  'cooking_time',
                  )

    def get_ingredients(self, obj):
        ingredient_recipes = IngredientRecipe.objects.filter(recipe=obj)
        return IngredientRecipeSerializer(ingredient_recipes, many=True).data

    def get_is_favorite(self, obj):
        return obj.favorites.filter(user=self.context['request'].user).exists()

    def get_is_in_shopping_cart(self, obj):
        return obj.shopping_list.filter(user=self.context['request'].user).exists()


class RecipeCreateSerializer(serializers.ModelSerializer):
    image = Base64ImageField(
        max_length=None,
        use_url=True)
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all())
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
        for tag in tags:
            if not isinstance(tag, Tag):
                raise serializers.ValidationError(
                    f'Недопустимые данные. Ожидался Tag, но был получен {type(tag)}.')
        return data

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) < 1:
            raise serializers.ValidationError(
                'Время приготовления >= 1!')
        return cooking_time

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Мин. 1 ингредиент в рецепте!')
        for ingredient in ingredients:
            if int(ingredient.get('amount')) < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента >= 1!')
        return ingredients

    def create_ingredients(self, ingredients, recipe):
        for ingredient in ingredients:
            IngredientRecipe.objects.create(
                recipe=recipe,
                ingredient_id=ingredient.get('id'),
                amount=ingredient.get('amount'), )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.ingredients.clear()
            self.create_ingredients(ingredients, instance)
        if 'tags' in validated_data:
            tag_ids = [tag.id if isinstance(tag, Tag) else tag for tag in validated_data.pop('tags')]
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }).data


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    author = UserReadSerializer(read_only=True)
    user = UserReadSerializer(read_only=True)
    recipes = RecipeSerializer(many=True, read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'author', 'user', 'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request:
            return Subscription.objects.filter(author=obj.author, user=request.user).exists()
        return False

    def get_recipes_count(self, obj):
        return obj.author.recipes.aggregate(count=Count('id'))['count']


class SubscriptionListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='author.email')
    username = serializers.CharField(source='author.username')
    first_name = serializers.CharField(source='author.first_name')
    last_name = serializers.CharField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = RecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = ('id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            author = obj.author
            if user.following.filter(author=author).exists():
                return True
        return False

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['recipes'] = RecipeSerializer(
            instance.author.recipes.all(),
            many=True,
            context={'request': self.context.get('request')}
        ).data
        return representation


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        fields = ('id', 'name', 'image', 'cooking_time')
        return {key: value for key, value in data.items() if key in fields}


class ShoppingListSerializer(serializers.ModelSerializer):
    recipe = RecipeSerializer(read_only=True)
    recipe_data = serializers.SerializerMethodField()
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ShoppingList
        fields = ['id', 'recipe', 'user', 'recipe_data']

    def get_recipe_data(self, obj):
        recipe = Recipe.objects.get(id=obj.recipes.first().id)
        serializer = RecipeSerializer(recipe)
        return serializer.data

    def create(self, validated_data):
        recipe_id = self.context.get('view').kwargs.get('recipe_id')
        recipe = Recipe.objects.get(id=recipe_id)
        shopping_list, _ = ShoppingList.objects.get_or_create(user=self.context['request'].user)
        if recipe not in shopping_list.recipes.all():
            shopping_list.recipes.add(recipe)
            return shopping_list
        else:
            raise serializers.ValidationError('Этот рецепт уже есть в списке покупок')