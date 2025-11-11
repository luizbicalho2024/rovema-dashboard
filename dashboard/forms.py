from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class CustomUserCreationForm(forms.ModelForm):
    """
    Formulário para CRIAR novos utilizadores.
    Baseado na sua página de Admin do Streamlit.
    """
    # Adiciona campos de palavra-passe que não estão no modelo
    password = forms.CharField(label="Palavra-passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar Palavra-passe", widget=forms.PasswordInput)

    class Meta:
        model = User
        # Campos que o admin deve preencher
        fields = ('email', 'first_name', 'last_name', 'role', 'manager')

    def clean_password2(self):
        # Validação para garantir que as palavras-passe coincidem
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('As palavras-passe não coincidem.')
        return cd['password2']

    def save(self, commit=True):
        # Sobrescreve o 'save' para fazer o HASH da palavra-passe
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class CustomUserChangeForm(forms.ModelForm):
    """
    Formulário para EDITAR utilizadores existentes.
    Não inclui a palavra-passe (para alteração de passe, usamos outra ferramenta).
    """
    class Meta:
        model = User
        # Permite editar estes campos
        fields = ('email', 'first_name', 'last_name', 'role', 'manager')
