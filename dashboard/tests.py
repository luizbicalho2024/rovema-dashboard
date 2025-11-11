from django.test import TestCase, Client
from django.urls import reverse
from .models import User

class UserRoleTests(TestCase):
    def setUp(self):
        # Cria usuários de teste antes de cada teste rodar
        # Adicionamos 'username' pois o UserManager padrão ainda o exige
        self.consultant = User.objects.create_user(
            username='consultor_teste',
            email='consultor@teste.com', 
            password='password123', 
            role=User.Role.CONSULTANT
        )
        self.manager = User.objects.create_user(
            username='gestor_teste',
            email='gestor@teste.com', 
            password='password123', 
            role=User.Role.MANAGER
        )
        self.admin = User.objects.create_user(
            username='admin_teste',
            email='admin@teste.com', 
            password='password123', 
            role=User.Role.ADMIN
        )
        self.client = Client()

    def test_dashboard_access_login_required(self):
        """Testa se o dashboard exige login"""
        response = self.client.get(reverse('dashboard_geral'))
        # Deve redirecionar (302) para o login, não deixar entrar (200)
        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302)

    def test_admin_access_user_list(self):
        """Testa se ADMIN pode ver a lista de usuários"""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)

    def test_consultant_denied_user_list(self):
        """Testa se CONSULTOR é BLOQUEADO de ver a lista de usuários"""
        self.client.force_login(self.consultant)
        response = self.client.get(reverse('user_list'))
        # Deve receber 403 Forbidden (graças ao seu RoleRequiredMixin/decorator)
        self.assertEqual(response.status_code, 403)