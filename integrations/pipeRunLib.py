import requests
import os
import sys
from pathlib import Path

# Adiciona o diretório pai ao sys.path para importar config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    PIPERUN_API_BASE_URL,
    PIPERUN_TOKEN,
    PIPERUN_EMAIL,
    PIPERUN_SENHA
)


class PipeRunAPI:
    def __init__(self):
        self.base_url = PIPERUN_API_BASE_URL
        self.headers = {
            "token": PIPERUN_TOKEN,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def _get(self, endpoint, params=None):
        """Método auxiliar para requisições GET"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params)
        return self._handle_response(response)

    def _handle_response(self, response):
        """Trata erros comuns de API"""
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Token inválido ou expirado."}
        else:
            return {"error": f"Erro {response.status_code}", "message": response.text}

    def get_me(self):
        """Retorna informações do usuário autenticado (seu cURL)"""
        return self._get("me")

    def get_deals(self):
        """Exemplo: Busca todos os negócios (deals)"""
        return self._get("deals")

    def get_proposals(self):
        """Exemplo: Busca propostas"""
        return self._get("proposals")

    def get_users(self):
        """Exemplo: Busca usuários do PipeRun"""
        return self._get("users/")

    def get_goals(self,user_id=None,show = 50):
        """Exemplo: Busca metas avançadas"""
        params = {"user_id": user_id} if user_id else {}
        params["show"] = show
        return self._get("advanced-goals/", params=params)
    
    def get_goal_details(self, goal_id):
        """Exemplo: Busca detalhes de uma meta específica"""
        params = {"with": "items"}
        return self._get(f"advanced-goals/{goal_id}", params=params)
    
    def get_goal_stats(self, goal_id):
        """Busca estatísticas e valores de uma meta"""
        return self._get(f"advanced-goals/{goal_id}/stats")
    
    def get_goal_value_by_user(self, goal_id, user_id):
        """Busca valor da meta para um usuário específico"""
        # Tenta primeiro endpoint de valores
        values = self.get_goal_values(goal_id, user_id)
        if values.get("data"):
            return values
        
        # Se não funcionar, tenta buscar metas do usuário
        goals = self.get_goals(user_id=user_id, show=100)
        for goal in goals.get("data", []):
            if goal["id"] == goal_id:
                return {"data": goal}
        
        return None
    
    def get_user_goals_with_values(self, user_id):
        """Busca metas com valores de um usuário específico"""
        endpoints = [
            f"users/{user_id}/goals",
            f"users/{user_id}/advanced-goals",
            f"users/{user_id}/goals-with-values",
        ]
        
        for endpoint in endpoints:
            result = self._get(endpoint)
            if not result.get("error"):
                return {"endpoint": endpoint, "data": result}
        
        return {"error": "Nenhum endpoint funcionou", "endpoints_testados": endpoints}
    
if __name__ == "__main__":
    import datetime
    import json
    api = PipeRunAPI()
    
    user_id = 98148
    print(f"\n=== Testando endpoint /stats para usuário ID: {user_id} ===\n")
    
    # Buscar metas do usuário
    print(f"📌 Buscando metas do usuário {user_id}...")
    user_goals = api.get_goals(user_id=user_id, show=100)
    print(f"Total de metas para esse usuário: {len(user_goals.get('data', []))}\n")
    
    if user_goals.get("data"):
        for idx, goal in enumerate(user_goals["data"][:3]):  # Testa as 3 primeiras metas
            goal_id = goal["id"]
            goal_title = goal.get("title", "N/A")
            
            print(f"{'='*60}")
            print(f"Meta #{idx+1}: {goal_title} (ID: {goal_id})")
            print(f"{'='*60}")
            
            # Teste do endpoint /stats
            print(f"📊 Testando /advanced-goals/{goal_id}/stats...\n")
            stats = api.get_goal_stats(goal_id)
            
            if not stats.get("error"):
                print("✓ SUCESSO! Resposta do endpoint /stats:")
                print(json.dumps(stats, indent=2, ensure_ascii=False))
                
                # Procurar 'value' ou valores numéricos
                print("\n📍 Procurando valores numéricos na resposta:")
                def find_values(obj, depth=0, max_depth=4):
                    if depth > max_depth:
                        return
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, (int, float)) and value > 0:
                                print(f"  {'  '*depth}✓ {key}: {value}")
                            if isinstance(value, (dict, list)):
                                find_values(value, depth + 1, max_depth)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_values(item, depth + 1, max_depth)
                
                find_values(stats)
            else:
                print(f"❌ Erro: {stats.get('error')}")
                print(f"   Mensagem: {stats.get('message')}\n")
    
    print(f"\n{'='*60}")
    print("✅ Teste concluído!")
