# src/IA_service.py
from ollama import ChatResponse, Client

class IAService:
    
    def __init__(self, model_name: str = "llama3"): # Chave amigável default pode ser "llama3"
        # IMPORTANTE: Os VALORES neste dicionario devem ser os NOMES/TAGS EXATOS 
        # que aparecem no 'ollama list' apos o pull bem-sucedido.
        self.available_models_map = {
            "llama3": "llama3:latest",  # Assumindo que 'ollama pull llama3' resulta em 'llama3:latest'
                                        # Se 'ollama list' mostrar apenas 'llama3', use 'llama3' aqui.
            "deepseek-llm-7b": "deepseek-llm:7b" # Este deve ser o nome exato como no Ollama Hub e no pull
        }
        
        self.model_key_used = model_name # O nome amigável passado (ex: "llama3" ou "deepseek-llm-7b-chat")
        
        if model_name in self.available_models_map:
            self.model_ollama_tag = self.available_models_map[model_name] # O nome/tag exato para o Ollama
            print(f"[IAService] Configurado para usar a chave '{model_name}', que mapeia para o modelo Ollama: '{self.model_ollama_tag}'")
        else:
            default_key = "llama3" 
            if default_key in self.available_models_map:
                 self.model_ollama_tag = self.available_models_map[default_key]
                 print(f"[IAService] ATENCAO: Chave de modelo '{model_name}' nao reconhecida no mapeamento. Usando default '{default_key}' -> '{self.model_ollama_tag}'.")
                 self.model_key_used = default_key
            else:
                self.model_ollama_tag = model_name # Tenta usar o nome diretamente se nao estiver no mapa e o default tambem nao
                print(f"[IAService] ERRO CRITICO: Chave de modelo '{model_name}' E a chave default '{default_key}' nao encontradas no mapeamento 'available_models_map'.")
                print(f"[IAService] Tentando usar '{model_name}' diretamente. Verifique a configuracao e os nomes dos modelos no Ollama.")


        self.client = Client(host="http://ollama:11434")
        
        try:
            server_models_info = self.client.list() 
            print(f"[IAService] Conectado ao Ollama. Verificando modelo Ollama '{self.model_ollama_tag}'...")
            models_on_server = server_models_info.get('models', [])
            
            model_found = any(m.get('name') == self.model_ollama_tag for m in models_on_server)
            
            if not model_found:
                 print(f"[IAService] ATENCAO: Modelo Ollama '{self.model_ollama_tag}' (da chave '{self.model_key_used}') NAO FOI ENCONTRADO na lista do servidor Ollama.")
                 print(f"[IAService] Modelos disponiveis no servidor: {[m.get('name') for m in models_on_server]}")
                 print(f"[IAService] Certifique-se que o modelo foi baixado ('pulled') corretamente e o nome/tag em 'available_models_map' esta exato.")
            else:
                print(f"[IAService] Modelo Ollama '{self.model_ollama_tag}' parece estar disponivel no servidor.")

        except Exception as e:
            print(f"[IAService] ERRO ao conectar ou listar modelos do Ollama: {e}")
            print("[IAService] O servico de IA pode nao funcionar.")

    def ask(self, prompt: str) -> str:
        if not prompt:
            return "Erro: Prompt vazio fornecido ao servico de IA."
        try:
            print(f"[IAService] Enviando prompt para o modelo Ollama '{self.model_ollama_tag}': '{prompt[:50]}...'")
            ia_response: ChatResponse = self.client.chat(
                model=self.model_ollama_tag, 
                messages=[{"role": "user", "content": prompt}]
            )
            response_content = ia_response.message.content
            print(f"[IAService] Resposta recebida do modelo Ollama '{self.model_ollama_tag}': '{response_content[:50]}...'")
            return response_content
        except Exception as e:
            error_message = f"{e}" 
            print(f"[IAService] ERRO ao chamar o modelo de IA '{self.model_ollama_tag}': {error_message}")
            return f"Erro ao processar com IA: {error_message}"