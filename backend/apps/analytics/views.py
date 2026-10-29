from datetime import date
from django.db.models import Sum
from rest_framework import response, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from apps.expenses.models import Expense, Income


class AnalyticsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        try:
            raw_month = request.query_params.get("month")
            if raw_month and len(raw_month) == 7:
                year, month = map(int, raw_month.split("-"))
            else:
                year = int(request.query_params.get("year", today.year))
                month = int(raw_month or today.month)
        except ValueError:
            return response.Response({"detail": "year and month must be integers."}, status=400)
        expenses = Expense.objects.filter(user=request.user, date__year=year, date__month=month)
        incomes = Income.objects.filter(user=request.user, date__year=year, date__month=month)
        return response.Response({
            "year": year, "month": month,
            "income": incomes.aggregate(total=Sum("amount"))["total"] or 0,
            "expenses": expenses.aggregate(total=Sum("amount"))["total"] or 0,
            "by_category": list(expenses.values("category").annotate(total=Sum("amount")).order_by("-total")),
        })


class AnalyticsTrendsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rows = list(Expense.objects.filter(user=request.user).values(
            "date__year", "date__month"
        ).annotate(expenses=Sum("amount")).order_by("-date__year", "-date__month"))
        paginator = PageNumberPagination()
        paginator.page_size = min(int(request.query_params.get("page_size", 20)), 100)
        return paginator.get_paginated_response(paginator.paginate_queryset(rows, request))


class AnalyticsCategoryTrendsView(AnalyticsTrendsView):
    def get(self, request):
        rows = list(Expense.objects.filter(user=request.user).values(
            "category", "date__year", "date__month"
        ).annotate(expenses=Sum("amount")).order_by("-date__year", "-date__month", "category"))
        paginator = PageNumberPagination()
        paginator.page_size = min(int(request.query_params.get("page_size", 20)), 100)
        return paginator.get_paginated_response(paginator.paginate_queryset(rows, request))
