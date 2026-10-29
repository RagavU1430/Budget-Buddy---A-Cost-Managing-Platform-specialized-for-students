from rest_framework import serializers

from .models import SavingsGoal


class SavingsGoalSerializer(serializers.ModelSerializer):
    progress_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = SavingsGoal
        fields = [
            "id", "title", "description", "target_amount", "current_amount",
            "target_date", "priority", "is_completed", "progress_pct",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_completed", "progress_pct", "created_at", "updated_at"]

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
