from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import TemplateView, RedirectView
from django.contrib.auth.views import LogoutView

urlpatterns = (
    [
        path("admin/", admin.site.urls),
        path("bowl-pool/", include("bowlpool_app.urls")),
        path("accounts/", include("allauth.urls")),
        path("", RedirectView.as_view(url="bowl-pool/")),
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
)
