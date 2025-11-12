from django.urls import path
from . import views # Views das nossas páginas
from . import user_management_views # Views para o CRUD de utilizadores
from . import commission_views 

urlpatterns = [
    # URLs do Dashboard
    path('', views.dashboard_geral, name='dashboard_geral'),
    path('minha-carteira/', views.minha_carteira, name='minha_carteira'),
    path('cliente/<str:cnpj>/', views.client_detail, name='client_detail'),
    path('atribuir-clientes/', views.atribuir_clientes, name='atribuir_clientes'),
    
    # (NOVO) URL da API para o Dashboard Geral
    path('api/dashboard-geral/', views.api_dashboard_geral_data, name='api_dashboard_geral_data'),
    
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
    
    path('gestao-metas/eliminar/<int:goal_id>/', 
         views.eliminar_meta, 
         name='eliminar_meta'),

    # URLs de Gestão de Comissões
    path('gestao-comissoes/', 
         commission_views.CommissionRuleListView.as_view(), 
         name='commission_list'),
    
    path('gestao-comissoes/criar/', 
         commission_views.CommissionRuleCreateView.as_view(), 
         name='commission_create'),
    
    path('gestao-comissoes/editar/<int:pk>/', 
         commission_views.CommissionRuleUpdateView.as_view(), 
         name='commission_update'),
    
    path('gestao-comissoes/eliminar/<int:pk>/', 
         commission_views.CommissionRuleDeleteView.as_view(), 
         name='commission_delete'),

    # URLs de Carga de Dados
    path('carga-dados/', views.carga_dados, name='carga_dados'),
]