from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Expense, Income
from .serializers import ExpenseSerializer, IncomeSerializer
from apps.notifications.utils import check_budget_alerts


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user)
        params = self.request.query_params
        for field in ("category", "payment_method"):
            if params.get(field):
                queryset = queryset.filter(**{field: params[field]})
        if params.get("month"):
            try:
                year, month = map(int, params["month"].split("-"))
                queryset = queryset.filter(date__year=year, date__month=month)
            except ValueError:
                return queryset.none()
        if params.get("date_from"):
            queryset = queryset.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(date__lte=params["date_to"])
        if params.get("search"):
            queryset = queryset.filter(title__icontains=params["search"])
        return queryset

    def perform_create(self, serializer):
        expense = serializer.save()
        check_budget_alerts(expense.user)

    def perform_update(self, serializer):
        expense = serializer.save()
        check_budget_alerts(expense.user)


class IncomeViewSet(viewsets.ModelViewSet):
    serializer_class = IncomeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Income.objects.filter(user=self.request.user)
        params = self.request.query_params
        if params.get("source_type"):
            queryset = queryset.filter(source_type=params["source_type"])
        if params.get("month"):
            try:
                year, month = map(int, params["month"].split("-"))
                queryset = queryset.filter(date__year=year, date__month=month)
            except ValueError:
                return queryset.none()
        if params.get("date_from"):
            queryset = queryset.filter(date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(date__lte=params["date_to"])
        return queryset


def _month(value):
    if value:
        year, month = map(int, value.split("-"))
        return date(year, month, 1)
    today = date.today()
    return date(today.year, today.month, 1)


class MonthlySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            month = _month(request.query_params.get("month"))
        except (TypeError, ValueError):
            return Response({"detail": "month must use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        expenses = Expense.objects.filter(user=request.user, date__year=month.year, date__month=month.month)
        incomes = Income.objects.filter(user=request.user, date__year=month.year, date__month=month.month)
        from apps.budgets.models import Budget
        budgets = Budget.objects.filter(user=request.user, month=month)
        total_expense = expenses.aggregate(value=Sum("amount"))["value"] or Decimal("0")
        total_income = incomes.aggregate(value=Sum("amount"))["value"] or Decimal("0")
        total_budget = budgets.aggregate(value=Sum("limit_amount"))["value"] or Decimal("0")
        days = monthrange(month.year, month.month)[1]
        remaining_days = max(days - date.today().day + 1, 1) if month == date.today().replace(day=1) else days
        by_category = []
        for category, label in Expense.Category.choices:
            spent = expenses.filter(category=category).aggregate(value=Sum("amount"))["value"] or Decimal("0")
            limit = budgets.filter(category=category).values_list("limit_amount", flat=True).first() or Decimal("0")
            by_category.append({"category": category, "spent": spent, "budget_limit": limit,
                                "utilization_pct": round(float(spent / limit * 100), 2) if limit else 0.0})
        top = expenses.order_by("-amount").first()
        return Response({
            "month": month.strftime("%B %Y"), "total_income": total_income, "total_expense": total_expense,
            "net_balance": total_income - total_expense, "total_budget_limit": total_budget,
            "budget_utilization_pct": round(float(total_expense / total_budget * 100), 2) if total_budget else 0.0,
            "safe_daily_spend": max(total_budget - total_expense, Decimal("0")) / remaining_days,
            "remaining_days": remaining_days, "category_breakdown": by_category,
            "payment_method_breakdown": list(expenses.values("payment_method").annotate(total=Sum("amount")).order_by("payment_method")),
            "income_source_breakdown": list(incomes.values("source_type").annotate(total=Sum("amount")).order_by("source_type")),
            "top_expense": {"title": top.title, "amount": top.amount, "category": top.category, "date": top.date} if top else None,
            "recent_expenses": list(expenses.values("id", "title", "amount", "category", "date", "payment_method")[:5]),
        })


class MonthlyTrendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            count = min(max(int(request.query_params.get("months", 6)), 1), 12)
        except ValueError:
            count = 6
        today = date.today().replace(day=1)
        rows = []
        for offset in range(count - 1, -1, -1):
            year, month = today.year, today.month - offset
            while month <= 0:
                year, month = year - 1, month + 12
            expenses = Expense.objects.filter(user=request.user, date__year=year, date__month=month).aggregate(v=Sum("amount"))["v"] or 0
            incomes = Income.objects.filter(user=request.user, date__year=year, date__month=month).aggregate(v=Sum("amount"))["v"] or 0
            from apps.budgets.models import Budget
            budget = Budget.objects.filter(user=request.user, month=date(year, month, 1)).aggregate(v=Sum("limit_amount"))["v"] or 0
            rows.append({"month": date(year, month, 1), "month_label": date(year, month, 1).strftime("%b %Y"),
                         "income": incomes, "expense": expenses, "net": incomes - expenses, "budget": budget})
        return Response(rows)


class CategoryTrendsView(MonthlyTrendsView):
    def get(self, request):
        try:
            count = min(max(int(request.query_params.get("months", 3)), 1), 12)
        except ValueError:
            count = 3
        today = date.today().replace(day=1)
        rows = []
        for offset in range(count - 1, -1, -1):
            year, month = today.year, today.month - offset
            while month <= 0:
                year, month = year - 1, month + 12
            rows.extend(Expense.objects.filter(user=request.user, date__year=year, date__month=month)
                        .values("category").annotate(total=Sum("amount"))
                        .values("category", "total"))
        return Response(rows)
