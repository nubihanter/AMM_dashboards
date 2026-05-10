import pandas as pd
import numpy as np
from datetime import datetime
import os

def load_and_clean_data(file_epis="notas_fiscais_AMM_EPIS.csv", file_solucoes="notas_fiscais_AMM_Solucoes.csv"):
    """
    Carrega, combina e limpa os arquivos CSVs de notas fiscais
    """
    # Carrega ambos os arquivos
    print("Carregando arquivos...")
    df_epis = pd.read_csv(file_epis)
    df_solucoes = pd.read_csv(file_solucoes)
    
    print(f"EPIS - Registros iniciais: {len(df_epis)}")
    print(f"SOLUCOES - Registros iniciais: {len(df_solucoes)}")
    
    # Combina os dataframes
    df = pd.concat([df_epis, df_solucoes], ignore_index=True)
    print(f"Total combinado: {len(df)}")
    
    # 1. Remove status "Pendente"
    df = df[df['T007_Numero_Protocolo_Nfe'].notna()]
    
    # # 2. Remove linhas com Data_Envio_XML zerada (0000-00-00)
    # df = df[df['Data_Envio_XML'] != '0000-00-00 00:00:00']
    # print(f"Após remover Data_Envio_XML zerada: {len(df)}")
    
    # 3. Mantém apenas T007_Flag_Cancelada = "N"
    df = df[df['T007_Flag_Cancelada'] == 'N']
    print(f"Após filtrar T007_Flag_Cancelada='N': {len(df)}")
    
    # 4. Converte datas para datetime
    df['T007_Data_Emissao'] = pd.to_datetime(df['T007_Data_Emissao'], errors='coerce')
    df['Data_Envio_XML']    = pd.to_datetime(df['Data_Envio_XML'], errors='coerce')
    
    # 5. Preenche vendedores faltando com o último vendedor que vendeu para essa empresa
    # Ordena por empresa e data para encontrar o último vendedor
    df = df.sort_values(['D024_Id', 'T007_Data_Emissao'])
    
    # Para cada empresa (D024_Id), preenche vendedores vazios com o último vendedor válido
    for company_id in df['D024_Id'].unique():
        mask = df['D024_Id'] == company_id
        company_df = df[mask].copy()
        
        # Encontra o último vendedor válido para essa empresa
        valid_sellers = company_df[company_df['vendedor.C007_Primeiro_Nome'].notna()]['vendedor.C007_Primeiro_Nome']
        
        if len(valid_sellers) > 0:
            last_seller = valid_sellers.iloc[-1]
            # Preenche os nulos com o último vendedor
            df.loc[mask, 'vendedor.C007_Primeiro_Nome'] = df.loc[mask, 'vendedor.C007_Primeiro_Nome'].fillna(last_seller)
    
    # 6. Usa nome fantasia quando disponível, senão usa nome da empresa
    df['Empresa'] = df['D024_Nome_Fantasia'].fillna(df['D024_Nome_Empresa'])
    
    # 7. Remove linhas sem vendedor após preenchimento
    df['vendedor.C007_Primeiro_Nome'] = df['vendedor.C007_Primeiro_Nome'].fillna('Desconhecido')
    
    print(f"Após preencher vendedores: {len(df)}")
    
    # 8. Cria coluna de mês e trimestre para agrupamentos
    df['Mes'] = df['T007_Data_Emissao'].dt.to_period('M')
    df['Trimestre'] = df['T007_Data_Emissao'].dt.to_period('Q')
    df['Ano'] = df['T007_Data_Emissao'].dt.year
    df['Ano_Mes'] = df['T007_Data_Emissao'].dt.strftime('%Y-%m')
    
    # Usa T007_Valor_Total_Produtos para análise de vendas
    df['Valor_Venda'] = df['T007_Valor_Total_Produtos'].fillna(0)
    
    print(f"Registros finais após limpeza: {len(df)}")
    
    return df


def get_monthly_sales(df):
    """Agrupa vendas por mês"""
    return df.groupby(['Ano_Mes', 'vendedor.C007_Primeiro_Nome'])['Valor_Venda'].sum().reset_index()


def get_quarterly_sales(df):
    """Agrupa vendas por trimestre"""
    df_temp = df.copy()
    df_temp['Trimestre_str'] = df_temp['Trimestre'].astype(str)
    return df_temp.groupby(['Trimestre_str', 'vendedor.C007_Primeiro_Nome'])['Valor_Venda'].sum().reset_index()


def get_annual_sales(df):
    """Agrupa vendas por ano"""
    return df.groupby(['Ano', 'vendedor.C007_Primeiro_Nome'])['Valor_Venda'].sum().reset_index()


if __name__ == "__main__":
    # Carrega e combina os dois arquivos
    df_clean = load_and_clean_data(
        file_epis="notas_fiscais_AMM_EPIS.csv",
        file_solucoes="notas_fiscais_AMM_Solucoes.csv"
    )
    
    # Salva o dataframe combinado e limpo
    output_file = "notas_fiscais_COMBINADAS_CLEAN.csv"
    df_clean.to_csv(output_file, index=False)
    print(f"\n✅ Arquivo combinado e limpo salvo como: {output_file}")
    
    # Exibe estatísticas
    print("\n=== ESTATÍSTICAS GERAIS ===")
    print(f"Vendedoras únicas: {df_clean['vendedor.C007_Primeiro_Nome'].nunique()}")
    print(f"Empresas únicas: {df_clean['Empresa'].nunique()}")
    print(f"Período: {df_clean['T007_Data_Emissao'].min()} a {df_clean['T007_Data_Emissao'].max()}")
    print(f"Valor total de vendas: R$ {df_clean['Valor_Venda'].sum():,.2f}")
   
