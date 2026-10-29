from rest_framework import decorators, response, status, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") in {"1", "true", "yes"}:
            queryset = queryset.filter(is_read=False)
        return queryset

    @decorators.action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return response.Response(self.get_serializer(notification).data)

    @decorators.action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return response.Response({"updated": True}, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        return response.Response({"count": self.get_queryset().filter(is_read=False).count()})
