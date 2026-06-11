import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import os


# Função com cache para executar atualização a cada 1 hora
@st.cache_resource(ttl=3600)
def executar_atualizacao_dados(): 
    from getDataHardness import atualiza_dados_produtos_e_notas_fiscais
    atualiza_dados_produtos_e_notas_fiscais()

    from data_preparation import load_and_clean_data, prepare_products_with_profit
    df_notas = load_and_clean_data()
    df_produtos = prepare_products_with_profit()
    
    # Converte colunas de data
    df_notas['T007_Data_Emissao'] = pd.to_datetime(df_notas['T007_Data_Emissao'])
    df_notas['Data_Envio_XML'] = pd.to_datetime(df_notas['Data_Envio_XML'])
    
    df_produtos['T007_Data_Emissao'] = pd.to_datetime(df_produtos['T007_Data_Emissao'])
    
    return df_notas, df_produtos


FATURAMENTO_MINIMO_INATIVIDADE = 500

# Configuração da página
st.set_page_config(
    page_title="Dashboard Gerencial de Vendas - AMM",
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
    .kpi-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

# Carrega dados
df_notas, df_produtos = executar_atualizacao_dados()

# Header
st.markdown('<div class="main-header">📊 Dashboard Gerencial de Vendas - AMM</div>', unsafe_allow_html=True)

# Sidebar - Filtros
st.sidebar.header("🔍 Filtros")

# Filtro de período
st.sidebar.subheader("Período de Análise")
min_date = df_notas['T007_Data_Emissao'].min()
max_date = df_notas['T007_Data_Emissao'].max()

date_range = st.sidebar.date_input(
    "Selecione o período:",
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date()
)

# Validação do date_range
if len(date_range) == 1:
    date_range = (date_range[0], date_range[0])
elif len(date_range) == 0:
    date_range = (min_date.date(), max_date.date())
elif len(date_range) > 2:
    date_range = (date_range[0], date_range[1])

# Filtra dados por data
df_notas_filtered = df_notas[
    (df_notas['T007_Data_Emissao'].dt.date >= date_range[0]) &
    (df_notas['T007_Data_Emissao'].dt.date <= date_range[1])
].copy()

df_produtos_filtered = df_produtos[
    (df_produtos['T007_Data_Emissao'].dt.date >= date_range[0]) &
    (df_produtos['T007_Data_Emissao'].dt.date <= date_range[1])
].copy()

# Métricas principais para sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Métricas Principais")

total_vendas = df_notas_filtered['Valor_Venda'].sum()
total_lucro = df_produtos_filtered['Lucro_Bruto_Total'].sum()
num_vendas = len(df_notas_filtered)
num_clientes = df_notas_filtered['Empresa'].nunique()

margem_percentual = (total_lucro / total_vendas * 100) if total_vendas > 0 else 0

col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("Vendas Totais", f"R$ {total_vendas:,.0f}")
with col2:
    st.metric("Lucro Bruto", f"R$ {total_lucro:,.0f}")

col3, col4 = st.sidebar.columns(2)
with col3:
    st.metric("Margem %", f"{margem_percentual:.1f}%")
with col4:
    st.metric("Nº Clientes", num_clientes)

# Tabs principais
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["💡 KPIs", "📅 Vendas", "💰 Lucro", "⏱️ Clientes Inativos", "🏢 ABC Clientes", "📦 ABC Produtos"]
)

