
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    # path("apparel-config/", include("designer.apparel_urls")),
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("login/", RedirectView.as_view(pattern_name="login", permanent=False), name="legacy_login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    
  path(
        "accounts/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="designer/password_reset_form.html",
            email_template_name="designer/password_reset_email.html",
            subject_template_name="designer/password_reset_subject.txt",
            success_url="/accounts/password-reset/done/",
        ),
        name="password_reset"
    ),

    # =====================================================
    # PASSWORD RESET EMAIL SENT
    # =====================================================
    path(
        "accounts/password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="designer/password_reset_done.html"
        ),
        name="password_reset_done"
    ),

    # =====================================================
    # USER CLICKS RESET LINK FROM EMAIL
    # =====================================================
    path(
        "accounts/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="designer/password_reset_confirm.html",
            success_url="/accounts/reset/done/",
        ),
        name="password_reset_confirm"
    ),

    # =====================================================
    # PASSWORD SUCCESSFULLY CHANGED
    # =====================================================
    path(
        "accounts/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="designer/password_reset_complete.html"
        ),
        name="password_reset_complete"
    ),



    path("", include("designer.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
