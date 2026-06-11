"""
Config Manager para Streamlit Secrets
Funciona tanto localmente (com .env e secrets.toml) quanto na nuvem (Streamlit Cloud)
"""

import os
from typing import Any, Optional

# Tenta importar streamlit - se não conseguir, roda sem ele
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False


def get_secret(key: str, default: Optional[str] = None) -> str:
    """
    Obtém um secret do Streamlit ou do .env
    
    Ordem de busca:
    1. st.secrets (Streamlit) - funciona em local (secrets.toml) e cloud
    2. os.environ (variáveis de ambiente)
    3. valor padrão fornecido
    4. levanta exceção se nenhum valor encontrado e padrão não fornecido
    
    Args:
        key: Nome da chave do secret
        default: Valor padrão se não encontrar
        
    Returns:
        Valor do secret
        
    Raises:
        KeyError: Se a chave não for encontrada e não houver valor padrão
    """
    
    # 1. Tenta Streamlit Secrets (funciona em local + cloud)
    if STREAMLIT_AVAILABLE:
        try:
            return st.secrets[key]
        except (KeyError, AttributeError):
            pass
    
    # 2. Tenta variáveis de ambiente (para compatibilidade com .env)
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value
    
    # 3. Usa valor padrão
    if default is not None:
        return default
    
    # 4. Levanta erro se não encontrou nada
    raise KeyError(f"Secret '{key}' não encontrado em st.secrets, os.environ ou arquivo .env")


def load_env_file():
    """
    Carrega variáveis do arquivo .env para os.environ
    Só é usado quando não está em Streamlit Cloud
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
    except ImportError:
        pass


# Carrega .env no início se não estiver no Streamlit
if not STREAMLIT_AVAILABLE:
    load_env_file()


# ============================================
# Secrets / Configurações
# ============================================

# Hardness (ERP) - Credenciais de Login
HARDNESS_LOGIN = get_secret("LOGIN")
HARDNESS_SENHA = get_secret("SENHA")

# Hardness (ERP) - Configurações Base
HARDNESS_BASE_URL = get_secret("HARDNESS_BASE_URL")
HARDNESS_NOTAFISCAL_GRID_ID = get_secret("HARDNESS_NOTAFISCAL_GRID_ID")
HARDNESS_PRODUTOS_GRID_ID = get_secret("HARDNESS_PRODUTOS_GRID_ID")
HARDNESS_ESTOQUE_GRID_ID = get_secret("HARDNESS_ESTOQUE_GRID_ID")

# PipeRun (CRM) - Credenciais e Token
PIPERUN_API_BASE_URL = get_secret("PIPERUN_API_BASE_URL")
PIPERUN_TOKEN = get_secret("TOKEN_PIPERUN")

# PipeRun - Credenciais (se necessário para login adicional)
PIPERUN_EMAIL = get_secret("EMAIL_PIPERUN")
PIPERUN_SENHA = get_secret("SENHA_PIPERUN")
