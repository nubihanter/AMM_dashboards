import requests
from dotenv import load_dotenv
import os
import re
from bs4 import BeautifulSoup
import pandas as pd
# from streamlit import form
import json
load_dotenv(".env")

class HardnessAPI:
    def __init__(self,verbose=True):
        self.name = "AMM"
        self.empresas_dict ={
                                "AMM EPIS": {
                                    "id_sistema": "1",
                               },
                                "AMM Solucoes": {
                                    "id_sistema": "2",
                               }
                            }
        self.session = requests.Session()
        self.session.headers.update({
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                        "X-Requested-With": "XMLHttpRequest",
                                        "Referer": "http://amm.chatechs.com.br/erp/"
                                    })
        self.base_url = "http://amm.chatechs.com.br"
        self.url_login = self.base_url + "/hardness3/outros/login/index.php"
        self.notafiscal_url = self.base_url + "/crm/crm001/grid/crm001GridPrincipalNotasFiscais/"
        self.produtos_url = self.base_url + "/crm/crm001/grid/crm001gridPrincipalProdutos/"
        self.verbose = verbose
        self.grid_dicts = {
            self.notafiscal_url: "9a4a52124b9ef45ed11c682313457e66",
            self.produtos_url: "417dd51bce34fe83280ebd6b01992a4f"
        }


    def login(self):
        print("Fazendo login no sistema...")
        payload_login = {
            "login": os.getenv("LOGIN"),
            "senha": os.getenv("SENHA"),
        }
        self.session.post(self.url_login, data=payload_login)
        if self.verbose:
            print("Login efetuado.")
    
    def trocar_empresa(self, empresa_id):
        url_troca_empresa = f"{self.base_url}/empresa/{empresa_id}/"
        if self.verbose:
            print(f"🔄 Trocando sessão para a empresa ID {empresa_id}...")
        resposta_troca = self.session.post(url_troca_empresa) 
        verifica_empresa = self.verifica_empresa()

        if verifica_empresa == empresa_id:
            if self.verbose:
                print("✅ Empresa trocada com sucesso no servidor.")
        else:
            input(f"⚠️ Atenção: A troca de empresa retornou status {resposta_troca.status_code}")

    def verifica_empresa(self):
        url = f"{self.base_url}/sistema/funcoes/util/verificaEmpresaAtual/?ajax=true&callback=jQuery16205376931034128021_1778415793103&_=1778415835153"
        resposta = self.session.get(url)
        # Extrai apenas o conteúdo dentro dos parênteses do callback
        match = re.search(r'^[^\(]+\((.*)\);?$', resposta.text)

        if match:
            dado_limpo = match.group(1)
            # Remove as aspas caso o dado venha como string JSON
            dado_limpo = dado_limpo.strip('"') 
            
            if self.verbose:
                print(f"O valor extraído é: {dado_limpo}") # Saída: 1
            return dado_limpo
        else:
            input("⚠️ Atenção: Não foi possível extrair o valor da empresa atual.")
            return None
        
    def filtrar(self, data_inicio="", data_fim="",CFOP="VENDA", cancelada="N",url=None):
        payload ={
            "ajax": "true",
            "divIdRoot": "crm001",
            "tab": "geral",
            # "loading": str(loading_offset) # O parâmetro mágico da paginação!
        }

        self.session.post(url or self.notafiscal_url, data=payload)
        response_pagina = self.session.get(url or self.notafiscal_url, params=payload)
        with open("pagina.html", "w", encoding="utf-8") as f:
            f.write(response_pagina.text)
        
        soup = BeautifulSoup(response_pagina.text, 'html.parser')
        # 2. Encontra o formulário de filtro (ID dinâmico)
        form = soup.select_one('div.gridFiltro form')
        
        if not form:
            print("Formulário de filtro não encontrado!")
            return False
        
        form_id = form['id']
        print(f"Form ID encontrado: {form_id}")

        # 3. Mágica: Descobrir as chaves em Base64 lendo o HTML
        # Vamos criar um dicionário vazio e preencher lendo os inputs ocultos de "-titulo"
        filter_data = {}
        
        for input_tag in form.find_all('input'):
            name = input_tag.get('name', '')
            
            # Ignoramos inputs sem nome
            if not name: continue
            
            # Mapeamento dinâmico pelo título
            if name.endswith('-titulo'):
                titulo = input_tag.get('value', '').lower()
                base64_name = name.replace('-titulo', '') # Remove o '-titulo' para pegar o nome do input real
                
                # Se o titulo for CFOP, preenchemos o valor
                if 'cfop' in titulo:
                    filter_data[base64_name] = CFOP
                # Se for Cancelada, preenchemos o valor
                elif 'cancelada' in titulo:
                    filter_data[base64_name] = cancelada
                    
            # Lidando com o campo de Data (que tem d1 e d2)
            elif name.endswith('-d1') and data_inicio:
                filter_data[name] = data_inicio
            elif name.endswith('-d2') and data_fim:
                filter_data[name] = data_fim

        # 4. Limpa todos os outros campos (opcional, mas recomendado)
        for input_tag in form.find_all(['input', 'select']):
            name = input_tag.get('name')
            if name and name not in filter_data:
                # Mantém só os campos que queremos definir
                if not name.endswith('-titulo') and 'VDAwN19EYXRhX0VtaXNzYW8=' not in name:
                    filter_data[name] = ""
        # 4. Procura o Hash do Grid no Javascript da página
        import re
        grid_hash = ""
        match_grid = re.search(r"encodeURIComponent\('([a-f0-9]{32})'\)", response_pagina.text)
        if match_grid:
            grid_hash = match_grid.group(1)
        else:
            print("Aviso: Não encontrou o hash do grid. O filtro vai falhar.")
            return False

        # 5. Monta o payload final dinamicamente
        post_data = {
            'ajax': 'true',
            'filtroUID': form_id,
            'grid': grid_hash,
        }

        # Adiciona os campos do formulário
        post_data.update(filter_data)

        # 6. Envia o filtro
        filter_url = "/sistema/funcoes/gridFiltro/filtrar/"
        full_url = f"{self.base_url.rstrip('/')}{filter_url}"

        response_filter = self.session.post(full_url, data=post_data)

        if response_filter.status_code == 200:
            print("✅ Filtro aplicado com sucesso!")
            # Recarrega o grid após filtrar
            self.session.get(self.notafiscal_url, params={"ajax": "true"})
            return True
        else:
            print(f"❌ Erro ao aplicar filtro: {response_filter.status_code}")
            print(response_filter.text[:500])
            return False
    
    def get_dados(self,url= None):
        if url is None:
            url = self.notafiscal_url

        # Variáveis para a Paginação
        todos_dados_empresa = []
        loading_offset = 0
        pagina = 0

        # Loop infinito que só para quando a página vier vazia
        while True:
            payload_grid = {
                "ajax": "true",
                "tab": "geral",
                "gridFiltrado": "true",
                "limit": "5000",
                "limite": "5000",
                "rows": "5000",
                "length": "5000",
                # "loading": str(loading_offset) # O parâmetro mágico da paginação!
            }
            if loading_offset > 0:
                payload_grid["loading"] = str(pagina)

            print(f"📥 Baixando página {pagina} (A partir da linha {loading_offset})...")
            response = self.session.post(url, data=payload_grid)
            
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
            loading_offset += len(linhas_com_dados)
            pagina += 1 
        df = pd.DataFrame(todos_dados_empresa)
        
        if "excluirLinha" in df.columns:
            df = df.drop(columns=["excluirLinha"])
        return df

if __name__ == "__main__":
    pass