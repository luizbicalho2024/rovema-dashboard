from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Client, Sale, Goal, AuditLog, CommissionRule # Importa o CommissionRule

# ---
# 1. Configuração do Admin para o Usuário Customizado
# ---
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Configura a tela de admin para o nosso modelo 'User' customizado.
    """
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Controle de Acesso (Rovema)', {
            'fields': ('role', 'manager'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Controle de Acesso (Rovema)', {
            'fields': ('role', 'manager'),
        }),
    )

# ---
# 2. Configuração dos outros modelos
# ---
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'cnpj', 'consultant', 'manager')
    list_filter = ('consultant', 'manager')
    search_fields = ('client_name', 'cnpj')
    raw_id_fields = ('consultant', 'manager')


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('date', 'source', 'client', 'consultant', 'revenue_net')
    list_filter = ('source', 'consultant', 'manager')
    search_fields = ('raw_client_name', 'raw_client_cnpj', 'client__client_name')
    date_hierarchy = 'date'
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


# ---
# 3. Registra o modelo de Comissão
# ---
@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_name', 'source', 'percentage')
    search_fields = ('rule_name', 'source')