from queue import Queue
import socket
import threading
from src.IA_service import IAService
from src.abstract_proxy import AbstractProxy
from src.utils import add_timestamp_to_message

class Service(AbstractProxy):
    def __init__(self, listen_port: int, service_time_ms: float, max_queue_size: int = 10):
        self.listen_port = listen_port
        self.queue = Queue(maxsize=max_queue_size)
        self.ia_service = IAService()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', self.listen_port))
        server.listen()
        print(f"Service listening on port {self.listen_port}")
        while True:
            client_sock, _ = server.accept()
            threading.Thread(target=self.handle_client, args=(client_sock,)).start()

    def handle_client(self, client_sock: socket.socket):
        data = client_sock.recv(1024).decode().strip()
        print(f"Received message: {data}")
        
        # Verifica se é ping
        if data == "ping":
            status = "busy" if self.queue.full() else "free"
            print(f"Queue status: {status}")
            client_sock.sendall(status.encode())
            client_sock.close()
            return

        if self.queue.full():
            print("Queue is full. Rejecting message.")
            client_sock.sendall("busy".encode())
            client_sock.close()
            return

        self.queue.put(data)
        
        try:
            # Adiciona timestamp de chegada à mensagem
            data = add_timestamp_to_message(data)

            print(f"Processing message: {data}")

            print(
                self.ia_service.ask("Como a IA tem revolucionado o século 21?")
            )

            # Adiciona timestamp de envio à mensagem
            data = add_timestamp_to_message(data)

            print(f"Sending message: {data}")

            # Envia a mensagem de volta ao cliente
            client_sock.sendall(data.encode())
        except Exception as e:
            print(f"Error processing request: {e}")
            client_sock.sendall(f"error: {str(e)}".encode())
        finally:
            self.queue.get()
            self.queue.task_done()
            client_sock.close()
