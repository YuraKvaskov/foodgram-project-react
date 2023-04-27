from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
   """Кастомный класс пользователя."""
   is_subscribed = models.BooleanField(default=False)