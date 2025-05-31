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
        self.considered_messages: List[str] = []
        self.qtd_services: List[int] = config.get("qtd_services", [])
        self.cycles_completed: List[bool] = [False] * len(self.qtd_services)
        self.dropp_count: int = 0
        self.loadbalancer_addresses = config.get("loadbalancer_addresses", "")
        self.response_times: List[float] = []

        self.target_ip: str = config.get("target_ip", "localhost")
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
        for _ in range(10):
            msg = f"1;{self.source_current_index_message};{get_current_timestamp()}"
            print("Enviando:", msg)
            self.send(msg)
            self.source_current_index_message += 1
            time.sleep(self.arrival_delay / 1000.0)

    def send_messages_validation_stage(self) -> None:
        for cycle, qts in enumerate(self.qtd_services):
            self.source_current_index_message = 1
            self.considered_messages.clear()
            self.response_times.clear()

            # Distribui as mensagens entre os load balancers
            num_balancers = len(self.loadbalancer_addresses)
            start_time = time.time()
            timeout = 10  # segundos
            threads: list[threading.Thread] = []

            for i in range(self.max_considered_messages_expected):
                # Escolhe o load balancer de forma round-robin
                lb_ip, lb_port = self.loadbalancer_addresses[i % num_balancers]

                # Configuração: envie para o load balancer correspondente
                config_message = "config;" + ",".join([f"{lb_ip}:{4001 + j}" for j in range(qts)])
                self.send_message_to_configure_server(config_message, lb_ip, lb_port)

                msg = f"{cycle};{self.source_current_index_message};{get_current_timestamp()}"
                t = threading.Thread(target=self.send_and_receive_to_lb, args=(lb_ip, lb_port, msg, cycle))
                t.start()
                threads.append(t)
                self.source_current_index_message += 1
                time.sleep(self.arrival_delay / 1000.0)

            for t in threads:
                t.join(timeout=max(0, timeout - (time.time() - start_time)))

            self.cycles_completed[cycle] = True

            total_msgs = len(self.response_times)
            avg_mrt = self.calculate_average(self.response_times)
            sd_mrt = self.calculate_standard_deviation(self.response_times)

            self.log(f"Ciclo {cycle} finalizado.")
            self.log(f"Mensagens consideradas: {total_msgs}")
            self.log(f"MRT médio: {avg_mrt:.2f} ms")
            self.log(f"Desvio padrão do MRT: {sd_mrt:.2f} ms")
            self.log("==============================")

    def send_message_to_configure_server(self, config_message: str, ip: str, port: int) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall(config_message.encode())
        except Exception as e:
            self.log(f"Erro ao enviar mensagem de configuração para {ip}:{port}: {e}")

    def send(self, msg: str) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.target_ip, self.target_port))
                s.sendall(msg.encode())
        except Exception as e:
            self.log(f"Erro ao enviar mensagem: {e}")

    def send_and_receive_to_lb(self, ip: str, port: int, msg: str, cycle: int) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))

                # Timestamp de envio para cálculo do MRT
                sent_timestamp = float(msg.split(";")[-1])

                s.sendall(msg.encode())
                response = s.recv(1024).decode()

                receive_time = time.time()
                mrt = (receive_time - sent_timestamp) * 1000  # tempo em ms

                self.response_times.append(mrt)
                self.considered_messages.append(response)

                self.log(f"[Ciclo {cycle}] Mensagem considerada: '{response}' | Tempo de resposta (MRT): {mrt:.2f} ms")

        except Exception as e:
            self.log(f"Erro ao enviar/receber mensagem para {ip}:{port}: {e}")

    @staticmethod
    def calculate_average(lst: List[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    @staticmethod
    def calculate_standard_deviation(lst: List[float]) -> float:
        if not lst:
            return 0.0
        mean = Source.calculate_average(lst)
        variance = sum((x - mean) ** 2 for x in lst) / len(lst)
        return variance ** 0.5
