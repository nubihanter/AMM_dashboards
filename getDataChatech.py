from integrations.chatechLib import HardnessAPI
import pandas as pd

def _remove_duplicates(df,subset, ultima_data):
    # 1. Garantir que a coluna está em formato datetime
    df['T007_Data_Emissao'] = pd.to_datetime(df['T007_Data_Emissao'], errors='coerce')
    # 2. Separar o DataFrame em dois: Histórico (antigo) e Novos (para processar)
    # Filtro: Data maior ou igual à última data conhecida
    mask_novos = df['T007_Data_Emissao'] >= ultima_data
    
    df_historico = df[~mask_novos].copy()
    df_novos = df[mask_novos].copy()
    print(df_novos)

    # 3. Aplicar a remoção de duplicatas APENAS no bloco de dados novos
    # Aqui ele remove duplicatas dentro dos novos e também o que for repetido em relação ao ID/Empresa
    df_novos.drop_duplicates(inplace=True,subset=subset,keep='first')

    # 4. Concatenar os dois blocos de volta
    df_final = pd.concat([df_historico, df_novos], ignore_index=True)
# =================================================================
    # 5. O PASSO QUE FALTAVA: A Varredura Final
    # Garante que nada que entrou no df_novos já existia no df_historico.
    # Como o histórico entrou primeiro no concat, o keep='first' mantém
    # a versão mais antiga e apaga a nova intrusa.
    # =================================================================
    df_final.drop_duplicates(subset=subset, inplace=True, keep='first')

    # 5. Ordenação final
    df_final.sort_values('T007_Data_Emissao', inplace=True)

    return df_final

def get_raw_data(empresas_list= ["AMM EPIS", "AMM Solucoes"], produtos = True, notas_fiscais = True, append=True):
    api = HardnessAPI()
    api.login()

    if append:
        try:
            df_produtos = pd.read_csv("data/produtos_combinados.csv")
            df_produtos['T007_Data_Emissao'] = pd.to_datetime(df_produtos['T007_Data_Emissao'], errors='coerce')
            ultima_data_produtos = df_produtos['T007_Data_Emissao'].max() if 'T007_Data_Emissao' in df_produtos.columns else ''
            print(f"✓ Arquivo existente de produtos carregado: {len(df_produtos)} registros. Última data de atualização: {ultima_data_produtos}")
        except FileNotFoundError:
            print("⚠️ Arquivos existentes não encontrados. Criando novos DataFrames.")
            df_produtos = pd.DataFrame()
        try:
            df_notas_fiscais = pd.read_csv("data/notas_fiscais_combinadas.csv")
            df_notas_fiscais['T007_Data_Emissao'] = pd.to_datetime(df_notas_fiscais['T007_Data_Emissao'], errors='coerce')
            ultima_data_notas_fiscais = df_notas_fiscais['T007_Data_Emissao'].max() if 'T007_Data_Emissao' in df_notas_fiscais.columns else ''
            print(f"✓ Arquivos existentes carregados: {len(df_produtos)} produtos e {len(df_notas_fiscais)} notas fiscais. Última data de atualização: {ultima_data_notas_fiscais}")
        except FileNotFoundError:
            df_notas_fiscais = pd.DataFrame()
    else:
        ultima_data_produtos = ''
        ultima_data_notas_fiscais = ''
        if produtos:
            df_produtos = pd.DataFrame()
        else:
            df_produtos = None

        if notas_fiscais:
            df_notas_fiscais = pd.DataFrame()
        else:
            df_notas_fiscais = None

    for empresa in empresas_list:
        empresa_id = api.empresas_dict.get(empresa, {}).get("id_sistema")
        if empresa_id:
            api.trocar_empresa(empresa_id)
        else:
            print(f"⚠️ Empresa '{empresa}' não encontrada no dicionário. Verifique o nome e tente novamente.")
            continue
        print(f"✅ Empresa '{empresa}' selecionada para extração de dados.")

        if produtos:
            print(f"📊 Extraindo dados de produtos para '{empresa}'...")
            api.filtrar(url=api.produtos_url,data_inicio=ultima_data_produtos.strftime("%Y-%m-%d") if append else "")
            produtos_data = api.get_dados(api.produtos_url)
            df_produtos_empresa = pd.DataFrame(produtos_data)
            df_produtos_empresa["Empresa"] = empresa
            if df_produtos.empty:
                df_produtos = df_produtos_empresa
            else:
                df_produtos = pd.concat([df_produtos, df_produtos_empresa], ignore_index=True)
            print(f"✓ Produtos extraídos para '{empresa}': {len(df_produtos_empresa)} registros.")
        if notas_fiscais:
            print(f"📊 Extraindo dados de notas fiscais para '{empresa}'...")
            api.filtrar(url=api.notafiscal_url,data_inicio=ultima_data_notas_fiscais.strftime("%Y-%m-%d") if append else "")
            notas_fiscais_data = api.get_dados(api.notafiscal_url)
            df_notas_fiscais_empresa = pd.DataFrame(notas_fiscais_data)
            df_notas_fiscais_empresa["Empresa"] = empresa
            if df_notas_fiscais.empty:
                df_notas_fiscais = df_notas_fiscais_empresa
            else:
                df_notas_fiscais = pd.concat([df_notas_fiscais, df_notas_fiscais_empresa], ignore_index=True)
            print(f"✓ Notas fiscais extraídas para '{empresa}': {len(df_notas_fiscais_empresa)} registros.")
    
    # Remover duplicatas apenas por T008_Id (para produtos) e T007_Id (para notas), mantendo a primeira ocorrência
    # Isto evita remover linhas legítimas devido a diferenças em formatação de data
    if not df_produtos.empty:
        df_produtos['T008_Id'] = pd.to_numeric(df_produtos['T008_Id'], errors='coerce').astype('Int64')
        df_produtos = _remove_duplicates(df_produtos,subset = ['T008_Id', "Empresa"], ultima_data=ultima_data_produtos)
    if not df_notas_fiscais.empty:
        df_notas_fiscais['T007_Id'] = pd.to_numeric(df_notas_fiscais['T007_Id'], errors='coerce').astype('Int64')
        df_notas_fiscais = _remove_duplicates(df_notas_fiscais,subset=['T007_Id',"Empresa"], ultima_data=ultima_data_notas_fiscais)
    return df_notas_fiscais, df_produtos

def get_estoque():
    api = HardnessAPI()
    api.login()
    print("📊 Extraindo dados de estoque...")
    api.filtrar_estoque()
    df_estoque = api.get_dados_estoque()
    return df_estoque


if __name__ == "__main__":
    # df_notas_fiscais, df_produtos = get_raw_data()
    # df_notas_fiscais.to_csv("data/notas_fiscais_combinadas.csv", index=False)
    # df_produtos.to_csv("data/produtos_combinados.csv", index=False)
    df_estoque = get_estoque()
    df_estoque.to_csv("data/estoque_combinado.csv", index=False)