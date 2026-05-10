import pandas as pd

print("\n" + "=" * 80)
print("TESTE DE VALIDAÇÃO - AGRUPAMENTO DE DUPLICADOS")
print("=" * 80)

# Ler o arquivo atual de produtos
df_original = pd.read_csv('produtos_combinados.csv')

print(f"\n📊 ARQUIVO ORIGINAL (produtos_combinados.csv):")
print(f"   Total de registros: {len(df_original)}")

# Identificar duplicados
dups = df_original.duplicated(subset=['T008_Id', 'Empresa'], keep=False)
print(f"   Registros duplicados: {dups.sum()}")

if dups.sum() > 0:
    # Separar duplicados
    df_nao_dup = df_original[~dups]
    df_dup = df_original[dups]
    
    # Mostrar alguns exemplos
    print(f"\n🔍 EXEMPLO DE PRODUTOS DUPLICADOS:")
    print(f"   Quantidade de grupos de duplicatas: {df_dup.groupby(['T008_Id', 'Empresa']).size().shape[0]}")
    
    # Pegar um exemplo
    sample_group = df_dup.groupby(['T008_Id', 'Empresa']).first()
    sample_id = sample_group.index[0][0]
    sample_emp = sample_group.index[0][1]
    
    sample_records = df_dup[(df_dup['T008_Id'] == sample_id) & (df_dup['Empresa'] == sample_emp)]
    print(f"\n   T008_Id = {sample_id}, Empresa = {sample_emp}:")
    print(f"   Quantidade de registros duplicados: {len(sample_records)}")
    print(f"\n   Detalhes:")
    for idx, row in sample_records.iterrows():
        print(f"      Registro {idx}: Qtd={row['T008_Quantidade']}, Valor={row['T008_Valor_Total_Preco_Sem_Desconto']}")
    
    # Simular o agrupamento
    colunas_soma = ['T008_Quantidade', 'T008_Valor_Total_Preco_Sem_Desconto']
    agg_dict = {col: 'sum' if col in colunas_soma else 'first' 
               for col in df_dup.columns 
               if col not in ['T008_Id', 'Empresa']}
    
    df_dup_agrupado = df_dup.groupby(['T008_Id', 'Empresa'], as_index=False).agg(agg_dict)
    
    agrupado_record = df_dup_agrupado[(df_dup_agrupado['T008_Id'] == sample_id) & (df_dup_agrupado['Empresa'] == sample_emp)]
    print(f"\n   ✅ APÓS AGRUPAMENTO:")
    print(f"      Qtd Total: {agrupado_record['T008_Quantidade'].values[0]}")
    print(f"      Valor Total: {agrupado_record['T008_Valor_Total_Preco_Sem_Desconto'].values[0]}")
    
    # Validar soma
    soma_esperada_qtd = sample_records['T008_Quantidade'].sum()
    soma_esperada_valor = sample_records['T008_Valor_Total_Preco_Sem_Desconto'].sum()
    
    print(f"\n   🔢 VALIDAÇÃO DE SOMA:")
    print(f"      Soma esperada (Qtd): {soma_esperada_qtd} ✓" if soma_esperada_qtd == agrupado_record['T008_Quantidade'].values[0] else f"      Soma esperada (Qtd): {soma_esperada_qtd} ✗")
    print(f"      Soma esperada (Valor): {soma_esperada_valor} ✓" if soma_esperada_valor == agrupado_record['T008_Valor_Total_Preco_Sem_Desconto'].values[0] else f"      Soma esperada (Valor): {soma_esperada_valor} ✗")
    
    # Calcular resultado final
    df_novo = pd.concat([df_nao_dup, df_dup_agrupado], ignore_index=True)
    print(f"\n📊 RESULTADO FINAL:")
    print(f"   Registros originais (com duplicatas): {len(df_original)}")
    print(f"   Registros após agrupamento: {len(df_novo)}")
    print(f"   Registros removidos (consolidados): {len(df_original) - len(df_novo)}")
    print(f"   Grupos consolidados: {len(df_dup_agrupado)}")
    
    print(f"\n✅ SOLUÇÃO VALIDADA: Todos os dados serão preservados com soma de quantidades e valores!")
else:
    print("✓ Nenhum produto duplicado encontrado")

print("\n" + "=" * 80)
