from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.core.exceptions import PermissionDenied

from .models import User
from .forms import CustomUserCreationForm, CustomUserChangeForm

# ---
# (NOVO) Mixin de Segurança para Vistas Baseadas em Classes
# ---
class RoleRequiredMixin:
    """
    Um Mixin que funciona como o nosso decorator @role_required
    para Vistas Baseadas em Classes (CBVs).
    """
    allowed_roles = [] # Lista de roles permitidos

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        
        if request.user.role not in self.allowed_roles:
            raise PermissionDenied
        
        return super().dispatch(request, *args, **kwargs)

# ---
# Vistas do CRUD
# ---

class UserListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """(Read) - Lista todos os utilizadores."""
    model = User
    template_name = 'dashboard/user_list.html'
    context_object_name = 'users'
    allowed_roles = [User.Role.ADMIN] # Apenas Admins podem ver

class UserCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """(Create) - Formulário para criar um utilizador."""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'dashboard/user_form.html'
    success_url = reverse_lazy('user_list') # Volta para a lista após criar
    allowed_roles = [User.Role.ADMIN]

    def get_context_data(self, **kwargs):
        # Adiciona um título à página
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Criar Novo Utilizador'
        return context

class UserUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """(Update) - Formulário para editar um utilizador."""
    model = User
    form_class = CustomUserChangeForm
    template_name = 'dashboard/user_form.html'
    success_url = reverse_lazy('user_list')
    allowed_roles = [User.Role.ADMIN]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar Utilizador'
        return context

class UserDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """(Delete) - Página de confirmação para eliminar."""
    model = User
    template_name = 'dashboard/user_confirm_delete.html'
    success_url = reverse_lazy('user_list')
    allowed_roles = [User.Role.ADMIN]
