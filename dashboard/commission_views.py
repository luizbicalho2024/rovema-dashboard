# dashboard/commission_views.py

from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
import json

from .models import User, CommissionRule, AuditLog
from .forms import CommissionRuleForm
from .user_management_views import RoleRequiredMixin # Reutiliza o Mixin de segurança

class CommissionRuleListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """(Read) - Lista todas as regras de comissão."""
    model = CommissionRule
    template_name = 'dashboard/commission_list.html'
    context_object_name = 'rules'
    allowed_roles = [User.Role.ADMIN] # Apenas Admins

class CommissionRuleCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """(Create) - Formulário para criar uma nova regra."""
    model = CommissionRule
    form_class = CommissionRuleForm
    template_name = 'dashboard/commission_form.html'
    success_url = reverse_lazy('commission_list')
    allowed_roles = [User.Role.ADMIN]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Criar Nova Regra de Comissão'
        return context

    def form_valid(self, form):
        messages.success(self.request, "Regra de comissão criada com sucesso.")
        
        # Log de auditoria
        AuditLog.objects.create(
            user=self.request.user,
            action="create_commission_rule",
            details={
                "rule_name": form.cleaned_data['rule_name'],
                "source": form.cleaned_data['source'],
                "percentage": float(form.cleaned_data['percentage']) # Converte Decimal para float para JSON
            }
        )
        return super().form_valid(form)

class CommissionRuleUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """(Update) - Formulário para editar uma regra."""
    model = CommissionRule
    form_class = CommissionRuleForm
    template_name = 'dashboard/commission_form.html'
    success_url = reverse_lazy('commission_list')
    allowed_roles = [User.Role.ADMIN]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar Regra de Comissão'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, "Regra de comissão atualizada com sucesso.")
        
        # Prepara os dados antigos (form.initial) e novos (form.cleaned_data) para o log
        # Converte Decimals para float para serem compatíveis com JSON
        old_data = {k: float(v) if isinstance(v, Decimal) else v for k, v in form.initial.items()}
        new_data = {k: float(v) if isinstance(v, Decimal) else v for k, v in form.cleaned_data.items()}

        # Log de auditoria
        AuditLog.objects.create(
            user=self.request.user,
            action="update_commission_rule",
            details={
                "rule_id": self.object.id,
                "rule_name": new_data['rule_name'],
                "changes": {
                    "old": old_data,
                    "new": new_data
                }
            }
        )
        return super().form_valid(form)

class CommissionRuleDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """(Delete) - Página de confirmação para eliminar."""
    model = CommissionRule
    template_name = 'dashboard/commission_confirm_delete.html'
    success_url = reverse_lazy('commission_list')
    allowed_roles = [User.Role.ADMIN]

    def delete(self, request, *args, **kwargs):
        # Guarda o objeto antes de eliminar para o log
        self.object = self.get_object() 
        rule_name = self.object.rule_name
        
        # Chama o delete() original
        response = super().delete(request, *args, **kwargs)
        
        messages.success(self.request, f"Regra '{rule_name}' eliminada com sucesso.")
        
        # Log de auditoria
        AuditLog.objects.create(
            user=self.request.user,
            action="delete_commission_rule",
            details={
                "rule_id": self.object.id,
                "rule_name": self.object.rule_name,
                "source": self.object.source,
                "percentage": float(self.object.percentage)
            }
        )
        return response