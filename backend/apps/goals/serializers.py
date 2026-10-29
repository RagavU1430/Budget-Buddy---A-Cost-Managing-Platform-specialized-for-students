from rest_framework import serializers

from .models import SavingsGoal


class SavingsGoalSerializer(serializers.ModelSerializer):
    progress_pct = serializers.FloatField(read_only=True)
    progress_percentage = serializers.FloatField(source="progress_pct", read_only=True)
    saved_amount = serializers.DecimalField(source="current_amount", max_digits=12, decimal_places=2, required=False)
    deadline = serializers.DateField(source="target_date", required=False, allow_null=True)

    class Meta:
        model = SavingsGoal
        fields = [
            "id", "title", "description", "target_amount", "current_amount", "saved_amount",
            "target_date", "deadline", "priority", "is_completed", "progress_pct", "progress_percentage",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "current_amount", "is_completed", "progress_pct", "created_at", "updated_at"]

    def validate(self, attrs):
        target = attrs.get("target_amount", getattr(self.instance, "target_amount", None))
        current = attrs.get("current_amount", getattr(self.instance, "current_amount", 0))
        if target is not None and target <= 0:
            raise serializers.ValidationError({"target_amount": "Target amount must be positive."})
        if current < 0:
            raise serializers.ValidationError({"current_amount": "Current amount cannot be negative."})
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
