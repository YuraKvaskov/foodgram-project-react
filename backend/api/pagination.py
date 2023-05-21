from rest_framework.pagination import PageNumberPagination


class LimitPagination(PageNumberPagination):
    # page_size = 10
    page_size_query_param = 'limit'

    # def get_paginated_response(self, data):
    #     recipes_limit = self.request.query_params.get('recipes_limit')
    #     if recipes_limit is not None:
    #         for item in data:
    #             item['recipes'] = item['recipes'][:int(recipes_limit)]
    #     return super().get_paginated_response(data)