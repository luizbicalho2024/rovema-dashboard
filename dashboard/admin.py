from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Client, Sale, Goal, AuditLog

# ---
# 1. Configuração do Admin para o Usuário Customizado
# ---
# Precisamos de uma configuração especial para o User,
# pois ele é mais complexo que os outros modelos.
# ---

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Configura a tela de admin para o nosso modelo 'User' customizado.
    """
    # Mostra estes campos na lista de usuários
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff')
    
    # Adiciona 'role' e 'manager' aos campos editáveis
    # (Note: 'fieldsets' é uma tupla de tuplas)
    fieldsets = UserAdmin.fieldsets + (
        ('Controle de Acesso (Rovema)', {
            'fields': ('role', 'manager'),
        }),
    )
    
    # Adiciona 'role' e 'manager' aos campos de criação de usuário
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Controle de Acesso (Rovema)', {
            'fields': ('role', 'manager'),
        }),
    )

# ---
# 2. Configuração dos outros modelos (mais simples)
# ---
# Para os outros modelos, podemos usar um registro mais simples,
# mas vamos customizar um pouco para ficar mais fácil de usar.
# ---

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    # Quais campos mostrar na lista
    list_display = ('client_name', 'cnpj', 'consultant', 'manager')
    # Adiciona filtros rápidos na lateral
    list_filter = ('consultant', 'manager')
    # Adiciona uma barra de busca
    search_fields = ('client_name', 'cnpj')
    
    # Otimiza a busca do 'consultant' e 'manager'
    raw_id_fields = ('consultant', 'manager')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'client', 'consultant', 'revenue_net')
    list_filter = ('source', 'consultant', 'manager')
    search_fields = ('raw_client_name', 'raw_client_cnpj', 'client__client_name')
    
    # Deixa as datas navegáveis
    date_hierarchy = 'date'
    
    # É melhor usar raw_id para tabelas com muitas linhas
    raw_id_fields = ('client', 'consultant', 'manager')


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'year', 'month', 'target_value')
    list_filter = ('user', 'year')
    search_fields = ('user__email',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action')
    list_filter = ('action', 'user')
    date_hierarchy = 'timestamp'
