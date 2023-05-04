from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from recipes.models import Recipe, IngredientRecipe, Ingredient

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


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')


class CustomUserCreateSerializer(UserCreateSerializer):
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


class RecipeListSerializer(serializers.ModelSerializer):
    """Получение списка рецептов"""

    ingredients = serializers.SerializerMethodField()
    is_favorite = serializers.BooleanField()

    def get_ingredients(self, obj):
        return IngredientRecipeSerializer(
            IngredientRecipe.objects.filter(recipe=obj).all(), many=True
        ).data

    class Meta:
        model = Recipe
        fields = ('name', 'ingredients', 'is_favorite', 'text')


class IngredientCreateInRecipeSerializer(serializers.ModelSerializer):
    recipe = serializers.PrimaryKeyRelatedField(read_only=True)
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = Ingredient
        fields = '__all__'

class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    ingredients = IngredientCreateInRecipeSerializer(many=True)

    def validate_ingredients(self, value):
        pass
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)

        create_ingredients = [
            IngredientRecipe(
                recipe=recipe,
                ingredient=ingredient['ingredients'],
                amount=ingredients['amount']
            )
            for ingredient in ingredients
            ]
        IngredientRecipe.objects.bulk_create(
            create_ingredients
        )
        return recipe

    def update(self, instance, validated_data):
        pass
    def to_representation(self, instance):
        self.fields.pop('ingredients')
        representation = super().to_representation(instance)
        # representation('ingredients') = IngredientRecipeSerializer(
        # 	IngredientRecipe.object.filter(recipe=instance).all(), many=True).data
        # return representation

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')



