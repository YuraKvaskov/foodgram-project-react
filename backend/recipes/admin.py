from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from recipes.models import Ingredient, Recipe, Tag, IngredientRecipe, Favorite, Subscription, ShoppingList

User = get_user_model()

admin.site.register(User, UserAdmin)
admin.site.register(Ingredient)
admin.site.register(Recipe)
admin.site.register(Tag)
admin.site.register(IngredientRecipe)
admin.site.register(Favorite)
admin.site.register(Subscription)
admin.site.register(ShoppingList)


class CustomUserAdmin(UserAdmin):
    actions = ['block_users', 'unblock_users', 'reset_passwords']

    def block_users(self, request, queryset):
        queryset.update(is_active=False)
    block_users.short_description = "Block selected users"

    def unblock_users(self, request, queryset):
        queryset.update(is_active=True)
    unblock_users.short_description = "Unblock selected users"

    def reset_passwords(self, request, queryset):
        for user in queryset:
            user.set_unusable_password()
            user.save()
    reset_passwords.short_description = "Reset passwords of selected users"


class RecipeAdmin(admin.ModelAdmin):
    actions = ['delete_recipes']

    def delete_recipes(self, request, queryset):
        for recipe in queryset:
            recipe.delete()
    delete_recipes.short_description = "Delete selected recipes"


class IngredientAdmin(admin.ModelAdmin):
    list_display = ['name', 'measurement_unit']
    list_filter = ['name']