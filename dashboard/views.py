from .services import calcular_kpis_gerais
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Value, Max
from django.db.models.functions import Coalesce, TruncMonth
from django.db import transaction # Importação que faltava
from .decorators import role_required
# Importações dos models
from .models import Sale, Client, User, Goal 
# Imports de utilitários
import json
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import calendar
from django.utils import timezone
# Imports para a Carga de Dados
import sys
import os
import subprocess
import uuid
from django.conf import settings
from django.contrib import messages
from django.core.files.storage import default_storage


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

# ---
# View 1: Dashboard Geral
# ---
@login_required
def dashboard_geral(request):
    """
    View do Dashboard Geral, refatorada para focar
    em TPV (Volume Bruto) e Receita Líquida (Lucro).
    """
    
    # --- 1. LÓGICA DE FILTROS ---
    today = timezone.now().date()
    start_date_str = request.GET.get('start_date', today.replace(day=1).isoformat())
    end_date_str = request.GET.get('end_date', today.isoformat())
    selected_products = request.GET.getlist('products')
    selected_consultants = request.GET.getlist('consultants')

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = today.replace(day=1)
        end_date = today

    # --- 2. BUSCAR DADOS PARA OS FILTROS ---
    all_consultants = User.objects.filter(role=User.Role.CONSULTANT).order_by('first_name')
    all_products = Sale.objects.values_list('source', flat=True).distinct()

    # --- 3. CONSULTAS PARA O PERÍODO SELECIONADO ---
    
    queryset_periodo = Sale.objects.filter(
        date__date__gte=start_date,
        date__date__lte=end_date
    )
    if selected_products:
        queryset_periodo = queryset_periodo.filter(source__in=selected_products)
    if selected_consultants:
        queryset_periodo = queryset_periodo.filter(consultant_id__in=selected_consultants)

    kpis = queryset_periodo.aggregate(
        total_revenue_net=Sum('revenue_net'),
        total_revenue_gross=Sum('revenue_gross'),
        total_sales=Count('id')
    )
    
    kpi_tpv = kpis['total_revenue_gross'] or Decimal(0)
    kpi_net = kpis['total_revenue_net'] or Decimal(0)
    
    if kpi_tpv > 0:
        kpi_margin = (kpi_net / kpi_tpv) * 100
    else:
        kpi_margin = Decimal(0)

    sales_by_source = (
        queryset_periodo
        .values('source')
        .annotate(revenue=Sum('revenue_net'))
        .order_by('-revenue')
    )
    pie_chart_data = list(sales_by_source)
    
    clients_performance = (
        queryset_periodo
        .values('raw_client_cnpj', 'raw_client_name') # Agrupa por CNPJ/Nome
        .annotate(total_tpv=Sum('revenue_gross'))
        .order_by('-total_tpv')
    )
    
    top_5_clients = clients_performance[:5]
    bottom_5_clients = clients_performance.filter(total_tpv__gt=0).order_by('total_tpv')[:5]

    # --- 4. CONSULTA PARA O GRÁFICO DE LINHA ---
    twelve_months_ago = today - timedelta(days=365)
    line_chart_qs = Sale.objects.filter(date__date__gte=twelve_months_ago)
    
    if selected_products:
        line_chart_qs = line_chart_qs.filter(source__in=selected_products)
    if selected_consultants:
        line_chart_qs = line_chart_qs.filter(consultant_id__in=selected_consultants)
    
    trend_data = (
        line_chart_qs
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(tpv=Sum('revenue_gross'))
        .order_by('month')
    )
    line_chart_data = [{"date": item['month'].isoformat(), "volume": item['tpv']} for item in trend_data]

    # --- 5. ENVIA OS DADOS PARA O TEMPLATE ---
    context = {
        'kpi_tpv': kpi_tpv,
        'kpi_net': kpi_net,
        'kpi_margin': kpi_margin,
        'kpi_total_sales': kpis['total_sales'] or 0,
        'pie_chart_json': json.dumps(pie_chart_data, cls=DecimalEncoder),
        'line_chart_json': json.dumps(line_chart_data, cls=DecimalEncoder),
        'current_start_date': start_date.isoformat(),
        'current_end_date': end_date.isoformat(),
        'start_date_display': start_date.strftime('%d/%m/%Y'),
        'end_date_display': end_date.strftime('%d/%m/%Y'),
        'all_products': all_products,
        'selected_products': selected_products,
        'all_consultants': all_consultants,
        'selected_consultants': [int(c) for c in selected_consultants],
        'top_5_clients': top_5_clients,
        'bottom_5_clients': bottom_5_clients,
    }
    
    return render(request, 'dashboard/dashboard_geral.html', context)


