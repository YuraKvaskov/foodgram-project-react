from django.contrib.auth import get_user_model
from django_filters.rest_framework import FilterSet, filters
from django.db.models import Q

from recipes.models import Recipe, Tag, Ingredient

User = get_user_model()


class CustomIngredientFilter(FilterSet):
    name_contains = filters.CharFilter(
        field_name='name',
        method='filter_name_contains'
    )

    class Meta:
        model = Ingredient
        fields = ['name_contains']

    def filter_name_contains(self, queryset, name, value):
        lowercase_value = value.lower()
        return queryset.filter(
            Q(name__startswith=lowercase_value) |
            Q(name__icontains=lowercase_value)
        )


class CustomRecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    is_favorited = filters.BooleanFilter(
        method='is_favorited_filter', lookup_expr='isnull', exclude=True)
    is_in_shopping_cart = filters.BooleanFilter(
        method='shopping_list_filter', lookup_expr='isnull')

    class Meta:
        model = Recipe
        fields = ('tags', 'author')

    def is_favorited_filter(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def shopping_list_filter(self, queryset, name, value):
        if value and not self.request.user.is_anonymous:
            return queryset.filter(shopping_list__user=self.request.user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('tags', 'author',)
