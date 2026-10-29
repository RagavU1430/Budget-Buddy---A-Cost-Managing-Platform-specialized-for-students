from rest_framework.routers import DefaultRouter

from .views import SavingsGoalViewSet

router = DefaultRouter()
router.register("goals", SavingsGoalViewSet, basename="goal")
urlpatterns = router.urls
