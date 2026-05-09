import requests
import dotenv
import os
import pandas as pd
from bs4 import BeautifulSoup
import re
import json # Import do json movido para o topo

dotenv.load_dotenv(".env")

dict_empresa = {
    "AMM EPIS": {
        "id_sistema": "1",
        "divs": ["69ff9d5148af1","YToxMTp7aTowO3M6MTM6IjY5ZmY5ZDUxNDhhZjEiO2k6MTtzOjEzOiI2OWZmOWQ1MTI2ODY4IjtpOjI7czoxMzoiNjlmZjlkNGI4MDI3YyI7aTozO3M6MTM6IjY5ZmY5ZDRiODAyN2IiO2k6NDtzOjEzOiI2OWZmOWQ0YjgwMjdhIjtpOjU7czoxMzoiNjlmZjlkNGI4MDI3NiI7aTo2O3M6MTM6IjY5ZmY5ZDRiNWQ5NzciO2k6NztzOjEzOiI2OWZmOWQ0YjM5YzVjIjtpOjg7czoxMzoiNjlmZjlkNGIwYWY2ZSI7aTo5O3M6MTM6IjY5ZmY5ZDRhZGNmZjYiO2k6MTA7czoxMzoiUDV4VXIwRkx4VFVOViI7fQ=="]
    },
    "AMM Solucoes": {
        "id_sistema": "2",
        "divs": ["69ff9df129cbf","YToxMTp7aTowO3M6MTM6IjY5ZmY5ZGYxMjljYmYiO2k6MTtzOjEzOiI2OWZmOWRmMTA3MmNlIjtpOjI7czoxMzoiNjlmZjlkZTg2Mzc5ZSI7aTozO3M6MTM6IjY5ZmY5ZGU4NjM3OWQiO2k6NDtzOjEzOiI2OWZmOWRlODYzNzljIjtpOjU7czoxMzoiNjlmZjlkZTg2Mzc5OCI7aTo2O3M6MTM6IjY5ZmY5ZGU4MmUzOTgiO2k6NztzOjEzOiI2OWZmOWRlODBiMDZjIjtpOjg7czoxMzoiNjlmZjlkZTdkNjQzYSI7aTo5O3M6MTM6IjY5ZmY5ZDRhZGNmZjYiO2k6MTA7czoxMzoiUDV4VXIwRkx4VFVOViI7fQ=="]
    }
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "http://amm.chatechs.com.br/erp/"
})

grid_url = "http://amm.chatechs.com.br/crm/crm001/grid/crm001GridPrincipalNotasFiscais/"
url_login = "http://amm.chatechs.com.br/hardness3/outros/login/index.php"

print("Fazendo login no sistema...")
payload_login = {
    "login": os.getenv("LOGIN"),
    "senha": os.getenv("SENHA"),
}
session.post(url_login, data=payload_login)
print("Login efetuado.")

for nome_empresa, dados in dict_empresa.items():
    print(f"\n{'='*40}")
    print(f"🚀 Iniciando processamento para: {nome_empresa}")
    print(f"{'='*40}")

    id_sistema = dados["id_sistema"]
    url_troca_empresa = f"http://amm.chatechs.com.br/empresa/{id_sistema}/"
    
    print(f"🔄 Trocando sessão para a empresa ID {id_sistema}...")
    resposta_troca = session.post(url_troca_empresa) 
    
    if resposta_troca.status_code == 200:
        print("✅ Empresa trocada com sucesso no servidor.")
    else:
        print(f"⚠️ Atenção: A troca de empresa retornou status {resposta_troca.status_code}")

    divid = dados["divs"][0]
    divIdChain = dados["divs"][1]
    
    # Variáveis para a Paginação
    todos_dados_empresa = []
    loading_offset = 0
    pagina = 1

    # Loop infinito que só para quando a página vier vazia
    while True:
        payload_grid = {
            "ajax": "true",
            "divIdRoot": "crm001",
            "divIdParent": "",
            "divId": divid,
            "divIdChain": divIdChain,
            "tab": "geral",
            "gridFiltrado": "true",
            "limit": "5000",
            "limite": "5000",
            "rows": "5000",
            "length": "5000",
            "loading": str(loading_offset) # O parâmetro mágico da paginação!
        }

        print(f"📥 Baixando página {pagina} (A partir da linha {loading_offset})...")
        response = session.post(grid_url, data=payload_grid)
        
        soup = BeautifulSoup(response.text, "html.parser")
        linhas_com_dados = soup.find_all("tr", attrs={"todoscampos": True})

        # CONDIÇÃO DE PARADA: Se não vier nenhuma nota, quebra o while
        if not linhas_com_dados:
            print("🏁 Fim dos dados retornado pelo servidor!")
            break 
        
        print(f"   ✅ Encontradas {len(linhas_com_dados)} notas nesta página.")
        
        # Extrai os dados da página atual
        for linha in linhas_com_dados:
            json_texto = linha.get("todoscampos")
            if json_texto:
                try:
                    dados_linha = json.loads(json_texto)
                    todos_dados_empresa.append(dados_linha)
                except json.JSONDecodeError:
                    continue
        
        # PREPARA PARA A PRÓXIMA PÁGINA
        # Incrementamos o offset com a quantidade de itens que acabamos de receber
        loading_offset += 1
        pagina += 1

    # ==========================================
    # SALVAR OS DADOS DA EMPRESA (Fora do while!)
    # ==========================================
    if todos_dados_empresa:
        df = pd.DataFrame(todos_dados_empresa)
        
        if "excluirLinha" in df.columns:
            df = df.drop(columns=["excluirLinha"])
        
        output_file = f"notas_fiscais_{nome_empresa.replace(' ', '_')}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        
        print(f"\n🎉 CONCLUÍDO! Total de {len(df)} notas da empresa {nome_empresa} salvas!")
        print(f"💾 CSV salvo em: {output_file}")
    else:
        print(f"❌ Nenhuma nota encontrada ou erro na extração para a empresa {nome_empresa}.")