from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, filters
from recipes.models import Ingredient, Recipe, Tag

User = get_user_model()


class CustomIngredientFilter(FilterSet):
    name_starts_with = filters.CharFilter(field_name='name', lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ['name_starts_with']


class CustomRecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author',)

