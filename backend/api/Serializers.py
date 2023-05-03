from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from rest_framework import status, serializers
from rest_framework.response import Response


class UserCreateSerializer(DjoserUserCreateSerializer):
	email = serializers.CharField(required=True)
	username = serializers.CharField(required=True)
	first_name = serializers.CharField(required=True)
	last_name = serializers.CharField(required=True)
	password = serializers.CharField(required=True)


