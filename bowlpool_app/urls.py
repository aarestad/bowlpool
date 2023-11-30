from django.contrib import admin
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    re_path(
        r"^$",
        TemplateView.as_view(template_name="static_pages/index.html"),
        name="home",
    ),
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
