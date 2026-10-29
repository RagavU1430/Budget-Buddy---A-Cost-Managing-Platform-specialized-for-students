from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Budget
from .serializers import BudgetSerializer


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Budget.objects.filter(user=self.request.user)
        if self.request.query_params.get("month"):
            queryset = queryset.filter(month=self.request.query_params["month"] + "-01")
        if self.request.query_params.get("category"):
            queryset = queryset.filter(category=self.request.query_params["category"])
        return queryset
