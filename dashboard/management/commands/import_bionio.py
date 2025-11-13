import pandas as pd
from datetime import datetime
from decimal import Decimal
import sys
import os 

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone # <--- ESTE IMPORT É CRUCIAL
# (NOVO) Importa os modelos de Log e User
from dashboard.models import User, Client, Sale, AuditLog
# ... (restante do código)

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
    help = 'Importa dados de vendas do arquivo CSV Bionio'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho para o arquivo Bionio.csv')
        # (NOVO) Argumento para saber QUEM iniciou
        parser.add_argument('--user-id', type=int, help='ID do utilizador que iniciou a ação', default=None)

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando importação do Bionio...'))
        
        file_path = options['csv_file']
        user = None
        if options['user_id']:
            try: user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist: user = None
        
        log_details = {"file_type": "bionio", "filename": os.path.basename(file_path)}
        
        try:
            # --- 1. Pré-carrega mapas ---
            self.stdout.write("Carregando mapa de clientes e consultores...")
            client_map = {c.cnpj: c for c in Client.objects.all()}
            user_map = {u: u.manager for u in User.objects.filter(role=User.Role.CONSULTANT)}
            cnpj_to_consultant = {c.cnpj: c.consultant for c in Client.objects.all() if c.consultant}

            # --- 2. Leitura do CSV ---
            try:
                df = pd.read_csv(
                    file_path, sep=';', 
                    dtype={'CNPJ da organização': str}, encoding='latin-1'
                )
            except Exception as e:
                raise Exception(f"Erro ao ler o CSV: {e}")

            df_paid = df[df['Status do pedido'].isin(['Transferido', 'Pago e Agendado'])].copy()
            if df_paid.empty:
                self.stdout.write(self.style.WARNING("Nenhum registro de venda válida encontrado."))
                return

            # --- 3. Processamento ---
            sales_to_process = {}
            total_rows = len(df_paid)
            orphans_found = 0
            
            for index, row in df_paid.iterrows():
                cnpj = clean_cnpj(row['CNPJ da organização'])
                if not cnpj: continue 

                try:
                    naive_datetime = datetime.strptime(row['Data do pagamento do pedido'], "%d/%m/%Y")
                    # (CORREÇÃO - Naive Datetime)
                    # CORREÇÃO: Esta linha exige o import de timezone
                    data_pagamento = timezone.make_aware(naive_datetime, timezone.get_default_timezone())
                except: continue 

                revenue = clean_value(row['Valor total do pedido'])
                doc_id = f"BIONIO_{row['Número do pedido']}"
                
                client_obj = client_map.get(cnpj)
                consultant_obj = client_obj.consultant if client_obj else cnpj_to_consultant.get(cnpj)
                manager_obj = client_obj.manager if client_obj else (user_map.get(consultant_obj) if consultant_obj else None)

                if not consultant_obj:
                    orphans_found += 1

                sale = Sale(
                    source="Bionio", raw_id=doc_id, client=client_obj,
                    consultant=consultant_obj, manager=manager_obj,
                    raw_client_cnpj=cnpj, raw_client_name=row['Nome fantasia'],
                    date=data_pagamento, revenue_gross=revenue, revenue_net=revenue,
                    product_name=row['Nome do benefício'], status=row['Status do pedido'],
                    payment_type=row['Tipo de pagamento'],
                )
                sales_to_process[doc_id] = sale
            
            # --- 4. Salva no Banco de Dados ---
            final_sales_list = list(sales_to_process.values())
            self.stdout.write(f"Processamento concluído. {len(final_sales_list)} vendas ÚNICAS prontas para salvar.")
            
            Sale.objects.bulk_create(
                final_sales_list, batch_size=1000,
                unique_fields=['source', 'raw_id'],
                update_conflicts=True,
                update_fields=['client', 'consultant', 'manager', 'date', 'revenue_gross', 
                               'revenue_net', 'product_name', 'status', 'payment_type']
            )
            
            # (NOVO) Regista o SUCESSO no log
            log_details.update({
                "status": "Sucesso",
                "rows_found": len(df),
                "rows_processed": total_rows,
                "rows_saved": len(final_sales_list),
                "orphans_found": orphans_found
            })
            AuditLog.objects.create(user=user, action="fim_carga_csv", details=log_details)
            self.stdout.write(self.style.SUCCESS(f"Importação Bionio concluída! {len(final_sales_list)} registros salvos."))

        except Exception as e:
            # (NOVO) Regista a FALHA no log
            self.stdout.write(self.style.ERROR(f"Erro durante a importação: {e}"))
            log_details.update({"status": "Falha", "error": str(e)})
            AuditLog.objects.create(user=user, action="falha_carga_csv", details=log_details)
            sys.exit(1) # Termina com erro