# ---
# View 2: Minha Carteira (CORREÇÃO DO BUG 3 DAS METAS)
# ---
@login_required
def minha_carteira(request):
    
    user = request.user
    today = timezone.now().date()
    
    # --- 1. LÓGICA DE FILTROS DE DATA ---
    start_date_str = request.GET.get('start_date', today.replace(day=1).isoformat())
    end_date_str = request.GET.get('end_date', today.isoformat())
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        start_date = today.replace(day=1)
        end_date = today
        
    # --- (CORREÇÃO BUG 3) Define o mês/ano de referência para as METAS
    # Usamos a DATA INICIAL do filtro, e não o "today".
    meta_year = start_date.year
    meta_month = start_date.month

    # --- 2. LÓGICA DE FILTROS DE NÍVEL DE ACESSO ---
    
    clientes_qs = Client.objects.none()
    vendas_periodo_qs = Sale.objects.none()
    # (CORREÇÃO BUG 3) Query para o mês da meta
    vendas_mes_meta_qs = Sale.objects.none()
    meta_qs = Goal.objects.none()
    performance_equipa = []
    
    twelve_months_ago = today - timedelta(days=365)
    line_chart_qs_base = Sale.objects.filter(date__date__gte=twelve_months_ago)
    
    if user.role == User.Role.CONSULTANT:
        clientes_qs = Client.objects.filter(consultant=user)
        vendas_periodo_qs = Sale.objects.filter(
            consultant=user, date__date__gte=start_date, date__date__lte=end_date
        )
        # (CORREÇÃO BUG 3) Busca vendas do mês selecionado no filtro
        vendas_mes_meta_qs = Sale.objects.filter(
            consultant=user, date__year=meta_year, date__month=meta_month
        )
        # (CORREÇÃO BUG 3) Busca meta do mês selecionado no filtro
        meta_qs = Goal.objects.filter(
            user=user, year=meta_year, month=meta_month
        )
        line_chart_qs = line_chart_qs_base.filter(consultant=user)

    elif user.role == User.Role.MANAGER:
        team_ids = User.objects.filter(manager=user).values_list('id', flat=True)
        
        clientes_qs = Client.objects.filter(consultant_id__in=team_ids)
        vendas_periodo_qs = Sale.objects.filter(
            consultant_id__in=team_ids, date__date__gte=start_date, date__date__lte=end_date
        )
        # (CORREÇÃO BUG 3) Busca vendas do mês selecionado no filtro
        vendas_mes_meta_qs = Sale.objects.filter(
            consultant_id__in=team_ids, date__year=meta_year, date__month=meta_month
        )
        # (CORREÇÃO BUG 3) Busca meta do mês selecionado no filtro
        meta_qs = Goal.objects.filter(
            user_id__in=team_ids, year=meta_year, month=meta_month
        )
        
        # (CORREÇÃO BUG 3) Busca performance da equipa para o mês selecionado
        performance_equipa = (
            User.objects.filter(id__in=team_ids)
            .annotate(
                revenue_month=Coalesce(Sum('sales__revenue_net', 
                    filter=Q(sales__date__year=meta_year, sales__date__month=meta_month)
                ), Decimal(0)),
                goal_month=Coalesce(Sum('goals__target_value',
                    filter=Q(goals__year=meta_year, goals__month=meta_month)
                ), Decimal(0))
            )
            .order_by('-revenue_month')
        )
        
        for consultor in performance_equipa:
            if consultor.goal_month > 0:
                consultor.percent_atingido = (consultor.revenue_month / consultor.goal_month) * 100
            else:
                consultor.percent_atingido = Decimal(0)
        
        line_chart_qs = line_chart_qs_base.filter(consultant_id__in=team_ids)

    # --- 3. CÁLCULO DE KPIs ---
    kpi_revenue_periodo = vendas_periodo_qs.aggregate(
        total=Coalesce(Sum('revenue_net'), Decimal(0))
    )['total']
    kpi_sales_periodo = vendas_periodo_qs.count()
    kpi_clients_activated = vendas_periodo_qs.values('client_id').distinct().count()
    kpi_total_clients = clientes_qs.count()
    
    # (CORREÇÃO BUG 3) KPIs de Meta agora usam as queries dinâmicas
    kpi_revenue_mes = vendas_mes_meta_qs.aggregate(
        total=Coalesce(Sum('revenue_net'), Decimal(0))
    )['total']
    kpi_meta_mes = meta_qs.aggregate(
        total=Coalesce(Sum('target_value'), Decimal(0))
    )['total']
    if kpi_meta_mes > 0:
        kpi_percentual_meta = (kpi_revenue_mes / kpi_meta_mes) * 100
    else:
        kpi_percentual_meta = Decimal(0)

    clientes_com_performance = clientes_qs.annotate(
        revenue_periodo=Coalesce(
            Sum(
                'sales__revenue_net',
                filter=Q(sales__date__date__gte=start_date, sales__date__date__lte=end_date)
            ),
            Decimal(0)
        )
    ).order_by('-revenue_periodo')
    
    # --- 4. PROCESSAMENTO DO GRÁFICO DE LINHA ---
    trend_data = (
        line_chart_qs
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(revenue=Sum('revenue_net'))
        .order_by('month')
    )
    line_chart_data = [{"date": item['month'].isoformat(), "revenue": item['revenue']} for item in trend_data]

    # --- 5. ENVIA OS DADOS PARA O TEMPLATE ---
    context = {
        'kpi_revenue_net': kpi_revenue_periodo,
        'kpi_total_sales': kpi_sales_periodo,
        'kpi_clients_activated': kpi_clients_activated,
        'kpi_total_clients': kpi_total_clients,
        'kpi_revenue_mes': kpi_revenue_mes,
        'kpi_meta_mes': kpi_meta_mes,
        'kpi_percentual_meta': kpi_percentual_meta,
        'clientes_performance': clientes_com_performance,
        'performance_equipa': performance_equipa,
        'line_chart_json': json.dumps(line_chart_data, cls=DecimalEncoder),
        
        # --- CORREÇÃO (BUG 4) ---
        # Passa o objeto 'date' (que é a 'start_date' do filtro)
        # O template irá formatá-lo para Português.
        'meta_date_object': start_date, 
        
        'current_start_date': start_date.isoformat(),
        'current_end_date': end_date.isoformat(),
        'start_date_display': start_date.strftime('%d/%m/%Y'),
        'end_date_display': end_date.strftime('%d/%m/%Y'),
    }
    
    return render(request, 'dashboard/minha_carteira.html', context)


