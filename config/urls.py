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

# Importações necessárias para servir Static e Media files em desenvolvimento
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URLs do sistema de autenticação do Django (login, logout, etc.)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Roteia todas as outras URLs para a aplicação dashboard
    path('', include('dashboard.urls')),
]

# Configuração para servir Static e Media files *apenas* durante o desenvolvimento (DEBUG=True)
if settings.DEBUG:
    # Serve arquivos estáticos (CSS, JS, o seu logo)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Serve arquivos de Mídia (uploads, como os temporários da Carga de Dados)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)