"""
Realiza a chamada do framework stackspot utilizando o agente construct-cost-ai-lpu-embeddings

Esse agente tem o objetivo:

1) Receber um item da LPU -> Enriquecer com informações para tornar mais preciso a execução do match contextual de engenharia civil.

Usaremos esse agente principalmente para:
- No módulo de validador Não LPU, quando um item não encontrar match na base de LPU, o agente será acionado para tentar encontrar um match contextual utilizando embeddings.

"""

__author__ = "Emerson V. Rafael (emervin)"
__copyright__ = "Verificador Inteligente de Orçamentos de Obras"
__credits__ = ["Emerson V. Rafael", "Clarissa Simoyama"]
__license__ = "MIT"
__version__ = "1.0.0"
__maintainer__ = "Emerson V. Rafael (emervin), Clarissa Simoyama (simoyam)"
__squad__ = "DataCraft"
__email__ = "emersonssmile@gmail.com"
__status__ = "Development"

import sys
from pathlib import Path

# Adicionar src ao path
base_dir = Path(__file__).parents[3]
sys.path.insert(0, str(Path(base_dir, "src")))

from utils.frameworks.stackspot.src.agents.chat import AgentChat
from utils.frameworks.stackspot.src.models.chat_session import ChatSession

if __name__ == "__main__":
    
    agent_id = "01KFJ78NYVJSY8YS5A681Q5XT5"
    realm = "stackspot-freemium"
    client_id = "5ebf7401-29fc-494c-b7e4-ec59f2518077"
    client_secret = "7ty3d1ef3bhbj6k6Dq5Ez14xa7x6vCSK6xKkVSYkaDCbEQ788ut2C4CPq5Pg6i9p"
    auth_url = "https://idm.stackspot.com/stackspot-freemium/oidc/oauth/token"
    base_url = "https://genai-inference-app.stackspot.com/v1/agent/01K950EYCETA9KX9XBMNNAHE49"
    chat_endpoint = "chat"

    # Executa o agente desejado
    session = ChatSession()

    # Initialize chat with agent
    chat = AgentChat(
        agent_id=agent_id,
        realm=realm,
        client_id=client_id,
        client_secret=client_secret,
        auth_url=auth_url,
        base_url=base_url,
        chat_endpoint=chat_endpoint,
    )