from queue import Queue
import socket
import threading
import time
from src.IA_service import IAService
from src.abstract_proxy import AbstractProxy
from src.utils import add_timestamp_to_message

class Service(AbstractProxy):
    def __init__(self, listen_port: int, service_time_ms: float, max_queue_size: int = 10):
        self.listen_port = listen_port
        self.service_time_ms = service_time_ms
        self.queue = Queue()
        self.max_queue_size = max_queue_size
        self.ia_service = IAService()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', self.listen_port))
        server.listen()
        print(f"Service listening on port {self.listen_port}")
        while True:
            # Aceita conexões de clientes
            client_sock, _ = server.accept()
            # Cria uma nova thread para lidar com o cliente
            threading.Thread(target=self.handle_client, args=(client_sock,)).start()

    def handle_client(self, client_sock: socket.socket):
        data = client_sock.recv(1024).decode()

        print(f"Received message: {data}")
        
        # Verifica se a mensagem é "ping"
        if data == "ping":
            if self.queue.full():
                print(f"Queue is full {self.queue.maxsize / self.max_queue_size} messages")
                client_sock.sendall("busy".encode())
            else:
                print(f"Queue is free {self.queue.maxsize / self.max_queue_size} messages")
                client_sock.sendall("free".encode())
            client_sock.close()
            return
        if self.queue.full():
            print(f"Queue is full {self.queue.maxsize / self.max_queue_size} messages")
            client_sock.sendall("busy".encode())
            client_sock.close()
            return
        self.queue.put(data)
        
        # Se não for "ping", processa a mensagem normalmente

        # Adiciona timestamp de chegada à mensagem
        data = add_timestamp_to_message(data)

        print(f"Processing message: {data}")

        time.sleep(self.service_time_ms / 1000.0)  # Simula tempo de serviço em ms

        # Adiciona timestamp de envio à mensagem
        data = add_timestamp_to_message(data)

        print(f"Sending message: {data}")

        # Envia a mensagem de volta ao cliente
        client_sock.sendall(data.encode())
        client_sock.close()