# ---
# View 3: Atribuir Clientes (Feedback de Erro/Sucesso)
# ---
@login_required
@role_required(allowed_roles=[User.Role.ADMIN, User.Role.MANAGER])
def atribuir_clientes(request):
    
    if request.method == 'POST':
        cnpj = request.POST.get('cnpj')
        consultor_id = request.POST.get('consultor')
        client_name = request.POST.get('client_name')

        if cnpj and consultor_id:
            try:
                consultor = User.objects.get(id=consultor_id, role=User.Role.CONSULTANT)
                manager = consultor.manager
                
                client_obj, created = Client.objects.update_or_create(
                    cnpj=cnpj,
                    defaults={'client_name': client_name, 'consultant': consultor, 'manager': manager}
                )
                
                Sale.objects.filter(raw_client_cnpj=cnpj, consultant__isnull=True).update(
                    consultant=consultor, manager=manager, client=client_obj
                )
                
                messages.success(request, f"Cliente {client_name} atribuído a {consultor.first_name}.")
                
            except User.DoesNotExist:
                messages.error(request, "Erro: Consultor não encontrado.")
            except Exception as e:
                messages.error(request, f"Erro ao salvar: {e}")
        
        return redirect('atribuir_clientes')

    consultores_list = User.objects.filter(role=User.Role.CONSULTANT).order_by('first_name')
    vendas_orfas = Sale.objects.filter(consultant__isnull=True)
    clientes_orfaos = (
        vendas_orfas
        .values('raw_client_cnpj', 'raw_client_name')
        .annotate(total_revenue=Sum('revenue_net'), last_sale=Max('date'))
        .order_by('-last_sale')
    )
    context = {'clientes_orfaos': clientes_orfaos, 'consultores_list': consultores_list}
    return render(request, 'dashboard/atribuir_clientes.html', context)


