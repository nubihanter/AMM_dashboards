import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Vendas AMM - EPIS + Soluções",
    page_icon="📊",
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
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Carrega o arquivo CSV combinado e limpo"""
    file_path = "data/notas_fiscais_combinadas_CLEAN.csv"
    
    # Verifica se arquivo limpo existe, caso contrário, prepara os dados
    if not os.path.exists(file_path):
        from data_preparation import load_and_clean_data
        df = load_and_clean_data(
        )
        df.to_csv(file_path, index=False)
    else:
        df = pd.read_csv(file_path)
    
    # Converte colunas de data
    df['T007_Data_Emissao'] = pd.to_datetime(df['T007_Data_Emissao'])
    df['Data_Envio_XML'] = pd.to_datetime(df['Data_Envio_XML'])
    
    return df

# Carrega dados
df = load_data()

# Header
st.markdown('<div class="main-header">📊 Dashboard de Vendas - AMM (EPIS + Soluções)</div>', unsafe_allow_html=True)

# Sidebar - Filtros
st.sidebar.header("🔍 Filtros")

# Filtro de Vendedora
vendedoras_list = sorted(df['vendedor.C007_Primeiro_Nome'].unique().tolist())
vendedoras_list.insert(0, "TOTAL EMPRESA")

vendedora_selecionada = st.sidebar.selectbox(
    "Selecione a Vendedora:",
    vendedoras_list,
    index=0
)

# Filtro de período
st.sidebar.subheader("Período de Análise")
min_date = df['T007_Data_Emissao'].min()
max_date = df['T007_Data_Emissao'].max()

date_range = st.sidebar.date_input(
    "Selecione o período:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filtra dados conforme seleção
if vendedora_selecionada != "TOTAL EMPRESA":
    df_filtered = df[df['vendedor.C007_Primeiro_Nome'] == vendedora_selecionada].copy()
else:
    df_filtered = df.copy()

# Filtra por data
if len(date_range) == 2:
    df_filtered = df_filtered[
        (df_filtered['T007_Data_Emissao'].dt.date >= date_range[0]) &
        (df_filtered['T007_Data_Emissao'].dt.date <= date_range[1])
    ]

# Métricas principais
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Métricas Principais")

total_vendas = df_filtered['Valor_Venda'].sum()
num_vendas = len(df_filtered)
ticket_medio = total_vendas / num_vendas if num_vendas > 0 else 0
num_clientes = df_filtered['Empresa'].nunique()

col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("Vendas Totais", f"R$ {total_vendas:,.0f}")
with col2:
    st.metric("Nº Vendas", num_vendas)

col3, col4 = st.sidebar.columns(2)
with col3:
    st.metric("Ticket Médio", f"R$ {ticket_medio:,.0f}")
with col4:
    st.metric("Nº Clientes", num_clientes)

# Tabs principais
tab1, tab2, tab3, tab4 = st.tabs(
    ["📅 Mensal", "📊 Trimestral", "📈 Anual", "🎯 Detalhado"]
)

# =============== TAB 1: ANÁLISE MENSAL ===============
with tab1:
    st.subheader("Análise Mensal de Vendas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Vendas mensais (série temporal)
        df_mensal = df_filtered.groupby('Ano_Mes')['Valor_Venda'].agg(['sum', 'count']).reset_index()
        df_mensal.columns = ['Mês', 'Valor', 'Quantidade']
        df_mensal = df_mensal.sort_values('Mês')
        
        fig_linha = px.line(
            df_mensal,
            x='Mês',
            y='Valor',
            markers=True,
            title="Evolução de Vendas (Mensal)",
            labels={'Valor': 'Valor (R$)', 'Mês': 'Período'}
        )
        fig_linha.update_traces(line=dict(color='#1f77b4', width=3), marker=dict(size=8))
        st.plotly_chart(fig_linha, width="stretch")
    
    with col2:
        # Quantidade de vendas mensais
        fig_barras = px.bar(
            df_mensal,
            x='Mês',
            y='Quantidade',
            title="Quantidade de Vendas (Mensal)",
            labels={'Quantidade': 'Quantidade', 'Mês': 'Período'},
            color='Quantidade',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_barras, width="stretch")
    
    # Tabela mensal
    st.subheader("Tabela de Vendas Mensais")
    df_mensal_display = df_mensal.copy()
    df_mensal_display['Valor'] = df_mensal_display['Valor'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_mensal_display, width="stretch")

# =============== TAB 2: ANÁLISE TRIMESTRAL ===============
with tab2:
    st.subheader("Análise Trimestral de Vendas")
    
    # Prepara dados trimestrais
    df_filtered_temp = df_filtered.copy()
    df_filtered_temp['Trimestre_str'] = df_filtered_temp['Trimestre'].astype(str)
    df_trimestral = df_filtered_temp.groupby('Trimestre_str')['Valor_Venda'].agg(['sum', 'count']).reset_index()
    df_trimestral.columns = ['Trimestre', 'Valor', 'Quantidade']
    df_trimestral = df_trimestral.sort_values('Trimestre')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_trim_linha = px.line(
            df_trimestral,
            x='Trimestre',
            y='Valor',
            markers=True,
            title="Evolução de Vendas (Trimestral)",
            labels={'Valor': 'Valor (R$)', 'Trimestre': 'Trimestre'}
        )
        fig_trim_linha.update_traces(line=dict(color='#2ca02c', width=3), marker=dict(size=10))
        st.plotly_chart(fig_trim_linha, width="stretch")
    
    with col2:
        fig_trim_pizza = px.pie(
            df_trimestral,
            labels='Trimestre',
            values='Valor',
            title="Distribuição de Vendas por Trimestre"
        )
        st.plotly_chart(fig_trim_pizza, width="stretch")
    
    # Tabela trimestral
    st.subheader("Tabela de Vendas Trimestrais")
    df_trimestral_display = df_trimestral.copy()
    df_trimestral_display['Valor'] = df_trimestral_display['Valor'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_trimestral_display, width="stretch")

# =============== TAB 3: ANÁLISE ANUAL ===============
with tab3:
    st.subheader("Análise Anual de Vendas")
    
    # Prepara dados anuais
    df_anual = df_filtered.groupby('Ano')['Valor_Venda'].agg(['sum', 'count']).reset_index()
    df_anual.columns = ['Ano', 'Valor', 'Quantidade']
    df_anual = df_anual.sort_values('Ano')
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_anual_barras = px.bar(
            df_anual,
            x='Ano',
            y='Valor',
            title="Vendas Anuais",
            labels={'Valor': 'Valor (R$)', 'Ano': 'Ano'},
            color='Valor',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_anual_barras, width="stretch")
    
    with col2:
        fig_anual_quantidade = px.bar(
            df_anual,
            x='Ano',
            y='Quantidade',
            title="Quantidade de Vendas Anuais",
            labels={'Quantidade': 'Quantidade', 'Ano': 'Ano'},
            color='Quantidade',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_anual_quantidade, width="stretch")
    
    # Tabela anual
    st.subheader("Tabela de Vendas Anuais")
    df_anual_display = df_anual.copy()
    df_anual_display['Valor'] = df_anual_display['Valor'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_anual_display, width="stretch")

# =============== TAB 4: ANÁLISE DETALHADA ===============
with tab4:
    st.subheader("Análise Detalhada de Vendas")
    
    # Vendas por Vendedora (se filtro não está em total)
    if vendedora_selecionada == "TOTAL EMPRESA":
        st.subheader("🏢 Vendas por Vendedora")
        
        df_vendedoras = df_filtered.groupby('vendedor.C007_Primeiro_Nome')['Valor_Venda'].agg(['sum', 'count']).reset_index()
        df_vendedoras.columns = ['Vendedora', 'Total_Vendas', 'Quantidade']
        df_vendedoras = df_vendedoras.sort_values('Total_Vendas', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_vendedoras_barras = px.bar(
                df_vendedoras,
                x='Vendedora',
                y='Total_Vendas',
                title="Vendas por Vendedora",
                labels={'Total_Vendas': 'Valor (R$)', 'Vendedora': 'Vendedora'},
                color='Total_Vendas',
                color_continuous_scale='RdYlGn'
            )
            fig_vendedoras_barras.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_vendedoras_barras, width="stretch")
        
        with col2:
            fig_vendedoras_pizza = px.pie(
                df_vendedoras,
                labels='Vendedora',
                values='Total_Vendas',
                title="Distribuição de Vendas por Vendedora"
            )
            st.plotly_chart(fig_vendedoras_pizza, width="stretch")
        
        # Tabela de vendedoras
        st.subheader("Tabela: Vendas por Vendedora")
        df_vendedoras_display = df_vendedoras.copy()
        df_vendedoras_display['Total_Vendas'] = df_vendedoras_display['Total_Vendas'].apply(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_vendedoras_display, width="stretch", hide_index=True)
    
    # Vendas por Cliente/Empresa
    st.subheader("🏭 Vendas por Empresa")
    
    df_empresas = df_filtered.groupby('Empresa')['Valor_Venda'].agg(['sum', 'count']).reset_index()
    df_empresas.columns = ['Empresa', 'Total_Vendas', 'Quantidade']
    df_empresas = df_empresas.sort_values('Total_Vendas', ascending=False).head(15)
    
    fig_empresas = px.bar(
        df_empresas,
        x='Total_Vendas',
        y='Empresa',
        title="Top 15 Empresas por Vendas",
        labels={'Total_Vendas': 'Valor (R$)', 'Empresa': 'Empresa'},
        color='Total_Vendas',
        color_continuous_scale='Blues'
    )
    fig_empresas.update_layout(height=600)
    st.plotly_chart(fig_empresas, width="stretch")
    
    # Tabela de empresas
    st.subheader("Tabela: Vendas por Empresa")
    df_empresas_completo = df_filtered.groupby('Empresa')['Valor_Venda'].agg(['sum', 'count']).reset_index()
    df_empresas_completo.columns = ['Empresa', 'Total_Vendas', 'Quantidade']
    df_empresas_completo = df_empresas_completo.sort_values('Total_Vendas', ascending=False)
    df_empresas_completo['Total_Vendas'] = df_empresas_completo['Total_Vendas'].apply(lambda x: f"R$ {x:,.2f}")
    
    st.dataframe(df_empresas_completo, width="stretch", hide_index=True)

# =============== RODAPÉ ===============
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.info(f"**Período Selecionado:** {date_range[0].strftime('%d/%m/%Y')} a {date_range[1].strftime('%d/%m/%Y')}")

with col2:
    st.info(f"**Vendedora Selecionada:** {vendedora_selecionada}")

with col3:
    st.info(f"**Atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
