import sys

from src.config import carregar_config
from src.load_balance import LoadBalancer
from src.source import Source
from src.service import Service

def iniciar_source(config=None):
    if config is None:
        config = carregar_config()
    print("Config completa:", config)

    # Primeiro estágio: model feeding
    print("=== Iniciando etapa de alimentação do modelo ===")
    config_alimentacao = config.copy()
    config_alimentacao["model_feeding_stage"] = True
    source_alimentacao = Source(config_alimentacao)
    source_alimentacao.run()

    # Segundo estágio: validação
    print("=== Iniciando etapa de validação ===")
    config_validacao = config.copy()
    config_validacao["model_feeding_stage"] = False
    source_validacao = Source(config_validacao)
    source_validacao.run()

def iniciar_load_balancer(listen_port=2000, service_addresses=None):
    if service_addresses is None or not service_addresses: # Adicionado 'not service_addresses'
        # Este caminho só deve ser tomado se explicitamente nenhum endereço for fornecido E você quiser um default.
        # Dado o docker-compose, service_addresses NUNCA deveria ser None aqui.
        print(f"ALERTA: Load balancer na porta {listen_port} esta sem servicos de backend configurados ou usando default problemático.")
        # Considerar sair com erro se service_addresses for None ou vazio quando é esperado do docker-compose.
        # service_addresses = [("localhost", 4001), ("localhost", 4002)] # Remova ou comente defaults 'localhost' se não aplicável
        if not service_addresses: # Se for uma lista vazia explicitamente
             print(f"ERRO: Load balancer na porta {listen_port} recebeu uma lista vazia de servicos.")
             sys.exit(1) # Ou trate como o LoadBalancer deve se comportar sem backends

    lb = LoadBalancer(listen_port=listen_port, service_addresses=service_addresses)
    lb.start()

def iniciar_service(port, service_time_ms):
    service = Service(listen_port=port, service_time_ms=service_time_ms)
    service.start()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Chamada de argumentos invalida")
        sys.exit(1)

    role = sys.argv[1].lower()

    if role == "source":
        print("Iniciando Source")
        iniciar_source()

    elif role == "load_balancer":
        if len(sys.argv) < 4: # Espera: python main.py load_balancer <listen_port> "<ip1>:<port1>,<ip2>:<port2>,..."
            print(f"Erro: Parametros invalidos para load_balancer.")
            print(f"Esperado: python main.py load_balancer <listen_port> \"ip1:port1,ip2:port2,...\"")
            sys.exit(1)

        try:
            listen_port = int(sys.argv[2])
        except ValueError:
            print(f"Erro: listen_port ('{sys.argv[2]}') invalido para load_balancer.")
            sys.exit(1)

        service_addresses_str = sys.argv[3]
        parsed_service_addresses = []
        if not service_addresses_str:
            print(f"Erro: String de enderecos de servico (service_addresses) esta vazia para load_balancer.")
            sys.exit(1)

        try:
            address_pairs = service_addresses_str.split(',')
            for pair_str in address_pairs:
                if ':' not in pair_str:
                    # Levanta um erro se um par nao contiver ':'
                    raise ValueError(f"Formato invalido para o par endereco:porta '{pair_str}' na string '{service_addresses_str}'")

                ip, port_str = pair_str.split(':', 1) # Divide apenas no primeiro ':'
                if not ip or not port_str: # Verifica se ip ou porta estao vazios
                    raise ValueError(f"IP ou porta vazios no par '{pair_str}' na string '{service_addresses_str}'")
                parsed_service_addresses.append((ip.strip(), int(port_str.strip())))
        except ValueError as e:
            print(f"Erro critico ao parsear service_addresses ('{service_addresses_str}') para o load_balancer: {e}")
            sys.exit(1)

        if not parsed_service_addresses:
            print(f"Erro: Nenhum endereco de servico valido foi parseado de '{service_addresses_str}' para o load_balancer.")
            sys.exit(1)

        # Se chegou aqui, o parsing foi bem-sucedido
        print(f"Iniciando Load_Balancer na porta {listen_port} com servicos: {parsed_service_addresses}")
        # Certifique-se que iniciar_load_balancer use esses enderecos parseados
        # e não o default 'localhost' que está na assinatura da função.
        iniciar_load_balancer(listen_port=listen_port, service_addresses=parsed_service_addresses)

    elif role == "service":
        if len(sys.argv) < 4: # Espera: python main.py service <port> <service_time_ms>
            print(f"Erro: Parametros invalidos para service.")
            print(f"Esperado: python main.py service <port> <service_time_ms>")
            sys.exit(1)
        try:
            port = int(sys.argv[2])
            service_time_ms = float(sys.argv[3])
        except ValueError:
            print(f"Erro: port ('{sys.argv[2]}') ou service_time_ms ('{sys.argv[3]}') invalidos para service.")
            sys.exit(1)

        print(f"Iniciando servico na porta {port} com tempo de servico {service_time_ms}ms")
        iniciar_service(port, service_time_ms)
