from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def role_required(allowed_roles=[]):
    """
    Decorator para views que verifica se o usuário logado
    tem um dos 'roles' permitidos.
    
    Substitui o 'check_role' do Streamlit.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            # Se o usuário não estiver logado, o @login_required (usado antes)
            # já o terá redirecionado para o login.
            if not request.user.is_authenticated:
                return redirect('login') # Garante o redirecionamento
            
            # Verifica se o 'role' do usuário está na lista permitida
            if request.user.role not in allowed_roles:
                # Se não tiver permissão, nega o acesso
                raise PermissionDenied
            
            # Se tiver permissão, executa a view
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
