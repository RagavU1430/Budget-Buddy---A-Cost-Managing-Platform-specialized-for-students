from datetime import date
from django.http import FileResponse
from rest_framework import decorators, response, status, viewsets
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsPremium
from .generator import build_report
from .models import Report
from .serializers import ReportSerializer


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated, IsPremium]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user)

    @decorators.action(detail=False, methods=["post"])
    def generate(self, request):
        return self.create(request)

    def create(self, request, *args, **kwargs):
        raw_month = request.data.get("month", "")
        try:
            month = date.fromisoformat(raw_month + "-01" if len(raw_month) == 7 else raw_month)
        except ValueError:
            return response.Response({"month": "Use YYYY-MM or YYYY-MM-DD."}, status=400)
        report_type = request.data.get("report_type", Report.ReportType.MONTHLY)
        file_format = request.data.get("file_format", Report.Format.PDF)
        if report_type not in Report.ReportType.values or file_format not in Report.Format.values:
            return response.Response({"detail": "Invalid report type or format."}, status=400)
        content, summary = build_report(request.user, month, report_type, file_format)
        report = Report.objects.create(user=request.user, month=month, report_type=report_type, file_format=file_format, summary=summary)
        report.file.save(content.name, content, save=True)
        return response.Response(self.get_serializer(report).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        report = self.get_object()
        if not report.file:
            return response.Response({"detail": "Report file is unavailable."}, status=404)
        return FileResponse(report.file.open("rb"), as_attachment=True, filename=report.file.name.rsplit("/", 1)[-1])
