from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=254)
    username = models.CharField(max_length=150, validators=[RegexValidator(
        r'^[\w.@+-]+$', 'Enter a valid username.')], unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    password = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'username'],
                name='unique_email_and_username')
        ]

    def __str__(self):
        return self.email
