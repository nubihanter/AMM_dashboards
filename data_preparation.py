import pandas as pd
import numpy as np
from datetime import datetime
import os

def load_and_clean_data(notas_fiscais_file=None, produtos_file=None):
    """
    Carrega, combina e limpa os arquivos CSVs de notas fiscais
    Adiciona cálculos de lucro bruto por item
    """
    # Define caminhos padrão relativos ao diretório do script
    if notas_fiscais_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        notas_fiscais_file = os.path.join(script_dir, "data", "notas_fiscais_combinadas.csv")
    
    if produtos_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        produtos_file = os.path.join(script_dir, "data", "produtos_combinados.csv")
    
    # Carrega ambos os arquivos
    print("Carregando arquivos...")
    print(f"Carregando notas fiscais de: {notas_fiscais_file}")
    print(f"Carregando produtos de: {produtos_file}")
    
    df_notas = pd.read_csv(notas_fiscais_file)
    df_produtos = pd.read_csv(produtos_file)

    print(f"NOTAS FISCAIS - Registros iniciais: {len(df_notas)}")
    print(f"PRODUTOS - Registros iniciais: {len(df_produtos)}")

    print(f"Total de itens de produtos: {len(df_produtos)}")
    
    # 1. Remove status "Pendente"
    df_notas = df_notas[df_notas['T007_Numero_Protocolo_Nfe'].notna()]
    
    # # 2. Remove linhas com Data_Envio_XML zerada (0000-00-00)
    # df = df[df['Data_Envio_XML'] != '0000-00-00 00:00:00']
    # print(f"Após remover Data_Envio_XML zerada: {len(df)}")
    
    # 3. Mantém apenas T007_Flag_Cancelada = "N"
    df_notas = df_notas[df_notas['T007_Flag_Cancelada'] == 'N']
    print(f"Após filtrar T007_Flag_Cancelada='N': {len(df_notas)}")
    
    # 4. Converte datas para datetime
    df_notas['T007_Data_Emissao'] = pd.to_datetime(df_notas['T007_Data_Emissao'], errors='coerce')
    df_notas['Data_Envio_XML']    = pd.to_datetime(df_notas['Data_Envio_XML'], errors='coerce')
    
    # 5. Preenche vendedores faltando com o último vendedor "to date" (em ordem cronológica)
    # Ordena por empresa e data para fazer forward fill correto
    df_notas = df_notas.sort_values(['D024_Id', 'T007_Data_Emissao'])
    
    # Para cada empresa (D024_Id), preenche vendedores vazios com o vendedor do registro anterior
    # Isso garante que vendedores novos não apareçam com histórico de clientes antigos
    for company_id in df_notas['D024_Id'].unique():
        mask = df_notas['D024_Id'] == company_id
        # Forward fill: preenche cada vazio com o vendedor do registro anterior (cronologicamente)
        df_notas.loc[mask, 'vendedor.C007_Primeiro_Nome'] = df_notas.loc[mask, 'vendedor.C007_Primeiro_Nome'].ffill()
    
    # 6. Usa nome fantasia quando disponível, senão usa nome da empresa
    df_notas['Empresa'] = df_notas['D024_Nome_Fantasia'].fillna(df_notas['D024_Nome_Empresa'])
    
    # 7. Remove linhas sem vendedor após preenchimento
    df_notas['vendedor.C007_Primeiro_Nome'] = df_notas['vendedor.C007_Primeiro_Nome'].fillna('Desconhecido')
    
    print(f"Após preencher vendedores: {len(df_notas)}")
    
    # 8. Cria coluna de mês e trimestre para agrupamentos
    df_notas['Mes'] = df_notas['T007_Data_Emissao'].dt.to_period('M')
    df_notas['Trimestre'] = df_notas['T007_Data_Emissao'].dt.to_period('Q')
    df_notas['Ano'] = df_notas['T007_Data_Emissao'].dt.year
    df_notas['Ano_Mes'] = df_notas['T007_Data_Emissao'].dt.strftime('%Y-%m')
    
    # Usa T007_Valor_Total_Produtos para análise de vendas
    df_notas['Valor_Venda'] = df_notas['T007_Valor_Total_Produtos'].fillna(0)
    
    print(f"Registros finais após limpeza: {len(df_notas)}")
    
    return df_notas


