from django.core.management.base import BaseCommand
from datetime import datetime

class Command(BaseCommand):
    help = 'Importa dados da API ASTO (Logpay). ATUALMENTE EM MANUTENÇÃO.'

    def add_arguments(self, parser):
        parser.add_argument('start_date', type=str, help='Data inicial (YYYY-MM-DD)')
        parser.add_argument('end_date', type=str, help='Data final (YYYY-MM-DD)')

    def handle(self, *args, **options):
        self.stdout.write(self.style.ERROR("Integração ASTO (Manutenção) Pausada"))
        self.stdout.write(self.style.WARNING(
            """
Não foi possível carregar os dados do ASTO (Manutenção).

Motivo: Nenhuma das APIs ASTO/Logpay testadas fornece os dados necessários.
- A API de Fatura (`.../FaturaPagamentoFechadaApuracao`) funciona, mas **não retorna o CNPJ do Cliente**.
- A API de Transações (`.../ManutencoesAnalitico`) **retorna erro 404**.

Ação Necessária: Por favor, entre em contato com o suporte da ASTO/Logpay e solicite um 
endpoint de transações analíticas que inclua `cnpjCliente`, `valor` e `data`.
            """
        ))
        self.stdout.write(self.style.SUCCESS("Nenhum dado do ASTO foi importado."))
