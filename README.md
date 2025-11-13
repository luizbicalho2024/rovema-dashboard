![Logo Rovema Bank](https://raw.githubusercontent.com/luizbicalho2024/rovema-dashboard/main/dashboard/static/dashboard/images/logoRB.png)

# Rovema Bank - BI Comercial (Rovema Pulse)

O projeto **BI Comercial Rovema** é uma plataforma analítica robusta, migrada de um protótipo em Streamlit para uma aplicação web completa em Django. Ela foi desenhada para consolidar, analisar e visualizar métricas de performance de vendas de múltiplos produtos (Rovema Pay, Bionio, ELIQ, etc.), fornecendo dashboards e ferramentas de gestão para diferentes níveis de acesso: Administradores, Gestores e Consultores.

A aplicação utiliza uma arquitetura de backend Django com uma base de dados PostgreSQL para garantir performance e escalabilidade, e um frontend moderno com Bootstrap 5, amCharts e DataTables para uma experiência de utilizador rica e responsiva.

---

## 1. Arquitetura da Solução

* **Backend:** Django 5.x
* **Base de Dados:** PostgreSQL
* **Frontend:** Bootstrap 5, amCharts (Gráficos), Tom Select (Filtros), DataTables.js (Tabelas Interativas).
* **Servidor:** Ubuntu Server (preparado para Gunicorn + Nginx)
* **Processamento de Dados:** Pandas (para limpeza de CSVs) e `subprocess` (para tarefas de importação em segundo plano).

---

## 2. Funcionalidades Principais

O sistema é dividido por nível de acesso para garantir que cada utilizador veja apenas os dados relevantes.

### 2.1. Funcionalidades para Todos (Autenticados)

* **Login Personalizado:** Página de login segura e com a marca Rovema Bank.
* **Modo Dark/Light:** Um seletor de tema que persiste e atualiza os gráficos (amCharts).

### 2.2. Administrador (`admin`)

Tem acesso a tudo.
* **Dashboard Geral:** Visão completa da empresa, com filtros por Consultor, Produto e Data.
* **Gestão de Utilizadores (CRUD):** Interface para Criar, Ler, Editar e Eliminar utilizadores (Consultores, Gestores, Admins).
* **Gestão de Metas (CRUD):** Página para definir ou eliminar metas de receita para **todos** os consultores.
* **Atribuir Clientes:** Gestão de vendas órfãs para associar clientes sem consultor.
* **Gestão de Comissões (CRUD):** Interface para definir as regras de comissão (percentagem) por produto (source).
* **Carga de Dados:** Página para fazer upload de CSVs (Bionio, Rovema Pay) e disparar sincronizações de API (ELIQ).
* **Logs de Auditoria:** Visualização de todas as ações importantes (logins, uploads, saves) no sistema.

### 2.3. Gestor (`manager`)

Tem acesso aos seus dados e aos dados da sua equipa.
* **Dashboard Geral:** Visão filtrada por defeito para a sua equipa, com capacidade de filtrar por consultores *dentro* da sua equipa.
* **Minha Equipa (Dashboard de Gestor):** Visão consolidada da performance da sua equipa.
* **Gestão de Metas (CRUD):** Página para definir ou eliminar metas de receita *apenas* para os consultores da sua equipa.
* **Atribuir Clientes:** Pode atribuir clientes órfãos *apenas* a consultores da sua equipa.
* **Carga de Dados:** Pode iniciar uploads e sincronizações.

### 2.4. Consultor (`consultant`)

Tem acesso apenas aos seus próprios dados.
* **Dashboard Geral:** Visão filtrada *apenas* com os seus dados (não pode filtrar por outros consultores).
* **Minha Carteira (Dashboard de Consultor):** Visão detalhada da sua performance individual, metas e clientes.

---

## 3. Lógica de Negócio e Cálculos (BI)

A plataforma calcula vários KPIs e métricas de BI:

### 3.1. Dashboard Geral

* **Volume Total (TPV):** `Sum('revenue_gross')`. O volume total (bruto) transacionado pelos clientes.
* **Receita Líquida (Lucro):** `Sum('revenue_net')`. O valor líquido (lucro) gerado para a Rovema (ex: Spread do Rovema Pay ou valor total do Bionio).
* **Margem Média:** `(Receita Líquida / TPV) * 100`.
* **Top/Bottom 5 Clientes:** Agrupamento por `raw_client_cnpj` e `raw_client_name` (para incluir clientes órfãos) e ordenado por `Sum('revenue_gross')` (TPV).
* **Gráfico de TPV (12 Meses):** Agrupamento mensal (`TruncMonth`) de `Sum('revenue_gross')` dos últimos 365 dias.
* **Gráfico de Lucro por Produto:** Agrupamento por `source` de `Sum('revenue_net')`.

### 3.2. Minha Carteira / Minha Equipa

* **KPIs de Período:** (Receita Líquida, Clientes Ativados, Total na Carteira) são calculados com base no *período selecionado nos filtros de data*.
* **KPIs de Meta (Bug Corrigido):**
    * **Lógica:** O sistema de metas é **dinâmico**. Ele utiliza o **Mês e Ano** do campo **"Data Inicial"** do filtro (e não o mês atual) para calcular o progresso.
    * **Meta:** `Sum('target_value')` do mês/ano do filtro, para o consultor ou equipa.
    * **Realizado:** `Sum('revenue_net')` do mês/ano do filtro, para o consultor ou equipa.
    * **% Atingido:** `(Realizado / Meta) * 100`.
* **KPI de Comissão:**
    * Calculado com base no "Realizado" (`revenue_net`) do mês/ano do filtro.
    * A `views.py` busca todas as regras do modelo `CommissionRule` e aplica a percentagem correspondente a cada venda (ex: `vendas_bionio * percent_bionio_db`).
* **Gráfico de Receita (12 Meses):** Tendência de `Sum('revenue_net')` dos últimos 365 dias, filtrado *apenas* para o consultor ou equipa.

---

## 4. Guia de Instalação e Replicação (Linux Server)

Este guia detalha o passo a passo para replicar esta aplicação num novo servidor **Ubuntu Server 22.04 LTS**.

### Passo 1: Pré-requisitos (No novo servidor)

Atualize o servidor e instale as dependências essenciais do sistema.

```bash
# Atualiza o sistema
sudo apt update && sudo apt upgrade -y

# Instala Python, Pip, Venv e Git
sudo apt install -y python3-pip python3-dev python3-venv git

# Instala as ferramentas de build (necessárias para o 'psycopg2')
sudo apt install -y build-essential
