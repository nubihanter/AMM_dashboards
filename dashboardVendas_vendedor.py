import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import os
import json

VENDEDORES_OCULTOS = [
    "DESCONHECIDO",
    "ANDRE",
    "INANJARA",
    "JUSLIENE",
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
        with open("data/metas_por_vendedores.json", "r", encoding='utf-8') as f:
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
    page_title="Dashboard Individual - Vendedor - AMM",
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
st.markdown('<div class="main-header">👩‍💼 Dashboard Individual - Vendedor</div>', unsafe_allow_html=True)

# Sidebar - Seletor de Vendedor
st.sidebar.header("🔍 Seleção")

# Cria lista de vendedores únicos
vendedoras_list = sorted(df['vendedor.C007_Primeiro_Nome'].unique().tolist())
vendedoras_list = [v for v in vendedoras_list if v.upper() not in VENDEDORES_OCULTOS]

vendedora_selecionada = st.sidebar.selectbox(
    "Selecione a Vendedora:",
    vendedoras_list,
    index=0
)

# Filtra dados do vendedor selecionado
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

# Selectboxes para mês e ano
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

# Cria período do mês/ano selecionado
data_inicio = pd.Timestamp(year=ano_selecionado, month=mes_selecionado, day=1)
# Calcula o último dia do mês
if mes_selecionado == 12:
    data_fim = pd.Timestamp(year=ano_selecionado+1, month=1, day=1) - timedelta(days=1)
else:
    data_fim = pd.Timestamp(year=ano_selecionado, month=mes_selecionado+1, day=1) - timedelta(days=1)

# Filtra dados por mês/ano
df_vendedor_filtered = df_vendedor[
    (df_vendedor['T007_Data_Emissao'].dt.date >= data_inicio.date()) &
    (df_vendedor['T007_Data_Emissao'].dt.date <= data_fim.date())
].copy()

# Filtra todos os dados para ranking (todas as vendedoras no período)
df_filtered = df[
    (df['T007_Data_Emissao'].dt.date >= data_inicio.date()) &
    (df['T007_Data_Emissao'].dt.date <= data_fim.date())
].copy()

# Métricas principais para sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📈 Vendas do Mês")

total_vendas = df_vendedor_filtered['Valor_Venda'].sum()
num_vendas = len(df_vendedor_filtered)
num_clientes = df_vendedor_filtered['Empresa'].nunique()
ticket_medio = total_vendas / num_vendas if num_vendas > 0 else 0

col1, col2 = st.sidebar.columns(2)
with col1:
    st.metric("Vendas", f"R$ {total_vendas:,.0f}")
with col2:
    st.metric("Nº Vendas", num_vendas)

col3, col4 = st.sidebar.columns(2)
with col3:
    st.metric("Ticket Médio", f"R$ {ticket_medio:,.0f}")
with col4:
    st.metric("Nº Clientes", num_clientes)

# Tabs principais
tab1, tab2, tab3, tab4 = st.tabs(
    ["🎯 Metas", "📊 Vendas", "⏱️ Clientes Inativos", "🏆 Ranking"]
)

# =============== TAB 1: METAS ===============
with tab1:
    st.subheader(f"🎯 Metas - {vendedora_selecionada}")
    
    # Procura a meta do vendedor
    meta_vendedor = None
    nome_normalizado = normalizar_nome(vendedora_selecionada)
    for vendedor_meta in metas_data:
        if normalizar_nome(vendedor_meta['nome']) == nome_normalizado:
            meta_vendedor = vendedor_meta
            break
    
    if meta_vendedor is None:
        # Mostra vendas sem comparação de meta
        st.info(f"ℹ️ Nenhuma meta cadastrada para {vendedora_selecionada}. Exibindo vendas do período.")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Vendas Total", f"R$ {total_vendas:,.0f}")
        
        with col2:
            st.metric("📊 Nº de Vendas", num_vendas)
        
        with col3:
            st.metric("📈 Ticket Médio", f"R$ {ticket_medio:,.0f}")
        
        with col4:
            st.metric("🏢 Nº de Clientes", num_clientes)
        
        # Gráfico de vendas diárias mesmo sem meta
        st.subheader("Evolução de Vendas")
        
        df_vendedor_filtered['Data'] = df_vendedor_filtered['T007_Data_Emissao'].dt.date
        df_diario = df_vendedor_filtered.groupby('Data').agg({
            'Valor_Venda': ['sum', 'count']
        }).reset_index()
        df_diario.columns = ['Data', 'Valor', 'Quantidade']
        df_diario = df_diario.sort_values('Data')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if len(df_diario) > 0:
                fig_linha = px.line(
                    df_diario,
                    x='Data',
                    y='Valor',
                    markers=True,
                    title="Evolução de Vendas (Diário)",
                    labels={'Valor': 'Valor (R$)', 'Data': 'Dia'},
                    color_discrete_sequence=['#1f77b4']
                )
                fig_linha.update_traces(line=dict(width=3), marker=dict(size=8))
                st.plotly_chart(fig_linha, width='stretch', key="fig_linha_sem_meta")
        
        with col2:
            if len(df_diario) > 0:
                fig_barras = px.bar(
                    df_diario,
                    x='Data',
                    y='Quantidade',
                    title="Quantidade de Vendas (Diário)",
                    labels={'Quantidade': 'Nº de Vendas', 'Data': 'Dia'},
                    color='Quantidade',
                    color_continuous_scale='Blues'
                )
                st.plotly_chart(fig_barras, width='stretch', key="fig_barras_sem_meta")
    else:
        # Calcula meta total no período selecionado
        meta_periodo = 0
        metas_list = []
        
        for meta in meta_vendedor['metas']:
            meta_date_inicio = pd.to_datetime(meta['data_inicio']).date()
            meta_date_fim = pd.to_datetime(meta['data_fim']).date()
            
            # Se a meta sobrepõe o período selecionado, conta
            if not (meta_date_fim < data_inicio.date() or meta_date_inicio > data_fim.date()):
                meta_periodo += meta['valor']
                metas_list.append({
                    'período': f"{meta_date_inicio.strftime('%m/%Y')}",
                    'valor': meta['valor'],
                    'titulo': meta['goal_title']
                })
        
        # Calcula realizado
        realizado = total_vendas
        percentual_atingido = (realizado / meta_periodo * 100) if meta_periodo > 0 else 0
        
        # Status
        if percentual_atingido >= 100:
            status = "✅ META ATINGIDA"
            status_class = "status-ok"
        elif percentual_atingido >= 80:
            status = "⚠️ META PRÓXIMA"
            status_class = "status-warning"
        else:
            status = "❌ ABAIXO DA META"
            status_class = "status-alert"
        
        # Exibe KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🎯 Meta Total", f"R$ {meta_periodo:,.0f}")
        
        with col2:
            st.metric("📊 Realizado", f"R$ {realizado:,.0f}")
        
        with col3:
            st.metric("📈 % Atingido", f"{percentual_atingido:.1f}%")
        
        with col4:
            st.markdown(f"<div class='{status_class}'>{status}</div>", unsafe_allow_html=True)
        
        # Gráfico de progresso
        col1, col2 = st.columns(2)
        
        with col1:
            # Indicador de progresso em gauge
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=percentual_atingido,
                title={'text': "Progresso da Meta (%)"},
                delta={'reference': 100},
                gauge={
                    'axis': {'range': [0, 150]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 80], 'color': "lightgray"},
                        {'range': [80, 100], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 100
                    }
                }
            ))
            fig_gauge.update_layout(height=400)
            st.plotly_chart(fig_gauge, width='stretch', key="fig_gauge_meta")
        
        with col2:
            # Histórico das últimas 3 metas vs Realizado
            historico_metas = []
            for meta in meta_vendedor['metas']:
                m_inicio = pd.to_datetime(meta['data_inicio']).date()
                m_fim = pd.to_datetime(meta['data_fim']).date()
                if m_inicio <= data_inicio.date():
                    historico_metas.append({
                        'data_inicio': m_inicio,
                        'data_fim': m_fim,
                        'valor_meta': meta['valor'],
                        'periodo_str': m_inicio.strftime('%m/%Y')
                    })
            
            # Pega as últimas 3 e ordena cronologicamente
            historico_metas = sorted(historico_metas, key=lambda x: x['data_inicio'], reverse=True)[:3]
            historico_metas = sorted(historico_metas, key=lambda x: x['data_inicio'])
            
            historico_plot_data = []
            for m in historico_metas:
                # Calcular vendas no período específico da meta
                vendas_periodo = df_vendedor[
                    (df_vendedor['T007_Data_Emissao'].dt.date >= m['data_inicio']) &
                    (df_vendedor['T007_Data_Emissao'].dt.date <= m['data_fim'])
                ]['Valor_Venda'].sum()
                
                historico_plot_data.append({
                    'Período': m['periodo_str'],
                    'Tipo': 'Meta',
                    'Valor': m['valor_meta']
                })
                historico_plot_data.append({
                    'Período': m['periodo_str'],
                    'Tipo': 'Realizado',
                    'Valor': vendas_periodo
                })
                
            if not historico_plot_data:
                # Fallback caso não haja histórico
                historico_plot_data = [
                    {'Período': data_inicio.strftime('%m/%Y'), 'Tipo': 'Meta', 'Valor': meta_periodo},
                    {'Período': data_inicio.strftime('%m/%Y'), 'Tipo': 'Realizado', 'Valor': realizado}
                ]
                
            df_compare = pd.DataFrame(historico_plot_data)
            
            fig_compare = px.bar(
                df_compare,
                x='Período',
                y='Valor',
                color='Tipo',
                barmode='group',
                title="Últimas 3 Metas vs Realizado",
                labels={'Valor': 'Valor (R$)'},
                color_discrete_map={'Meta': '#1f77b4', 'Realizado': '#ff7f0e'},
                text_auto=True
            )
            st.plotly_chart(fig_compare, width='stretch', key="fig_compare_meta")
        
        # Tabela de metas mensais
        st.subheader("Detalhamento de Metas")
        if metas_list:
            df_metas_display = pd.DataFrame(metas_list)
            st.dataframe(
                df_metas_display,
                width='stretch',
                hide_index=True,
                column_config={
                    "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
                }
            )
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
            # Vendas diárias (série temporal)
            df_vendedor_filtered['Data'] = df_vendedor_filtered['T007_Data_Emissao'].dt.date
            df_diario = df_vendedor_filtered.groupby('Data').agg({
                'Valor_Venda': ['sum', 'count']
            }).reset_index()
            df_diario.columns = ['Data', 'Valor', 'Quantidade']
            df_diario = df_diario.sort_values('Data')
            
            fig_linha = px.line(
                df_diario,
                x='Data',
                y='Valor',
                markers=True,
                title="Evolução de Vendas (Diário)",
                labels={'Valor': 'Valor (R$)', 'Data': 'Dia'},
                color_discrete_sequence=['#1f77b4']
            )
            fig_linha.update_traces(line=dict(width=3), marker=dict(size=8))
            st.plotly_chart(fig_linha, width='stretch', key=f"fig_linha_tab2_{vendedora_selecionada}")
        
        with col2:
            # Quantidade de vendas
            fig_barras = px.bar(
                df_diario,
                x='Data',
                y='Quantidade',
                title="Quantidade de Vendas (Diário)",
                labels={'Quantidade': 'Nº de Vendas', 'Data': 'Dia'},
                color='Quantidade',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig_barras, width='stretch', key=f"fig_barras_tab2_{vendedora_selecionada}")
        
        # Tabela diária com empresa
        st.subheader("Detalhe Diário de Vendas")
        
        # Agrupa por Data e Empresa
        df_detalhe = df_vendedor_filtered.groupby(['Data', 'Empresa']).agg({
            'Valor_Venda': ['sum', 'count']
        }).reset_index()
        df_detalhe.columns = ['Data', 'Empresa', 'Valor', 'Quantidade']
        df_detalhe = df_detalhe.sort_values(['Data', 'Valor'], ascending=[False, False])
        
        df_detalhe_display = df_detalhe.copy()
        df_detalhe_display['Data'] = df_detalhe_display['Data'].apply(lambda x: x.strftime('%d/%m/%Y'))
        
        st.dataframe(
            df_detalhe_display,
            width='stretch',
            hide_index=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f")
            }
        )


