from django.contrib.auth.forms import BaseUserCreationForm
from django.contrib.auth.models import User
from django import forms


class BowlPoolUserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")
