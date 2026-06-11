import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os


# Função com cache para executar atualização a cada 1 hora
@st.cache_resource(ttl=3600)
def executar_atualizacao_dados(): 
    from getDataHardness import atualiza_dados_produtos_e_notas_fiscais
    atualiza_dados_produtos_e_notas_fiscais()

    from data_preparation import load_and_clean_data
    df = load_and_clean_data(
    )
    
    # Converte colunas de data
    df['T007_Data_Emissao'] = pd.to_datetime(df['T007_Data_Emissao'])
    df['Data_Envio_XML'] = pd.to_datetime(df['Data_Envio_XML'])
    df['vendedor.C007_Primeiro_Nome'] = df['vendedor.C007_Primeiro_Nome'].replace("ANDRE","ECOMMERCE").replace("ANDRÉ","ECOMMERCE")
    return df

FATURAMENTO_MINIMO_INATIVIDADE = 500
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

# Carrega dados
df = executar_atualizacao_dados()

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
    value=(min_date.date(), max_date.date()),
    min_value=min_date.date(),
    max_value=max_date.date()
)

# Validação do date_range - garante que sempre teremos 2 datas
if len(date_range) == 1:
    date_range = (date_range[0], date_range[0])
elif len(date_range) == 0:
    date_range = (min_date.date(), max_date.date())
elif len(date_range) > 2:
    date_range = (date_range[0], date_range[1])

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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["📅 Mensal", "📊 Trimestral", "📈 Anual", "🎯 Detalhado", "📦 Produtos", "🏢 Pareto Empresas", "⏱️ Inatividade"]
)