# =============== TAB 3: CLIENTES INATIVOS ===============
with tab3:
    st.subheader(f"⏱️ Clientes Inativos - {vendedora_selecionada}")
    
    if len(df_vendedor) == 0:
        st.warning("Sem dados de clientes para este vendedor")
    else:
        # Calcula última venda por cliente (do vendedor)
        df_clientes_ultima_venda = df_vendedor.groupby('Empresa').agg({
            'T007_Data_Emissao': 'max',
            'Valor_Venda': ['sum', 'count']
        }).reset_index()
        df_clientes_ultima_venda.columns = ['Empresa', 'Ultima_Venda', 'Faturamento_Total', 'Num_Vendas']
        
        # Filtra clientes com faturamento mínimo
        df_clientes_ultima_venda = df_clientes_ultima_venda[
            df_clientes_ultima_venda['Faturamento_Total'] >= FATURAMENTO_MINIMO_INATIVIDADE
        ]
        
        # Calcula dias de inatividade
        data_referencia = df_vendedor['T007_Data_Emissao'].max()
        df_clientes_ultima_venda['Dias_Inatividade'] = (
            data_referencia - df_clientes_ultima_venda['Ultima_Venda']
        ).dt.days
        
        # Ordena por inatividade
        df_clientes_ultima_venda = df_clientes_ultima_venda.sort_values('Dias_Inatividade', ascending=False)
        
        if len(df_clientes_ultima_venda) == 0:
            st.info("Nenhum cliente inativo encontrado com faturamento mínimo")
        else:
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
                nbins=15,
                title="Distribuição de Clientes por Dias Inativos",
                labels={'Dias_Inatividade': 'Dias de Inatividade', 'count': 'Quantidade de Clientes'},
                color_discrete_sequence=['#ff7f0e']
            )
            st.plotly_chart(fig_inatividade, width='stretch', key=f"fig_inatividade_{vendedora_selecionada}")
            
            # Tabela de clientes inativos
            st.subheader("Clientes Inativos (Ordenado por Inatividade)")
            df_inativos_display = df_clientes_ultima_venda.copy()
            df_inativos_display['Ultima_Venda'] = df_inativos_display['Ultima_Venda'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(
                df_inativos_display[['Empresa', 'Ultima_Venda', 'Dias_Inatividade', 'Faturamento_Total', 'Num_Vendas']],
                width='stretch',
                hide_index=True,
                column_config={
                    "Faturamento_Total": st.column_config.NumberColumn("Faturamento Total", format="R$ %.2f")
                }
            )


# =============== TAB 4: RANKING ===============
with tab4:
    st.subheader("🏆 Ranking de Vendedoras")
    st.markdown(f"**Período:** {data_inicio.strftime('%m/%Y')}")
    
    # Processa dados para ranking de TODAS as vendedoras
    vendedoras_uniques = sorted(df['vendedor.C007_Primeiro_Nome'].unique().tolist())
    vendedoras_uniques = [v for v in vendedoras_uniques if v.upper() not in VENDEDORES_OCULTOS]
    
    # Cria estrutura para ranking
    ranking_data = []
    
    for vendedora in vendedoras_uniques:
        # Vendas do período
        df_vendedora = df_filtered[df_filtered['vendedor.C007_Primeiro_Nome'] == vendedora]
        total_vendas = df_vendedora['Valor_Venda'].sum()
        
        # Procura metas
        meta_vendedor = None
        nome_normalizado = normalizar_nome(vendedora)
        for vendedor_meta in metas_data:
            if normalizar_nome(vendedor_meta['nome']) == nome_normalizado:
                meta_vendedor = vendedor_meta
                break
        
        # Calcula metas no período
        meta_total = 0
        if meta_vendedor is not None:
            for meta in meta_vendedor['metas']:
                meta_date_inicio = pd.to_datetime(meta['data_inicio']).date()
                meta_date_fim = pd.to_datetime(meta['data_fim']).date()
                
                # Se a meta sobrepõe o período selecionado, conta
                if not (meta_date_fim < data_inicio.date() or meta_date_inicio > data_fim.date()):
                    meta_total += meta['valor']
        
        # Calcula percentual
        percentual_atingido = (total_vendas / meta_total * 100) if meta_total > 0 else 0
        
        ranking_data.append({
            'Posição': 0,  # Será preenchido depois
            'Vendedora': vendedora,
            '% Meta': percentual_atingido,
            'tem_meta': meta_total > 0
        })
    
    # Cria DataFrame
    df_ranking = pd.DataFrame(ranking_data)
    
    # Ordena por % da meta (descrescente) - Coloca sem meta por último
    df_ranking_com_meta = df_ranking[df_ranking['tem_meta']].copy()
    df_ranking_sem_meta = df_ranking[~df_ranking['tem_meta']].copy()
    
    df_ranking_com_meta = df_ranking_com_meta.sort_values('% Meta', ascending=False).reset_index(drop=True)
    df_ranking_sem_meta = df_ranking_sem_meta.sort_values('Vendedora', ascending=True).reset_index(drop=True)
    
    # Adiciona posição
    df_ranking_com_meta['Posição'] = range(1, len(df_ranking_com_meta) + 1)
    df_ranking_sem_meta['Posição'] = range(len(df_ranking_com_meta) + 1, len(df_ranking_com_meta) + len(df_ranking_sem_meta) + 1)
    
    df_ranking_final = pd.concat([df_ranking_com_meta, df_ranking_sem_meta], ignore_index=True)
    
    st.markdown("---")
    
    # Adiciona formatação para o gráfico
    def formata_nome(row):
        pos = int(row['Posição'])
        nome = row['Vendedora']
        if pos == 1:
            return f"🥇 {nome}"
        elif pos == 2:
            return f"🥈 {nome}"
        elif pos == 3:
            return f"🥉 {nome}"
        return f"{pos}º {nome}"

    def define_cor(pos):
        if pos == 1:
            return "#ffd700"  # Ouro
        elif pos == 2:
            return "#c0c0c0"  # Prata
        elif pos == 3:
            return "#cd7f32"  # Bronze
        return "#1f77b4"      # Padrão

    df_ranking_final['Nome_Display'] = df_ranking_final.apply(formata_nome, axis=1)
    df_ranking_final['Cor'] = df_ranking_final['Posição'].apply(define_cor)
    
    # Cria o gráfico de barras
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
    
    fig_ranking.update_traces(
        texttemplate='%{text:.1f}%', 
        textposition='outside'
    )
    
    fig_ranking.update_layout(
        xaxis_tickangle=-45,
        yaxis=dict(ticksuffix="%"),
        showlegend=False,
        height=500,
        margin=dict(t=50, b=100)
    )
    
    st.plotly_chart(fig_ranking, width='stretch')


st.markdown("---")
st.markdown("👩‍💼 Dashboard Individual - Última atualização: {} | Período: {} a {}".format(
    datetime.now().strftime("%d/%m/%Y %H:%M"),
    data_inicio.strftime("%d/%m/%Y"),
    data_fim.strftime("%d/%m/%Y")
))
