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
    if service_addresses is None:
        service_addresses = [("localhost", 4001), ("localhost", 4002)]
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
        if len(sys.argv) < 3:
            print("Erro ao executar load balancer. Parametros invalidos")
            sys.exit(1)
        listen_port = int(sys.argv[2])
        service_addresses = None
        print("Iniciando Load_Balancer")
        iniciar_load_balancer(listen_port=listen_port, service_addresses=service_addresses)

    elif role == "service":
        if len(sys.argv) < 4:
            print("Erro ao executar service. Parametros invalidos")
            sys.exit(1)
        port = int(sys.argv[2])
        service_time_ms = float(sys.argv[3])
        print(f"Iniciando serviço na porta: {port}")
        iniciar_service(port, service_time_ms)

    else:
        print(f"Opção desconhecida: {role}")
        sys.exit(1)
