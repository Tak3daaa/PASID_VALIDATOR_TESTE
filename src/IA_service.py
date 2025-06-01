from decouple import config
from groq import Groq, RateLimitError, APIConnectionError, APIStatusError
import time
import random # Para adicionar jitter ao delay

GROQ_API_KEY = config("GROQ_API_KEY", default=None)

class IAService:
    def __init__(self):
        if not GROQ_API_KEY:
            print("[IAService] ERRO CRÍTICO: GROQ_API_KEY não definida!")
            raise ValueError("A variável de ambiente GROQ_API_KEY não foi definida.")

        # Desabilita retentativas da biblioteca para controle manual total
        self.client = Groq(
            api_key=GROQ_API_KEY,
            max_retries=0 
        )
        self.model = "llama-3.1-8b-instant"
        print(f"[IAService] Configurado para usar o modelo Groq: '{self.model}' com retentativas manuais.")

    def ask(self, prompt: str, max_manual_retries: int = 5, initial_delay_seconds: float = 5.0) -> str:
        print(f"[IAService] Enviando para Groq (modelo: '{self.model}', prompt com {len(prompt)} chars): '{prompt[:100]}...'")

        for attempt in range(max_manual_retries):
            start_time_attempt = time.time()
            try:
                chat_completion = self.client.chat.completions.create(
                    model=self.model, 
                    messages=[{"role": "user", "content": prompt}]
                    # Considere adicionar um timeout para a requisição da API aqui se suportado
                    # Ex: timeout=60.0 (segundos)
                )
                end_time_attempt = time.time()
                response_content = chat_completion.choices[0].message.content.strip().replace('*', '')
                print(f"[IAService] Resposta da Groq recebida (tentativa {attempt + 1}) em {end_time_attempt - start_time_attempt:.2f}s: '{response_content[:100]}...'")
                return response_content

            except RateLimitError as e:
                end_time_attempt = time.time()
                error_message = e.body.get('error', {}).get('message', str(e)) if hasattr(e, 'body') and e.body else str(e)
                print(f"[IAService] RATE LIMIT da Groq (tentativa {attempt + 1}/{max_manual_retries}) em {end_time_attempt - start_time_attempt:.2f}s: {error_message}")

                if attempt < max_manual_retries - 1:
                    # Backoff exponencial com jitter
                    # Extrai o tempo de espera da mensagem de erro se possível, senão usa backoff
                    # Ex: "Please try again in 1m7.026s."
                    delay_seconds = initial_delay_seconds * (2 ** attempt) + random.uniform(0, 1)

                    # Tenta parsear o 'try again in' da mensagem de erro para um delay mais preciso
                    if "try again in" in error_message:
                        try:
                            time_str = error_message.split("try again in")[1].split(".")[0].strip() # Pega "XmYs" ou "Xs" ou "Xm"
                            parsed_delay = 0
                            if "m" in time_str:
                                parsed_delay += int(time_str.split("m")[0]) * 60
                                if "s" in time_str.split("m")[1]:
                                     parsed_delay += int(time_str.split("m")[1].replace("s",""))
                            elif "s" in time_str:
                                parsed_delay += int(time_str.replace("s",""))

                            if parsed_delay > 0:
                                delay_seconds = parsed_delay + random.uniform(1, 3) # Adiciona pequeno buffer
                                print(f"[IAService] Respeitando delay da API Groq: {delay_seconds:.2f}s")

                        except Exception as parse_ex:
                            print(f"[IAService] Não foi possível parsear o delay da mensagem de erro Groq: {parse_ex}. Usando backoff exponencial padrão.")

                    print(f"[IAService] Próxima tentativa em {delay_seconds:.2f}s...")
                    time.sleep(delay_seconds)
                else:
                    print(f"[IAService] Máximo de {max_manual_retries} tentativas manuais excedido para rate limit.")
                    return f"Erro: Limite de taxa da Groq excedido após {max_manual_retries} tentativas. {error_message}"

            except (APIConnectionError, APIStatusError) as e:
                end_time_attempt = time.time()
                status_code_info = f" (status: {e.status_code})" if hasattr(e, 'status_code') else ""
                print(f"[IAService] ERRO DE API/CONEXÃO da Groq{status_code_info} (tentativa {attempt + 1}/{max_manual_retries}) em {end_time_attempt - start_time_attempt:.2f}s: {e}")
                # Para esses erros, um backoff mais curto pode ser apropriado se forem transientes
                if attempt < max_manual_retries - 1:
                    delay_seconds = initial_delay_seconds * (2 ** attempt) / 2 + random.uniform(0, 1) # Backoff mais curto
                    print(f"[IAService] Próxima tentativa em {delay_seconds:.2f}s...")
                    time.sleep(delay_seconds)
                else:
                    print(f"[IAService] Máximo de {max_manual_retries} tentativas manuais excedido para erro de API/Conexão.")
                    return f"Erro de API/Conexão com a Groq após {max_manual_retries} tentativas: {str(e)}"

            except Exception as e:
                end_time_attempt = time.time()
                print(f"[IAService] ERRO INESPERADO (tentativa {attempt + 1}/{max_manual_retries}) em {end_time_attempt - start_time_attempt:.2f}s: {type(e).__name__} - {e}")
                # Para erros inesperados, pode não fazer sentido tentar novamente muitas vezes
                if attempt < 1 : # Tenta apenas mais uma vez para erro totalmente inesperado
                     delay_seconds = initial_delay_seconds + random.uniform(0, 1)
                     print(f"[IAService] Próxima tentativa em {delay_seconds:.2f}s...")
                     time.sleep(delay_seconds)
                else:
                    return f"Erro inesperado ao processar com a Groq: {str(e)}"

        # Se o loop terminar sem retornar, todas as tentativas falharam
        return f"Erro: Falha ao obter resposta da Groq após {max_manual_retries} tentativas manuais."