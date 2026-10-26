from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model in StudyRAG."""
    list_display = ('username', 'email', 'first_name', 'last_name', 'learning_goals', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'learning_goals')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('StudyRAG Profile Details', {
            'fields': ('avatar', 'bio', 'learning_goals')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('StudyRAG Profile Details', {
            'fields': ('email', 'first_name', 'last_name', 'learning_goals', 'bio')
        }),
    )
