import json
import os
from integrations.pipeRunLib import PipeRunAPI


def export_goals_by_seller():
    api = PipeRunAPI()
    
    print("\n" + "="*70)
    print("🚀 EXPORTANDO METAS POR VENDEDOR")
    print("="*70 + "\n")
    
    # Passo 1: Buscar todos os usuários para mapear ID -> Nome
    print("📌 Passo 1: Buscando todos os usuários...")
    users_response = api.get_users()
    users_map = {}
    if users_response.get("data"):
        for user in users_response["data"]:
            users_map[user["id"]] = user.get("name", f"Usuário {user['id']}")
        print(f"✓ {len(users_map)} usuários carregados\n")
    else:
        print("❌ Erro ao buscar usuários\n")
    
    # Passo 2: Buscar todas as metas
    print("📌 Passo 2: Buscando todas as metas cadastradas...")
    all_goals = api.get_goals(show=100)
    goals_list = all_goals.get("data", [])
    print(f"✓ {len(goals_list)} metas encontradas\n")
    
    # Passo 3: Processar cada meta e extrair dados dos vendedores
    print("📌 Passo 3: Processando dados de cada meta...")
    
    # Estrutura: {user_id: {nome, metas: [{...}]}}
    users_data = {}
    total_processed = 0
    
    for idx, goal in enumerate(goals_list, 1):
        goal_id = goal["id"]
        goal_title = goal.get("title", "N/A")
        start_date = goal.get("start_at", "N/A")
        end_date = goal.get("end_at", "N/A")
        
        # Buscar stats da meta
        stats = api.get_goal_stats(goal_id)
        
        if stats.get("data") and stats["data"].get("processed"):
            processed = stats["data"]["processed"]
            
            for item in processed:
                by_user = item.get("byUser", {})
                user_id = by_user.get("user_id")
                valor = by_user.get("value", "0")
                
                if user_id:
                    user_name = users_map.get(user_id, f"Usuário {user_id}")
                    
                    # Adicionar ao dicionário
                    if user_id not in users_data:
                        users_data[user_id] = {"nome": user_name, "metas": []}
                    
                    users_data[user_id]["metas"].append({
                        "goal_id": goal_id,
                        "goal_title": goal_title,
                        "data_inicio": start_date,
                        "data_fim": end_date,
                        "valor": float(valor) if valor else 0.0
                    })
                    
                    total_processed += 1
        
        # Mostrar progresso
        if idx % 10 == 0:
            print(f"  Processadas {idx}/{len(goals_list)} metas...")
    
    print(f"✓ {total_processed} registros de metas processados\n")
    
    # Passo 4: Agregar dados por vendedor único
    print("📌 Passo 4: Agregando dados por vendedor único...")
    
    export_data = []
    total_vendedores = 0
    
    for user_id, data in sorted(users_data.items()):
        vendedor_entry = {
            "user_id": user_id,
            "nome": data["nome"],
            "total_metas": len(data["metas"]),
            "valor_total": sum(m["valor"] for m in data["metas"]),
            "metas": data["metas"]
        }
        export_data.append(vendedor_entry)
        total_vendedores += 1
    
    print(f"✓ {total_vendedores} vendedores únicos encontrados\n")
    
    # Passo 5: Exportar para JSON
    print("📌 Passo 5: Exportando para JSON...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "data", "metas_por_vendedores.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Arquivo '{output_file}' criado com sucesso!\n")
    
    # Passo 6: Mostrar resumo
    print("="*70)
    print("📊 RESUMO DA EXPORTAÇÃO")
    print("="*70)
    print(f"Total de vendedores únicos: {total_vendedores}")
    print(f"Total de registros de metas: {total_processed}")
    print(f"Valor total de todas as metas: R$ {sum(e['valor_total'] for e in export_data):,.2f}")
    print("="*70 + "\n")
    
    # Mostrar top 5 vendedores por valor
    print("🏆 TOP 5 VENDEDORES POR VALOR TOTAL:")
    top_5 = sorted(export_data, key=lambda x: x["valor_total"], reverse=True)[:5]
    for idx, vendor in enumerate(top_5, 1):
        print(f"  {idx}. {vendor['nome']}: R$ {vendor['valor_total']:,.2f} ({vendor['total_metas']} metas)")
    print()
