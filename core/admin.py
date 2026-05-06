from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "role", "is_active_staff")
    list_filter = ("role", "is_active_staff", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("role", "phone", "photo", "is_active_staff")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información adicional", {"fields": ("role", "phone", "is_active_staff")}),
    )
