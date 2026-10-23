from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ["email", "username", "role", "is_staff", "is_active"]
    list_filter = ["role", "is_staff", "is_active"]
    fieldsets = UserAdmin.fieldsets + (("BudgetBuddy", {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("BudgetBuddy", {"fields": ("email", "role")}),)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "monthly_income", "currency"]
    search_fields = ["user__email", "user__username"]