def prepare_products_with_profit(produtos_file=None):
    """
    Carrega produtos e calcula lucro bruto por item
    Lucro Bruto = Preço_Venda - Custo_Unitário
    """
    if produtos_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        produtos_file = os.path.join(script_dir, "data", "produtos_combinados.csv")
    
    print("\n=== PROCESSANDO LUCRO BRUTO ===")
    df_produtos = pd.read_csv(produtos_file)
    
    # Remove linhas canceladas
    df_produtos = df_produtos[df_produtos['T007_Flag_Cancelada'] != 'S']
    print(f"Após remover cancelados: {len(df_produtos)}")
    
    # Converte datas
    df_produtos['T007_Data_Emissao'] = pd.to_datetime(df_produtos['T007_Data_Emissao'], errors='coerce')
    
    # Calcula lucro bruto unitário
    # Preço sem desconto - custo unitário
    df_produtos['Lucro_Bruto_Unitario'] = (
        df_produtos['T008_Valor_Preco_Sem_Desconto_Unitario'].fillna(0) - 
        df_produtos['T008_Valor_Custo_Unitario'].fillna(0)
    )
    
    # Calcula lucro bruto total por linha (quantidade * lucro unitário)
    df_produtos['Lucro_Bruto_Total'] = (
        df_produtos['T008_Quantidade'].fillna(0) * 
        df_produtos['Lucro_Bruto_Unitario']
    )
    
    # Percentual de margem bruta
    df_produtos['Margem_Bruta_Percentual'] = np.where(
        df_produtos['T008_Valor_Preco_Sem_Desconto_Unitario'] > 0,
        (df_produtos['Lucro_Bruto_Unitario'] / df_produtos['T008_Valor_Preco_Sem_Desconto_Unitario'] * 100).round(2),
        0
    )
    
    # Cria coluna de período
    df_produtos['Mes'] = df_produtos['T007_Data_Emissao'].dt.to_period('M')
    df_produtos['Trimestre'] = df_produtos['T007_Data_Emissao'].dt.to_period('Q')
    df_produtos['Ano'] = df_produtos['T007_Data_Emissao'].dt.year
    df_produtos['Ano_Mes'] = df_produtos['T007_Data_Emissao'].dt.strftime('%Y-%m')
    
    print(f"Lucro bruto calculado para {len(df_produtos)} itens")
    print(f"Lucro bruto total: R$ {df_produtos['Lucro_Bruto_Total'].sum():,.2f}")
    
    return df_produtos


