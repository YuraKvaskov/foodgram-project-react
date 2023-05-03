from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from djoser.views import UserViewSet

from api.Serializers import RecipeListSerializer, RecipeCreateUpdateSerializer
from api.permissions import IsOwnerOrReadOnly
from recipes.models import Recipe


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
