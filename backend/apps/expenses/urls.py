from rest_framework.routers import DefaultRouter

from .views import CategoryTrendsView, ExpenseViewSet, IncomeViewSet, MonthlySummaryView, MonthlyTrendsView
from django.urls import path

router = DefaultRouter()
router.register(r"expenses", ExpenseViewSet, basename="expense")
router.register(r"incomes", IncomeViewSet, basename="income")

urlpatterns = router.urls + [
    path("analytics/summary/", MonthlySummaryView.as_view()),
    path("analytics/trends/", MonthlyTrendsView.as_view()),
    path("analytics/category-trends/", CategoryTrendsView.as_view()),
]