# =============== TAB 1: KPIs ===============
with tab1:
    st.subheader("📊 Indicadores-Chave de Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Vendas Totais",
            f"R$ {total_vendas:,.0f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "📈 Lucro Bruto",
            f"R$ {total_lucro:,.0f}",
            delta=f"{margem_percentual:.1f}%"
        )
    
    with col3:
        avg_ticket = total_vendas / num_vendas if num_vendas > 0 else 0
        st.metric(
            "🎟️ Ticket Médio",
            f"R$ {avg_ticket:,.0f}",
            delta=None
        )
    
    with col4:
        st.metric(
            "👥 Clientes Únicos",
            num_clientes,
            delta=None
        )
    
    # Vendedoras únicas
    col5, col6, col7 = st.columns(3)
    
    with col5:
        num_vendedoras = df_notas_filtered['vendedor.C007_Primeiro_Nome'].nunique()
        st.metric("👩‍💼 Vendedoras", num_vendedoras)
    
    with col6:
        num_notas = len(df_notas_filtered)
        st.metric("📄 Notas Fiscais", num_notas)
    
    with col7:
        num_produtos = len(df_produtos_filtered)
        st.metric("📦 Itens Vendidos", num_produtos)
    
    # Divisão de vendas
    st.markdown("---")
    st.subheader("Divisão de Vendas por Período")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Vendas mensais
        df_mensal = df_notas_filtered.groupby('Ano_Mes')['Valor_Venda'].sum().reset_index()
        df_mensal.columns = ['Mês', 'Valor']
        df_mensal = df_mensal.sort_values('Mês')
        
        fig_mensal = px.bar(
            df_mensal,
            x='Mês',
            y='Valor',
            title="Vendas Mensais",
            labels={'Valor': 'Valor (R$)', 'Mês': 'Período'},
            color='Valor',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_mensal, width='stretch')
    
    with col2:
        # Vendas por vendedora (top 10)
        df_vendedoras = df_notas_filtered.groupby('vendedor.C007_Primeiro_Nome')['Valor_Venda'].sum().reset_index()
        df_vendedoras.columns = ['Vendedora', 'Valor']
        df_vendedoras = df_vendedoras.sort_values('Valor', ascending=True).tail(10)
        
        fig_vendedoras = px.bar(
            df_vendedoras,
            x='Valor',
            y='Vendedora',
            title="Top 10 Vendedoras",
            labels={'Valor': 'Valor (R$)'},
            color='Valor',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_vendedoras, width='stretch')


