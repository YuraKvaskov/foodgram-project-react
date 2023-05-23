from rest_framework.pagination import LimitOffsetPagination, BasePagination
from rest_framework.response import Response


class CustomPagination(BasePagination):
    def paginate_queryset(self, queryset, request, view=None):
        recipes_limit = int(request.GET.get('recipes_limit', 0))
        self.recipes_limit = recipes_limit
        page_number = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 10))
        start_index = (page_number - 1) * limit
        end_index = start_index + limit
        if recipes_limit > 0:
            queryset = queryset[:recipes_limit]
        self.page_number = page_number
        self.limit = limit
        self.start_index = start_index
        self.end_index = end_index
        self.request = request
        self.count = queryset.count()
        return queryset[start_index:end_index]

    def get_paginated_response(self, data):
        return Response({
            'count': self.recipes_limit if self.recipes_limit > 0 else self.count,
            'results': data,
            'page_number': self.page_number,
            'has_next': self.end_index < self.count,
            'has_previous': self.start_index > 0,
        })