# =============== TAB 1: ANÁLISE MENSAL ===============
with tab1:
    st.subheader("Análise Mensal de Vendas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Vendas mensais (série temporal)
        df_mensal = df_filtered.groupby('Ano_Mes')['Valor_Venda'].agg(['sum', 'count']).reset_index()
        df_mensal.columns = ['Mês', 'Valor', 'Quantidade']
        df_mensal['Quantidade'] = df_mensal['Quantidade'].astype(int)
        df_mensal['Valor'] = df_mensal['Valor'].astype(float)
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
    df_trimestral['Quantidade'] = df_trimestral['Quantidade'].astype(int)
    df_trimestral['Valor'] = df_trimestral['Valor'].astype(float)
    # Sort por trimestre numericamentee (ex: 1T2024, 2T2024)
    df_trimestral = df_trimestral.sort_values('Trimestre', key=lambda x: x.str.extract(r'(\d+)')[0].astype(int))
    
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
    df_anual['Ano'] = df_anual['Ano'].astype(int)
    df_anual['Quantidade'] = df_anual['Quantidade'].astype(int)
    df_anual['Valor'] = df_anual['Valor'].astype(float)
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
        df_vendedoras['Quantidade'] = df_vendedoras['Quantidade'].astype(int)
        df_vendedoras['Total_Vendas'] = df_vendedoras['Total_Vendas'].astype(float)
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
    df_empresas['Quantidade'] = df_empresas['Quantidade'].astype(int)
    df_empresas['Total_Vendas'] = df_empresas['Total_Vendas'].astype(float)
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

# =============== TAB 5: ANÁLISE DE PRODUTOS ===============
with tab5:
    st.subheader("📦 Análise de Produtos")
    
    # Carrega dados de produtos para análise detalhada
    file_path = "data/produtos_combinados.csv"
    if os.path.exists(file_path):
        df_produtos = pd.read_csv(file_path, low_memory=False)
        
        # Filtra os produtos conforme seleção de período e vendedora
        df_produtos['T007_Data_Emissao'] = pd.to_datetime(df_produtos['T007_Data_Emissao'])
        
        if vendedora_selecionada != "TOTAL EMPRESA":
            df_produtos_filtered = df_produtos[df_produtos['vendedor.C007_Primeiro_Nome'] == vendedora_selecionada].copy()
        else:
            df_produtos_filtered = df_produtos.copy()
        
        # Filtra por data
        if len(date_range) == 2:
            df_produtos_filtered = df_produtos_filtered[
                (df_produtos_filtered['T007_Data_Emissao'].dt.date >= date_range[0]) &
                (df_produtos_filtered['T007_Data_Emissao'].dt.date <= date_range[1])
            ]
        
        # Calcula lucro por produto
        df_produtos_filtered['Lucro_Total'] = (
            (df_produtos_filtered['T008_Valor_Preco_Sem_Desconto_Unitario'].fillna(0) - 
             df_produtos_filtered['T008_Valor_Custo_Unitario'].fillna(0)) * 
            df_produtos_filtered['T008_Quantidade'].fillna(0)
        )
        
        # Agrupa produtos "botinas" (formato: código-número)
        df_produtos_filtered['Codigo_Base'] = df_produtos_filtered['T008_Codigo_Produto'].str.extract(r'(.*?)(?:-\d+)?$', expand=False)
        
        # Remove produtos com valor nulo
        df_produtos_filtered = df_produtos_filtered[df_produtos_filtered['T008_Valor_Total_Preco_Sem_Desconto'].notna()]
        df_produtos_filtered = df_produtos_filtered[df_produtos_filtered['T008_Valor_Total_Preco_Sem_Desconto'] > 0]
        
        col1, col2 = st.columns(2)
        
        # TOP PRODUTOS MAIS VENDIDOS
        with col1:
            st.markdown("### 🏆 Produtos Mais Vendidos (Por Código Base)")
            
            df_top_vendidos = df_produtos_filtered.groupby('Codigo_Base').agg({
                'T008_Quantidade': 'sum',
                'T008_Valor_Total_Preco_Sem_Desconto': 'sum',
                'T008_Descricao_Produto': 'first'
            }).reset_index()
            df_top_vendidos.columns = ['Código', 'Quantidade', 'Faturamento', 'Descrição']
            df_top_vendidos['Quantidade'] = df_top_vendidos['Quantidade'].astype(int)
            df_top_vendidos['Faturamento'] = df_top_vendidos['Faturamento'].astype(float)
            df_top_vendidos = df_top_vendidos.sort_values('Faturamento', ascending=False).head(15)
            
            fig_vendidos = px.bar(
                df_top_vendidos,
                x='Código',
                y='Faturamento',
                hover_name='Descrição',
                title="Top 15 Produtos por Faturamento",
                labels={'Faturamento': 'Faturamento (R$)', 'Código': 'Código Produto'},
                color='Faturamento',
                color_continuous_scale='Viridis'
            )
            fig_vendidos.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig_vendidos, width="stretch")
            
            # Tabela detalhada
            st.markdown("#### Tabela: Produtos Mais Vendidos")
            df_vendidos_display = df_top_vendidos.copy()
            df_vendidos_display['Faturamento'] = df_vendidos_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
            df_vendidos_display['Quantidade'] = df_vendidos_display['Quantidade'].astype(int)
            st.dataframe(df_vendidos_display, width="stretch", hide_index=True)
        
        # PRODUTOS COM MAIOR LUCRO
        with col2:
            st.markdown("### 💰 Produtos com Maior Lucro (Por Código Base)")
            
            df_top_lucro = df_produtos_filtered.groupby('Codigo_Base').agg({
                'Lucro_Total': 'sum',
                'T008_Valor_Total_Preco_Sem_Desconto': 'sum',
                'T008_Descricao_Produto': 'first',
                'T008_Quantidade': 'sum'
            }).reset_index()
            df_top_lucro.columns = ['Código', 'Lucro', 'Faturamento', 'Descrição', 'Quantidade']
            df_top_lucro['Quantidade'] = df_top_lucro['Quantidade'].astype(int)
            df_top_lucro['Lucro'] = df_top_lucro['Lucro'].astype(float)
            df_top_lucro['Faturamento'] = df_top_lucro['Faturamento'].astype(float)
            df_top_lucro = df_top_lucro.sort_values('Lucro', ascending=False).head(15)
            
            # Remove lucros negativos para visualização mais clara
            df_top_lucro_plot = df_top_lucro[df_top_lucro['Lucro'] > 0]
            
            fig_lucro = px.bar(
                df_top_lucro_plot,
                x='Código',
                y='Lucro',
                hover_name='Descrição',
                title="Top 15 Produtos por Lucro",
                labels={'Lucro': 'Lucro (R$)', 'Código': 'Código Produto'},
                color='Lucro',
                color_continuous_scale='RdYlGn'
            )
            fig_lucro.update_layout(height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig_lucro, width="stretch")
            
            # Tabela detalhada
            st.markdown("#### Tabela: Produtos com Maior Lucro")
            df_lucro_display = df_top_lucro.copy()
            df_lucro_display['Lucro'] = df_lucro_display['Lucro'].apply(lambda x: f"R$ {x:,.2f}")
            df_lucro_display['Faturamento'] = df_lucro_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
            df_lucro_display['Quantidade'] = df_lucro_display['Quantidade'].astype(int)
            st.dataframe(df_lucro_display, width="stretch", hide_index=True)
        
        # ANÁLISE ADICIONAL DE PRODUTOS
        st.markdown("---")
        st.markdown("### 📊 Análise Complementar de Produtos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Margem de lucro por produto
            st.markdown("#### Margem de Lucro (%)")
            df_margem = df_produtos_filtered.groupby('Codigo_Base').agg({
                'T008_Valor_Preco_Sem_Desconto_Unitario': 'mean',
                'T008_Valor_Custo_Unitario': 'mean',
                'T008_Descricao_Produto': 'first'
            }).reset_index()
            
            df_margem['Margem'] = ((df_margem['T008_Valor_Preco_Sem_Desconto_Unitario'] - df_margem['T008_Valor_Custo_Unitario']) / 
                                   df_margem['T008_Valor_Preco_Sem_Desconto_Unitario'] * 100)
            df_margem.columns = ['Código', 'Preço Médio', 'Custo Médio', 'Descrição', 'Margem %']
            df_margem['Margem %'] = df_margem['Margem %'].astype(float)
            df_margem = df_margem.sort_values('Margem %', ascending=False).head(15)
            
            fig_margem = px.bar(
                df_margem,
                x='Código',
                y='Margem %',
                title="Top 15 Produtos por Margem de Lucro",
                labels={'Margem %': 'Margem (%)', 'Código': 'Código Produto'},
                color='Margem %',
                color_continuous_scale='RdYlGn'
            )
            fig_margem.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_margem, width="stretch")
        
        with col2:
            # Quantidade de produtos vendidos
            st.markdown("#### Quantidade por Produto")
            df_qtd = df_produtos_filtered.groupby('Codigo_Base').agg({
                'T008_Quantidade': 'sum',
                'T008_Descricao_Produto': 'first'
            }).reset_index()
            df_qtd.columns = ['Código', 'Quantidade', 'Descrição']
            df_qtd['Quantidade'] = df_qtd['Quantidade'].astype(int)
            df_qtd = df_qtd.sort_values('Quantidade', ascending=False).head(15)
            
            fig_qtd = px.bar(
                df_qtd,
                x='Código',
                y='Quantidade',
                title="Top 15 Produtos por Quantidade Vendida",
                labels={'Quantidade': 'Quantidade', 'Código': 'Código Produto'},
                color='Quantidade',
                color_continuous_scale='Blues'
            )
            fig_qtd.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_qtd, width="stretch")
    else:
        st.warning("⚠️ Arquivo de produtos não encontrado!")

