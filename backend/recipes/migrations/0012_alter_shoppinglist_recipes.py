# Generated by Django 3.2.11 on 2023-05-10 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0011_alter_shoppinglist_recipes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shoppinglist',
            name='recipes',
            field=models.ManyToManyField(to='recipes.Recipe', verbose_name='Рецепты в списке покупок'),
        ),
    ]