# ---
# View 4: Gestão de Metas (CORREÇÃO DO BUG 1 e 2)
# ---
@login_required
@role_required(allowed_roles=[User.Role.ADMIN, User.Role.MANAGER])
def gestao_metas(request):
    
    today = timezone.now().date()
    
    if request.method == 'POST':
        # Esta parte (POST) estava correta, pois recebia '2025' e '11'
        # O 'ValueError' acontecia na lógica GET
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        
        try:
            with transaction.atomic(): 
                for key, value in request.POST.items():
                    if key.startswith('meta_'):
                        user_id = key.split('_')[1]
                        try:
                            target_value = Decimal(value if value else '0.0')
                        except InvalidOperation:
                            raise Exception(f"Valor inválido '{value}' para o utilizador ID {user_id}")

                        if request.user.role == User.Role.ADMIN:
                            consultor_check = User.objects.filter(id=user_id).exists()
                        else:
                            consultor_check = User.objects.filter(id=user_id, manager=request.user).exists()

                        if consultor_check:
                            Goal.objects.update_or_create(
                                user_id=user_id,
                                year=year,
                                month=month,
                                defaults={'target_value': target_value}
                            )
            
            messages.success(request, 'Metas salvas com sucesso!')
        
        except Exception as e:
            messages.error(request, f"Erro ao salvar metas: {e}")
        
        # Redireciona para a URL GET com os mesmos parâmetros
        return redirect(f"{reverse_lazy('gestao_metas')}?year={year}&month={month}")

    # (Lógica GET - Onde o BUG 1 ("2.025") acontece)
    try:
        # Tenta converter o 'year' e 'month' da URL
        selected_year_str = request.GET.get('year', str(today.year))
        selected_month_str = request.GET.get('month', str(today.month))
        
        # Converte para int
        selected_year = int(selected_year_str)
        selected_month = int(selected_month_str)
        
    except ValueError:
        # Se falhar (ex: '2.025'), reverte para o padrão e avisa o utilizador
        selected_year = today.year
        selected_month = today.month
        messages.error(request, f"Ano inválido recebido ('{selected_year_str}'). A carregar dados do mês atual.")

    if request.user.role == User.Role.ADMIN:
        consultants_list = User.objects.filter(role=User.Role.CONSULTANT).order_by('first_name')
    else:
        consultants_list = User.objects.filter(role=User.Role.CONSULTANT, manager=request.user).order_by('first_name')
    
    existing_goals = Goal.objects.filter(
        year=selected_year,
        month=selected_month,
        user__in=consultants_list
    )
    
    # Esta lógica está correta. O problema era que 'selected_year' estava errado.
    meta_map = {goal.user_id: goal.target_value for goal in existing_goals}
    
    consultant_data = []
    for consultant in consultants_list:
        # (NOVA LÓGICA) Adiciona o ID da meta (goal.id) se ela existir
        # Isto é necessário para o novo botão "Eliminar"
        goal = next((g for g in existing_goals if g.user_id == consultant.id), None)
        
        consultant_data.append({
            'consultant': consultant,
            'meta': meta_map.get(consultant.id, Decimal('0.0')),
            'goal_id': goal.id if goal else None, # Passa o ID da meta para o template
        })
        
    context = {
        'consultant_data': consultant_data,
        'selected_year_int': selected_year, # (NOVO) Passa o INT para o template
        'selected_month_int': selected_month, # (NOVO) Passa o INT para o template
        'selected_year_str': selected_year_str, # (NOVO) Passa a STR para o template
        'selected_month_str': selected_month_str, # (NOVO) Passa a STR para o template
        
        'year_range': [str(y) for y in range(today.year - 1, today.year + 2)],
        'month_range': [(str(i), calendar.month_name[i]) for i in range(1, 13)],
    }
    
    return render(request, 'dashboard/gestao_metas.html', context)


