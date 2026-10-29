from django.urls import path
from .views import AnalyticsCategoryTrendsView, AnalyticsTrendsView, AnalyticsView

urlpatterns = [
    path("analytics/summary/", AnalyticsView.as_view(), name="analytics-summary"),
    path("analytics/trends/", AnalyticsTrendsView.as_view(), name="analytics-trends"),
    path("analytics/category-trends/", AnalyticsCategoryTrendsView.as_view(), name="analytics-category-trends"),
]
