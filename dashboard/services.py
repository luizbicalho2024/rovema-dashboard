from django.db.models import Sum, Count
from decimal import Decimal
from .models import Sale

def calcular_kpis_gerais(queryset):
    """
    Calcula os KPIs principais para um queryset de Vendas.
    Retorna um dicionário com os valores prontos.
    """
    kpis = queryset.aggregate(
        total_revenue_net=Sum('revenue_net'),
        total_revenue_gross=Sum('revenue_gross'),
        total_sales=Count('id')
    )

    kpi_tpv = kpis['total_revenue_gross'] or Decimal('0.0')
    kpi_net = kpis['total_revenue_net'] or Decimal('0.0')

    # Evita divisão por zero
    if kpi_tpv > 0:
        kpi_margin = (kpi_net / kpi_tpv) * 100
    else:
        kpi_margin = Decimal('0.0')

    return {
        'kpi_tpv': kpi_tpv,
        'kpi_net': kpi_net,
        'kpi_margin': kpi_margin,
        'kpi_total_sales': kpis['total_sales'] or 0
    }