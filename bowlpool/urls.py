from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import TemplateView

urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("bowl-pool/", include("bowlpool_app.urls")),
        path("accounts/", include("django.contrib.auth.urls")),
        re_path(
            r"^$",
            TemplateView.as_view(template_name="static_pages/index.html"),
            name="home",
        ),
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)
