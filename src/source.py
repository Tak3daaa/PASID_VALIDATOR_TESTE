import socket
import threading
import time
from typing import List, Dict, Any

from src.abstract_proxy import AbstractProxy
from src.utils import get_current_timestamp


class Source(AbstractProxy):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config.get("log_file", "log.txt"))
        self.model_feeding_stage: bool = config.get("model_feeding_stage", False)
        self.arrival_delay: int = config.get("arrival_delay", 0)
        self.max_considered_messages_expected: int = config.get("max_considered_messages_expected", 10)
        self.source_current_index_message: int = 0
        # self.considered_messages: List[str] = [] # Não mais usado como acumulador de instância para threads
        # self.response_times: List[float] = [] # Não mais usado como acumulador de instância para threads
        self.qtd_services: List[int] = config.get("qtd_services", [])
        self.cycles_completed: List[bool] = [False] * len(self.qtd_services)
        self.dropp_count: int = 0
        self.loadbalancer_addresses = config.get("loadbalancer_addresses", "")

        self.target_ip: str = config.get("target_ip", "loadbalancer1")
        self.target_port: int = config.get("target_port", 2000)

        print("Loadbalancer addresses:", self.loadbalancer_addresses)
        print("Target IP:", self.target_ip)
        print("Target Port:", self.target_port)

        if isinstance(self.loadbalancer_addresses, str):
            self.loadbalancer_addresses = [
                (address.split(":")[0], int(address.split(":")[1]))
                for address in self.loadbalancer_addresses.split(",")
            ]

    def run(self) -> None:
        self.log("Starting source")
        if self.model_feeding_stage:
            self.send_message_feeding_stage()
        else:
            self.send_messages_validation_stage()

    def send_message_feeding_stage(self) -> None:
        self.log("Model Feeding Stage Started")
        for _ in range(10): # Mantido como 10 para o estágio de alimentação
            msg = f"1;{self.source_current_index_message};{get_current_timestamp()}"
            print("Enviando:", msg)
            self.send(msg) # O método send não usa threads e não afeta as listas de métricas
            self.source_current_index_message += 1
            time.sleep(self.arrival_delay / 1000.0)

    def send_messages_validation_stage(self) -> None:
        for cycle, qts in enumerate(self.qtd_services):
            self.log(f"Iniciando Ciclo {cycle} com {qts} serviços.")
            self.source_current_index_message = 1 # Reinicia índice da mensagem para o ciclo

            # Listas locais para os resultados deste ciclo específico
            current_cycle_response_times: List[float] = []
            current_cycle_considered_messages: List[str] = []
            
            num_balancers = len(self.loadbalancer_addresses)
            start_time_cycle = time.time() # Tempo de início para o ciclo
            
            # Ajuste o timeout geral para as threads do ciclo se necessário.
            # Se o arrival_delay é 5s e há 10 mensagens, o envio leva ~50s.
            # Um timeout de 10s para todas as threads juntas pode ser muito curto.
            # Considere um timeout por thread ou um timeout total maior.
            # Ex: timeout_per_thread = 30 (segundos) ou total_timeout_for_cycle = 60 + self.max_considered_messages_expected * (self.arrival_delay/1000.0)
            
            # Aqui, vamos manter o timeout original para o join, mas a coleta de resultados é mais robusta.
            # O timeout do join agora é relativo ao tempo restante no ciclo de envio.
            # No entanto, é melhor ter um timeout por thread, que pode ser gerenciado no `send_and_receive_to_lb`
            # ou um timeout de join mais generoso.
            # Para este exemplo, vamos simplificar e dar um timeout maior para o join de cada thread.
            thread_join_timeout = 30.0 # Segundos de timeout para cada thread no join

            threads: list[threading.Thread] = []

            for i in range(self.max_considered_messages_expected):
                if not self.loadbalancer_addresses:
                    self.log("Erro: Nenhum endereço de load balancer configurado.")
                    break 
                lb_ip, lb_port = self.loadbalancer_addresses[i % num_balancers]

                # A configuração do servidor pode ser feita uma vez por ciclo por load balancer, se aplicável
                # Para simplificar, mantemos como está, mas pode ser otimizado.
                config_message = "config;" + ",".join([f"{lb_ip}:{4001 + j}" for j in range(qts)])
                self.send_message_to_configure_server(config_message, lb_ip, lb_port)

                msg = f"{cycle};{self.source_current_index_message};{get_current_timestamp()}"
                
                # Passa as listas locais para a thread
                t = threading.Thread(target=self.send_and_receive_to_lb, 
                                     args=(lb_ip, lb_port, msg, cycle, 
                                           current_cycle_response_times, 
                                           current_cycle_considered_messages))
                t.start()
                threads.append(t)
                self.source_current_index_message += 1
                if i < self.max_considered_messages_expected -1 : # Evita delay após a última mensagem
                    time.sleep(self.arrival_delay / 1000.0)
            
            for i, t in enumerate(threads):
                thread_start_time_for_join_calc = time.time() # Não usado no timeout fixo
                # Use um timeout fixo por thread no join
                t.join(timeout=thread_join_timeout)
                if t.is_alive():
                    self.log(f"AVISO: Thread {i} do ciclo {cycle} ainda ativa após timeout de {thread_join_timeout}s no join.")
                    # Você pode decidir o que fazer aqui: tentar cancelar, ignorar, etc.
                    # Para este exemplo, apenas logamos.

            self.cycles_completed[cycle] = True

            # Agora as estatísticas são baseadas nas listas locais do ciclo
            total_msgs = len(current_cycle_response_times) # Ou len(current_cycle_considered_messages)
            
            # Garante que as duas listas tenham o mesmo tamanho se for usar response_times para avg/std
            # Isso pode não ser necessário se send_and_receive_to_lb sempre adicionar a ambas ou a nenhuma.
            # Se current_cycle_response_times pode ser menor, use len(current_cycle_response_times)
            # e apenas os tempos dessa lista.

            avg_mrt = self.calculate_average(current_cycle_response_times)
            sd_mrt = self.calculate_standard_deviation(current_cycle_response_times)

            self.log(f"Ciclo {cycle} finalizado.")
            self.log(f"Mensagens efetivamente consideradas (com MRT): {total_msgs}")
            self.log(f"Lista de mensagens consideradas (respostas): {len(current_cycle_considered_messages)}")
            self.log(f"MRT médio: {avg_mrt:.2f} ms")
            self.log(f"Desvio padrão do MRT: {sd_mrt:.2f} ms")
            self.log("==============================")

    def send_message_to_configure_server(self, config_message: str, ip: str, port: int) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(15.0) # Adiciona um timeout para conexão e envio
                s.connect((ip, port))
                s.sendall(config_message.encode())
        except socket.timeout:
            self.log(f"Timeout ao enviar mensagem de configuração para {ip}:{port}")
        except Exception as e:
            self.log(f"Erro ao enviar mensagem de configuração para {ip}:{port}: {e}")

    def send(self, msg: str) -> None: # Usado apenas no model_feeding_stage
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0) # Adiciona um timeout
                s.connect((self.target_ip, self.target_port))
                s.sendall(msg.encode())
        except socket.timeout:
            self.log(f"Timeout ao enviar mensagem (feeding stage) para {self.target_ip}:{self.target_port}")
        except Exception as e:
            self.log(f"Erro ao enviar mensagem (feeding stage): {e}")

    def send_and_receive_to_lb(self, ip: str, port: int, msg: str, cycle: int, 
                                 # Parâmetros adicionados para as listas locais do ciclo:
                                 cycle_response_times: List[float], 
                                 cycle_considered_messages: List[str]) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(20.0) # Define um timeout para operações de socket (connect, send, recv)
                                   # Ajuste este valor conforme necessário. Deve ser menor que o thread_join_timeout.
                s.connect((ip, port))

                sent_timestamp = float(msg.split(";")[-1])
                s.sendall(msg.encode())
                
                response_bytes = b''
                try:
                    # Loop para garantir que todos os dados sejam recebidos se forem fragmentados
                    # Isso é uma simplificação; um recv mais robusto lidaria com tamanho exato ou delimitador
                    while True:
                        chunk = s.recv(1024)
                        if not chunk:
                            break # Conexão fechada pelo servidor
                        response_bytes += chunk
                        if len(response_bytes) >= 1024 or b'\n' in response_bytes: # Exemplo de condição de parada
                             # Se você espera uma resposta delimitada por \n, pode verificar aqui.
                             # Ou se você sabe o tamanho da resposta, pode verificar.
                             # Se a resposta pode ser menor que 1024 e não tem delimitador claro,
                             # o recv pode bloquear até o timeout se o servidor não fechar a conexão.
                             # Para este caso, vamos assumir que 1024 é suficiente ou o servidor fecha.
                            break
                except socket.timeout:
                    self.log(f"[Ciclo {cycle}] Timeout ao receber resposta de {ip}:{port} para msg: {msg}")
                    return # Não adiciona às listas se houver timeout no recv

                response = response_bytes.decode('utf-8', errors='replace').strip()
                if not response:
                    self.log(f"[Ciclo {cycle}] Resposta vazia de {ip}:{port} para msg: {msg}")
                    return # Não adiciona se a resposta for vazia

                receive_time = time.time()
                mrt = (receive_time - sent_timestamp) * 1000  # tempo em ms

                # Adiciona aos resultados do ciclo atual
                cycle_response_times.append(mrt)
                cycle_considered_messages.append(response)

                self.log(f"[Ciclo {cycle}] Mensagem considerada: '{response}' | Tempo de resposta (MRT): {mrt:.2f} ms")

        except socket.timeout:
            self.log(f"[Ciclo {cycle}] Timeout na operação de socket para {ip}:{port} (ex: connect, send). Msg: {msg}")
        except ConnectionRefusedError:
            self.log(f"[Ciclo {cycle}] Conexão recusada por {ip}:{port}. Msg: {msg}")
        except Exception as e:
            self.log(f"[Ciclo {cycle}] Erro em send_and_receive_to_lb para {ip}:{port}: {e}. Msg: {msg}")

    @staticmethod
    def calculate_average(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    @staticmethod
    def calculate_standard_deviation(lst: List[float]) -> float:
        if not lst:
            return 0.0
        mean = Source.calculate_average(lst)
        # Para evitar erro se len(lst) for 0 após filtragem ou em outros cenários
        if not lst: return 0.0 
        variance = sum((x - mean) ** 2 for x in lst) / len(lst)
        return variance ** 0.5