import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import os
import json

USUARIO_PIPERUN_META_EMPRESA = "MARCELO NERIS"

VENDEDORES_OCULTOS = [
    "DESCONHECIDO",
    # "ANDRE",
    # "INANJARA",
    # "JUSLIENE",
    "LETICIA",
    "THIAGO",
    "VERONICA",
    "LENIRA",
    "RODRIGO",
    "ROBSON"
]

# Função com cache para executar atualização a cada 1 hora
@st.cache_resource(ttl=3600/2)
def executar_atualizacao_dados(): 
    from getDataHardness import atualiza_dados_produtos_e_notas_fiscais
    atualiza_dados_produtos_e_notas_fiscais()

    from data_preparation import load_and_clean_data
    df = load_and_clean_data()
    
    # Converte colunas de data
    df['T007_Data_Emissao'] = pd.to_datetime(df['T007_Data_Emissao'])
    df['Data_Envio_XML'] = pd.to_datetime(df['Data_Envio_XML'])
    
    return df


@st.cache_resource(ttl=24*3600)
def carregar_metas():
    from getGoalsPipeRun import export_goals_by_seller
    export_goals_by_seller()  # Garante que o JSON seja atualizado antes de carregar
    """Carrega metas de vendedores do JSON"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        metas_file = os.path.join(script_dir, "data", "metas_por_vendedores.json")
        with open(metas_file, "r", encoding='utf-8') as f:
            metas = json.load(f)
        return metas
    except:
        return []


def normalizar_nome(nome):
    """Normaliza nomes para comparação, removendo acentos e espaços extras
    Extrai apenas o primeiro nome se houver múltiplas palavras"""
    import unicodedata
    if nome is None:
        return ""
    # Remove acentos
    nome_nfd = unicodedata.normalize('NFD', nome.upper())
    nome_sem_acentos = ''.join(char for char in nome_nfd if unicodedata.category(char) != 'Mn')
    # Remove espaços extras
    nome_normalizado = ' '.join(nome_sem_acentos.split())
    # Extrai apenas o primeiro nome
    primeiro_nome = nome_normalizado.split()[0] if nome_normalizado else ""
    return primeiro_nome


FATURAMENTO_MINIMO_INATIVIDADE = 500

# Configuração da página
st.set_page_config(
    page_title="Dashboard - AMM",
    page_icon="👩‍💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
    <style>
    .main-header {
        font-size: 3em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-ok {
        color: green;
        font-weight: bold;
    }
    .status-warning {
        color: orange;
        font-weight: bold;
    }
    .status-alert {
        color: red;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Carrega dados
df = executar_atualizacao_dados()
metas_data = carregar_metas()

# Header
st.markdown('<div class="main-header">📊 Dashboard de Vendas</div>', unsafe_allow_html=True)

# Sidebar - Seletor de Vendedor
st.sidebar.header("🔍 Seleção")

# Cria lista de vendedores únicos
vendedoras_list = sorted(df['vendedor.C007_Primeiro_Nome'].unique().tolist())
vendedoras_list = [v for v in vendedoras_list if v.upper() not in VENDEDORES_OCULTOS]
vendedoras_list.insert(0, "EMPRESA") 

vendedora_selecionada = st.sidebar.selectbox(
    "Selecione a Visão:",
    vendedoras_list,
    index=0
)

# Filtra dados de acordo com a seleção
if vendedora_selecionada == "EMPRESA":
    df_vendedor = df.copy()
else:
    df_vendedor = df[df['vendedor.C007_Primeiro_Nome'] == vendedora_selecionada].copy()

# Seletor de Mês/Ano
st.sidebar.subheader("📅 Período de Análise")

# Get current month/year as default
agora = datetime.now()
mes_padrao = agora.month
ano_padrao = agora.year

# Get available months and years from data
meses_disponiveis = sorted(df_vendedor['T007_Data_Emissao'].dt.month.unique())
anos_disponiveis = sorted(df_vendedor['T007_Data_Emissao'].dt.year.unique(), reverse=True)

# Handle empty data scenarios
if not meses_disponiveis:
    meses_disponiveis = [mes_padrao]
if not anos_disponiveis:
    anos_disponiveis = [ano_padrao]

col_mes, col_ano = st.sidebar.columns(2)

with col_mes:
    mes_selecionado = st.selectbox(
        "Mês:",
        meses_disponiveis,
        index=meses_disponiveis.index(mes_padrao) if mes_padrao in meses_disponiveis else 0,
        format_func=lambda x: f"{x:02d} - {['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][x-1]}"
    )

with col_ano:
    ano_selecionado = st.selectbox(
        "Ano:",
        anos_disponiveis,
        index=anos_disponiveis.index(ano_padrao) if ano_padrao in anos_disponiveis else 0
    )

data_inicio = pd.Timestamp(year=ano_selecionado, month=mes_selecionado, day=1)
if mes_selecionado == 12:
    data_fim = pd.Timestamp(year=ano_selecionado+1, month=1, day=1) - timedelta(days=1)
else:
    data_fim = pd.Timestamp(year=ano_selecionado, month=mes_selecionado+1, day=1) - timedelta(days=1)

df_vendedor_filtered = df_vendedor[
    (df_vendedor['T007_Data_Emissao'].dt.date >= data_inicio.date()) &
    (df_vendedor['T007_Data_Emissao'].dt.date <= data_fim.date())
].copy()

df_filtered = df[
    (df['T007_Data_Emissao'].dt.date >= data_inicio.date()) &
    (df['T007_Data_Emissao'].dt.date <= data_fim.date())
].copy()

# Métricas principais
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Vendas do Mês")

total_vendas = df_vendedor_filtered['Valor_Venda'].sum()
num_vendas = len(df_vendedor_filtered)
num_clientes = df_vendedor_filtered['Empresa'].nunique()
ticket_medio = total_vendas / num_vendas if num_vendas > 0 else 0

col1, col2 = st.sidebar.columns(2)
with col1: st.metric("Vendas", f"R$ {total_vendas:,.0f}")
with col2: st.metric("Nº Vendas", num_vendas)

col3, col4 = st.sidebar.columns(2)
with col3: st.metric("Ticket Médio", f"R$ {ticket_medio:,.0f}")
with col4: st.metric("Nº Clientes", num_clientes)

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Manutenção")
if st.sidebar.button("Forçar Atualização Completa"):
    st.sidebar.info("Iniciando atualização forçada...")
    st.cache_resource.clear()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    arquivos_para_deletar = [
        os.path.join(data_dir, "notas_fiscais_combinadas.csv"),
        os.path.join(data_dir, "produtos_combinados.csv"),
        os.path.join(data_dir, "metas_por_vendedores.json")
    ]
    for arquivo in arquivos_para_deletar:
        if os.path.exists(arquivo):
            os.remove(arquivo)
            st.sidebar.write(f"Arquivo {os.path.basename(arquivo)} removido.")
    st.rerun()

# Tabs principais
tab1, tab2, tab3, tab4 = st.tabs(
    ["🎯 Metas", "📊 Vendas", "👥 Análise de Clientes", "🏆 Ranking"]
)

# =============== TAB 1: METAS ===============
with tab1:
    st.subheader(f"🎯 Metas - {vendedora_selecionada}")
    meta_vendedor = None
    
    if vendedora_selecionada == "EMPRESA":
        # Busca a meta cadastrada para o usuário configurado para a Empresa (ex: Marcelo Neris)
        nome_meta_empresa_norm = normalizar_nome(USUARIO_PIPERUN_META_EMPRESA)
        for vendedor_meta in metas_data:
            if normalizar_nome(vendedor_meta['nome']) == nome_meta_empresa_norm:
                meta_vendedor = vendedor_meta
                break
    else:
        nome_normalizado = normalizar_nome(vendedora_selecionada)
        for vendedor_meta in metas_data:
            if normalizar_nome(vendedor_meta['nome']) == nome_normalizado:
                meta_vendedor = vendedor_meta
                break
    
    if meta_vendedor is None:
        st.info(f"ℹ️ Nenhuma meta cadastrada para {vendedora_selecionada}. Exibindo vendas do período.")
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("💰 Vendas Total", f"R$ {total_vendas:,.0f}")
        with col2: st.metric("📊 Nº de Vendas", num_vendas)
        with col3: st.metric("📈 Ticket Médio", f"R$ {ticket_medio:,.0f}")
        with col4: st.metric("🏢 Nº de Clientes", num_clientes)
        
        st.subheader("Evolução de Vendas")
        if not df_vendedor_filtered.empty:
            df_vendedor_filtered['Data'] = df_vendedor_filtered['T007_Data_Emissao'].dt.date
            df_diario = df_vendedor_filtered.groupby('Data').agg({'Valor_Venda': ['sum', 'count']}).reset_index()
            df_diario.columns = ['Data', 'Valor', 'Quantidade']
            df_diario = df_diario.sort_values('Data')
            
            col1, col2 = st.columns(2)
            with col1:
                if len(df_diario) > 0:
                    fig_linha = px.line(df_diario, x='Data', y='Valor', markers=True, title="Evolução de Vendas (Diário)", labels={'Valor': 'Valor (R$)', 'Data': 'Dia'}, color_discrete_sequence=['#1f77b4'])
                    fig_linha.update_traces(line=dict(width=3), marker=dict(size=8))
                    st.plotly_chart(fig_linha, width='stretch', key="fig_linha_sem_meta")
            with col2:
                if len(df_diario) > 0:
                    fig_barras = px.bar(df_diario, x='Data', y='Quantidade', title="Quantidade de Vendas (Diário)", labels={'Quantidade': 'Nº de Vendas', 'Data': 'Dia'}, color='Quantidade', color_continuous_scale='Blues')
                    st.plotly_chart(fig_barras, width='stretch', key="fig_barras_sem_meta")
    else:
        meta_periodo = 0
        metas_list = []
        for meta in meta_vendedor['metas']:
            meta_date_inicio = pd.to_datetime(meta['data_inicio']).date()
            meta_date_fim = pd.to_datetime(meta['data_fim']).date()
            if not (meta_date_fim < data_inicio.date() or meta_date_inicio > data_fim.date()):
                meta_periodo += meta['valor']
                metas_list.append({'período': f"{meta_date_inicio.strftime('%m/%Y')}", 'valor': meta['valor'], 'titulo': meta['goal_title']})
        
        # Realizado atual
        realizado = total_vendas
        percentual_atingido = (realizado / meta_periodo * 100) if meta_periodo > 0 else 0
        
        # --- CÁLCULO PONDERADO POR DIAS DECORRIDOS (PRORATA) ---
        hoje = datetime.now().date()
        
        # Identifica quantos dias o mês do filtro possui (ex: 28, 30, 31)
        dias_no_mes = (data_fim - data_inicio).days + 1
        
        # Determina quantos dias já se passaram no mês selecionado
        if ano_selecionado < hoje.year or (ano_selecionado == hoje.year and mes_selecionado < hoje.month):
            # Mês já encerrado: considera 100% dos dias
            dias_decorridos = dias_no_mes
        elif ano_selecionado > hoje.year or (ano_selecionado == hoje.year and mes_selecionado > hoje.month):
            # Mês futuro: considera 0 dias
            dias_decorridos = 0
        else:
            # Mês atual: considera os dias decorridos até hoje
            dias_decorridos = min(hoje.day, dias_no_mes)

        # Proporção do mês decorrida (ex: 15/30 = 0.5 ou 50%)
        proporcao_decorrida = (dias_decorridos / dias_no_mes) if dias_no_mes > 0 else 1.0

        # Meta esperada para o dia atual do mês
        meta_proporcional = meta_periodo * proporcao_decorrida

        # Percentual atingido em relação à meta esperada no dia (% do ritmo ideal)
        percentual_ritmo = (realizado / meta_proporcional * 100) if meta_proporcional > 0 else (100.0 if percentual_atingido >= 100 else 0.0)

        # --- AVALIAÇÃO DE STATUS PONDERADA ---
        if percentual_atingido >= 100:
            status, status_class = "✅ META ATINGIDA", "status-ok"
        elif percentual_ritmo >= 100:
            status, status_class = "✅ NO RITMO DA META", "status-ok"
        elif percentual_ritmo >= 80:
            status, status_class = "⚠️ META PRÓXIMA", "status-warning"
        else:
            status, status_class = "❌ ABAIXO DA META", "status-alert"

        # Métricas exibidas na tela
        col1, col2, col3, col4 = st.columns(4)
        with col1: 
            st.metric("🎯 Meta Total", f"R$ {meta_periodo:,.0f}", help=f"Meta proporcional até dia {dias_decorridos}/{dias_no_mes}: R$ {meta_proporcional:,.0f}")
        with col2: 
            st.metric("📊 Realizado", f"R$ {realizado:,.0f}")
        with col3: 
            st.metric("% Atingido (Mês / Ritmo)", f"{percentual_atingido:.1f}%", delta=f"{percentual_ritmo:.1f}% do ritmo esperado" if proporcao_decorrida < 1.0 else None)
        with col4: 
            st.markdown(f"<div class='{status_class}'>{status}</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=percentual_atingido, title={'text': "Progresso da Meta (%)"}, delta={'reference': 100},
                gauge={'axis': {'range': [0, 150]}, 'bar': {'color': "darkblue"}, 'steps': [{'range': [0, 80], 'color': "lightgray"}, {'range': [80, 100], 'color': "gray"}], 'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 100}}
            ))
            fig_gauge.update_layout(height=400)
            st.plotly_chart(fig_gauge, width='stretch', key="fig_gauge_meta")
        
        with col2:
            historico_metas = []
            for meta in meta_vendedor['metas']:
                m_inicio = pd.to_datetime(meta['data_inicio']).date()
                m_fim = pd.to_datetime(meta['data_fim']).date()
                if m_inicio <= data_inicio.date():
                    historico_metas.append({'data_inicio': m_inicio, 'data_fim': m_fim, 'valor_meta': meta['valor'], 'periodo_str': m_inicio.strftime('%m/%Y')})
            
            historico_metas = sorted(historico_metas, key=lambda x: x['data_inicio'], reverse=True)[:3]
            historico_metas = sorted(historico_metas, key=lambda x: x['data_inicio'])
            
            historico_plot_data = []
            for m in historico_metas:
                vendas_periodo = df_vendedor[(df_vendedor['T007_Data_Emissao'].dt.date >= m['data_inicio']) & (df_vendedor['T007_Data_Emissao'].dt.date <= m['data_fim'])]['Valor_Venda'].sum()
                historico_plot_data.append({'Período': m['periodo_str'], 'Tipo': 'Meta', 'Valor': m['valor_meta']})
                historico_plot_data.append({'Período': m['periodo_str'], 'Tipo': 'Realizado', 'Valor': vendas_periodo})
                
            if not historico_plot_data:
                historico_plot_data = [{'Período': data_inicio.strftime('%m/%Y'), 'Tipo': 'Meta', 'Valor': meta_periodo}, {'Período': data_inicio.strftime('%m/%Y'), 'Tipo': 'Realizado', 'Valor': realizado}]
                
            df_compare = pd.DataFrame(historico_plot_data)
            fig_compare = px.bar(df_compare, x='Período', y='Valor', color='Tipo', barmode='group', title="Últimas 3 Metas vs Realizado", labels={'Valor': 'Valor (R$)'}, color_discrete_map={'Meta': '#1f77b4', 'Realizado': '#ff7f0e'}, text_auto=True)
            st.plotly_chart(fig_compare, width='stretch', key="fig_compare_meta")
        
        st.subheader("Detalhamento de Metas")
        if metas_list:
            df_metas_display = pd.DataFrame(metas_list)
            st.dataframe(df_metas_display, width='stretch', hide_index=True, column_config={"valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})
        else:
            st.info("Nenhuma meta no período selecionado")


# =============== TAB 2: VENDAS ===============
with tab2:
    st.subheader(f"📊 Análise de Vendas - {vendedora_selecionada}")
    
    if len(df_vendedor_filtered) == 0:
        st.warning("Sem dados de vendas no período selecionado")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            df_vendedor_filtered['Data'] = df_vendedor_filtered['T007_Data_Emissao'].dt.date
            df_diario = df_vendedor_filtered.groupby('Data').agg({'Valor_Venda': ['sum', 'count']}).reset_index()
            df_diario.columns = ['Data', 'Valor', 'Quantidade']
            df_diario = df_diario.sort_values('Data')
            
            cor_linha = '#2ca02c' if vendedora_selecionada == "EMPRESA" else '#1f77b4'
            fig_linha = px.line(df_diario, x='Data', y='Valor', markers=True, title="Evolução de Vendas (Diário)", labels={'Valor': 'Valor (R$)', 'Data': 'Dia'}, color_discrete_sequence=[cor_linha])
            fig_linha.update_traces(line=dict(width=3), marker=dict(size=8))
            st.plotly_chart(fig_linha, width='stretch', key=f"fig_linha_tab2_{vendedora_selecionada}")
        
        with col2:
            escala_cores = 'Greens' if vendedora_selecionada == "EMPRESA" else 'Blues'
            fig_barras = px.bar(df_diario, x='Data', y='Quantidade', title="Quantidade de Vendas (Diário)", labels={'Quantidade': 'Nº de Vendas', 'Data': 'Dia'}, color='Quantidade', color_continuous_scale=escala_cores)
            st.plotly_chart(fig_barras, width='stretch', key=f"fig_barras_tab2_{vendedora_selecionada}")
        
        st.subheader("Detalhe Diário de Vendas")
        df_detalhe = df_vendedor_filtered.groupby(['Data', 'Empresa']).agg({'Valor_Venda': ['sum', 'count']}).reset_index()
        df_detalhe.columns = ['Data', 'Empresa', 'Valor', 'Quantidade']
        df_detalhe = df_detalhe.sort_values(['Data', 'Valor'], ascending=[False, False])
        
        df_detalhe_display = df_detalhe.copy()
        df_detalhe_display['Data'] = df_detalhe_display['Data'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.dataframe(df_detalhe_display, width='stretch', hide_index=True, column_config={"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")})


# =============== TAB 3: ANÁLISE DE CLIENTES ===============
with tab3:
    st.subheader(f"👥 Análise de Carteira de Clientes - {vendedora_selecionada}")
    
    if len(df_vendedor) == 0:
        st.warning("Sem dados de clientes para esta visualização")
    else:
        # 1. Busca as datas GLOBAIS do cliente (usando df completo, sem filtro de vendedor)
        df_global_datas = df.groupby('Empresa').agg(
            Ultima_Venda=('T007_Data_Emissao', 'max'),
            Primeira_Venda=('T007_Data_Emissao', 'min')
        ).reset_index()

        # 2. Agrupa os dados do VENDEDOR atual (para saber quanto ELE vendeu para essa empresa)
        df_clientes = df_vendedor.groupby('Empresa').agg(
            Faturamento_Total=('Valor_Venda', 'sum'),
            Num_Vendas=('Valor_Venda', 'count'),
            Vendedora=('vendedor.C007_Primeiro_Nome', 'first')
        ).reset_index()
        
        # 3. Junta as informações: Histórico do Vendedor + Datas Globais de Atividade
        df_clientes = pd.merge(df_clientes, df_global_datas, on='Empresa', how='left')
        
        # Filtra clientes com faturamento mínimo (pelo histórico do vendedor)
        df_clientes = df_clientes[df_clientes['Faturamento_Total'] >= FATURAMENTO_MINIMO_INATIVIDADE].copy()
        
        # Calcula dias de inatividade baseado na última venda GLOBAL
        data_referencia = df['T007_Data_Emissao'].max()
        df_clientes['Dias_Inatividade'] = (data_referencia - df_clientes['Ultima_Venda']).dt.days
        
        # Faturamento Médio Mensal dos Últimos 6 Meses do Cliente (Usa o histórico GLOBAL)
        def calcular_ticket_6m(empresa):
            # Alterado de df_vendedor para df (analisa a força de compra real do cliente na empresa)
            df_cliente = df[df['Empresa'] == empresa]
            if df_cliente.empty: return 0
            
            ultima_data = df_cliente['T007_Data_Emissao'].max()
            seis_meses_antes = ultima_data - pd.Timedelta(days=180)
            
            vendas_6m = df_cliente[df_cliente['T007_Data_Emissao'] >= seis_meses_antes]
            if vendas_6m.empty: return 0
            
            return vendas_6m['Valor_Venda'].sum() / 6

        df_clientes['Ticket_Medio_6m'] = df_clientes['Empresa'].apply(calcular_ticket_6m)
        
        # Classificação AA a D
        def classificar_cliente(ticket):
            if ticket >= 5000: return 'AA'
            elif ticket >= 3000: return 'A'
            elif ticket >= 1500: return 'B'
            elif ticket >= 700: return 'C'
            else: return 'D'

        df_clientes['Curva'] = df_clientes['Ticket_Medio_6m'].apply(classificar_cliente)
        
        # Definição de Status (Novo, Ativo, Em Risco, Inativo)
        def definir_status(row):
            if row['Primeira_Venda'].year == 2026:
                return 'Novo'
            elif row['Dias_Inatividade'] <= 30:
                return 'Ativo'
            elif row['Dias_Inatividade'] <= 90:
                return 'Em Risco'
            else:
                return 'Inativo'
        
        df_clientes['Status'] = df_clientes.apply(definir_status, axis=1)
        
        if len(df_clientes) == 0:
            st.info("Nenhum cliente encontrado com os critérios.")
        else:
            st.markdown("### 🎯 Foco de Ação (Curvas AA, A e B)")
            st.markdown("Gráficos filtrados para exibir apenas os clientes de maior retorno, indicando onde devemos priorizar o atendimento.")
            
            # Filtro apenas para Curvas AA, A e B
            df_prioridade = df_clientes[df_clientes['Curva'].isin(['AA', 'A', 'B'])].copy()
            
            if not df_prioridade.empty:
                col_graf1, col_graf2 = st.columns(2)
                
                with col_graf1:
                    # Gráfico de Barras: Status por Curva
                    fig_status = px.histogram(
                        df_prioridade, 
                        x='Status', 
                        color='Curva',
                        title="Clientes Alta Prioridade (AA, A, B) por Status",
                        category_orders={"Status": ["Novo", "Ativo", "Em Risco", "Inativo"], "Curva": ["AA", "A", "B"]},
                        color_discrete_map={"AA": "#00441b", "A": "#238b45", "B": "#74c476"},
                        barmode="group",
                        text_auto=True
                    )
                    fig_status.update_layout(yaxis_title="Qtd Clientes")
                    st.plotly_chart(fig_status, width='stretch')
                    
                with col_graf2:
                    # Scatter Plot: Dias Inatividade vs Ticket
                    fig_scatter = px.scatter(
                        df_prioridade,
                        x='Dias_Inatividade',
                        y='Ticket_Medio_6m',
                        color='Status',
                        size='Faturamento_Total',
                        hover_name='Empresa',
                        title="Matriz de Risco: Inatividade vs Ticket Médio",
                        labels={'Dias_Inatividade': 'Dias sem comprar', 'Ticket_Medio_6m': 'Fat. Médio Mensal (6m)'},
                        category_orders={"Status": ["Novo", "Ativo", "Em Risco", "Inativo"]},
                        color_discrete_map={"Novo": "#17becf", "Ativo": "#2ca02c", "Em Risco": "#ff7f0e", "Inativo": "#d62728"}
                    )
                    # Linhas de demarcação de Risco (30 e 90 dias)
                    fig_scatter.add_vline(x=30, line_dash="dash", line_color="green", annotation_text="Ativos", annotation_position="top left")
                    fig_scatter.add_vline(x=90, line_dash="dash", line_color="red", annotation_text="Inativos", annotation_position="top right")
                    
                    st.plotly_chart(fig_scatter, width='stretch')
            else:
                st.info("Não há clientes nas categorias AA, A ou B para análise de risco neste período.")

            st.markdown("---")
            st.subheader("📋 Tabela Analítica de Clientes (Geral)")
            
            df_display = df_clientes.copy()
            df_display['Ultima_Venda'] = df_display['Ultima_Venda'].dt.strftime('%d/%m/%Y')
            
            # Ordenação personalizada (Curva AA->D, depois por Inatividade descrescente)
            ordem_curva = {'AA': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5}
            df_display['Ordem'] = df_display['Curva'].map(ordem_curva)
            df_display = df_display.sort_values(by=['Ordem', 'Dias_Inatividade'], ascending=[True, False]).drop('Ordem', axis=1)
            
            # ================= CRIANDO OS FILTROS =================
            opcoes_curva = [c for c in ['AA', 'A', 'B', 'C', 'D'] if c in df_display['Curva'].unique()]
            opcoes_status = [s for s in ['Novo', 'Ativo', 'Em Risco', 'Inativo'] if s in df_display['Status'].unique()]
            
            col_filtro1, col_filtro2 = st.columns(2)
            
            with col_filtro1:
                filtro_curva = st.multiselect(
                    "Filtrar por Curva (Deixe vazio para mostrar todas):",
                    options=opcoes_curva,
                    default=[]
                )
                
            with col_filtro2:
                filtro_status = st.multiselect(
                    "Filtrar por Status (Deixe vazio para mostrar todos):",
                    options=opcoes_status,
                    default=[]
                )
            
            # Aplica os filtros ao dataframe se houver algo selecionado
            df_tabela_filtrada = df_display.copy()
            
            if filtro_curva:
                df_tabela_filtrada = df_tabela_filtrada[df_tabela_filtrada['Curva'].isin(filtro_curva)]
                
            if filtro_status:
                df_tabela_filtrada = df_tabela_filtrada[df_tabela_filtrada['Status'].isin(filtro_status)]
            # =======================================================
            
            # Ajustando a ordem das colunas para visualização
            cols_display = ['Empresa', 'Vendedora', 'Curva', 'Status', 'Ticket_Medio_6m', 'Dias_Inatividade', 'Ultima_Venda', 'Faturamento_Total', 'Num_Vendas']
            
            st.dataframe(
                df_tabela_filtrada[cols_display],
                width='stretch',
                hide_index=True,
                column_config={
                    "Curva": st.column_config.TextColumn("Curva"),
                    "Status": st.column_config.TextColumn("Status"),
                    "Ticket_Medio_6m": st.column_config.NumberColumn("Fat. Mensal (6m)", format="R$ %.2f"),
                    "Dias_Inatividade": st.column_config.NumberColumn("Dias Inativos"),
                    "Ultima_Venda": st.column_config.TextColumn("Última Venda (Global)"),
                    "Faturamento_Total": st.column_config.NumberColumn("Fat. Total (Vendedor)", format="R$ %.2f"),
                    "Num_Vendas": st.column_config.NumberColumn("Nº Vendas (Vendedor)")
                }
            )


# =============== TAB 4: RANKING ===============
with tab4:
    st.subheader("🏆 Ranking de Vendedoras")
    st.markdown(f"**Período:** {data_inicio.strftime('%m/%Y')}")
    
    vendedoras_uniques_ranking = sorted(df['vendedor.C007_Primeiro_Nome'].unique().tolist())
    vendedoras_uniques_ranking = [v for v in vendedoras_uniques_ranking if v.upper() not in VENDEDORES_OCULTOS]
    
    ranking_data = []
    
    for vendedora_rank in vendedoras_uniques_ranking:
        df_vendedora = df_filtered[df_filtered['vendedor.C007_Primeiro_Nome'] == vendedora_rank]
        total_vendas_vendedora = df_vendedora['Valor_Venda'].sum()
        
        meta_vendedor_rank = None
        nome_normalizado_rank = normalizar_nome(vendedora_rank)
        for vendedor_meta in metas_data:
            if normalizar_nome(vendedor_meta['nome']) == nome_normalizado_rank:
                meta_vendedor_rank = vendedor_meta
                break
        
        meta_total = 0
        if meta_vendedor_rank is not None:
            for meta in meta_vendedor_rank['metas']:
                meta_date_inicio = pd.to_datetime(meta['data_inicio']).date()
                meta_date_fim = pd.to_datetime(meta['data_fim']).date()
                if not (meta_date_fim < data_inicio.date() or meta_date_inicio > data_fim.date()):
                    meta_total += meta['valor']
        
        percentual_atingido = (total_vendas_vendedora / meta_total * 100) if meta_total > 0 else 0
        
        ranking_data.append({
            'Posição': 0, 
            'Vendedora': vendedora_rank,
            '% Meta': percentual_atingido,
            'tem_meta': meta_total > 0
        })
    
    df_ranking = pd.DataFrame(ranking_data)
    
    df_ranking_com_meta = df_ranking[df_ranking['tem_meta']].copy()
    df_ranking_sem_meta = df_ranking[~df_ranking['tem_meta']].copy()
    
    df_ranking_com_meta = df_ranking_com_meta.sort_values('% Meta', ascending=False).reset_index(drop=True)
    df_ranking_sem_meta = df_ranking_sem_meta.sort_values('Vendedora', ascending=True).reset_index(drop=True)
    
    df_ranking_com_meta['Posição'] = range(1, len(df_ranking_com_meta) + 1)
    df_ranking_sem_meta['Posição'] = range(len(df_ranking_com_meta) + 1, len(df_ranking_com_meta) + len(df_ranking_sem_meta) + 1)
    
    df_ranking_final = pd.concat([df_ranking_com_meta, df_ranking_sem_meta], ignore_index=True)
    
    st.markdown("---")
    
    def formata_nome(row):
        pos = int(row['Posição'])
        nome = row['Vendedora']
        if pos == 1: return f"🥇 {nome}"
        elif pos == 2: return f"🥈 {nome}"
        elif pos == 3: return f"🥉 {nome}"
        return f"{pos}º {nome}"

    def define_cor(pos):
        if pos == 1: return "#ffd700"
        elif pos == 2: return "#c0c0c0"
        elif pos == 3: return "#cd7f32"
        return "#1f77b4"

    df_ranking_final['Nome_Display'] = df_ranking_final.apply(formata_nome, axis=1)
    df_ranking_final['Cor'] = df_ranking_final['Posição'].apply(define_cor)
    
    fig_ranking = px.bar(
        df_ranking_final,
        x='Nome_Display',
        y='% Meta',
        title="Ranking Geral de Vendedoras - % da Meta Atingida",
        labels={'% Meta': '% da Meta', 'Nome_Display': 'Vendedora'},
        color='Cor',
        color_discrete_map='identity',
        text='% Meta'
    )
    
    fig_ranking.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_ranking.update_layout(xaxis_tickangle=-45, yaxis=dict(ticksuffix="%"), showlegend=False, height=500, margin=dict(t=50, b=100))
    st.plotly_chart(fig_ranking, width='stretch')


st.markdown("---")
st.markdown("👩‍💼 Dashboard - Última atualização: {} | Período: {} a {}".format(
    datetime.now().strftime("%d/%m/%Y %H:%M"),
    data_inicio.strftime("%d/%m/%Y"),
    data_fim.strftime("%d/%m/%Y")
))