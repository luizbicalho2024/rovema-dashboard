from django.urls import path
from . import views # Views das nossas páginas
from . import user_management_views # Views para o CRUD de utilizadores

urlpatterns = [
    # URLs do Dashboard
    path('', views.dashboard_geral, name='dashboard_geral'),
    path('minha-carteira/', views.minha_carteira, name='minha_carteira'),
    path('atribuir-clientes/', views.atribuir_clientes, name='atribuir_clientes'),
    
    # URLs de Gestão de Utilizadores
    path('gestao-utilizadores/', 
         user_management_views.UserListView.as_view(), 
         name='user_list'),
    
    path('gestao-utilizadores/criar/', 
         user_management_views.UserCreateView.as_view(), 
         name='user_create'),
    
    path('gestao-utilizadores/editar/<int:pk>/', 
         user_management_views.UserUpdateView.as_view(), 
         name='user_update'),
    
    path('gestao-utilizadores/eliminar/<int:pk>/', 
         user_management_views.UserDeleteView.as_view(), 
         name='user_delete'),
         
    # URLs de Gestão de Metas
    path('gestao-metas/', views.gestao_metas, name='gestao_metas'),
    
    # (NOVA URL PARA ELIMINAR META)
    path('gestao-metas/eliminar/<int:goal_id>/', 
         views.eliminar_meta, 
         name='eliminar_meta'),

    # URLs de Carga de Dados
    path('carga-dados/', views.carga_dados, name='carga_dados'),
]