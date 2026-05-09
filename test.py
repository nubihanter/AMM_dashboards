import requests

def obter_token_api():
    session = requests.Session()
    url_login = "http://amm.chatechs.com.br/hardness3/outros/login/index.php"

    payload = {
        "login": "leticia",
        "senha": "1234",
        # "empresa": "AMM"   # descomente se pedir
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = session.post(url_login, data=payload, headers=headers)

    print("Status:", response.status_code)
    print("URL final:", response.url)

    # Se redirecionou para o sistema, provavelmente logou
    if "sistema" in response.url or response.status_code == 200:
        print("✅ Login parece ter funcionado!")
        
        # Testa uma chamada protegida
        r = session.get("http://amm.chatechs.com.br/sistema/funcoes/util/verificaEmpresaAtual/?ajax=true")
        print("Teste API:", r.text[:500])
    else:
        print("Resposta:", response.text[:1000])


# Executa a função
if __name__ == "__main__":

    meu_token = obter_token_api()


    if meu_token:
        # A partir daqui você pode construir as funções para baixar seus relatórios,
        # passando este 'meu_token' no cabeçalho 'Authorization' das próximas requisições.
        input(f"Pronto para baixar relatórios! na url Token carregado na memória.")


69ff9df129cbf