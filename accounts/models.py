from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for StudyRAG.
    Allows authentication and extended profile attributes for personalized RAG assistance.
    """
    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
        help_text='Required. A valid email address for account notifications and login.',
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text='Profile picture',
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text='A short description of yourself and your study interests.',
    )
    learning_goals = models.CharField(
        max_length=255,
        blank=True,
        help_text='e.g., Python Backend, Machine Learning, Operating Systems',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username or self.email

    @property
    def display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.first_name:
            return self.first_name
        return self.username

    @property
    def avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        # Fallback to UI Avatars using username
        name_param = self.first_name or self.username or 'User'
        return f"https://ui-avatars.com/api/?name={name_param}&background=4f46e5&color=fff&rounded=true"