# =============== TAB 2: VENDAS ===============
with tab2:
    st.subheader("📊 Análise de Vendas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Vendas mensais (série temporal)
        df_mensal = df_notas_filtered.groupby('Ano_Mes').agg({
            'Valor_Venda': ['sum', 'count']
        }).reset_index()
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
        st.plotly_chart(fig_linha, width='stretch')
    
    with col2:
        # Quantidade de vendas
        fig_barras = px.bar(
            df_mensal,
            x='Mês',
            y='Quantidade',
            title="Quantidade de Vendas (Mensal)",
            labels={'Quantidade': 'Nº de Vendas', 'Mês': 'Período'},
            color='Quantidade',
            color_continuous_scale='Purples'
        )
        st.plotly_chart(fig_barras, width='stretch')
    
    # Tabela mensal
    st.subheader("Detalhe Mensal")
    df_mensal_display = df_mensal.copy()
    df_mensal_display['Valor'] = df_mensal_display['Valor'].apply(lambda x: f"R$ {x:,.2f}")
    st.dataframe(df_mensal_display, width='stretch', hide_index=True)


# =============== TAB 3: LUCRO BRUTO ===============
with tab3:
    st.subheader("💰 Análise de Lucro Bruto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Lucro bruto mensal
        df_lucro_mensal = df_produtos_filtered.groupby('Ano_Mes').agg({
            'Lucro_Bruto_Total': 'sum',
            'Margem_Bruta_Percentual': 'mean'
        }).reset_index()
        df_lucro_mensal.columns = ['Mês', 'Lucro_Bruto', 'Margem_Media']
        df_lucro_mensal = df_lucro_mensal.sort_values('Mês')
        
        fig_lucro = px.line(
            df_lucro_mensal,
            x='Mês',
            y='Lucro_Bruto',
            markers=True,
            title="Lucro Bruto Mensal",
            labels={'Lucro_Bruto': 'Lucro (R$)', 'Mês': 'Período'},
            color_discrete_sequence=['#2ca02c']
        )
        fig_lucro.update_traces(line=dict(width=3), marker=dict(size=8))
        st.plotly_chart(fig_lucro, width='stretch')
    
    with col2:
        # Margem bruta média mensal
        fig_margem = px.bar(
            df_lucro_mensal,
            x='Mês',
            y='Margem_Media',
            title="Margem Bruta Média Mensal (%)",
            labels={'Margem_Media': 'Margem (%)', 'Mês': 'Período'},
            color='Margem_Media',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_margem, width='stretch')
    
    # Lucro por vendedora
    st.subheader("Lucro por Vendedora")
    
    df_lucro_vendedora = df_produtos_filtered.groupby('vendedor.C007_Primeiro_Nome').agg({
        'Lucro_Bruto_Total': 'sum'
    }).reset_index()
    df_lucro_vendedora.columns = ['Vendedora', 'Lucro']
    df_lucro_vendedora = df_lucro_vendedora.sort_values('Lucro', ascending=True).tail(15)
    
    fig_vendedora = px.bar(
        df_lucro_vendedora,
        x='Lucro',
        y='Vendedora',
        title="Lucro Bruto por Vendedora (Top 15)",
        labels={'Lucro': 'Lucro (R$)'},
        color='Lucro',
        color_continuous_scale='Greens'
    )
    st.plotly_chart(fig_vendedora, width='stretch')


# =============== TAB 4: CLIENTES INATIVOS ===============
with tab4:
    st.subheader("⏱️ Clientes Inativos")
    
    # Calcula última venda por cliente
    df_clientes_ultima_venda = df_notas_filtered.groupby('Empresa').agg({
        'T007_Data_Emissao': 'max',
        'Valor_Venda': ['sum', 'count']
    }).reset_index()
    df_clientes_ultima_venda.columns = ['Empresa', 'Ultima_Venda', 'Faturamento_Total', 'Num_Vendas']
    
    # Filtra clientes com faturamento mínimo
    df_clientes_ultima_venda = df_clientes_ultima_venda[
        df_clientes_ultima_venda['Faturamento_Total'] >= FATURAMENTO_MINIMO_INATIVIDADE
    ]
    
    # Calcula dias de inatividade
    data_referencia = df_notas['T007_Data_Emissao'].max()
    df_clientes_ultima_venda['Dias_Inatividade'] = (
        data_referencia - df_clientes_ultima_venda['Ultima_Venda']
    ).dt.days
    
    # Ordena por inatividade
    df_clientes_ultima_venda = df_clientes_ultima_venda.sort_values('Dias_Inatividade', ascending=False)
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    inativos_90 = len(df_clientes_ultima_venda[df_clientes_ultima_venda['Dias_Inatividade'] >= 90])
    inativos_180 = len(df_clientes_ultima_venda[df_clientes_ultima_venda['Dias_Inatividade'] >= 180])
    inativos_360 = len(df_clientes_ultima_venda[df_clientes_ultima_venda['Dias_Inatividade'] >= 360])
    
    with col1:
        st.metric("Inativo > 90 dias", inativos_90)
    with col2:
        st.metric("Inativo > 180 dias", inativos_180)
    with col3:
        st.metric("Inativo > 1 ano", inativos_360)
    
    # Gráfico de distribuição
    st.subheader("Distribuição de Inatividade")
    
    fig_inatividade = px.histogram(
        df_clientes_ultima_venda,
        x='Dias_Inatividade',
        nbins=20,
        title="Distribuição de Clientes por Dias Inativos",
        labels={'Dias_Inatividade': 'Dias de Inatividade', 'count': 'Quantidade de Clientes'},
        color_discrete_sequence=['#ff7f0e']
    )
    st.plotly_chart(fig_inatividade, width='stretch')
    
    # Tabela de clientes inativos (top 50)
    st.subheader("Top 50 Clientes Mais Inativos")
    df_inativos_display = df_clientes_ultima_venda.head(50).copy()
    df_inativos_display['Ultima_Venda'] = df_inativos_display['Ultima_Venda'].dt.strftime('%d/%m/%Y')
    df_inativos_display['Faturamento_Total'] = df_inativos_display['Faturamento_Total'].apply(lambda x: f"R$ {x:,.2f}")
    
    st.dataframe(
        df_inativos_display[['Empresa', 'Ultima_Venda', 'Dias_Inatividade', 'Faturamento_Total', 'Num_Vendas']],
        width='stretch',
        hide_index=True
    )


# =============== TAB 5: CURVA ABC CLIENTES ===============
with tab5:
    st.subheader("🏢 Curva ABC de Clientes")
    
    # Agrupa faturamento por cliente
    df_abc_clientes = df_notas_filtered.groupby('Empresa').agg({
        'Valor_Venda': 'sum',
        'T007_Numero_Nota_Fiscal': 'count'
    }).reset_index()
    df_abc_clientes.columns = ['Empresa', 'Faturamento', 'Num_Vendas']
    
    # Ordena descendente
    df_abc_clientes = df_abc_clientes.sort_values('Faturamento', ascending=False)
    
    # Calcula percentual acumulado
    faturamento_total = df_abc_clientes['Faturamento'].sum()
    df_abc_clientes['Percentual_Individual'] = (df_abc_clientes['Faturamento'] / faturamento_total * 100)
    df_abc_clientes['Percentual_Acumulado'] = df_abc_clientes['Percentual_Individual'].cumsum()
    
    # Classifica A, B, C
    def classificar_abc(percentual):
        if percentual <= 80:
            return 'A'
        elif percentual <= 95:
            return 'B'
        else:
            return 'C'
    
    df_abc_clientes['Classe'] = df_abc_clientes['Percentual_Acumulado'].apply(classificar_abc)
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    clientes_a = len(df_abc_clientes[df_abc_clientes['Classe'] == 'A'])
    clientes_b = len(df_abc_clientes[df_abc_clientes['Classe'] == 'B'])
    clientes_c = len(df_abc_clientes[df_abc_clientes['Classe'] == 'C'])
    
    with col1:
        st.metric("Clientes Classe A", clientes_a)
    with col2:
        st.metric("Clientes Classe B", clientes_b)
    with col3:
        st.metric("Clientes Classe C", clientes_c)
    
    # Gráfico Pareto
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras com percentual acumulado
        df_abc_top = df_abc_clientes.head(30).copy()
        
        # Map classes to colors
        color_map = {'A': '#2ca02c', 'B': '#ff7f0e', 'C': '#d62728'}
        df_abc_top['Color'] = df_abc_top['Classe'].map(color_map)
        
        fig_abc = go.Figure()
        fig_abc.add_trace(go.Bar(
            x=df_abc_top['Empresa'],
            y=df_abc_top['Faturamento'],
            name='Faturamento',
            marker=dict(color=df_abc_top['Color'])
        ))
        fig_abc.add_trace(go.Scatter(
            x=df_abc_top['Empresa'],
            y=df_abc_top['Percentual_Acumulado'],
            name='% Acumulado',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='blue', width=2)
        ))
        
        fig_abc.update_layout(
            title="Curva ABC de Clientes (Top 30)",
            xaxis_title="Cliente",
            yaxis_title="Faturamento (R$)",
            yaxis2=dict(
                title="% Acumulado",
                overlaying="y",
                side="right"
            ),
            hovermode='x unified'
        )
        st.plotly_chart(fig_abc, width='stretch')
    
    with col2:
        # Distribuição A, B, C
        df_abc_dist = df_abc_clientes['Classe'].value_counts().reset_index()
        df_abc_dist.columns = ['Classe', 'Quantidade']
        df_abc_dist = df_abc_dist.sort_values('Classe')
        
        fig_pie = px.pie(
            df_abc_dist,
            labels='Classe',
            values='Quantidade',
            title="Distribuição de Clientes por Classe",
            color='Classe',
            color_discrete_map={'A': 'green', 'B': 'yellow', 'C': 'red'}
        )
        st.plotly_chart(fig_pie, width='stretch')
    
    # Tabela ABC detalhada
    st.subheader("Detalhamento da Curva ABC")
    df_abc_display = df_abc_clientes.head(50).copy()
    df_abc_display['Faturamento'] = df_abc_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
    df_abc_display['Percentual_Individual'] = df_abc_display['Percentual_Individual'].apply(lambda x: f"{x:.2f}%")
    df_abc_display['Percentual_Acumulado'] = df_abc_display['Percentual_Acumulado'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(
        df_abc_display[['Empresa', 'Faturamento', 'Percentual_Individual', 'Percentual_Acumulado', 'Classe', 'Num_Vendas']],
        width='stretch',
        hide_index=True
    )


# =============== TAB 6: CURVA ABC PRODUTOS ===============
with tab6:
    st.subheader("📦 Curva ABC de Produtos")
    
    # Agrupa volume/faturamento por produto
    df_abc_produtos = df_produtos_filtered.groupby('T008_Descricao_Produto').agg({
        'T008_Valor_Preco_Sem_Desconto_Unitario': 'sum',  # Volume em R$
        'T008_Quantidade': 'sum',  # Quantidade
        'T008_Id': 'count'  # Número de linhas
    }).reset_index()
    df_abc_produtos.columns = ['Produto', 'Faturamento', 'Quantidade', 'Num_Linhas']
    
    # Ordena descendente
    df_abc_produtos = df_abc_produtos.sort_values('Faturamento', ascending=False)
    
    # Calcula percentual acumulado
    faturamento_total_prod = df_abc_produtos['Faturamento'].sum()
    df_abc_produtos['Percentual_Individual'] = (df_abc_produtos['Faturamento'] / faturamento_total_prod * 100)
    df_abc_produtos['Percentual_Acumulado'] = df_abc_produtos['Percentual_Individual'].cumsum()
    
    # Classifica A, B, C
    df_abc_produtos['Classe'] = df_abc_produtos['Percentual_Acumulado'].apply(classificar_abc)
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    produtos_a = len(df_abc_produtos[df_abc_produtos['Classe'] == 'A'])
    produtos_b = len(df_abc_produtos[df_abc_produtos['Classe'] == 'B'])
    produtos_c = len(df_abc_produtos[df_abc_produtos['Classe'] == 'C'])
    
    with col1:
        st.metric("Produtos Classe A", produtos_a)
    with col2:
        st.metric("Produtos Classe B", produtos_b)
    with col3:
        st.metric("Produtos Classe C", produtos_c)
    
    # Gráfico Pareto
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras com percentual acumulado (top 30)
        df_abc_prod_top = df_abc_produtos.head(30).copy()
        
        # Map classes to colors
        color_map = {'A': '#2ca02c', 'B': '#ff7f0e', 'C': '#d62728'}
        df_abc_prod_top['Color'] = df_abc_prod_top['Classe'].map(color_map)
        
        fig_abc_prod = go.Figure()
        fig_abc_prod.add_trace(go.Bar(
            x=df_abc_prod_top['Produto'],
            y=df_abc_prod_top['Faturamento'],
            name='Faturamento',
            marker=dict(color=df_abc_prod_top['Color'])
        ))
        fig_abc_prod.add_trace(go.Scatter(
            x=df_abc_prod_top['Produto'],
            y=df_abc_prod_top['Percentual_Acumulado'],
            name='% Acumulado',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='blue', width=2)
        ))
        
        fig_abc_prod.update_layout(
            title="Curva ABC de Produtos (Top 30)",
            xaxis_title="Produto",
            yaxis_title="Faturamento (R$)",
            yaxis2=dict(
                title="% Acumulado",
                overlaying="y",
                side="right"
            ),
            hovermode='x unified'
        )
        st.plotly_chart(fig_abc_prod, width='stretch')
    
    with col2:
        # Distribuição A, B, C
        df_abc_prod_dist = df_abc_produtos['Classe'].value_counts().reset_index()
        df_abc_prod_dist.columns = ['Classe', 'Quantidade']
        df_abc_prod_dist = df_abc_prod_dist.sort_values('Classe')
        
        fig_pie_prod = px.pie(
            df_abc_prod_dist,
            labels='Classe',
            values='Quantidade',
            title="Distribuição de Produtos por Classe",
            color='Classe',
            color_discrete_map={'A': 'green', 'B': 'yellow', 'C': 'red'}
        )
        st.plotly_chart(fig_pie_prod, width='stretch')
    
    # Tabela ABC detalhada
    st.subheader("Detalhamento da Curva ABC")
    df_abc_prod_display = df_abc_produtos.head(50).copy()
    df_abc_prod_display['Faturamento'] = df_abc_prod_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
    df_abc_prod_display['Percentual_Individual'] = df_abc_prod_display['Percentual_Individual'].apply(lambda x: f"{x:.2f}%")
    df_abc_prod_display['Percentual_Acumulado'] = df_abc_prod_display['Percentual_Acumulado'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(
        df_abc_prod_display[['Produto', 'Faturamento', 'Percentual_Individual', 'Percentual_Acumulado', 'Classe', 'Quantidade']],
        width='stretch',
        hide_index=True
    )

st.markdown("---")
st.markdown("📊 Dashboard Gerencial - Última atualização: {} | Período: {} a {}".format(
    datetime.now().strftime("%d/%m/%Y %H:%M"),
    date_range[0].strftime("%d/%m/%Y"),
    date_range[1].strftime("%d/%m/%Y")
))
