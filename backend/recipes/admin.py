from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from import_export.admin import ImportExportMixin

from recipes.models import (
    Ingredient,
    Recipe,
    Tag,
    IngredientRecipe,
    Favorite,
    Subscription,
    ShoppingList
)

User = get_user_model()


class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
        ('Разрешения', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    actions = ['block_users', 'unblock_users', 'reset_passwords']

    def block_users(self, request, queryset):
        queryset.update(is_active=False)
    block_users.short_description = "Заблокировать пользователя"

    def unblock_users(self, request, queryset):
        queryset.update(is_active=True)
    unblock_users.short_description = "Разблокировать пользователя"

    def reset_passwords(self, request, queryset):
        for user in queryset:
            user.set_unusable_password()
            user.save()
    reset_passwords.short_description = "Сбросить пароль пользователя"


class IngredientRecipeInline(admin.TabularInline):
    model = IngredientRecipe


class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'cooking_time', 'get_favorite_count')
    list_filter = ('author__email', 'author__first_name')
    search_fields = ('name', 'author__email', 'author__first_name')
    inlines = [IngredientRecipeInline]

    def get_favorite_count(self, obj):
        return obj.favorites.count()

    get_favorite_count.short_description = 'Число добавлений в избранное'


class IngredientAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug')


class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')


class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'get_recipe_names')
    search_fields = ('user__email',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email владельца списка'

    def get_recipe_names(self, obj):
        return ', '.join([r.title for r in obj.recipes.all()])
    get_recipe_names.short_description = 'Рецепты в списке покупок'


admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Favorite, FavoriteAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(ShoppingList, ShoppingListAdmin)
admin.site.register(User, CustomUserAdmin)
