from django.urls import path
from . import views

urlpatterns = [
    path(
        "<int:bowl_year>/all-picks",
        views.view_all_picks_for_year,
        name="view_all_picks_for_year",
    ),
    path(
        "<int:bowl_year>/my-picks",
        views.view_my_picks_for_year,
        name="view_my_picks_for_year",
    ),
    path(
        "<int:bowl_year>/my-picks/submit",
        views.submit_my_picks_for_year,
        name="submit_my_picks_for_year",
    ),
]
