from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from rest_framework import status, serializers
from rest_framework.response import Response

from recipes.models import Recipe, IngredientRecipe, Ingredient


class UserCreateSerializer(DjoserUserCreateSerializer):
	email = serializers.CharField(required=True)
	username = serializers.CharField(required=True)
	first_name = serializers.CharField(required=True)
	last_name = serializers.CharField(required=True)
	password = serializers.CharField(required=True)




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
		queryset=Ingredient.odjects.all())
	amount = serializers.IntegerField(write_only=True, min_value=1)

	class Meta:
		model = Ingredient
		fields = '__all__'

class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
	ingredients = IngredientCreateInRecipeSerializer(many=True)

	def validate_ingredients(self, value):

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

	def to_representation(self, instance):
		self.fields.pop('ingredients')
		representation = super().to_representation(instance)
		representation('ingredients') = IngredientRecipeSerializer(
			IngredientRecipe.object.filter(recipe=instance).all(), many=True).data
		return representation

	class Meta:
		model = Recipe
		fields = ('ingredients', 'tags', 'image', 'name', 'text', 'cooking_time')



