from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Позволяет изменять данные только автору или администратору.
    Доступ на чтение разрешен для всех.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_staff
