from decimal import Decimal
from rest_framework import decorators, response, status, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import SavingsGoal
from .serializers import SavingsGoalSerializer


class SavingsGoalViewSet(viewsets.ModelViewSet):
    serializer_class = SavingsGoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavingsGoal.objects.filter(user=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def deposit(self, request, pk=None):
        goal = self.get_object()
        try:
            amount = Decimal(str(request.data["amount"]))
        except (KeyError, TypeError, ValueError):
            return response.Response({"amount": "A valid amount is required."}, status=400)
        if amount <= 0:
            return response.Response({"amount": "Amount must be positive."}, status=400)
        goal.current_amount += amount
        goal.save()
        return response.Response(self.get_serializer(goal).data, status=status.HTTP_200_OK)
