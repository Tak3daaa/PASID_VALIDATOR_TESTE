from queue import Queue
import socket
import threading
import time
from src.IA_service import IAService
from src.abstract_proxy import AbstractProxy
from src.utils import add_timestamp_to_message, get_current_timestamp # Adicionado get_current_timestamp

class Service(AbstractProxy):
    # Modificado __init__ para aceitar model_name
    def __init__(self, listen_port: int, service_time_ms: float, max_queue_size: int = 10, model_name: str = "llama3.2"):
        super().__init__(log_file=f"log_service_{listen_port}.txt") # Log individual por serviço
        self.listen_port = listen_port
        # self.service_time_ms = service_time_ms # O tempo de serviço será determinado pela chamada de IA
        print(f"[Service:{self.listen_port}] Inicializando com modelo de IA: {model_name}")
        self.ia_service = IAService(model_name=model_name)
        self.queue = Queue(maxsize=max_queue_size) # Definido maxsize diretamente
        # self.max_queue_size = max_queue_size # Nao mais necessario se Queue(maxsize) e usado diretamente

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permite reusar o endereço rapidamente
        try:
            server.bind(('0.0.0.0', self.listen_port))
            server.listen()
            self.log(f"Service listening on port {self.listen_port}") # Usando self.log
            print(f"Service listening on port {self.listen_port}")
        except Exception as e:
            self.log(f"ERRO ao iniciar o servico na porta {self.listen_port}: {e}")
            print(f"ERRO ao iniciar o servico na porta {self.listen_port}: {e}")
            return

        while True:
            try:
                client_sock, client_address = server.accept()
                self.log(f"Conexao aceita de {client_address} na porta {self.listen_port}")
                print(f"Conexao aceita de {client_address} na porta {self.listen_port}")
                threading.Thread(target=self.handle_client, args=(client_sock,)).start()
            except Exception as e:
                self.log(f"ERRO ao aceitar conexao na porta {self.listen_port}: {e}")
                print(f"ERRO ao aceitar conexao na porta {self.listen_port}: {e}")


    def handle_client(self, client_sock: socket.socket):
        try:
            data = client_sock.recv(1024).decode()
            if not data:
                self.log(f"Nenhum dado recebido do cliente na porta {self.listen_port}.")
                print(f"Nenhum dado recebido do cliente na porta {self.listen_port}.")
                client_sock.close()
                return

            self.log(f"Received message on port {self.listen_port}: {data}")
            print(f"Received message on port {self.listen_port}: {data}")
            
            if data == "ping":
                # A fila padrao Queue(0) e infinita. Queue(N) tem tamanho N.
                # queue.full() so funciona se maxsize > 0
                if self.queue.maxsize > 0 and self.queue.full():
                    self.log(f"Queue is full on port {self.listen_port} ({self.queue.qsize()}/{self.queue.maxsize} messages)")
                    print(f"Queue is full on port {self.listen_port} ({self.queue.qsize()}/{self.queue.maxsize} messages)")
                    client_sock.sendall("busy".encode())
                else:
                    # Se maxsize for 0 (infinita), nunca estara "full" por este metodo.
                    # Se maxsize > 0 e nao esta full, ou se e infinita, esta "free".
                    q_status = f"{self.queue.qsize()}/{self.queue.maxsize if self.queue.maxsize > 0 else 'infinito'}"
                    self.log(f"Queue is free on port {self.listen_port} ({q_status} messages)")
                    print(f"Queue is free on port {self.listen_port} ({q_status} messages)")
                    client_sock.sendall("free".encode())
                client_sock.close()
                return

            # Processamento de mensagem regular (nao eh ping)
            # Adicionar a fila apenas se houver espaco. Se nao houver, pode retornar "busy" ou descartar.
            if self.queue.maxsize > 0 and self.queue.full():
                self.log(f"Queue full, rejecting message on port {self.listen_port}: {data}")
                print(f"Queue full, rejecting message on port {self.listen_port}: {data}")
                client_sock.sendall("busy".encode()) # Informa que esta ocupado
                client_sock.close()
                return
        
            message_with_arrival_ts = f"{data};{get_current_timestamp()}"
            
            
            prompt_for_ia = f"Process this data: {data}" 

            self.log(f"Processing message with IA on port {self.listen_port}: {prompt_for_ia}")
            print(f"Processing message with IA on port {self.listen_port}: {prompt_for_ia}")

            # Chamada ao servico de IA - esta e a parte "pesada"
            ai_response = self.ia_service.ask(prompt=prompt_for_ia)
            
            
            final_response_message = f"{message_with_arrival_ts};{get_current_timestamp()};AI_RESPONSE:{ai_response}"
            
            self.log(f"Sending response from port {self.listen_port}: {final_response_message}")
            print(f"Sending response from port {self.listen_port}: {final_response_message}")

            client_sock.sendall(final_response_message.encode())
        
        except socket.timeout:
            self.log(f"Socket timeout on port {self.listen_port}")
            print(f"Socket timeout on port {self.listen_port}")
        except Exception as e:
            self.log(f"Error handling client on port {self.listen_port}: {e}")
            print(f"Error handling client on port {self.listen_port}: {e}")
        finally:
            client_sock.close()
            self.log(f"Connection closed on port {self.listen_port}")
            print(f"Connection closed on port {self.listen_port}")