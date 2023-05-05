from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from recipes.models import Recipe, Ingredient, Tag, ShoppingList

User = get_user_model()


class ShoppingListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingList
        fields = '__all__'


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


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True)
    tags = TagSerializer(many=True)

    class Meta:
        model = Recipe
        fields = ('id',
                  'author',
                  'title',
                  'image',
                  'text',
                  'ingredients',
                  'tags',
                  'cooking_time',
                  'pub_date')