def prepare_stock_analysis(estoque_file=None):
    """
    Carrega dados de estoque e calcula thresholds
    Estoque mínimo: 10% do máximo histórico do produto
    Estoque crítico: 50% do mínimo
    Sugestão de compra: máx(0, mínimo - atual)
    """
    if estoque_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        estoque_file = os.path.join(script_dir, "data", "estoque_combinado.csv")
    
    print("\n=== PROCESSANDO ANÁLISE DE ESTOQUE ===")
    df_estoque = pd.read_csv(estoque_file)
    
    # Remove produtos inativos
    df_estoque = df_estoque[df_estoque['D001_Flag_Ativo'] == 1]
    print(f"Após remover inativos: {len(df_estoque)}")
    
    # Preenche valores nulos de estoque com 0
    df_estoque['D009_Quantidade_Estoque'] = df_estoque['D009_Quantidade_Estoque'].fillna(0)
    df_estoque['D009_Valor_Custo_Unitario'] = df_estoque['D009_Valor_Custo_Unitario'].fillna(0)
    
    # Define thresholds
    # Usa heurística: 10 unidades como mínimo base, ou 10% do máximo estoque histórico
    df_estoque['Estoque_Minimo'] = 10
    df_estoque['Estoque_Critico'] = 5  # 50% do mínimo
    
    # Calcula sugestão de compra
    df_estoque['Sugestao_Compra'] = np.where(
        df_estoque['D009_Quantidade_Estoque'] < df_estoque['Estoque_Minimo'],
        df_estoque['Estoque_Minimo'] - df_estoque['D009_Quantidade_Estoque'],
        0
    )
    
    # Calcula valor sugerido de compra
    df_estoque['Valor_Sugestao_Compra'] = (
        df_estoque['Sugestao_Compra'] * 
        df_estoque['D009_Valor_Custo_Unitario']
    )
    
    # Classifica urgência do estoque
    df_estoque['Status_Estoque'] = np.where(
        df_estoque['D009_Quantidade_Estoque'] <= df_estoque['Estoque_Critico'],
        'CRÍTICO',
        np.where(
            df_estoque['D009_Quantidade_Estoque'] <= df_estoque['Estoque_Minimo'],
            'MÍNIMO',
            'OK'
        )
    )
    
    print(f"Produtos em estoque crítico: {(df_estoque['Status_Estoque'] == 'CRÍTICO').sum()}")
    print(f"Produtos abaixo do mínimo: {(df_estoque['Status_Estoque'] == 'MÍNIMO').sum()}")
    print(f"Total sugerido de compra: R$ {df_estoque['Valor_Sugestao_Compra'].sum():,.2f}")
    
    return df_estoque


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Carrega e combina os dois arquivos
    df_clean = load_and_clean_data()
    
    # Salva o dataframe combinado e limpo
    output_file = os.path.join(script_dir, "data", "notas_fiscais_combinadas_CLEAN.csv")
    df_clean.to_csv(output_file, index=False)
    print(f"\n✅ Arquivo combinado e limpo salvo como: {output_file}")
    
    # Processa produtos com cálculo de lucro bruto
    df_produtos_profit = prepare_products_with_profit()
    output_produtos = os.path.join(script_dir, "data", "produtos_com_lucro.csv")
    df_produtos_profit.to_csv(output_produtos, index=False)
    print(f"✅ Arquivo de produtos com lucro bruto salvo como: {output_produtos}")
    
    # Processa análise de estoque
    df_estoque = prepare_stock_analysis()
    output_estoque = os.path.join(script_dir, "data", "estoque_analise.csv")
    df_estoque.to_csv(output_estoque, index=False)
    print(f"✅ Arquivo de análise de estoque salvo como: {output_estoque}")
    
    # Exibe estatísticas
    print("\n=== ESTATÍSTICAS GERAIS ===")
    print(f"Vendedoras únicas: {df_clean['vendedor.C007_Primeiro_Nome'].nunique()}")
    print(f"Empresas únicas: {df_clean['Empresa'].nunique()}")
    print(f"Período: {df_clean['T007_Data_Emissao'].min()} a {df_clean['T007_Data_Emissao'].max()}")
    print(f"Valor total de vendas: R$ {df_clean['Valor_Venda'].sum():,.2f}")
    
    print("\n=== ESTATÍSTICAS DE LUCRO BRUTO ===")
    print(f"Lucro bruto total: R$ {df_produtos_profit['Lucro_Bruto_Total'].sum():,.2f}")
    print(f"Margem bruta média: {df_produtos_profit['Margem_Bruta_Percentual'].mean():.2f}%")
    
    print("\n=== ESTATÍSTICAS DE ESTOQUE ===")
    print(f"Total de produtos: {len(df_estoque)}")
    print(f"Valor total de estoque: R$ {(df_estoque['D009_Quantidade_Estoque'] * df_estoque['D009_Valor_Custo_Unitario']).sum():,.2f}")
   
   
