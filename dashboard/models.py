import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

# ---
# Modelo 1: Usuário (O Modelo Central)
# ---
# Vamos criar um "Modelo de Usuário Customizado". Isso permite que 
# você use o sistema de autenticação do Django, mas adicione
# campos extras como "role" e "manager", que eram essenciais
# no seu projeto Streamlit.
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

    # O 'uid' do Firebase será o 'id' (PK) automático do Django.
    # Vamos adicionar os campos que você tinha no Firestore.
    
    # Sobrescreve campos padrão (username não será usado para login)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    
    # Seus campos customizados
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CONSULTANT)
    
    # Chave estrangeira "para si mesmo".
    # Um 'manager' é um 'User'. Um 'consultant' aponta para seu 'manager'.
    manager = models.ForeignKey(
        'self',  # Aponta para o próprio modelo 'User'
        on_delete=models.SET_NULL, # Se o gestor for deletado, o campo fica nulo
        null=True, 
        blank=True,
        limit_choices_to={'role': Role.MANAGER}, # Só permite selecionar gestores
        related_name='team_members' # Permite fazer user.team_members.all()
    )

    # Diz ao Django que o campo de login agora é o 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # 'username' ainda é necessário para o createsuperuser

    def __str__(self):
        return self.email


# ---
# Modelo 2: Cliente
# ---
# Substitui a coleção 'clients'
# O ID (document_id) era o CNPJ, aqui vamos usar o CNPJ como Primary Key.
# ---

class Client(models.Model):
    # CNPJ será a Chave Primária (PK) da tabela
    cnpj = models.CharField(max_length=14, primary_key=True, unique=True)
    client_name = models.CharField(max_length=255)
    
    # Relação: Cada cliente pertence a um Consultor (User)
    consultant = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # Se o consultor sair, o cliente fica "órfão"
        null=True,
        blank=True,
        related_name='clients',
        limit_choices_to={'role': User.Role.CONSULTANT}
    )
    
    # Relação (denormalizada para performance, como no seu original):
    # Armazena também o gestor do consultor
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
# Substitui a coleção 'sales_data'. Esta é a sua tabela de fatos principal.
# ---

class Sale(models.Model):
    # O Django dará um 'id' automático (1, 2, 3...)
    
    # Armazena a fonte original (Bionio, Rovema Pay, etc.)
    source = models.CharField(max_length=50, db_index=True)
    
    # ID original do sistema de origem (para evitar duplicatas na importação)
    raw_id = models.CharField(max_length=100, db_index=True)

    # Relações com Cliente e Consultor
    client = models.ForeignKey(
        Client, 
        on_delete=models.PROTECT, # Impede deletar um cliente que tenha vendas
        null=True, 
        blank=True,
        related_name='sales'
    )
    consultant = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, # Se o consultor for deletado, a venda vira "órfã"
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
    
    # Campos de dados (Use DecimalField para dinheiro, NUNCA FloatField)
    date = models.DateTimeField(db_index=True)
    revenue_gross = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    revenue_net = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    volume = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True) # Ex: Litros
    
    # Campos descritivos (strings)
    product_name = models.CharField(max_length=100, blank=True)
    product_detail = models.CharField(max_length=100, blank=True) # Ex: Bandeira (visa)
    payment_type = models.CharField(max_length=50, blank=True)   # Ex: Tipo de pagamento
    status = models.CharField(max_length=50, blank=True)         # Ex: Pago, Transferido

    # Armazena o nome/cnpj cru da importação, para o caso
    # de vendas órfãs que ainda não têm um 'client' relacionado.
    raw_client_name = models.CharField(max_length=255, blank=True)
    raw_client_cnpj = models.CharField(max_length=20, blank=True, db_index=True)

    class Meta:
        # Garante que não haja duplicatas (mesma fonte, mesmo ID)
        unique_together = ('source', 'raw_id')

    def __str__(self):
        return f"{self.source}: R$ {self.revenue_net} em {self.date.strftime('%Y-%m-%d')}"


# ---
# Modelo 4: Metas (Goals)
# ---
# Substitui a coleção 'goals'.
# No Firestore, você tinha 1 doc por mês. No SQL, é melhor ter 1 *linha* por meta.
# ---

class Goal(models.Model):
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, # Se o usuário for deletado, suas metas somem
        related_name='goals'
    )
    year = models.IntegerField()
    month = models.IntegerField() # 1 = Jan, 12 = Dez
    target_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    
    class Meta:
        # Garante 1 meta por usuário por mês
        unique_together = ('user', 'year', 'month')

    def __str__(self):
        return f"Meta de {self.user.email} para {self.month}/{self.year}: R$ {self.target_value}"


# ---
# Modelo 5: Logs de Auditoria
# ---
# Substitui a coleção 'audit_logs'
# ---

class AuditLog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, # Mantém o log mesmo se o usuário for deletado
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100, db_index=True)
    
    # JSONField é perfeito para o campo 'details' que era um dict
    details = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.user} - {self.action}"
