from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from colegioapp import views, views_misc

urlpatterns = [
    path('admin/', admin.site.urls),

    # Sitio público
    path('', include(('sitio.urls', 'sitio'), namespace='sitio')),

    # Autenticación
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        redirect_authenticated_user=True
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Redirección post login
    path('post-login/', views_misc.post_login_redirect, name='post_login'),

    # Dashboard interno
    path('home/', views.home, name='home'),

    # Módulos
    path('academico/', include(('academico.urls', 'academico'), namespace='academico')),
    path('administrativo/', include(('administrativo.urls', 'administrativo'), namespace='administrativo')),
    path('cartera/', include(('cartera.urls', 'cartera'), namespace='cartera')),
    path('tablero/', include(('tablero.urls', 'tablero'), namespace='tablero')),
    path('cuentas/', include('cuentas.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)