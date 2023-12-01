from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import TemplateView, RedirectView

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
