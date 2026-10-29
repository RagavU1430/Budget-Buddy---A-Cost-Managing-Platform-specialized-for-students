from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "report_type", "month", "file_format", "file", "download_url", "summary", "generated_at"]
        read_only_fields = ["id", "file", "download_url", "summary", "generated_at"]

    def get_download_url(self, obj):
        return obj.file.url if obj.file else None
