# 📊 Dashboard de Vendas - AMM (EPIS + Soluções)

Dashboard Streamlit para monitoramento de equipe de vendas com análises mensais, trimestrais e anuais, combinando dados de EPIS e Soluções.

## 🚀 Como Usar

### 1. Instalação de Dependências

```bash
pip install -r requirements.txt
```

### 2. Preparação dos Dados

Execute o script de preparação de dados:

```bash
python data_preparation.py
```

Este script irá:
- ✅ Combinar os dois arquivos (EPIS e Soluções)
- ✅ Remover status "Pendente" da coluna "T005_Status"
- ✅ Preencher vendedores ausentes com o último vendedor que vendeu para cada empresa
- ✅ Manter apenas registros com "T007_Flag_Cancelada" = "N"
- ✅ Usar o nome fantasia da empresa quando disponível
- ✅ Eliminar linhas com "Data_Envio_XML" zerada (0000-00-00)
- ✅ Criar um arquivo limpo e combinado `notas_fiscais_COMBINADAS_CLEAN.csv`

### 3. Executar o Dashboard

```bash
streamlit run dashboard.py
```

O dashboard será aberto automaticamente em `http://localhost:8501`

## 📋 Funcionalidades

### 🔍 Filtros
- **Filtro por Vendedora**: Selecione uma vendedora específica ou "TOTAL EMPRESA"
- **Filtro de Período**: Escolha o intervalo de datas para análise

### 📊 Abas de Análise

#### 📅 Mensal
- Evolução de vendas mês a mês (gráfico de linha)
- Quantidade de vendas por mês
- Tabela detalhada com valores e quantidades

#### 📊 Trimestral
- Evolução trimestral em gráfico de linha
- Distribuição percentual em gráfico de pizza
- Tabela com dados trimestrais

#### 📈 Anual
- Comparação de vendas anuais em gráfico de barras
- Quantidade de vendas por ano
- Tabela com dados anuais

#### 🎯 Detalhado
- **Vendas por Vendedora**: Gráfico de barras e pizza mostrando desempenho individual
- **Top 15 Empresas**: Ranking das maiores empresas clientes
- **Tabelas Completas**: Dados detalhados para exportação

### 📈 Métricas Principais (Sidebar)
- Total de Vendas (R$)
- Número de Vendas
- Ticket Médio
- Número de Clientes

## 📁 Arquivos do Projeto

```
├── notas_fiscais_AMM_EPIS.csv              # Arquivo original de EPIS
├── notas_fiscais_AMM_Solucoes.csv          # Arquivo original de Soluções
├── notas_fiscais_COMBINADAS_CLEAN.csv      # Arquivo combinado e limpo (gerado automaticamente)
├── data_preparation.py                      # Script de preparação e limpeza
├── dashboard.py                             # Dashboard Streamlit
├── requirements.txt                         # Dependências Python
└── README.md                               # Este arquivo
```

## 🔧 Requisitos do Sistema

- Python 3.8+
- pandas
- plotly
- streamlit
- numpy

## 💡 Dicas de Uso

1. **Primeira Execução**: O dashboard criará automaticamente o arquivo combinado e limpo na primeira execução
2. **Atualização de Dados**: Se algum arquivo original mudar, delete `notas_fiscais_COMBINADAS_CLEAN.csv` e execute o dashboard novamente
3. **Performance**: Para grandes volumes de dados, o cache do Streamlit melhora a performance
4. **Exportação**: Use a opção de download do Streamlit para exportar dados das tabelas

## 📞 Suporte

Para questões ou melhorias, entre em contato com a equipe de TI da AMM.

---

**Desenvolvido para:** AMM - Painel de Vendas  
**Data de Criação:** 2024
