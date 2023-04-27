from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.db import models

from users.models import User


class Ingredient(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=200,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Название'
    )
    color = models.CharField(
        max_length=7,
        unique=True,
        verbose_name='Цветовой HEX-код',
        help_text='HEX code'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        verbose_name='slug',
        validators=[
            RegexValidator(
                regex=r'^[-a-zA-Z0-9_]+$'
            )
        ])

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецепта приготовления блюд"""
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes'
    )
    name = models.CharField(max_length=200)
    image = models.CharField(
        max_length=100000,
        validators=[RegexValidator(
            r'^[a-zA-Z0-9+/=]+\Z',
            'Invalid Base64 format.')])
    text = models.TextField()
    ingredient = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        through_fields=('ingredient', 'recipe'))
    tag = models.ForeignKey(Tag, on_delete=models.SET_NULL)
    cooking_time = models.PositiveIntegerField(validators=[
        MinValueValidator(1),
        MaxValueValidator(1440),
    ])

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientRecipe(models.Model):
    amount = models.PositiveIntegerField(verbose_name='Количество')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'