from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Adiciona as URLs de login, logout, etc.
    # Elas estarão em /accounts/login/, /accounts/logout/
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Envia qualquer outra URL (como "/") para ser tratada
    # pelo nosso app "dashboard"
    path('', include('dashboard.urls')),
]
