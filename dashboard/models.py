import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal # Adicionar import

# ---
# Modelo 1: Usuário (O Modelo Central)
# ---
class User(AbstractUser):
    """
    Modelo de Usuário customizado que substitui o User padrão do Django.
    Ele usa 'email' como login e adiciona 'role' e 'manager'.
    """
    class Role(models.TextChoices):
        CONSULTANT = "consultant", "Consultor"
        MANAGER = "manager", "Gestor"
        ADMIN = "admin", "Administrador"

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONSULTANT)
    
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        limit_choices_to={'role': Role.MANAGER},
        related_name='team_members'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] 

    def __str__(self):
        return self.email


# ---
# Modelo 2: Cliente
# ---
class Client(models.Model):
    cnpj = models.CharField(max_length=14, primary_key=True, unique=True)
    client_name = models.CharField(max_length=255)
    
    consultant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients',
        limit_choices_to={'role': User.Role.CONSULTANT}
    )
    
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients_of_team',
        limit_choices_to={'role': User.Role.MANAGER}
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.client_name} ({self.cnpj})"


# ---
# Modelo 3: Vendas (SalesData)
# ---
class Sale(models.Model):
    source = models.CharField(max_length=50, db_index=True)
    raw_id = models.CharField(max_length=100, db_index=True)

    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        related_name='sales'
    )
    consultant = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='sales'
    )
    manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='sales_of_team'
    )
    
    date = models.DateTimeField(db_index=True)
    revenue_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    revenue_net = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    volume = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True) 
    
    product_name = models.CharField(max_length=100, blank=True)
    product_detail = models.CharField(max_length=100, blank=True) 
    payment_type = models.CharField(max_length=50, blank=True)   
    status = models.CharField(max_length=50, blank=True)         

    raw_client_name = models.CharField(max_length=255, blank=True)
    raw_client_cnpj = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta:
        unique_together = ('source', 'raw_id')

    def __str__(self):
        return f"{self.source}: R$ {self.revenue_net} em {self.date.strftime('%Y-%m-%d')}"


# ---
# Modelo 4: Metas (Goals)
# ---
class Goal(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='goals'
    )
    year = models.IntegerField()
    month = models.IntegerField() # 1 = Jan, 12 = Dez
    target_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    class Meta:
        unique_together = ('user', 'year', 'month')

    def __str__(self):
        return f"Meta de {self.user.email} para {self.month}/{self.year}: R$ {self.target_value}"


# ---
# Modelo 5: Logs de Auditoria
# ---
class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100, db_index=True)
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.user} - {self.action}"


# ---
# (NOVO) Modelo 6: Regras de Comissão
# ---
class CommissionRule(models.Model):
    """
    Armazena as regras de comissão.
    Ex: source='Bionio', percentage=10.0 (significa 10%)
    """
    rule_name = models.CharField(max_length=100, help_text="Ex: Comissão Bionio (10%)")
    
    source = models.CharField(max_length=50, unique=True, db_index=True, 
                              help_text="O 'source' exato da tabela de Vendas (ex: Rovema Pay)")
                              
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0,
                                     help_text="O valor da percentagem (ex: 10.5 para 10.5%)")

    def __str__(self):
        return f"{self.rule_name} ({self.source} @ {self.percentage}%)"