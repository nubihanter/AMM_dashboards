from integrations.chatechLib import HardnessAPI
import pandas as pd

def get_raw_data(empresas_list= ["AMM EPIS", "AMM Solucoes"], produtos = True, notas_fiscais = True, append=True):
    api = HardnessAPI()
    api.login()

    if append:
        try:
            df_produtos = pd.read_csv("produtos_combinados.csv")
            df_produtos['T007_Data_Emissao'] = pd.to_datetime(df_produtos['T007_Data_Emissao'], errors='coerce')
            ultima_data_produtos = df_produtos['T007_Data_Emissao'].max() if 'T007_Data_Emissao' in df_produtos.columns else ''
            print(f"✓ Arquivo existente de produtos carregado: {len(df_produtos)} registros. Última data de atualização: {ultima_data_produtos}")
        except FileNotFoundError:
            print("⚠️ Arquivos existentes não encontrados. Criando novos DataFrames.")
            df_produtos = pd.DataFrame()
        try:
            df_notas_fiscais = pd.read_csv("notas_fiscais_combinadas.csv")
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
        df_produtos['T007_Data_Emissao'] = pd.to_datetime(df_produtos['T007_Data_Emissao'], errors='coerce')
        df_produtos.drop_duplicates(subset=['T008_Id',"Empresa"], inplace=True)
        df_produtos.sort_values('T007_Data_Emissao', inplace=True)  # Ordena por data de emissão para facilitar análises futurasq
    if not df_notas_fiscais.empty:
        df_notas_fiscais['T007_Data_Emissao'] = pd.to_datetime(df_notas_fiscais['T007_Data_Emissao'], errors='coerce')
        df_notas_fiscais.drop_duplicates(subset=['T007_Id',"Empresa"],inplace=True)
        df_notas_fiscais.sort_values('T007_Data_Emissao', inplace=True)  # Ordena por data de emissão para facilitar análises futuras
    return df_notas_fiscais, df_produtos

if __name__ == "__main__":
    df_notas_fiscais, df_produtos = get_raw_data()
    df_notas_fiscais.to_csv("notas_fiscais_combinadas.csv", index=False)
    df_produtos.to_csv("produtos_combinados.csv", index=False)