# =============== TAB 6: ANÁLISE PARETO DE EMPRESAS ===============
with tab6:
    st.subheader("🏢 Análise Pareto de Empresas (Curva ABC)")
    
    st.markdown("""
    **Classificação Pareto (80/20):**
    - **Classe A:** Empresas que concentram os primeiros 80% do faturamento
    - **Classe B:** Empresas que concentram os próximos 15% do faturamento
    - **Classe C:** Empresas que concentram os últimos 5% do faturamento
    """)
    
    # Calcula total de vendas por empresa
    df_pareto = df_filtered.groupby('Empresa')['Valor_Venda'].sum().reset_index()
    df_pareto.columns = ['Empresa', 'Valor_Venda']
    df_pareto['Valor_Venda'] = df_pareto['Valor_Venda'].astype(float)
    df_pareto = df_pareto.sort_values('Valor_Venda', ascending=False)
    df_pareto['Faturamento_Acumulado'] = df_pareto['Valor_Venda'].cumsum()
    df_pareto['Faturamento_Total'] = df_pareto['Valor_Venda'].sum()
    df_pareto['Percentual_Acumulado'] = (df_pareto['Faturamento_Acumulado'] / df_pareto['Faturamento_Total'] * 100).astype(float)
    
    # Classifica empresas em A, B, C
    def classificar_empresa(percentual):
        if percentual <= 80:
            return 'A'
        elif percentual <= 95:
            return 'B'
        else:
            return 'C'
    
    df_pareto['Classe'] = df_pareto['Percentual_Acumulado'].apply(classificar_empresa)
    df_pareto['Indice_Pareto'] = range(1, len(df_pareto) + 1)
    
    # Cores para cada classe
    cores_classe = {'A': '#e74c3c', 'B': '#f39c12', 'C': '#2ecc71'}
    df_pareto['Cor'] = df_pareto['Classe'].map(cores_classe)
    
    col1, col2 = st.columns(2)
    
    # GRÁFICO PARETO
    with col1:
        st.markdown("### 📈 Curva de Pareto")
        
        fig_pareto = go.Figure()
        
        # Mapa de cores para cada classe
        cores_barra = df_pareto['Classe'].map(cores_classe)
        
        # Adiciona barras para faturamento por empresa
        fig_pareto.add_trace(go.Bar(
            x=df_pareto['Indice_Pareto'],
            y=df_pareto['Valor_Venda'],
            name='Faturamento',
            marker=dict(
                color=cores_barra,
                line=dict(color='#34495e', width=1)
            ),
            yaxis='y1'
        ))
        
        # Adiciona linha de percentual acumulado
        fig_pareto.add_trace(go.Scatter(
            x=df_pareto['Indice_Pareto'],
            y=df_pareto['Percentual_Acumulado'],
            name='% Acumulado',
            mode='lines+markers',
            line=dict(color='#3498db', width=3),
            marker=dict(size=6),
            yaxis='y2'
        ))
        
        # Adiciona linha de referência 80%
        fig_pareto.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="80%", yref='y2')
        
        fig_pareto.update_layout(
            title='Curva de Pareto de Empresas',
            xaxis=dict(title='Índice da Empresa'),
            yaxis=dict(title=dict(text='Faturamento (R$)', font=dict(color='black'))),
            yaxis2=dict(title=dict(text='% Acumulado', font=dict(color='#3498db')), overlaying='y', side='right'),
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_pareto, width="stretch")
    
    # ESTATÍSTICAS DAS CLASSES
    with col2:
        st.markdown("### 📊 Resumo das Classes")
        
        # Calcula estatísticas por classe
        df_resumo = df_pareto.groupby('Classe').agg({
            'Empresa': 'count',
            'Valor_Venda': 'sum',
            'Percentual_Acumulado': 'max'
        }).reset_index()
        df_resumo.columns = ['Classe', 'Quantidade', 'Faturamento', 'Percentual']
        df_resumo['Quantidade'] = df_resumo['Quantidade'].astype(int)
        df_resumo['Faturamento'] = df_resumo['Faturamento'].astype(float)
        df_resumo['Percentual'] = df_resumo['Percentual'].astype(float)
        
        # Cria cards para cada classe
        for _, row in df_resumo.iterrows():
            classe = row['Classe']
            quantidade = int(row['Quantidade'])
            faturamento = row['Faturamento']
            percentual = row['Percentual']
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric(
                    f"Classe {classe}",
                    f"{quantidade} empresa{'s' if quantidade > 1 else ''}",
                    f"R$ {faturamento:,.0f}"
                )
            with col_b:
                st.metric(
                    f"Acumulado %",
                    f"{percentual:.1f}%"
                )
        
        # Gráfico de pizza
        st.markdown("### Distribuição do Faturamento por Classe")
        df_resumo_pizza = df_pareto.groupby('Classe').agg({
            'Valor_Venda': 'sum'
        }).reset_index()
        df_resumo_pizza['Valor_Venda'] = df_resumo_pizza['Valor_Venda'].astype(float)
        
        fig_pizza = px.pie(
            df_resumo_pizza,
            labels='Classe',
            values='Valor_Venda',
            title='% do Faturamento por Classe',
            color='Classe',
            color_discrete_map=cores_classe
        )
        st.plotly_chart(fig_pizza, width="stretch")
    
    # TABELA COMPLETA
    st.markdown("---")
    st.markdown("### 📋 Tabela Completa de Empresas")
    
    df_pareto_display = df_pareto[['Empresa', 'Classe', 'Valor_Venda', 'Percentual_Acumulado']].copy()
    df_pareto_display.columns = ['Empresa', 'Classe', 'Faturamento', 'Acumulado %']
    df_pareto_display['Faturamento'] = df_pareto_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
    df_pareto_display['Acumulado %'] = df_pareto_display['Acumulado %'].apply(lambda x: f"{x:.2f}%")
    
    # Filtra por classe se necessário
    classe_filtro = st.selectbox("Filtrar por Classe:", ['Todas', 'A', 'B', 'C'])
    if classe_filtro != 'Todas':
        df_pareto_display = df_pareto_display[df_pareto['Classe'] == classe_filtro]
    
    st.dataframe(df_pareto_display, width="stretch", hide_index=True)
    
    # Download dos dados
    st.markdown("---")
    st.markdown("### 📥 Exportar Dados")
    
    csv_pareto = df_pareto_display.to_csv(index=False)
    st.download_button(
        label="📥 Baixar Análise Pareto em CSV",
        data=csv_pareto,
        file_name=f"pareto_empresas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# =============== TAB 7: ANÁLISE DE INATIVIDADE DE CLIENTES ===============
with tab7:
    st.subheader("⏱️ Análise de Inatividade de Clientes")
    
    st.markdown("""
    Esta análise identifica clientes inativos baseado na data da última compra.
    **Classificação:**
    - 🟢 **Ativo**: Última compra nos últimos 30 dias
    - 🟡 **Moderado**: Última compra entre 31 e 90 dias
    - 🔴 **Inativo**: Última compra há mais de 90 dias
    """)
    
    # Calcula data atual e data máxima nos dados
    data_hoje = datetime.now().date()
    data_max_df = df_filtered['T007_Data_Emissao'].max().date()
    
    # Análise de inatividade por cliente
    df_inatividade = df_filtered.groupby('Empresa').agg({
        'T007_Data_Emissao': ['max', 'count', 'min'],
        'Valor_Venda': ['sum', 'mean']
    }).reset_index()
    
    df_inatividade.columns = ['Empresa', 'Ultima_Compra', 'Num_Compras', 'Primeira_Compra', 'Faturamento_Total', 'Ticket_Medio']
    
    # Garante tipos corretos antes de cálculos
    df_inatividade['Num_Compras'] = df_inatividade['Num_Compras'].astype(int)
    df_inatividade['Faturamento_Total'] = df_inatividade['Faturamento_Total'].astype(float)
    df_inatividade['Ticket_Medio'] = df_inatividade['Ticket_Medio'].astype(float)
    
    # Calcula dias desde última compra - garante como int
    df_inatividade['Dias_Inatividade'] = (data_max_df - df_inatividade['Ultima_Compra'].dt.date).apply(lambda x: x.days).astype(int)
    
    df_inatividade = df_inatividade[df_inatividade['Faturamento_Total'] >= FATURAMENTO_MINIMO_INATIVIDADE].copy()
    # Classifica inatividade
    def classificar_inatividade(dias):
        if dias <= 30:
            return '🟢 Ativo'
        elif dias <= 90:
            return '🟡 Moderado'
        else:
            return '🔴 Inativo'
    
    df_inatividade['Status_Atividade'] = df_inatividade['Dias_Inatividade'].apply(classificar_inatividade)
    
    # Ordena por dias de inatividade (crescente)
    df_inatividade = df_inatividade.sort_values('Dias_Inatividade', ascending=False)
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Métricas
    total_clientes = len(df_inatividade)
    ativos = len(df_inatividade[df_inatividade['Dias_Inatividade'] <= 30])
    moderados = len(df_inatividade[(df_inatividade['Dias_Inatividade'] > 30) & (df_inatividade['Dias_Inatividade'] <= 90)])
    inativos = len(df_inatividade[df_inatividade['Dias_Inatividade'] > 90])
    
    with col1:
        st.metric("Total de Clientes", total_clientes)
    with col2:
        st.metric("🟢 Ativos", ativos)
    with col3:
        st.metric("🟡 Moderados", moderados)
    with col4:
        st.metric("🔴 Inativos", inativos)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    # GRÁFICO 1: Distribuição de Inatividade
    with col1:
        st.markdown("### Distribuição de Clientes por Status")
        
        df_status_count = df_inatividade['Status_Atividade'].value_counts().reset_index()
        df_status_count.columns = ['Status', 'Quantidade']
        
        # Mapear cores
        cores_status = {
            '🟢 Ativo': '#2ecc71',
            '🟡 Moderado': '#f39c12',
            '🔴 Inativo': '#e74c3c'
        }
        
        fig_status = px.pie(
            df_status_count,
            labels='Status',
            values='Quantidade',
            title='Distribuição de Clientes',
            color='Status',
            color_discrete_map=cores_status
        )
        st.plotly_chart(fig_status, width="stretch")
    
    # GRÁFICO 2: Dias de Inatividade vs Faturamento
    with col2:
        st.markdown("### Relação: Inatividade vs Faturamento")
        
        fig_scatter = px.scatter(
            df_inatividade,
            x='Dias_Inatividade',
            y='Faturamento_Total',
            hover_name='Empresa',
            hover_data={'Dias_Inatividade': True, 'Faturamento_Total': ':.2f', 'Num_Compras': True},
            color='Status_Atividade',
            color_discrete_map=cores_status,
            title='Inatividade x Faturamento',
            labels={'Dias_Inatividade': 'Dias sem Compra', 'Faturamento_Total': 'Faturamento (R$)'}
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, width="stretch")
    
    st.markdown("---")
    
    # ANÁLISE DETALHADA
    st.markdown("### 📊 Análise Detalhada por Status de Atividade")
    
    # Tabs para cada status
    tab_ativo, tab_moderado, tab_inativo = st.tabs(["🟢 Clientes Ativos", "🟡 Clientes Moderados", "🔴 Clientes Inativos"])
    
    # TAB: ATIVOS
    with tab_ativo:
        df_ativos = df_inatividade[df_inatividade['Dias_Inatividade'] <= 30].sort_values('Dias_Inatividade')
        
        st.markdown(f"**Total: {len(df_ativos)} clientes**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Faturamento Total", f"R$ {df_ativos['Faturamento_Total'].sum():,.0f}")
        with col2:
            st.metric("Ticket Médio", f"R$ {df_ativos['Ticket_Medio'].mean():,.0f}")
        
        # Gráfico de ativos
        fig_ativos_dias = px.bar(
            df_ativos.head(15),
            x='Dias_Inatividade',
            y='Faturamento_Total',
            hover_name='Empresa',
            hover_data={'Num_Compras': True, 'Faturamento_Total': ':.2f'},
            title='Top 15 Clientes Ativos (por Dias sem Compra)',
            labels={'Dias_Inatividade': 'Dias desde Última Compra', 'Faturamento_Total': 'Faturamento (R$)'},
            color='Dias_Inatividade',
            color_continuous_scale='Greens'
        )
        st.plotly_chart(fig_ativos_dias, width="stretch")
        
        # Tabela de ativos
        st.markdown("#### Tabela de Clientes Ativos")
        df_ativos_display = df_ativos[['Empresa', 'Dias_Inatividade', 'Ultima_Compra', 'Num_Compras', 'Faturamento_Total', 'Ticket_Medio']].copy()
        df_ativos_display.columns = ['Empresa', 'Dias s/ Compra', 'Última Compra', 'Nº Compras', 'Faturamento (R$)', 'Ticket Médio (R$)']
        df_ativos_display['Última Compra'] = df_ativos_display['Última Compra'].astype(str)
        # df_ativos_display['Faturamento'] = df_ativos_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
        # df_ativos_display['Ticket Médio'] = df_ativos_display['Ticket Médio'].apply(lambda x: f"R$ {x:,.2f}")
        df_ativos_display['Nº Compras'] = df_ativos_display['Nº Compras'].astype(int)
        df_ativos_display = df_ativos_display[df_ativos_display["Faturamento (R$)"]>500]
        st.dataframe(df_ativos_display, width="stretch", hide_index=True)
    
    # TAB: MODERADOS
    with tab_moderado:
        df_moderados = df_inatividade[(df_inatividade['Dias_Inatividade'] > 30) & (df_inatividade['Dias_Inatividade'] <= 90)].sort_values('Dias_Inatividade')
        
        st.markdown(f"**Total: {len(df_moderados)} clientes**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Faturamento Total", f"R$ {df_moderados['Faturamento_Total'].sum():,.0f}")
        with col2:
            st.metric("Ticket Médio", f"R$ {df_moderados['Ticket_Medio'].mean():,.0f}")
        
        # Gráfico de moderados
        fig_moderados_dias = px.bar(
            df_moderados.head(15),
            x='Dias_Inatividade',
            y='Faturamento_Total',
            hover_name='Empresa',
            hover_data={'Num_Compras': True, 'Faturamento_Total': ':.2f'},
            title='Top 15 Clientes Moderados (por Dias sem Compra)',
            labels={'Dias_Inatividade': 'Dias desde Última Compra', 'Faturamento_Total': 'Faturamento (R$)'},
            color='Dias_Inatividade',
            color_continuous_scale='Oranges'
        )
        st.plotly_chart(fig_moderados_dias, width="stretch")
        
        # Tabela de moderados
        st.markdown("#### Tabela de Clientes Moderados")
        df_moderados_display = df_moderados[['Empresa', 'Dias_Inatividade', 'Ultima_Compra', 'Num_Compras', 'Faturamento_Total', 'Ticket_Medio']].copy()
        df_moderados_display.columns = ['Empresa', 'Dias s/ Compra', 'Última Compra', 'Nº Compras', 'Faturamento (R$)', 'Ticket Médio  (R$)']
        df_moderados_display['Última Compra'] = df_moderados_display['Última Compra'].astype(str)
        # df_moderados_display['Faturamento'] = df_moderados_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
        # df_moderados_display['Ticket Médio'] = df_moderados_display['Ticket Médio'].apply(lambda x: f"R$ {x:,.2f}")
        df_moderados_display['Nº Compras'] = df_moderados_display['Nº Compras'].astype(int)
        df_moderados_display = df_moderados_display[df_moderados_display["Faturamento (R$)"]>500]
        st.dataframe(df_moderados_display, width="stretch", hide_index=True)
    
    # TAB: INATIVOS
    with tab_inativo:
        df_inativos = df_inatividade[df_inatividade['Dias_Inatividade'] > 90].sort_values('Dias_Inatividade', ascending=False)
        
        st.markdown(f"**Total: {len(df_inativos)} clientes**")
        st.warning(f"⚠️ Atenção: {len(df_inativos)} clientes sem comprar há mais de 90 dias!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Faturamento Total", f"R$ {df_inativos['Faturamento_Total'].sum():,.0f}")
        with col2:
            st.metric("Ticket Médio", f"R$ {df_inativos['Ticket_Medio'].mean():,.0f}")
        
        # Gráfico de inativos
        fig_inativos_dias = px.bar(
            df_inativos.head(15),
            x='Dias_Inatividade',
            y='Faturamento_Total',
            hover_name='Empresa',
            hover_data={'Num_Compras': True, 'Faturamento_Total': ':.2f'},
            title='Top 15 Clientes Inativos (por Dias sem Compra)',
            labels={'Dias_Inatividade': 'Dias desde Última Compra', 'Faturamento_Total': 'Faturamento (R$)'},
            color='Dias_Inatividade',
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_inativos_dias, width="stretch")
        
        # Tabela de inativos
        st.markdown("#### Tabela de Clientes Inativos")
        df_inativos_display = df_inativos[['Empresa', 'Dias_Inatividade', 'Ultima_Compra', 'Num_Compras', 'Faturamento_Total', 'Ticket_Medio']].copy()
        df_inativos_display.columns = ['Empresa', 'Dias s/ Compra', 'Última Compra', 'Nº Compras', 'Faturamento (R$)', 'Ticket Médio  (R$)']
        df_inativos_display['Última Compra'] = df_inativos_display['Última Compra'].astype(str)
        # df_inativos_display['Faturamento'] = df_inativos_display['Faturamento'].apply(lambda x: f"R$ {x:,.2f}")
        # df_inativos_display['Ticket Médio'] = df_inativos_display['Ticket Médio'].apply(lambda x: f"R$ {x:,.2f}")
        df_inativos_display['Nº Compras'] = df_inativos_display['Nº Compras'].astype(int)
        df_inativos_display = df_inativos_display[df_inativos_display["Faturamento (R$)"]>500]
        st.dataframe(df_inativos_display, width="stretch", hide_index=True)
        
        # Download de clientes inativos
        st.markdown("---")
        st.markdown("### 📥 Exportar Dados de Inativos")
        csv_inativos = df_inativos_display.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Lista de Clientes Inativos em CSV",
            data=csv_inativos,
            file_name=f"clientes_inativos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.info(f"**Período Selecionado:** {date_range[0].strftime('%d/%m/%Y')} a {date_range[1].strftime('%d/%m/%Y')}")

with col2:
    st.info(f"**Vendedora Selecionada:** {vendedora_selecionada}")

with col3:
    st.info(f"**Atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
