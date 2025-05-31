import socket
import threading
import time
from typing import List, Dict, Any

from src.abstract_proxy import AbstractProxy
from src.utils import get_current_timestamp


class Source(AbstractProxy):

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config.get("log_file", "log_source.txt")) # Log individual
        self.model_feeding_stage: bool = config.get("model_feeding_stage", False)
        self.arrival_delay: int = config.get("arrival_delay", 0) # em ms
        self.max_considered_messages_expected: int = config.get("max_considered_messages_expected", 10)
        self.source_current_index_message: int = 0
        self.qtd_services: List[int] = config.get("qtd_services", []) # Ex: [1, 2] N de servicos a serem usados pelos LBs

        
        loadbalancer_addresses_str = config.get("loadbalancer_addresses", "")
        self.response_times: List[float] = []

        self.target_ip: str = config.get("target_ip", "loadbalance1")
        self.target_port: int = config.get("target_port", 2000)

        self.log(f"Source iniciando. Model feeding stage: {self.model_feeding_stage}")
        self.log(f"Target para model feeding: {self.target_ip}:{self.target_port}")
        self.log(f"LoadBalancer addresses para validacao: {loadbalancer_addresses_str}")
        self.log(f"Qtd_services por ciclo de validacao: {self.qtd_services}")
        self.log(f"Arrival delay: {self.arrival_delay} ms")
        self.log(f"Max considered messages expected per cycle: {self.max_considered_messages_expected}")


        if isinstance(loadbalancer_addresses_str, str) and loadbalancer_addresses_str:
            self.loadbalancer_addresses_parsed: List[tuple[str, int]] = []
            try:
                for address in loadbalancer_addresses_str.split(","):
                    ip, port_str = address.split(":")
                    self.loadbalancer_addresses_parsed.append((ip, int(port_str)))
            except ValueError as e:
                self.log(f"ERRO ao parsear loadbalancer_addresses: '{loadbalancer_addresses_str}'. {e}")
                self.loadbalancer_addresses_parsed = [] # Reseta para evitar erros posteriores
        else:
            self.loadbalancer_addresses_parsed = []
        
        if not self.loadbalancer_addresses_parsed and not self.model_feeding_stage:
            self.log("ALERTA: Nenhum loadbalancer_address configurado para a etapa de validacao.")


    def run(self) -> None:
        self.log("Starting source run")
        if self.model_feeding_stage:
            self.send_message_feeding_stage()
        else:
            if not self.loadbalancer_addresses_parsed:
                self.log("ERRO FATAL: Etapa de validacao iniciada, mas nenhum load balancer configurado ou erro no parse.")
                return
            self.send_messages_validation_stage()
        self.log("Source run finished.")

    def send_message_feeding_stage(self) -> None:
        self.log("Model Feeding Stage Started")
        if not self.target_ip or not self.target_port:
            self.log("ERRO: target_ip ou target_port nao configurado para model_feeding_stage.")
            return

        for i in range(self.max_considered_messages_expected): # Enviar 10 mensagens como antes, ou usar um contador diferente?

            msg = f"FEED;{self.source_current_index_message};{get_current_timestamp()};Este_e_um_payload_para_alimentacao_do_modelo_{i}"
            self.log(f"Enviando mensagem de feeding: {msg} para {self.target_ip}:{self.target_port}")
            print(f"Enviando mensagem de feeding: {msg} para {self.target_ip}:{self.target_port}")
            response = self.send_and_receive(self.target_ip, self.target_port, msg, is_feeding=True)
            if response:
                self.log(f"Resposta do feeding: {response}")
            else:
                self.log(f"Nenhuma resposta ou erro ao enviar mensagem de feeding {msg}")
            self.source_current_index_message += 1
            if self.arrival_delay > 0:
                time.sleep(self.arrival_delay / 1000.0)
        self.log("Model Feeding Stage Finished.")

    def send_messages_validation_stage(self) -> None:
        self.log("Validation Stage Started")
        if not self.qtd_services:
            self.log("ALERTA: qtd_services esta vazio. Nenhum ciclo de validacao sera executado.")
            return

        for cycle_idx, num_target_services in enumerate(self.qtd_services):
            self.log(f"--- Iniciando Ciclo de Validacao {cycle_idx} com {num_target_services} servico(s) alvo no(s) LB(s) ---")
            self.source_current_index_message = 1 # Reinicia indice de mensagem por ciclo
            self.response_times.clear()
            # self.considered_messages.clear() # Nao usado para muito alem de contar

            if not self.loadbalancer_addresses_parsed:
                self.log(f"ERRO: Nenhum load balancer definido para o ciclo {cycle_idx}. Pulando ciclo.")
                continue

            num_balancers = len(self.loadbalancer_addresses_parsed)
            
            # Enviar mensagem de configuracao para CADA load balancer
            config_message = f"config;{num_target_services}" # Ex: "config;1" ou "config;2"
            for lb_ip, lb_port in self.loadbalancer_addresses_parsed:
                self.log(f"Enviando mensagem de configuracao '{config_message}' para LB {lb_ip}:{lb_port}")

                config_response = self.send_and_receive(lb_ip, lb_port, config_message, is_config=True)
                if config_response:
                    self.log(f"Resposta da configuracao do LB {lb_ip}:{lb_port}: {config_response}")
                else:
                    self.log(f"LB {lb_ip}:{lb_port} nao respondeu a configuracao ou erro.")


            threads: list[threading.Thread] = []
            messages_sent_this_cycle = 0

            for i in range(self.max_considered_messages_expected):
                lb_ip, lb_port = self.loadbalancer_addresses_parsed[i % num_balancers]
                
                # Mensagem para validacao: cycle_origem;indice_msg;timestamp_envio_source;payload_opcional
                msg_payload = f"Dados da mensagem {self.source_current_index_message} para o ciclo {cycle_idx}"
                msg = f"{cycle_idx};{self.source_current_index_message};{get_current_timestamp()};{msg_payload}"
                
                
                self.log(f"Enviando msg de validacao '{msg}' para LB {lb_ip}:{lb_port} (Ciclo {cycle_idx})")
                print(f"Enviando msg de validacao '{msg}' para LB {lb_ip}:{lb_port} (Ciclo {cycle_idx})")
                
                response_data = self.send_and_receive(lb_ip, lb_port, msg, cycle_info=cycle_idx) # Passa informacao do ciclo para logging no send_and_receive
                # send_and_receive agora vai popular self.response_times se for bem sucedido

                self.source_current_index_message += 1
                messages_sent_this_cycle +=1
                if self.arrival_delay > 0:
                    time.sleep(self.arrival_delay / 1000.0)
            total_responses = len(self.response_times) # response_times eh populado por send_and_receive
            avg_mrt = self.calculate_average(self.response_times) if self.response_times else 0.0
            sd_mrt = self.calculate_standard_deviation(self.response_times) if self.response_times else 0.0

            self.log(f"--- Ciclo de Validacao {cycle_idx} finalizado ---")
            self.log(f"Mensagens enviadas neste ciclo: {messages_sent_this_cycle}")
            self.log(f"Respostas validas (com MRT calculado): {total_responses}")
            self.log(f"MRT medio: {avg_mrt:.2f} ms")
            self.log(f"Desvio padrao do MRT: {sd_mrt:.2f} ms")
            self.log("===================================================")
        self.log("Validation Stage Finished.")

    # Metodo unificado para enviar e receber, tratando MRT
    def send_and_receive(self, ip: str, port: int, msg: str, is_config: bool = False, is_feeding: bool = False, cycle_info=None) -> str | None:
        response_content = None
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0) # Timeout de 10 segundos para conexao e recebimento
                s.connect((ip, port))
                
                sent_timestamp_float = 0.0
                if not is_config: # Mensagens de config nao tem timestamp relevante para MRT do source
                    try:
                        # Para mensagens de feeding e validacao, o timestamp esta no formato: TIPO;ID;TIMESTAMP;PAYLOAD
                        # Ou para validacao: CYCLE;ID;TIMESTAMP;PAYLOAD
                        parts = msg.split(";")
                        if len(parts) >=3:
                            sent_timestamp_float = float(parts[2])
                        else:
                            self.log(f"AVISO: Formato de mensagem inesperado para extrair timestamp de envio: {msg}")
                    except ValueError:
                        self.log(f"AVISO: Nao foi possivel parsear timestamp da mensagem: {msg}")


                s.sendall(msg.encode())
                response_bytes = s.recv(2048) # Aumentar buffer se respostas da IA forem grandes
                response_content = response_bytes.decode()

                if is_config:
                    self.log(f"Mensagem de config '{msg}' enviada para {ip}:{port}. Resposta: {response_content}")
                elif is_feeding:
                     self.log(f"Mensagem de feeding '{msg}' enviada para {ip}:{port}. Resposta: {response_content}")
                else: # Mensagem de validacao, calcular MRT
                    receive_time_float = time.time() # Timestamp de recebimento da resposta
                    if sent_timestamp_float > 0:
                        mrt_ms = (receive_time_float - sent_timestamp_float) * 1000.0
                        self.response_times.append(mrt_ms) # Adiciona ao MRT do ciclo atual
                        log_msg_detail = f"Msg: '{msg.split(';')[-1]}'" if msg else "N/A" # Pega o payload
                        log_cycle_info = f"[Ciclo {cycle_info}] " if cycle_info is not None else ""
                        self.log(f"{log_cycle_info}Resposta de {ip}:{port}: '{response_content}'. {log_msg_detail} | MRT: {mrt_ms:.2f} ms")
                        print(f"{log_cycle_info}Resposta de {ip}:{port}: '{response_content}'. {log_msg_detail} | MRT: {mrt_ms:.2f} ms")

                    else:
                        self.log(f"Resposta de {ip}:{port}: '{response_content}'. Nao foi possivel calcular MRT (timestamp de envio invalido).")
                        print(f"Resposta de {ip}:{port}: '{response_content}'. Nao foi possivel calcular MRT (timestamp de envio invalido).")


        except socket.timeout:
            self.log(f"ERRO (TIMEOUT) ao enviar/receber de {ip}:{port} para msg: {msg}")
            print(f"ERRO (TIMEOUT) ao enviar/receber de {ip}:{port} para msg: {msg}")
        except ConnectionRefusedError:
            self.log(f"ERRO (CONEXAO RECUSADA) ao conectar com {ip}:{port} para msg: {msg}")
            print(f"ERRO (CONEXAO RECUSADA) ao conectar com {ip}:{port} para msg: {msg}")
        except Exception as e:
            self.log(f"ERRO ao enviar/receber de {ip}:{port} para msg '{msg}': {e}")
            print(f"ERRO ao enviar/receber de {ip}:{port} para msg '{msg}': {e}")
        
        return response_content


    @staticmethod
    def calculate_average(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    @staticmethod
    def calculate_standard_deviation(lst: List[float]) -> float:
        if not lst or len(lst) < 2: # Desvio padrao nao e significativo para menos de 2 amostras
            return 0.0
        mean = Source.calculate_average(lst)
        # Usa N-1 no denominador para desvio padrao amostral, ou N para populacional.
        # Para N pequeno, N-1 e mais comum. Se len(lst) == 1, resultaria em divisao por zero.
        variance = sum((x - mean) ** 2 for x in lst) / (len(lst) -1 ) # Amostral
        return variance ** 0.5