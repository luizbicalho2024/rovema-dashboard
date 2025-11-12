from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import AuditLog

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Regista um log quando um utilizador faz login.
   
    """
    AuditLog.objects.create(
        user=user,
        action="login_success",
        details={"ip_address": request.META.get('REMOTE_ADDR')}
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    Regista um log quando um utilizador faz logout.
   
    """
    if user: # O 'user' pode ser None se a sessão expirou
        AuditLog.objects.create(
            user=user,
            action="logout",
            details={"ip_address": request.META.get('REMOTE_ADDR')}
        )