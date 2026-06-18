import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import os
import warnings
from data_preparation import prepare_stock_analysis
from getDataHardness import atualiza_dados_estoque
import extra_streamlit_components as stx  # Biblioteca para gerenciar cookies persistentemente

# Configuração da página (DEVE SER A PRIMEIRA FUNÇÃO STREAMLIT)
st.set_page_config(
    page_title="Dashboard Gerencial de Vendas - AMM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SISTEMA DE AUTENTICAÇÃO VIA COOKIES ---
cookie_manager = stx.CookieManager()

# 1. Check if we just authenticated in this session, otherwise read from browser cookies
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

auth_token = cookie_manager.get(cookie="amm_dashboard_token")

# 2. Grant access if either the cookie is valid OR the session state was just set to True
if auth_token == st.secrets["ESTOQUE_DASHBOARD_PASSWORD"]:
    st.session_state["autenticado"] = True

if not st.session_state["autenticado"]:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style='background-color: #f8f9fa; padding: 30px; border-radius: 10px; border-top: 5px solid #1f77b4; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h2 style='text-align: center; color: #1f77b4;'>🔒 Acesso Restrito</h2>
                <p style='text-align: center; color: #6c757d;'>Insira a senha do PipeRun para acessar o painel.</p>
            </div>
        """, unsafe_allow_html=True)
        
        senha_digitada = st.text_input("Senha", type="password", key="input_senha")
        botao_login = st.button("Entrar", use_container_width=True)
        
        if botao_login:
            if senha_digitada == st.secrets["ESTOQUE_DASHBOARD_PASSWORD"]:
                # Set the session state first so the UI unlocks immediately
                st.session_state["autenticado"] = True
                
                # Save the persistent cookie for future visits (10 years)
                data_expiracao = datetime.now() + timedelta(days=3650)
                cookie_manager.set(
                    cookie="amm_dashboard_token", 
                    val=senha_digitada,
                    expires_at=data_expiracao
                )
                
                st.success("Autenticado com sucesso! Carregando...")
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
                
    st.stop()

# --- FIM DO SISTEMA DE AUTENTICAÇÃO ---

warnings.filterwarnings('ignore')

# Função com cache para executar atualização dos dados de estoque
@st.cache_resource(ttl=3600)
def executar_atualizacao_estoque():
    atualiza_dados_estoque()
    """
    Carrega dados de vendas (produtos_combinados.csv) e estoque (estoque_combinado.csv).
    Faz merge por ID do produto e retorna um DataFrame consolidado.
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Carrega dados de vendas
        df_vendas = pd.read_csv(os.path.join(script_dir, "data", "produtos_combinados.csv"), low_memory=False)
        df_vendas['T007_Data_Emissao'] = pd.to_datetime(df_vendas['T007_Data_Emissao'])
        df_vendas['T008_Descricao_Produto'] = df_vendas['T008_Descricao_Produto'].astype(str).str.split('- ').str[0]
        df_vendas['T008_Codigo_Produto'] = df_vendas['T008_Codigo_Produto'].astype(str).str.split('-').str[0]
        
        df_vendas = df_vendas.groupby(['T007_Data_Emissao', 'T008_Codigo_Produto', 'T008_Descricao_Produto']).agg({
            'T008_Quantidade': 'sum',
            'T008_Valor_Total_Preco_Sem_Desconto': 'sum'
        }).reset_index()

        # Carrega dados de estoque
        df_estoque = pd.read_csv(os.path.join(script_dir, "data", "estoque_combinado.csv"), low_memory=False)
        df_estoque['D001_Descricao_Produto'] = df_estoque['D001_Descricao_Produto'].astype(str).str.split('- ').str[0]
        df_estoque['D001_Codigo_Produto'] = df_estoque['D001_Codigo_Produto'].astype(str).str.split('-').str[0]
        
        # Ajuste no nome da coluna de quantidade para evitar quebras por espaços internos
        col_qtd_estoque = 'D009A_Qtd_Liquida_Fora	+ D009_Quantidade_Estoque_Liquido'
        df_estoque[col_qtd_estoque] = pd.to_numeric(df_estoque[col_qtd_estoque], errors='coerce').fillna(0)
        
        df_estoque = df_estoque.groupby(['D001_Descricao_Produto', 'D001_Codigo_Produto', 'D082_Marca']).agg({
            col_qtd_estoque: 'sum'
        }).reset_index()

        # Renomeia coluna de código de produto no estoque para facilitar merge
        df_estoque_renamed = df_estoque.rename(columns={
            'D001_Codigo_Produto': 'T008_Codigo_Produto',
            'D001_Descricao_Produto': 'D001_Descricao_Estoque',
            col_qtd_estoque: 'Estoque_Quantidade'
        })
        
        # Merge: left join na tabela de vendas (para manter histórico completo)
        df_merged = df_vendas.merge(
            df_estoque_renamed[['T008_Codigo_Produto', 'Estoque_Quantidade', 'D001_Descricao_Estoque', 'D082_Marca']],
            on='T008_Codigo_Produto',
            how='left'
        )
        
        # Preenche estoque faltante com 0 e garante tipos corretos
        df_merged['Estoque_Quantidade'] = df_merged['Estoque_Quantidade'].fillna(0).astype(float)
        df_merged['D082_Marca'] = df_merged['D082_Marca'].fillna('N/A').astype(str)
        
        # Remove linhas com vendas zeradas ou inválidas
        df_merged = df_merged[df_merged['T008_Quantidade'] > 0].copy()

        df_estoque_analysis = prepare_stock_analysis()
        return df_merged, df_estoque_analysis
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# ========================= CONFIGURAÇÃO STREAMLIT =========================
st.set_page_config(
    page_title="Dashboard de Estoque Crítico AMM",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================= CSS CUSTOMIZADO =========================
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5em;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ========================= CARREGAMENTO DE DADOS =========================
df_stock_data, df_estoque_analise = executar_atualizacao_estoque()

if df_stock_data.empty:
    st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos CSV estão no diretório 'data/'")
    st.stop()

# ========================= HEADER =========================
st.markdown('<div class="main-header">📦 Gestão de Estoque Crítico - AMM</div>', unsafe_allow_html=True)

# ========================= SIDEBAR - FILTROS =========================
st.sidebar.header("🔍 Filtros de Análise")

# Filtro de período
st.sidebar.subheader("Período de Análise")
min_date = df_stock_data['T007_Data_Emissao'].min()
max_date = df_stock_data['T007_Data_Emissao'].max()

hoje = datetime.now().date()
primeiro_dia_ano = datetime(hoje.year, 1, 1).date()

filtro_rapido = st.sidebar.selectbox(
    "Filtros Rápidos",
    options=["Year to Date (YTD)", "Todo o Histórico", "Último Ano", "Personalizado"],
    index=0
)

if filtro_rapido == "Year to Date (YTD)":
    data_padrao = (primeiro_dia_ano, hoje)
elif filtro_rapido == "Todo o Histórico":
    data_padrao = (min_date.date(), max_date.date())
elif filtro_rapido == "Último Ano":
    data_padrao = (hoje - timedelta(days=365), hoje)
else:
    data_padrao = (primeiro_dia_ano, hoje)

date_range = st.sidebar.date_input(
    "Selecione as datas:",
    value=data_padrao,
    min_value=min_date.date(),
    max_value=max_date.date(),
    disabled=(filtro_rapido != "Personalizado") 
)

if len(date_range) == 1:
    date_range = (date_range[0], date_range[0])
elif len(date_range) == 0:
    date_range = (primeiro_dia_ano, hoje)

# Threshold ajustável de cobertura
st.sidebar.subheader("⚙️ Configuração")
threshold_meses = st.sidebar.slider(
    "Meses de cobertura esperada:",
    min_value=1,
    max_value=6,
    value=2,
    help="Quantos meses de estoque você espera manter para cada produto?"
)

# ========================= FILTRAGEM DE DADOS =========================
df_filtered = df_stock_data.copy()

if len(date_range) == 2:
    df_filtered = df_filtered[
        (df_filtered['T007_Data_Emissao'].dt.date >= date_range[0]) &
        (df_filtered['T007_Data_Emissao'].dt.date <= date_range[1])
    ]

# ========================= ANÁLISE DE DADOS PARA MÉTRICAS =========================
# Estatísticas baseadas nos últimos 90 dias dinâmicos do período filtrado para o cálculo de giro
data_max_filtrada = df_filtered['T007_Data_Emissao'].max()
tres_meses_atras = data_max_filtrada - timedelta(days=90)
df_tres_meses = df_filtered[df_filtered['T007_Data_Emissao'] >= tres_meses_atras].copy()

# Agrupa por produto calculando a volumetria e faturamento para extrair preço médio
df_produtos_stats = df_tres_meses.groupby('T008_Codigo_Produto').agg({
    'T008_Quantidade': 'sum',
    'T008_Valor_Total_Preco_Sem_Desconto': 'sum',
    'Estoque_Quantidade': 'first',
    'T008_Descricao_Produto': 'first',
    'D082_Marca': 'first'
}).reset_index()

df_produtos_stats.columns = ['Codigo_Produto', 'Qtd_Vendida_3M', 'Valor_Total_3M', 'Estoque_Atual', 'Descricao', 'Marca']

# Regra de negócio: Preço Médio Praticado Sem Desconto (Evita strings fixas no df)
df_produtos_stats['Preco_Medio'] = (df_produtos_stats['Valor_Total_3M'] / df_produtos_stats['Qtd_Vendida_3M']).fillna(0)

# Cálculos de projeção normatizados numericamente
df_produtos_stats['Vendas_Media_Mes'] = df_produtos_stats['Qtd_Vendida_3M'] / 3
df_produtos_stats['Projecao_Com_Threshold'] = df_produtos_stats['Vendas_Media_Mes'] * threshold_meses
df_produtos_stats['Diferenca'] = df_produtos_stats['Estoque_Atual'] - df_produtos_stats['Projecao_Com_Threshold']

# Classificação de status pura
def classificar_status_simples(row):
    if row['Estoque_Atual'] < row['Projecao_Com_Threshold'] * 0.8:
        return "DEFICIT"
    elif row['Estoque_Atual'] < row['Projecao_Com_Threshold']:
        return "CRÍTICO"
    else:
        return "PARADO"

df_produtos_stats['Status'] = df_produtos_stats.apply(classificar_status_simples, axis=1)

# Indicadores de Sidebar
total_produtos = len(df_produtos_stats)
produtos_deficit = len(df_produtos_stats[df_produtos_stats['Status'] == "DEFICIT"])
produtos_critico = len(df_produtos_stats[df_produtos_stats['Status'] == "CRÍTICO"])

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Resumo Operacional (90 dias)")
st.sidebar.metric("Total Produtos Ativos", total_produtos)
st.sidebar.metric("🔴 Em Deficit", produtos_deficit, delta=f"-{produtos_deficit} urgente", delta_color="inverse")
st.sidebar.metric("🟡 Nível Crítico", produtos_critico)

# ========================= PAINEL VISUAL PRINCIPAL =========================
st.subheader("📊 Diagnóstico de Ruptura e Cobertura de Estoque")

# Ordenação puramente numérica dos itens mais críticos
df_produtos_stats_sorted = df_produtos_stats.sort_values('Diferenca', ascending=True)

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("### 📈 Proporção de Saúde do Estoque")
    status_counts = df_produtos_stats['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']
    
    cores_status_map = {'DEFICIT': '#e74c3c', 'CRÍTICO': '#f39c12', 'PARADO': '#2ecc71'}
    cores_lista = [cores_status_map.get(s, '#95a5a6') for s in status_counts['Status']]
    
    fig_status = px.pie(
        status_counts,
        names='Status',
        values='Quantidade',
        color='Status',
        color_discrete_map=cores_status_map,
        hole=0.4
    )
    fig_status.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
    st.plotly_chart(fig_status, width='stretch')

with col2:
    st.markdown("### 🔴 Top 10 Produtos com Maior Gargalo de Deficit")
    df_deficit_chart = df_produtos_stats_sorted[df_produtos_stats_sorted['Status'] == 'DEFICIT'].head(10).copy()
    
    if not df_deficit_chart.empty:
        # CONCATENAÇÃO DA DESCRIÇÃO COM O CÓDIGO PARA TORNAR O GRÁFICO INTELEGÍVEL
        df_deficit_chart['Label_Produto'] = df_deficit_chart['Descricao'] + " (" + df_deficit_chart['Codigo_Produto'] + ")"
        
        # Convertemos para valor absoluto para visualização clara de unidades em falta
        df_deficit_chart['Unidades_Faltantes'] = df_deficit_chart['Diferenca'].abs()
        
        fig_deficit = px.bar(
            df_deficit_chart,
            x='Unidades_Faltantes',
            y='Label_Produto',
            orientation='h',
            labels={'Unidades_Faltantes': 'Qtd Faltante para Meta (un)', 'Label_Produto': 'Produto (Código)'},
            color='Unidades_Faltantes',
            color_continuous_scale='Reds'
        )
        fig_deficit.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=350, showlegend=False)
        fig_deficit.update_yaxes(categoryorder='total ascending')
        st.plotly_chart(fig_deficit, width='stretch')
    else:
        st.success("✅ Excelente! Nenhum produto mapeado em estado de Deficit de cobertura.")

# ========================= TABELA DE AGUÍ DE DECISÃO (COMPRA) =========================
st.markdown("---")
st.markdown("### 📋 Painel de Recomendação de Abastecimento Pró-Ativo")
st.markdown("_Nota: Ordene as colunas clicando nos cabeçalhos. A exportação mantém os dados estritamente numéricos para análises externas._")

# Seleção de colunas limpas sem strings estáticas coladas
df_table_display = df_produtos_stats_sorted[[
    'Codigo_Produto', 'Descricao', 'Marca', 'Preco_Medio', 
    'Qtd_Vendida_3M', 'Vendas_Media_Mes', 'Projecao_Com_Threshold', 
    'Estoque_Atual', 'Diferenca', 'Status'
]].copy()

# Mapeamento do Streamlit column_config para tratamento de strings de visualização nativas
st.dataframe(
    df_table_display,
    width='stretch',
    hide_index=True,
    column_config={
        "Codigo_Produto": st.column_config.TextColumn("Código"),
        "Descricao": st.column_config.TextColumn("Descrição Produto"),
        "Marca": st.column_config.TextColumn("Marca"),
        "Preco_Medio": st.column_config.NumberColumn("Preço Médio (Venda)", format="R$ %.2f"),
        "Qtd_Vendida_3M": st.column_config.NumberColumn("Vendas (90d)", format="%d"),
        "Vendas_Media_Mes": st.column_config.NumberColumn("Média Mensal", format="%.1f"),
        "Projecao_Com_Threshold": st.column_config.NumberColumn(f"Meta Giro ({threshold_meses}M)", format="%.0f"),
        "Estoque_Atual": st.column_config.NumberColumn("Estoque Atual", format="%d"),
        "Diferenca": st.column_config.NumberColumn("Diferença Bruta", format="%d"),
        "Status": st.column_config.TextColumn("Classificação Status")
    }
)

# Exportador nativo simplificado baseado em dados numéricos puros
col_space, col_btn = st.columns([4, 1])
with col_btn:
    csv_pure = df_table_display.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Exportar Dados de Compra (CSV)",
        data=csv_pure,
        file_name=f"plano_reabastecimento_amm_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        width='stretch'
    )

# ========================= RODAPÉ =========================
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #7f8c8d; font-size: 12px;'>
        <p>Dashboard de Estoque Crítico - AMM (EPIS + Soluções) | Foco Exclusivo em Ruptura de Estoque</p>
        <p>Sincronização de Dados Atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    """, 
    unsafe_allow_html=True
)