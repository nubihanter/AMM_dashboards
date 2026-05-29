import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import os
import warnings
from getDataChatech import atualiza_dados_estoque

warnings.filterwarnings('ignore')

# Função com cache para executar atualização apenas uma vez por sessão
@st.cache_resource(ttl=3600)
def executar_atualizacao_estoque():
    atualiza_dados_estoque()

# ========================= CONFIGURAÇÃO STREAMLIT =========================
st.set_page_config(
    page_title="Dashboard de Estoque Crítico AMM - EPIS + Soluções",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================= CSS CUSTOMIZADO =========================
st.markdown("""
    <style>
    .main-header {
        font-size: 3em;
        font-weight: bold;
        color: #e74c3c;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .status-deficit {
        color: #e74c3c;
        font-weight: bold;
    }
    .status-parado {
        color: #2ecc71;
        font-weight: bold;
    }
    .status-warning {
        color: #f39c12;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ========================= FUNÇÕES DE CARREGAMENTO DE DADOS =========================

@st.cache_data
def load_stock_data():
    """
    Carrega dados de vendas (produtos_combinados.csv) e estoque (estoque_combinado.csv).
    Faz merge por ID do produto e retorna um DataFrame consolidado.
    """
    try:
        # Carrega dados de vendas
        df_vendas = pd.read_csv("data/produtos_combinados.csv", low_memory=False)
        df_vendas['T007_Data_Emissao'] = pd.to_datetime(df_vendas['T007_Data_Emissao'])
        
        # Carrega dados de estoque
        df_estoque = pd.read_csv("data/estoque_combinado.csv", low_memory=False)
        
        # Renomeia coluna de código de produto no estoque para facilitar merge
        df_estoque_renamed = df_estoque.rename(columns={
            'D001_Codigo_Produto': 'T008_Codigo_Produto',
            'D001_Descricao_Produto': 'D001_Descricao_Estoque',
            'D009A_Qtd_Liquida_Fora	+ D009_Quantidade_Estoque_Liquido': 'Estoque_Quantidade'
        })
        
        # Merge: left join na tabela de vendas (para manter histórico completo)
        df_merged = df_vendas.merge(
            df_estoque_renamed[['T008_Codigo_Produto', 'Estoque_Quantidade', 'D001_Descricao_Estoque', 'D082_Marca']],
            on='T008_Codigo_Produto',
            how='left'
        )
        
        # Preenche estoque faltante com 0
        df_merged['Estoque_Quantidade'] = df_merged['Estoque_Quantidade'].fillna(0).astype(float)
        
        # Remove linhas com vendas zeradas ou inválidas
        df_merged = df_merged[df_merged['T008_Quantidade'] > 0].copy()
        
        return df_merged
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return pd.DataFrame()


def extrair_numeracao(codigo_produto):
    """
    Extrai a numeração de um código de produto (formato: codigo-numeracao).
    Retorna tupla (codigo_base, numeracao).
    Ex: "1718-13" -> ("1718", "13")
    """
    if pd.isna(codigo_produto) or codigo_produto == "":
        return (codigo_produto, "")
    
    codigo_str = str(codigo_produto)
    if '-' in codigo_str:
        partes = codigo_str.split('-', 1)
        return (partes[0], partes[1])
    else:
        return (codigo_str, "")


def classificar_status_estoque(estoque, projecao):
    """
    Classifica o status de estoque comparando com a projeção.
    """
    if estoque < projecao * 0.8:
        return "🔴 DEFICIT", "#e74c3c"
    elif estoque < projecao:
        return "🟡 CRÍTICO", "#f39c12"
    else:
        return "🟢 PARADO", "#2ecc71"


# ========================= CARREGAMENTO DE DADOS =========================
executar_atualizacao_estoque()
df_stock_data = load_stock_data()

if df_stock_data.empty:
    st.error("❌ Não foi possível carregar os dados. Verifique se os arquivos CSV estão no diretório 'data/'")
    st.stop()

# ========================= HEADER =========================
st.markdown('<div class="main-header">📦 Dashboard de Estoque Crítico - AMM (EPIS + Soluções)</div>', unsafe_allow_html=True)

# ========================= SIDEBAR - FILTROS =========================
st.sidebar.header("🔍 Filtros Estoque Crítico")

# Filtro de período
st.sidebar.subheader("Período de Análise")
min_date = df_stock_data['T007_Data_Emissao'].min()
max_date = df_stock_data['T007_Data_Emissao'].max()

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

# Filtro de produtos
st.sidebar.subheader("Filtro de Produtos")
# Cria um mapa de código -> descrição para exibição
produto_map = df_stock_data.drop_duplicates('T008_Codigo_Produto')[['T008_Codigo_Produto', 'T008_Descricao_Produto']].copy()
produto_map.columns = ['Codigo', 'Descricao']
produto_dict = dict(zip(produto_map['Descricao'] + ' (' + produto_map['Codigo'] + ')', produto_map['Codigo']))

produtos_display_list = sorted(produto_dict.keys())
produtos_display_list.insert(0, "TODOS OS PRODUTOS")

produto_display_selecionado = st.sidebar.selectbox(
    "Selecione o produto:",
    produtos_display_list,
    index=0
)

# Extrai o código do produto selecionado
if produto_display_selecionado == "TODOS OS PRODUTOS":
    produto_selecionado = "TODOS OS PRODUTOS"
else:
    produto_selecionado = produto_dict[produto_display_selecionado]

# Threshold ajustável de cobertura
st.sidebar.subheader("⚙️ Configuração")
threshold_meses = st.sidebar.slider(
    "Meses de cobertura esperada:",
    min_value=1,
    max_value=6,
    value=2,
    help="Quantos meses de estoque você espera manter para cada produto?"
)

# Toggle: Apenas botinas
filtrar_apenas_botinas = st.sidebar.checkbox(
    "Filtrar apenas botinas (com numeração)",
    value=False
)

# ========================= FILTRAGEM DE DADOS =========================
df_filtered = df_stock_data.copy()

# Filtra por data
if len(date_range) == 2:
    df_filtered = df_filtered[
        (df_filtered['T007_Data_Emissao'].dt.date >= date_range[0]) &
        (df_filtered['T007_Data_Emissao'].dt.date <= date_range[1])
    ]

# Filtra por produto
if produto_selecionado != "TODOS OS PRODUTOS":
    df_filtered = df_filtered[df_filtered['T008_Codigo_Produto'] == produto_selecionado]

# Filtra apenas botinas (com numeração "-")
if filtrar_apenas_botinas:
    df_filtered = df_filtered[df_filtered['T008_Codigo_Produto'].str.contains('-', na=False)]

# ========================= ANÁLISE DE DADOS PARA MÉTRICAS =========================
# Calcula estatísticas para sidebar
data_hoje = datetime.now().date()
tres_meses_atras = data_hoje - timedelta(days=90)

df_tres_meses = df_filtered[df_filtered['T007_Data_Emissao'].dt.date >= tres_meses_atras].copy()

# Agrupa por produto para análise
df_produtos_stats = df_tres_meses.groupby('T008_Codigo_Produto').agg({
    'T008_Quantidade': 'sum',
    'Estoque_Quantidade': 'first',
    'T008_Descricao_Produto': 'first'
}).reset_index()

df_produtos_stats.columns = ['Codigo_Produto', 'Qtd_Vendida_3M', 'Estoque_Atual', 'Descricao']

# Calcula projeção e status para cada produto
df_produtos_stats['Vendas_Media_Mes'] = df_produtos_stats['Qtd_Vendida_3M'] / 3
df_produtos_stats['Projecao_Com_Threshold'] = df_produtos_stats['Vendas_Media_Mes'] * threshold_meses
df_produtos_stats['Diferenca'] = df_produtos_stats['Estoque_Atual'] - df_produtos_stats['Projecao_Com_Threshold']

# Classifica status
def classificar_status_simples(row):
    if row['Estoque_Atual'] < row['Projecao_Com_Threshold'] * 0.8:
        return "DEFICIT"
    elif row['Estoque_Atual'] < row['Projecao_Com_Threshold']:
        return "CRÍTICO"
    else:
        return "PARADO"

df_produtos_stats['Status'] = df_produtos_stats.apply(classificar_status_simples, axis=1)

# Calcula métricas
total_produtos = len(df_produtos_stats)
produtos_deficit = len(df_produtos_stats[df_produtos_stats['Status'] == "DEFICIT"])
produtos_critico = len(df_produtos_stats[df_produtos_stats['Status'] == "CRÍTICO"])
produtos_parado = len(df_produtos_stats[df_produtos_stats['Status'] == "PARADO"])

# ========================= SIDEBAR - MÉTRICAS =========================
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Métricas Principais")

col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("Total Produtos", total_produtos)
with col2:
    st.metric("🔴 Deficit", produtos_deficit)

col3, col4 = st.sidebar.columns(2)
with col3:
    st.metric("🟡 Crítico", produtos_critico)
with col4:
    st.metric("🟢 Parado", produtos_parado)

# Percentual de estoque crítico
pct_critico = (produtos_deficit + produtos_critico) / total_produtos * 100 if total_produtos > 0 else 0
st.sidebar.metric("% Crítico", f"{pct_critico:.1f}%")

# ========================= TABS PRINCIPAIS =========================
tab1, tab2, tab3, tab4 = st.tabs(["📊 Análise Crítica", "👟 Análise de Grades", "📋 Detalhes", "🚨 Alertas & Sugestões"])

# ========================= TAB 1: ANÁLISE DE ESTOQUE CRÍTICO =========================
with tab1:
    st.subheader("📊 Análise de Estoque Crítico - Últimos 3 Meses")
    
    st.markdown(f"""
    **Configuração Atual:**
    - Período de análise: Últimos 3 meses (90 dias)
    - Threshold de cobertura: {threshold_meses} mês(es)
    - Total de produtos analisados: {total_produtos}
    """)
    
    # Ordena por diferença (os mais críticos aparecem primeiro)
    df_produtos_stats_sorted = df_produtos_stats.sort_values('Diferenca')
    
    # Cria visualizações lado a lado
    col1, col2 = st.columns(2)
    
    # GRÁFICO 1: Distribuição por Status
    with col1:
        st.markdown("### 📈 Distribuição de Produtos por Status")
        
        status_counts = df_produtos_stats['Status'].value_counts().reset_index()
        status_counts.columns = ['Status', 'Quantidade']
        
        # Mapeia cores
        cores_status_map = {'DEFICIT': '#e74c3c', 'CRÍTICO': '#f39c12', 'PARADO': '#2ecc71'}
        cores_lista = [cores_status_map.get(s, '#95a5a6') for s in status_counts['Status']]
        
        fig_status = px.pie(
            status_counts,
            labels='Status',
            values='Quantidade',
            title='Distribuição de Produtos por Status',
            color_discrete_sequence=cores_lista
        )
        st.plotly_chart(fig_status, width='stretch')
    
    # GRÁFICO 2: Top 10 Produtos em Deficit
    with col2:
        st.markdown("### 🔴 Top 10 Produtos em Deficit")
        
        df_deficit = df_produtos_stats_sorted[df_produtos_stats_sorted['Status'] == 'DEFICIT'].head(10)
        
        if len(df_deficit) > 0:
            fig_deficit = px.bar(
                df_deficit,
                x='Diferenca',
                y='Codigo_Produto',
                orientation='h',
                title='Maior Deficit (unidades faltando)',
                labels={'Diferenca': 'Deficit (unidades)', 'Codigo_Produto': 'Código'},
                color='Diferenca',
                color_continuous_scale='Reds'
            )
            fig_deficit.update_layout(height=400)
            st.plotly_chart(fig_deficit, width='stretch')
        else:
            st.info("✅ Nenhum produto em deficit!")
    
    # TABELA PRINCIPAL
    st.markdown("---")
    st.markdown("### 📋 Tabela Completa de Análise")
    
    # Prepara tabela para exibição
    df_table_display = df_produtos_stats_sorted[[
        'Codigo_Produto', 'Descricao', 'Qtd_Vendida_3M', 'Vendas_Media_Mes', 
        'Projecao_Com_Threshold', 'Estoque_Atual', 'Diferenca', 'Status'
    ]].copy()
    
    df_table_display.columns = [
        'Código', 'Descrição', 'Vendidas 3M', 'Média/Mês', 
        f'Projeção ({threshold_meses}M)', 'Estoque', 'Diferença', 'Status'
    ]
    
    df_table_display['Vendidas 3M'] = df_table_display['Vendidas 3M'].astype(int)
    df_table_display['Média/Mês'] = df_table_display['Média/Mês']
    df_table_display[f'Projeção ({threshold_meses}M)'] = df_table_display[f'Projeção ({threshold_meses}M)']
    df_table_display['Estoque'] = df_table_display['Estoque'].astype(int)
    df_table_display['Diferença'] = df_table_display['Diferença']
    
    st.dataframe(df_table_display, width='stretch', hide_index=True)
    
    # Resumo estatístico
    st.markdown("---")
    st.markdown("### 📊 Resumo Estatístico")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_estoque = df_produtos_stats['Estoque_Atual'].sum()
        st.metric("Total em Estoque", f"{int(total_estoque)} un.")
    
    with col2:
        total_projecao = df_produtos_stats['Projecao_Com_Threshold'].sum()
        st.metric("Total Esperado (Projeção)", f"{int(total_projecao)} un.")
    
    with col3:
        total_deficit = df_produtos_stats[df_produtos_stats['Diferenca'] < 0]['Diferenca'].sum()
        st.metric("Total em Deficit", f"{int(total_deficit)} un.", delta=None)
    
    with col4:
        total_parado = df_produtos_stats[df_produtos_stats['Diferenca'] > 0]['Diferenca'].sum()
        st.metric("Total Parado", f"{int(total_parado)} un.", delta=None)


# ========================= TAB 2: ANÁLISE DE GRADES =========================
with tab2:
    st.subheader("👟 Análise de Grades de Numeração")
    
    # Extrai informações de grade para botinas
    df_grade_info = df_filtered.copy()
    df_grade_info[['Codigo_Base', 'Numeracao']] = df_grade_info['T008_Codigo_Produto'].apply(
        lambda x: pd.Series(extrair_numeracao(x))
    )
    
    # Filtra apenas botinas (que têm numeração)
    df_botinas = df_grade_info[df_grade_info['Numeracao'] != ''].copy()
    
    if len(df_botinas) == 0:
        st.warning("⚠️ Nenhuma botina encontrada no período selecionado.")
    else:
        # Cria duas seções
        sub_tab1, sub_tab2 = st.tabs(["Por Modelo", "Análise Geral"])
        
        # =============== SEÇÃO A: POR MODELO ===============
        with sub_tab1:
            st.markdown("### Por Modelo de Botina")
            
            # Cria um mapa de codigo_base -> descrição para exibição
            modelo_map = df_botinas.drop_duplicates('Codigo_Base')[['Codigo_Base', 'T008_Descricao_Produto']].copy()
            modelo_map['Descricao_Modelo'] = modelo_map['T008_Descricao_Produto'].str.extract(r'^([A-Z\s]+)')[0]
            modelo_dict = dict(zip(modelo_map['Descricao_Modelo'] + ' (' + modelo_map['Codigo_Base'] + ')', modelo_map['Codigo_Base']))
            
            # Lista de modelos disponíveis
            modelos_display_list = sorted(modelo_dict.keys())
            modelo_display_selecionado = st.selectbox(
                "Selecione o modelo de botina:",
                modelos_display_list,
                key="modelo_selector"
            )
            
            # Extrai o código_base do modelo selecionado
            modelo_selecionado = modelo_dict[modelo_display_selecionado]
            
            # Filtra dados do modelo selecionado
            df_modelo = df_botinas[df_botinas['Codigo_Base'] == modelo_selecionado].copy()
            
            if len(df_modelo) > 0:
                # Agrupa por numeração
                df_grades_modelo = df_modelo.groupby('Numeracao').agg({
                    'T008_Quantidade': 'sum',
                    'Estoque_Quantidade': 'first',
                    'T008_Descricao_Produto': 'first'
                }).reset_index()
                
                df_grades_modelo.columns = ['Numeração', 'Qtd_Vendida', 'Estoque', 'Descrição']
                df_grades_modelo['% Vendido'] = (df_grades_modelo['Qtd_Vendida'] / df_grades_modelo['Qtd_Vendida'].sum() * 100)
                df_grades_modelo = df_grades_modelo.sort_values('Qtd_Vendida', ascending=False)
                
                # Métricas do modelo
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_vendido_modelo = df_grades_modelo['Qtd_Vendida'].sum()
                    st.metric("Total Vendido", f"{int(total_vendido_modelo)} un.")
                
                with col2:
                    total_estoque_modelo = df_grades_modelo['Estoque'].sum()
                    st.metric("Total em Estoque", f"{int(total_estoque_modelo)} un.")
                
                with col3:
                    tamanho_top = df_grades_modelo.iloc[0]['Numeração']
                    vendas_top = df_grades_modelo.iloc[0]['Qtd_Vendida']
                    st.metric("Tamanho Mais Vendido", f"P{tamanho_top}", f"{int(vendas_top)} un.")
                
                with col4:
                    tamanho_critico = df_grades_modelo[df_grades_modelo['Estoque'] < df_grades_modelo['Qtd_Vendida']]['Numeração'].tolist()
                    qtd_critica = len(tamanho_critico)
                    st.metric("Tamanhos Críticos", qtd_critica, help="Tamanhos com estoque < vendido")
                
                # Gráficos lado a lado
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📊 Distribuição de Vendas por Grade")
                    
                    fig_vendas_grade = px.bar(
                        df_grades_modelo,
                        x='Qtd_Vendida',
                        y='Numeração',
                        orientation='h',
                        labels={'Qtd_Vendida': 'Quantidade Vendida', 'Numeração': 'Tamanho'},
                        color='Qtd_Vendida',
                        color_continuous_scale='Blues'
                    )
                    fig_vendas_grade.update_yaxes(categoryorder='total ascending')
                    st.plotly_chart(fig_vendas_grade, width='stretch')
                
                with col2:
                    st.markdown("#### 📦 Estoque vs. Vendido por Grade")
                    
                    fig_estoque_grade = go.Figure(data=[
                        go.Bar(
                            x=df_grades_modelo['Numeração'],
                            y=df_grades_modelo['Estoque'],
                            name='Estoque',
                            marker_color='#2ecc71'
                        ),
                        go.Bar(
                            x=df_grades_modelo['Numeração'],
                            y=df_grades_modelo['Qtd_Vendida'],
                            name='Vendido (3M)',
                            marker_color='#3498db'
                        )
                    ])
                    fig_estoque_grade.update_layout(barmode='group', height=400)
                    st.plotly_chart(fig_estoque_grade, width='stretch')
                
                # Tabela detalhada
                st.markdown("---")
                st.markdown("#### 📋 Tabela Detalhada de Grades")
                
                df_grades_display = df_grades_modelo[[
                    'Numeração', 'Qtd_Vendida', '% Vendido', 'Estoque', 'Descrição'
                ]].copy()
                
                df_grades_display['Qtd_Vendida'] = df_grades_display['Qtd_Vendida'].astype(int)
                df_grades_display['% Vendido'] = df_grades_display['% Vendido'].apply(lambda x: f"{x:.1f}%")
                df_grades_display['Estoque'] = df_grades_display['Estoque'].astype(int)
                df_grades_display.columns = ['Numeração', 'Vendidas (3M)', '% do Total', 'Em Estoque', 'Descrição']
                
                st.dataframe(df_grades_display, width='stretch', hide_index=True)
            else:
                st.warning(f"Nenhum dado disponível para o modelo {modelo_selecionado}")
        
        # =============== SEÇÃO B: ANÁLISE GERAL ===============
        with sub_tab2:
            st.markdown("### Análise Geral Consolidada (Todas as Botinas)")
            
            # Agrupa todas as botinas por numeração
            df_grades_geral = df_botinas.groupby('Numeracao').agg({
                'T008_Quantidade': 'sum',
                'Estoque_Quantidade': 'sum',
                'Codigo_Base': 'nunique'
            }).reset_index()
            
            df_grades_geral.columns = ['Numeração', 'Qtd_Vendida', 'Estoque_Total', 'Qty_Modelos']
            df_grades_geral['% Vendido'] = (df_grades_geral['Qtd_Vendida'] / df_grades_geral['Qtd_Vendida'].sum() * 100)
            df_grades_geral['% Estoque'] = (df_grades_geral['Estoque_Total'] / df_grades_geral['Estoque_Total'].sum() * 100)
            df_grades_geral['Diferenca_Percentual'] = df_grades_geral['% Estoque'] - df_grades_geral['% Vendido']
            df_grades_geral = df_grades_geral.sort_values('Qtd_Vendida', ascending=False)
            
            # Métricas gerais
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_vendido_geral = df_grades_geral['Qtd_Vendida'].sum()
                st.metric("Total Vendido (Todas)", f"{int(total_vendido_geral)} un.")
            
            with col2:
                total_estoque_geral = df_grades_geral['Estoque_Total'].sum()
                st.metric("Total em Estoque", f"{int(total_estoque_geral)} un.")
            
            with col3:
                total_modelos = df_botinas['Codigo_Base'].nunique()
                st.metric("Modelos de Botina", total_modelos)
            
            with col4:
                total_grades = len(df_grades_geral)
                st.metric("Grades Diferentes", total_grades)
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Distribuição % de Vendas por Grade (Top 8)")
                
                df_top_grades = df_grades_geral.head(8)
                df_outros = pd.DataFrame({
                    'Numeração': ['Outros'],
                    'Qtd_Vendida': [df_grades_geral.iloc[8:]['Qtd_Vendida'].sum()] if len(df_grades_geral) > 8 else [0]
                })
                df_grades_pizza = pd.concat([df_top_grades[['Numeração', 'Qtd_Vendida']], df_outros], ignore_index=True)
                
                fig_pizza_grades = px.pie(
                    df_grades_pizza,
                    labels='Numeração',
                    values='Qtd_Vendida',
                    title='Distribuição de Vendas por Grade'
                )
                st.plotly_chart(fig_pizza_grades, width='stretch')
            
            with col2:
                st.markdown("#### 📈 Diferença % (Estoque vs. Vendido)")
                
                df_grades_diff = df_grades_geral.head(10).copy()
                
                cores_diff = ['#e74c3c' if x < 0 else '#2ecc71' for x in df_grades_diff['Diferenca_Percentual']]
                
                fig_diff = px.bar(
                    df_grades_diff,
                    x='Diferenca_Percentual',
                    y='Numeração',
                    orientation='h',
                    title='Diferença % (estoque - vendido)',
                    labels={'Diferenca_Percentual': 'Diferença %', 'Numeração': 'Grade'},
                    color_discrete_sequence=cores_diff
                )
                fig_diff.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_diff, width='stretch')
            
            # Recomendação Otimizada
            st.markdown("---")
            st.markdown("### 🎯 Recomendação Otimizada de Compra")
            
            # Identifica tamanhos desbalanceados
            recomendacoes = []
            for idx, row in df_grades_geral.head(10).iterrows():
                numeracao = row['Numeração']
                pct_vendido = row['% Vendido']
                pct_estoque = row['% Estoque']
                diferenca = pct_estoque - pct_vendido
                
                if diferenca < -5:  # Mais de 5% abaixo do esperado
                    recomendacoes.append({
                        'Numeração': numeracao,
                        'Problema': '📉 Subabastecido',
                        'Vendido': f"{pct_vendido:.1f}%",
                        'Estoque': f"{pct_estoque:.1f}%",
                        'Recomendação': f"AUMENTAR compra de P{numeracao} ({abs(diferenca):.1f}% acima do ideal)"
                    })
                elif diferenca > 5:  # Mais de 5% acima do esperado
                    recomendacoes.append({
                        'Numeração': numeracao,
                        'Problema': '📈 Superabastecido',
                        'Vendido': f"{pct_vendido:.1f}%",
                        'Estoque': f"{pct_estoque:.1f}%",
                        'Recomendação': f"REDUZIR compra de P{numeracao} ({diferenca:.1f}% acima do ideal)"
                    })
            
            if recomendacoes:
                df_recomendacoes = pd.DataFrame(recomendacoes)
                st.dataframe(df_recomendacoes, width='stretch', hide_index=True)
            else:
                st.success("✅ Distribuição de estoque balanceada com as vendas!")
            
            # Tabela ranking geral
            st.markdown("---")
            st.markdown("#### 📋 Tabela Ranking Geral de Grades")
            
            df_ranking = df_grades_geral[[
                'Numeração', 'Qtd_Vendida', '% Vendido', 'Estoque_Total', '% Estoque', 'Qty_Modelos'
            ]].copy()
            
            df_ranking['Qtd_Vendida'] = df_ranking['Qtd_Vendida'].astype(int)
            df_ranking['% Vendido'] = df_ranking['% Vendido']
            df_ranking['Estoque_Total'] = df_ranking['Estoque_Total'].astype(int)
            df_ranking['% Estoque'] = df_ranking['% Estoque']
            df_ranking.columns = ['Numeração', 'Vendidas (3M)', '% Vendido', 'Estoque Total', '% Estoque', 'Qty Modelos']
            
            st.dataframe(df_ranking, width='stretch', hide_index=True)


# ========================= TAB 3: DETALHES E EXPORT =========================
with tab3:
    st.subheader("📋 Detalhes Completos e Exportação")
    
    st.markdown("""
    Esta aba contém as tabelas completas com todos os dados para análise e exportação.
    """)
    
    # Abas de detalhes
    detail_tab1, detail_tab2 = st.tabs(["Análise Crítica", "Dados de Vendas"])
    
    with detail_tab1:
        st.markdown("### 📊 Tabela Completa - Análise Crítica")
        
        # Recarrega a tabela de análise crítica
        df_export_critica = df_produtos_stats_sorted[[
            'Codigo_Produto', 'Descricao', 'Qtd_Vendida_3M', 'Vendas_Media_Mes', 
            'Projecao_Com_Threshold', 'Estoque_Atual', 'Diferenca', 'Status'
        ]].copy()
        
        df_export_critica.columns = [
            'Código', 'Descrição', 'Vendidas 3M', 'Média/Mês', 
            f'Projeção ({threshold_meses}M)', 'Estoque', 'Diferença', 'Status'
        ]
        
        df_export_critica['Vendidas 3M'] = df_export_critica['Vendidas 3M'].astype(int)
        df_export_critica['Média/Mês'] = df_export_critica['Média/Mês']
        df_export_critica[f'Projeção ({threshold_meses}M)'] = df_export_critica[f'Projeção ({threshold_meses}M)']
        df_export_critica['Estoque'] = df_export_critica['Estoque'].astype(int)
        df_export_critica['Diferença'] = df_export_critica['Diferença']
        
        st.dataframe(df_export_critica, width='stretch', hide_index=True)
        
        # Download CSV
        csv_critica = df_export_critica.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Análise Crítica em CSV",
            data=csv_critica,
            file_name=f"analise_critica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with detail_tab2:
        st.markdown("### 📦 Tabela Completa - Dados de Vendas Filtrados")
        
        # Prepara tabela de vendas completa
        df_vendas_export = df_filtered[[
            'T008_Codigo_Produto', 'T008_Descricao_Produto', 'T007_Data_Emissao',
            'T008_Quantidade', 'Estoque_Quantidade', 'T008_Valor_Total_Preco_Sem_Desconto'
        ]].copy()
        
        df_vendas_export.columns = [
            'Código Produto', 'Descrição', 'Data Venda', 'Quantidade', 'Estoque', 'Valor Total'
        ]
        
        df_vendas_export['Data Venda'] = df_vendas_export['Data Venda'].dt.strftime('%d/%m/%Y')
        df_vendas_export['Valor Total'] = df_vendas_export['Valor Total'].apply(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "")
        df_vendas_export['Quantidade'] = df_vendas_export['Quantidade'].astype(int)
        df_vendas_export['Estoque'] = df_vendas_export['Estoque'].astype(int)
        
        st.dataframe(df_vendas_export, width='stretch', hide_index=True)
        
        # Download CSV
        csv_vendas = df_vendas_export.to_csv(index=False)
        st.download_button(
            label="📥 Baixar Dados de Vendas em CSV",
            data=csv_vendas,
            file_name=f"vendas_filtradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# ========================= TAB 4: ALERTAS & SUGESTÕES =========================
with tab4:
    st.subheader("🚨 Alertas de Estoque & Sugestões de Compra")
    
    # Carrega dados de estoque com análise
    try:
        df_estoque_analise = pd.read_csv("data/estoque_analise.csv", low_memory=False)
        
        # Filtra apenas alertas críticos e mínimos
        df_alertas = df_estoque_analise[
            (df_estoque_analise['Status_Estoque'].isin(['CRÍTICO', 'MÍNIMO'])) &
            (df_estoque_analise['D009_Quantidade_Estoque'] > 0)
        ].copy()
        
        if len(df_alertas) > 0:
            # Ordena por urgência (crítico primeiro, depois por sugestão de compra)
            df_alertas = df_alertas.sort_values(['Status_Estoque', 'Sugestao_Compra'], ascending=[True, False])
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            
            criticos = len(df_alertas[df_alertas['Status_Estoque'] == 'CRÍTICO'])
            minimos = len(df_alertas[df_alertas['Status_Estoque'] == 'MÍNIMO'])
            total_sugestao = df_alertas['Valor_Sugestao_Compra'].sum()
            total_quantidade = df_alertas['Sugestao_Compra'].sum()
            
            with col1:
                st.metric("🔴 Estoque Crítico", criticos)
            with col2:
                st.metric("🟡 Estoque Mínimo", minimos)
            with col3:
                st.metric("📊 Qtd Sugestão", f"{int(total_quantidade)}")
            with col4:
                st.metric("💰 Valor Sugestão", f"R$ {total_sugestao:,.0f}")
            
            # Tabs de visualização
            alert_tab1, alert_tab2, alert_tab3 = st.tabs(["🔴 Alertas Críticos", "🟡 Alertas Mínimo", "📋 Sugestão de Compra"])
            
            with alert_tab1:
                st.markdown("### 🔴 Produtos em Estoque CRÍTICO")
                df_criticos = df_alertas[df_alertas['Status_Estoque'] == 'CRÍTICO'].copy()
                
                if len(df_criticos) > 0:
                    # Exibe com cor vermelha
                    df_criticos_display = df_criticos[[
                        'D002_Descricao_Produto', 'D001_Codigo_Barras', 'D009_Quantidade_Estoque',
                        'Estoque_Critico', 'D009_Valor_Custo_Unitario', 'Sugestao_Compra', 'Valor_Sugestao_Compra'
                    ]].copy()
                    
                    df_criticos_display.columns = [
                        'Produto', 'Código', 'Qtd Atual', 'Limite Crítico', 'Custo Unit.', 'Qtd Sugestão', 'Valor Sugestão'
                    ]
                    
                    df_criticos_display['Qtd Atual'] = df_criticos_display['Qtd Atual'].astype(int)
                    df_criticos_display['Limite Crítico'] = df_criticos_display['Limite Crítico'].astype(int)
                    df_criticos_display['Custo Unit.'] = df_criticos_display['Custo Unit.'].apply(lambda x: f"R$ {x:,.2f}")
                    df_criticos_display['Qtd Sugestão'] = df_criticos_display['Qtd Sugestão'].astype(int)
                    df_criticos_display['Valor Sugestão'] = df_criticos_display['Valor Sugestão'].apply(lambda x: f"R$ {x:,.2f}")
                    
                    st.dataframe(df_criticos_display, width='stretch', hide_index=True)
                    
                    st.warning(f"⚠️ {len(df_criticos)} produtos em estoque crítico! Ação imediata recomendada.")
                else:
                    st.success("✅ Nenhum produto em estoque crítico")
            
            with alert_tab2:
                st.markdown("### 🟡 Produtos em Estoque MÍNIMO")
                df_minimos = df_alertas[df_alertas['Status_Estoque'] == 'MÍNIMO'].copy()
                
                if len(df_minimos) > 0:
                    df_minimos_display = df_minimos[[
                        'D002_Descricao_Produto', 'D001_Codigo_Barras', 'D009_Quantidade_Estoque',
                        'Estoque_Minimo', 'D009_Valor_Custo_Unitario', 'Sugestao_Compra', 'Valor_Sugestao_Compra'
                    ]].copy()
                    
                    df_minimos_display.columns = [
                        'Produto', 'Código', 'Qtd Atual', 'Limite Mínimo', 'Custo Unit.', 'Qtd Sugestão', 'Valor Sugestão'
                    ]
                    
                    df_minimos_display['Qtd Atual'] = df_minimos_display['Qtd Atual'].astype(int)
                    df_minimos_display['Limite Mínimo'] = df_minimos_display['Limite Mínimo'].astype(int)
                    df_minimos_display['Custo Unit.'] = df_minimos_display['Custo Unit.'].apply(lambda x: f"R$ {x:,.2f}")
                    df_minimos_display['Qtd Sugestão'] = df_minimos_display['Qtd Sugestão'].astype(int)
                    df_minimos_display['Valor Sugestão'] = df_minimos_display['Valor Sugestão'].apply(lambda x: f"R$ {x:,.2f}")
                    
                    st.dataframe(df_minimos_display, width='stretch', hide_index=True)
                    
                    st.info(f"ℹ️ {len(df_minimos)} produtos abaixo do estoque mínimo. Recomenda-se compra nos próximos dias.")
                else:
                    st.success("✅ Nenhum produto abaixo do estoque mínimo")
            
            with alert_tab3:
                st.markdown("### 📋 Sugestão Consolidada de Compra")
                
                df_sugestao = df_alertas[[
                    'D002_Descricao_Produto', 'D001_Codigo_Barras', 'D009_Quantidade_Estoque',
                    'Estoque_Minimo', 'D009_Valor_Custo_Unitario', 'Sugestao_Compra', 'Valor_Sugestao_Compra'
                ]].copy()
                
                df_sugestao.columns = [
                    'Produto', 'Código', 'Qtd Atual', 'Estoque Mín.', 'Custo Unit.', 'Qtd Compra', 'Valor Total'
                ]
                
                df_sugestao['Qtd Atual'] = df_sugestao['Qtd Atual'].astype(int)
                df_sugestao['Estoque Mín.'] = df_sugestao['Estoque Mín.'].astype(int)
                df_sugestao['Custo Unit.'] = df_sugestao['Custo Unit.'].apply(lambda x: f"R$ {x:,.2f}")
                df_sugestao['Qtd Compra'] = df_sugestao['Qtd Compra'].astype(int)
                df_sugestao['Valor Total'] = df_sugestao['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
                
                # Ordena por valor descendente
                df_sugestao_sorted = df_sugestao.sort_values('Valor Total', ascending=False)
                
                st.dataframe(df_sugestao_sorted, width='stretch', hide_index=True)
                
                # Resumo financeiro
                st.markdown("---")
                st.markdown("### 💰 Resumo Financeiro da Compra")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Total de Itens a Comprar", int(total_quantidade))
                
                with col2:
                    st.metric("Investimento Total", f"R$ {total_sugestao:,.2f}")
                
                # Gráfico de distribuição de custo
                st.markdown("---")
                df_chart = df_alertas.nlargest(15, 'Valor_Sugestao_Compra')[[
                    'D002_Descricao_Produto', 'Valor_Sugestao_Compra', 'Status_Estoque'
                ]].copy()
                df_chart.columns = ['Produto', 'Valor', 'Status']
                
                fig_chart = px.bar(
                    df_chart,
                    x='Valor',
                    y='Produto',
                    orientation='h',
                    title="Top 15 Produtos por Valor de Compra Sugerida",
                    labels={'Valor': 'Valor da Sugestão (R$)'},
                    color='Status',
                    color_discrete_map={'CRÍTICO': '#e74c3c', 'MÍNIMO': '#f39c12'}
                )
                st.plotly_chart(fig_chart, width='stretch')
        else:
            st.success("✅ Nenhum alerta de estoque! Todos os produtos estão em nível OK.")
    
    except FileNotFoundError:
        st.warning("⚠️ Arquivo 'estoque_analise.csv' não encontrado. Execute 'data_preparation.py' para gerar os dados.")

# ========================= RODAPÉ =========================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #95a5a6; font-size: 12px;'>
    <p>Dashboard de Estoque Crítico - AMM (EPIS + Soluções) | Desenvolvido em Streamlit</p>
    <p>Data atual: {}</p>
</div>
""".format(datetime.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)
