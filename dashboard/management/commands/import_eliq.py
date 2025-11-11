import pandas as pd
from datetime import datetime
from decimal import Decimal
import httpx
import sys

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.conf import settings
# (NOVO) Importa os modelos de Log e User
from dashboard.models import User, Client, Sale, AuditLog

def clean_value(value_str):
    if pd.isna(value_str): return Decimal('0.0')
    if isinstance(value_str, (int, float, Decimal)): return Decimal(value_str)
    value_str = str(value_str).strip().replace("R$", "").replace("%", "")
    value_str = value_str.replace(".", "").replace(",", ".")
    try: return Decimal(value_str)
    except Exception: return Decimal('0.0')

def clean_cnpj(cnpj_str):
    if pd.isna(cnpj_str): return None
    cnpj_str = str(cnpj_str)
    if 'E' in cnpj_str.upper():
        try: cnpj_str = "{:.0f}".format(float(cnpj_str.replace(',', '.')))
        except: pass 
    cleaned_cnpj = "".join(filter(str.isdigit, cnpj_str))
    return cleaned_cnpj.zfill(14)

class Command(BaseCommand):
    help = 'Importa dados de vendas da API ELIQ (Uzzipay/Sigyo)'

    def add_arguments(self, parser):
        parser.add_argument('start_date', type=str, help='Data inicial (YYYY-MM-DD)')
        parser.add_argument('end_date', type=str, help='Data final (YYYY-MM-DD)')
        # (NOVO) Argumento para saber QUEM iniciou
        parser.add_argument('--user-id', type=int, help='ID do utilizador que iniciou a ação', default=None)

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando importação da API ELIQ...'))
        
        start_date_str = options['start_date']
        end_date_str = options['end_date']
        user = None
        if options['user_id']:
            try: user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist: user = None
            
        log_details = {"api_type": "eliq", "start_date": start_date_str, "end_date": end_date_str}

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise Exception("Formato de data inválido. Use YYYY-MM-DD.")

        # --- 1. Carregar Credenciais ---
        try:
            creds = settings.API_CREDENTIALS
            URL_ELIQ = creds["eliq_url"]
            API_TOKEN = creds["eliq_token"]
        except (AttributeError, KeyError) as e:
            raise Exception(f"Erro ao ler credenciais de 'settings.py': {e}")

        # --- 2. Pré-carrega mapas ---
        self.stdout.write("Carregando mapa de clientes e consultores...")
        client_map = {c.cnpj: c for c in Client.objects.all()}
        user_map = {u: u.manager for u in User.objects.filter(role=User.Role.CONSULTANT)}
        cnpj_to_consultant = {c.cnpj: c.consultant for c in Client.objects.all() if c.consultant}

        # --- 3. Chamada de API ---
        date_range_str = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
        params = {"TransacaoSearch[data_cadastro]": date_range_str}
        headers = {"Authorization": f"Bearer {API_TOKEN}"}
        
        self.stdout.write(f"Buscando dados na API ELIQ ({URL_ELIQ})...")
        
        try:
            with httpx.Client(headers=headers, timeout=120.0) as client:
                response = client.get(URL_ELIQ, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(f"Erro na API ELIQ: {e.response.status_code} - {e.response.text}")
        except httpx.TimeoutException:
            raise Exception("Erro na API ELIQ: Timeout (120s) excedido.")
        except Exception as e:
            raise Exception(f"Erro ao chamar API ELIQ: {e}")

        if not data:
            self.stdout.write(self.style.WARNING("Nenhum dado retornado pela API ELIQ para o período."))
            return

        # --- 4. Processamento ---
        sales_to_process = {}
        orphans_found = 0

        for sale in data:
            if sale.get('status') != 'confirmada': continue 
            cliente_info = sale.get('cliente', {}) or sale.get('informacao', {}).get('cliente', {})
            if not cliente_info: continue 
            cnpj = clean_cnpj(cliente_info.get('cnpj'))
            if not cnpj: continue

            try:
                naive_datetime = datetime.strptime(sale['data_cadastro'], "%Y-%m-%d %H:%M:%S")
                data_venda = timezone.make_aware(naive_datetime, timezone.get_default_timezone())
            except: continue
            
            revenue_gross = clean_value(sale.get('valor_total', 0))
            revenue_net_raw = sale.get('valor_taxa_cliente', sale.get('desconto', 0))
            revenue_net = abs(clean_value(revenue_net_raw))
            produto_info = sale.get('produto', {}) or sale.get('informacao', {}).get('produto', {})
            
            client_obj = client_map.get(cnpj)
            consultant_obj = client_obj.consultant if client_obj else cnpj_to_consultant.get(cnpj)
            manager_obj = client_obj.manager if client_obj else (user_map.get(consultant_obj) if consultant_obj else None)

            if not consultant_obj:
                orphans_found += 1

            doc_id = f"ELIQ_{sale['id']}"
            
            sale_obj = Sale(
                source="ELIQ", raw_id=doc_id, client=client_obj,
                consultant=consultant_obj, manager=manager_obj,
                raw_client_cnpj=cnpj, raw_client_name=cliente_info.get('nome', 'N/A'),
                date=data_venda, revenue_gross=revenue_gross, revenue_net=revenue_net,
                volume=clean_value(sale.get('quantidade', 0)),
                product_name=produto_info.get('nome', 'N/A'),
                product_detail=produto_info.get('categoria', 'N/A'),
                status=sale['status'],
            )
            sales_to_process[doc_id] = sale_obj
            
        # --- 5. Salva no Banco de Dados ---
        final_sales_list = list(sales_to_process.values())
        self.stdout.write(f"Processamento concluído. {len(final_sales_list)} vendas ÚNICAS prontas para salvar.")
        
        Sale.objects.bulk_create(
            final_sales_list, batch_size=1000,
            unique_fields=['source', 'raw_id'],
            update_conflicts=True,
            update_fields=['client', 'consultant', 'manager', 'date', 'revenue_gross', 
                           'revenue_net', 'volume', 'product_name', 'product_detail', 'status']
        )
        
        # (NOVO) Regista o SUCESSO no log
        log_details.update({
            "status": "Sucesso",
            "rows_found": len(data),
            "rows_processed": len(final_sales_list),
            "rows_saved": len(final_sales_list),
            "orphans_found": orphans_found
        })
        AuditLog.objects.create(user=user, action="fim_carga_api", details=log_details)
        self.stdout.write(self.style.SUCCESS(f"Importação ELIQ concluída! {len(final_sales_list)} registros salvos."))

        # Bloco "except"
        except Exception as e:
            # (NOVO) Regista a FALHA no log
            self.stdout.write(self.style.ERROR(f"Erro durante a importação: {e}"))
            log_details.update({"status": "Falha", "error": str(e)})
            AuditLog.objects.create(user=user, action="falha_carga_api", details=log_details)
            sys.exit(1)