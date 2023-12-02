from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth import get_user_model
from django import forms


class BowlPoolUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ("email", "first_name", "last_name")
