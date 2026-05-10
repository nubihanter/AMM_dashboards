import pandas as pd
import numpy as np

empresas = [
    "AMM EPIS",
    "AMM Solucoes"]

df_combinado = pd.DataFrame()
for empresa in empresas:
    df = pd.read_csv(f'notas_fiscais_{empresa.replace(" ", "_")}.csv')
    df["Empresa"] = empresa
    if df_combinado.empty:
        df_combinado = df
    else:
        df_combinado = pd.concat([df_combinado, df], ignore_index=True)
print(np.sum(df_combinado["T007_Valor_Total_Produtos"]))
df_combinado.to_excel("notas_fiscais_combinadas.xlsx", index=False)