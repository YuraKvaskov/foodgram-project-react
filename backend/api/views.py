from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from djoser.views import UserViewSet

from api.Serializers import RecipeListSerializer, RecipeCreateUpdateSerializer
from api.Serializers import	ChangePasswordSerializer, CustomUserSerializer
from api.Serializers import CustomUserCreateSerializer
from api.permissions import IsOwnerOrReadOnly
from recipes.models import Recipe,

User = get_user_model()


class CustomUserViewSet(UserViewSet):
	queryset = User.objects.all()

	def get_serializer_class(self):
		if self.action == 'create':
			return CustomUserCreateSerializer
		elif self.action == 'set_password':
			return ChangePasswordSerializer
		return CustomUserSerializer

	def create(self, request, *args, **kwargs):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		serializer.save()
		headers = self.get_success_headers(serializer.data)
		return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

	permission_classes = [IsAuthenticated]

	@action(detail=False, methods=['post'])
	def set_password(self, request):
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = self.request.user
		user.set_password(serializer.validated_data['new_password'])
		user.save()
		return Response(
			{'detail': 'Пароль успешно изменен'},
			status=status.HTTP_204_NO_CONTENT)



class RecipesViewSet(ModelViewSet):
	queryset = Recipe.objects.all()
	http_method_names = ('get', 'post', 'patch')
	permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)

	def perform_create(self, serializer):
		serializer.save(author=self.request.user)

	def get_serializer_class(self):
		if self.action in ('create', 'update', 'partial_update'):
			return RecipeCreateUpdateSerializer
		return RecipeListSerializer

	def get_queryset(self):
		queryset = Recipe.objects.add_user_annotations(self.request.user.pk)
		author = self.request.query_params.get('author', None)
		if author:
			queryset = queryset.filter(author=author)

		return queryset
