# Generated by Django 3.2.11 on 2023-05-20 21:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0018_rename_recipes_shoppinglist_recipe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='favorite',
            name='recipe',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_recipes', to='recipes.recipe', verbose_name='Рецепт'),
        ),
        migrations.AlterField(
            model_name='shoppinglist',
            name='recipe',
            field=models.ManyToManyField(related_name='shopping_lists', to='recipes.Recipe', verbose_name='Рецепты в списке покупок'),
        ),
    ]
