import socket
import threading
from typing import List, Tuple 

from src.abstract_proxy import AbstractProxy


class LoadBalancer(AbstractProxy):
    def __init__(self, listen_port: int, service_addresses: List[Tuple[str, int]]): # Usar Tuple
        super().__init__(log_file=f"log_loadbalancer_{listen_port}.txt") # Log individual
        self.listen_port = listen_port
        
        if not service_addresses:
            self.log(f"ALERTA CRITICO: LoadBalancer na porta {listen_port} inicializado sem nenhum service_address.")
            print(f"ALERTA CRITICO: LoadBalancer na porta {listen_port} inicializado sem nenhum service_address.")
            self.all_service_addresses: List[Tuple[str, int]] = []
        else:
            self.all_service_addresses = list(service_addresses) # Copia da lista original

        self.active_service_addresses: List[Tuple[str, int]] = list(self.all_service_addresses) # Inicialmente todos ativos
        self.current_service_index: int = 0
        self.lock = threading.Lock() # Lock para proteger acesso a active_service_addresses e current_service_index
        self.log(f"LoadBalancer inicializado na porta {listen_port}. Todos os servicos configurados: {self.all_service_addresses}")
        self.log(f"Servicos ativos inicialmente: {self.active_service_addresses}")


    def update_active_services(self, num_to_activate: int) -> bool:
        with self.lock:
            if num_to_activate <= 0:
                self.log(f"Tentativa de ativar {num_to_activate} servicos. Definindo como 0 ativos (nenhum).")
                self.active_service_addresses = []
            elif num_to_activate > len(self.all_service_addresses):
                self.log(f"AVISO: Solicitado ativar {num_to_activate} servicos, mas apenas {len(self.all_service_addresses)} estao configurados. Usando todos.")
                self.active_service_addresses = list(self.all_service_addresses)
            else:
                self.active_service_addresses = list(self.all_service_addresses[:num_to_activate])
            
            self.current_service_index = 0 # Resetar o indice round-robin
            self.log(f"Configuracao de servicos ativos atualizada para: {self.active_service_addresses} (total de {len(self.active_service_addresses)} servicos)")
            print(f"Configuracao de servicos ativos atualizada para: {self.active_service_addresses} (total de {len(self.active_service_addresses)} servicos)")

        return True

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('0.0.0.0', self.listen_port))
            server.listen()
            self.log(f"LoadBalancer listening on port {self.listen_port}")
            print(f"LoadBalancer listening on port {self.listen_port}")
        except Exception as e:
            self.log(f"ERRO ao iniciar LoadBalancer na porta {self.listen_port}: {e}")
            print(f"ERRO ao iniciar LoadBalancer na porta {self.listen_port}: {e}")
            return

        while True:
            try:
                client_sock, client_address = server.accept()
                self.log(f"Conexao aceita de {client_address} no LB porta {self.listen_port}")
                print(f"Conexao aceita de {client_address} no LB porta {self.listen_port}")
                # Cada cliente em sua propria thread
                threading.Thread(target=self.handle_client, args=(client_sock, client_address)).start()
            except Exception as e:
                self.log(f"ERRO ao aceitar conexao no LB (porta {self.listen_port}): {e}")
                print(f"ERRO ao aceitar conexao no LB (porta {self.listen_port}): {e}")


    def handle_client(self, client_sock: socket.socket, client_address): # Adicionado client_address para logging
        try:
            data = client_sock.recv(1024).decode()
            if not data:
                self.log(f"Nenhum dado recebido de {client_address} no LB.")
                client_sock.close()
                return

            self.log(f"[LB:{self.listen_port}] Mensagem recebida de {client_address}: {data}")
            print(f"[LB:{self.listen_port}] Mensagem recebida de {client_address}: {data}")

            # Tratar mensagem de configuracao
            if data.startswith("config;"):
                try:
                    num_services_str = data.split(";", 1)[1]
                    num_services_to_activate = int(num_services_str)
                    self.log(f"[LB:{self.listen_port}] Recebida mensagem de config: Ativar {num_services_to_activate} servico(s).")
                    print(f"[LB:{self.listen_port}] Recebida mensagem de config: Ativar {num_services_to_activate} servico(s).")
                    if self.update_active_services(num_services_to_activate):
                        client_sock.sendall("CONFIG_OK".encode())
                    else:
                        client_sock.sendall("CONFIG_FAIL".encode())
                except Exception as e:
                    self.log(f"[LB:{self.listen_port}] Erro ao processar mensagem de config '{data}': {e}")
                    print(f"[LB:{self.listen_port}] Erro ao processar mensagem de config '{data}': {e}")
                    client_sock.sendall(f"CONFIG_ERROR: {e}".encode())
                client_sock.close()
                return # Mensagem de config tratada.

            

            selected_service_ip = None
            selected_service_port = None

            with self.lock: # Proteger leitura de active_service_addresses e current_service_index
                if not self.active_service_addresses:
                    self.log(f"[LB:{self.listen_port}] Nenhum servico ativo para lidar com a requisicao de {client_address}.")
                    print(f"[LB:{self.listen_port}] Nenhum servico ativo para lidar com a requisicao de {client_address}.")
                    client_sock.sendall("busy_no_active_services".encode())
                    client_sock.close()
                    return

                
                initial_index = self.current_service_index
                service_found_and_free = False
                for i in range(len(self.active_service_addresses)):
                    current_try_index = (initial_index + i) % len(self.active_service_addresses)
                    ip, port = self.active_service_addresses[current_try_index]
                    
                    self.log(f"[LB:{self.listen_port}] Tentando servico {ip}:{port} (indice {current_try_index}) para {client_address}")
                    print(f"[LB:{self.listen_port}] Tentando servico {ip}:{port} (indice {current_try_index}) para {client_address}")

                    if self.is_service_free(ip, port):
                        selected_service_ip, selected_service_port = ip, port
                        # Atualiza o current_service_index para a proxima requisicao comecar dali
                        self.current_service_index = (current_try_index + 1) % len(self.active_service_addresses)
                        service_found_and_free = True
                        break # Achou um servico livre
                    else:
                        self.log(f"[LB:{self.listen_port}] Servico {ip}:{port} esta ocupado ou indisponivel.")
                        print(f"[LB:{self.listen_port}] Servico {ip}:{port} esta ocupado ou indisponivel.")
                
            if service_found_and_free and selected_service_ip and selected_service_port:
                self.log(f"[LB:{self.listen_port}] Redirecionando requisicao de {client_address} para servico: {selected_service_ip}:{selected_service_port}")
                print(f"[LB:{self.listen_port}] Redirecionando requisicao de {client_address} para servico: {selected_service_ip}:{selected_service_port}")
                
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_to_service:
                        s_to_service.settimeout(10.0) # Timeout para conexao e operacoes com o service
                        s_to_service.connect((selected_service_ip, selected_service_port))
                        s_to_service.sendall(data.encode()) # Envia a mensagem original do cliente
                        response_from_service = s_to_service.recv(2048) # Aumentar se necessario
                    
                    client_sock.sendall(response_from_service)
                    self.log(f"[LB:{self.listen_port}] Resposta de {selected_service_ip}:{selected_service_port} enviada para {client_address}: {response_from_service.decode()[:60]}...")
                    print(f"[LB:{self.listen_port}] Resposta de {selected_service_ip}:{selected_service_port} enviada para {client_address}: {response_from_service.decode()[:60]}...")

                except socket.timeout:
                    self.log(f"[LB:{self.listen_port}] Timeout ao comunicar com o servico {selected_service_ip}:{selected_service_port}")
                    print(f"[LB:{self.listen_port}] Timeout ao comunicar com o servico {selected_service_ip}:{selected_service_port}")
                    client_sock.sendall(f"error_service_timeout".encode())
                except Exception as e_service:
                    self.log(f"[LB:{self.listen_port}] Erro ao comunicar com o servico {selected_service_ip}:{selected_service_port}: {e_service}")
                    print(f"[LB:{self.listen_port}] Erro ao comunicar com o servico {selected_service_ip}:{selected_service_port}: {e_service}")
                    client_sock.sendall(f"error_contacting_service".encode())
            else:
                # Nenhum service esta livre ou disponivel entre os ativos
                self.log(f"[LB:{self.listen_port}] Todos os servicos ativos estao ocupados/indisponiveis para {client_address}.")
                print(f"[LB:{self.listen_port}] Todos os servicos ativos estao ocupados/indisponiveis para {client_address}.")
                client_sock.sendall("busy_all_services_occupied_or_down".encode())

        except socket.timeout:
            self.log(f"[LB:{self.listen_port}] Timeout ao receber dados de {client_address}.")
            print(f"[LB:{self.listen_port}] Timeout ao receber dados de {client_address}.")
        except Exception as e:
            self.log(f"[LB:{self.listen_port}] Erro no handle_client para {client_address}: {e}")
            print(f"[LB:{self.listen_port}] Erro no handle_client para {client_address}: {e}")
            try: # Tenta enviar um erro generico se a conexao ainda estiver aberta
                client_sock.sendall("internal_lb_error".encode())
            except:
                pass # Ignora se nao conseguir enviar
        finally:
            client_sock.close()
            self.log(f"[LB:{self.listen_port}] Conexao com {client_address} fechada.")
            print(f"[LB:{self.listen_port}] Conexao com {client_address} fechada.")


    def is_service_free(self, ip:str, port:int) -> bool:
        try:
            # Timeout curto para pings, para nao bloquear o LB por muito tempo
            with socket.create_connection((ip, port), timeout=1.0) as s:
                s.sendall("ping".encode())
                status = s.recv(1024).decode()
                self.log(f"[LB:{self.listen_port}] Ping para {ip}:{port} retornou: {status}")
                print(f"[LB:{self.listen_port}] Ping para {ip}:{port} retornou: {status}")
                return status == "free"
        except socket.timeout:
            self.log(f"[LB:{self.listen_port}] Timeout no ping para o servico {ip}:{port}")
            print(f"[LB:{self.listen_port}] Timeout no ping para o servico {ip}:{port}")
            return False
        except ConnectionRefusedError:
            self.log(f"[LB:{self.listen_port}] Conexao recusada no ping para o servico {ip}:{port}")
            print(f"[LB:{self.listen_port}] Conexao recusada no ping para o servico {ip}:{port}")
            return False
        except Exception as e:
            self.log(f"[LB:{self.listen_port}] Erro no ping para o servico {ip}:{port}: {e}")
            print(f"[LB:{self.listen_port}] Erro no ping para o servico {ip}:{port}: {e}")
            return False