# ---
# (NOVA) View 6: Eliminar Meta
# ---
@login_required
@role_required(allowed_roles=[User.Role.ADMIN, User.Role.MANAGER])
def eliminar_meta(request, goal_id):
    """
    View para eliminar uma meta específica.
    """
    try:
        # Encontra a meta
        meta = Goal.objects.get(id=goal_id)
        
        # Segurança: Gestor só pode eliminar metas da sua equipa
        if request.user.role == User.Role.MANAGER:
            if meta.user.manager != request.user:
                messages.error(request, "Permissão negada.")
                return redirect('gestao_metas')
        
        # Guarda o mês/ano para redirecionar
        year = meta.year
        month = meta.month
        
        # Elimina a meta
        meta.delete()
        messages.success(request, "Meta eliminada com sucesso.")
        
        # Redireciona de volta para a página de gestão com os filtros
        return redirect(f"{reverse_lazy('gestao_metas')}?year={year}&month={month}")
        
    except Goal.DoesNotExist:
        messages.error(request, "Meta não encontrada.")
        return redirect('gestao_metas')
    except Exception as e:
        messages.error(request, f"Erro ao eliminar: {e}")
        return redirect('gestao_metas')


# ---
# View 7: Carga de Dados
# ---
@login_required
@role_required(allowed_roles=[User.Role.ADMIN, User.Role.MANAGER])
def carga_dados(request):
    
    python_exec = sys.executable
    manage_py = os.path.join(settings.BASE_DIR, 'manage.py')
    
    if request.method == 'POST':
        
        if 'upload_csv' in request.POST:
            file_type = request.POST.get('file_type')
            csv_file = request.FILES.get('csv_file')
            
            if not csv_file or not file_type:
                messages.error(request, 'Erro: Tipo de ficheiro ou ficheiro não fornecido.')
                return redirect('carga_dados')
                
            temp_name = f"{file_type}_{uuid.uuid4()}.csv"
            temp_path = default_storage.save(f"tmp/{temp_name}", csv_file)
            full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_path)

            if file_type == 'bionio':
                command = [python_exec, manage_py, 'import_bionio', full_temp_path]
            elif file_type == 'rovema':
                command = [python_exec, manage_py, 'import_rovema', full_temp_path]
            else:
                messages.error(request, 'Tipo de ficheiro inválido.')
                return redirect('carga_dados')

            subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            messages.success(request, f'Sucesso! A importação do {file_type.capitalize()} foi iniciada. Os dados estarão disponíveis em alguns minutos.')
            
            try:
                AuditLog.objects.create(
                    user=request.user,
                    action="inicio_carga_csv",
                    details={"file_type": file_type, "filename": csv_file.name}
                )
            except Exception as e:
                print(f"Erro ao salvar log: {e}")

        elif 'sync_api' in request.POST:
            api_type = request.POST.get('api_type')
            start_date = request.POST.get('api_start_date')
            end_date = request.POST.get('api_end_date')
            
            if not all([api_type, start_date, end_date]):
                messages.error(request, 'Erro: Datas ou tipo de API em falta.')
                return redirect('carga_dados')
            
            if api_type == 'eliq':
                command = [python_exec, manage_py, 'import_eliq', start_date, end_date]
            elif api_type == 'asto':
                command = [python_exec, manage_py, 'import_asto', start_date, end_date]
            else:
                messages.error(request, 'Tipo de API inválido.')
                return redirect('carga_dados')

            subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            messages.success(request, f'Sucesso! A sincronização da API {api_type.upper()} foi iniciada.')

            try:
                AuditLog.objects.create(
                    user=request.user,
                    action="inicio_carga_api",
                    details={"api_type": api_type, "start_date": start_date, "end_date": end_date}
                )
            except Exception as e:
                print(f"Erro ao salvar log: {e}")

        return redirect('carga_dados')

    # Busca os últimos 5 logs de carga para mostrar na página
    try:
        logs = AuditLog.objects.filter(
            action__in=["inicio_carga_api", "fim_carga_api", "inicio_carga_csv", "fim_carga_csv", "falha_carga_api", "falha_carga_csv"]
        ).order_by('-timestamp')[:5]
    except Exception as e:
        logs = []
        messages.warning(request, f"Não foi possível carregar o histórico de logs: {e}")

    today = timezone.now().date()
    default_start = today.replace(day=1)
    
    context = {
        'default_start_date': default_start.isoformat(),
        'default_end_date': today.isoformat(),
        'logs': logs, 
    }
    
    return render(request, 'dashboard/carga_dados.html', context)