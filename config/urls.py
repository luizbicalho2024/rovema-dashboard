"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

# --- (INÍCIO DA CORREÇÃO) ---
from django.conf import settings
from django.conf.urls.static import static
# --- (FIM DA CORREÇÃO) ---

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Adiciona as URLs de login, logout, etc.
    # Elas estarão em /accounts/login/, /accounts/logout/
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Envia qualquer outra URL (como "/") para ser tratada
    # pelo nosso app "dashboard"
    path('', include('dashboard.urls')),
]

# --- (INÍCIO DA CORREÇÃO) ---
# Adiciona o 'servidor' de arquivos estáticos APENAS em modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # (Opcional, mas recomendado) Adiciona o 'servidor' de arquivos de media (uploads)
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# --- (FIM DA CORREÇÃO) ---