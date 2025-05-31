import socket
import threading
from typing import List

from src.abstract_proxy import AbstractProxy
from src.utils import add_timestamp_to_message


class LoadBalancer(AbstractProxy):
    def __init__(self, listen_port: int, service_addresses: List[tuple]):
        self.listen_port = listen_port
        self.service_addresses = service_addresses
        self.current = 0

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', self.listen_port))
        server.listen()
        print(f"LoadBalancer listening on port {self.listen_port}")
        while True:
            client_sock, _ = server.accept()
            threading.Thread(target=self.handle_client, args=(client_sock,)).start()

    def handle_client(self, client_sock: socket.socket):
        try:
            data = client_sock.recv(1024).decode()
            print(f"[LB] Mensagem recebida do cliente: {data}")

            data = add_timestamp_to_message(data)

            # Tenta encontrar um service livre (round-robin)
            for _ in range(len(self.service_addresses)):
                ip, port = self.service_addresses[self.current]
                self.current = (self.current + 1) % len(self.service_addresses)
                # Verifica se o service está livre
                if self.is_service_free(ip, port):
                    print(f"[LB] Redirecionando para serviço: {ip}:{port}")
                    # Envia a mensagem para o service
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((ip, port))
                        s.sendall(data.encode())
                        response = s.recv(1024)
                    # Adiciona o timestamp de envio à mensagem
                    data = add_timestamp_to_message(data)
                    client_sock.sendall(response)
                    print(f"[LB] Resposta enviada ao cliente: {response.decode()}")
                    break
                else:
                    print(f"[LB] Serviço ocupado: {ip}:{port}")
            else:
                # Nenhum service está livre
                print("[LB] Todos os serviços estão ocupados.")
                client_sock.sendall("busy".encode())
        except Exception as e:
            print(f"Erro no LoadBalancer: {e}")
        finally:
            client_sock.close()

    def is_service_free(self, ip:str, port:int) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ip, port))
                s.sendall("ping".encode())
                status = s.recv(1024).decode()
                return status == "free"
        except Exception:
            return False


if __name__ == "__main__":
    service_addresses = [("localhost", 4001), ("localhost", 4002)]
    lb = LoadBalancer(listen_port=2000, service_addresses=service_addresses)
    lb.start()
