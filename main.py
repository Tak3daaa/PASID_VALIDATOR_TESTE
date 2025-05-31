import sys

from src.config import carregar_config
from src.load_balance import LoadBalancer
from src.source import Source
from src.service import Service

def iniciar_source(config=None):
    if config is None:
        config = carregar_config()
    print("Configuracao carregada para Source:", config)

    print("=== Iniciando etapa de alimentacao do modelo (se configurada) ===")
    config_alimentacao = config.copy()
    config_alimentacao["model_feeding_stage"] = True # Forcar true para esta instancia
    source_alimentacao = Source(config_alimentacao)
    if config_alimentacao.get("model_feeding_stage_enabled", True): # Adicionar uma flag para habilitar/desabilitar
        source_alimentacao.run()
    else:
        print("Etapa de alimentacao do modelo desabilitada na configuracao.")


    # Segundo estágio: validação
    print("=== Iniciando etapa de validacao (se configurada) ===")
    config_validacao = config.copy()
    config_validacao["model_feeding_stage"] = False # Forcar false para esta instancia
    source_validacao = Source(config_validacao)
    if config_validacao.get("validation_stage_enabled", True):  # Adicionar uma flag para habilitar/desabilitar
        source_validacao.run()
    else:
        print("Etapa de validacao desabilitada na configuracao.")


def iniciar_load_balancer(listen_port=2000, service_addresses_str=None): # Recebe a string
    parsed_service_addresses = []
    if service_addresses_str:
        try:
            address_pairs = service_addresses_str.split(',')
            for pair_str in address_pairs:
                if ':' not in pair_str:
                    raise ValueError(f"Par de endereco/porta invalido: '{pair_str}'")
                ip, port_s = pair_str.split(':', 1)
                parsed_service_addresses.append((ip.strip(), int(port_s.strip())))
        except ValueError as e:
            print(f"ERRO CRITICO ao parsear service_addresses ('{service_addresses_str}') para o load balancer: {e}")
            # Decidir se sai ou inicia com lista vazia (que o LB tratara como erro)
            # Por seguranca, vamos sair se o parse falhar
            sys.exit(f"Falha ao parsear enderecos para LB: {service_addresses_str}")
    
    if not parsed_service_addresses:
        # Isso acontecera se service_addresses_str for None ou vazio, ou se o parse falhar e nao sair acima.
        print(f"ALERTA: Load balancer na porta {listen_port} iniciando sem servicos de backend explicitos. Verifique a chamada.")
        # O construtor do LoadBalancer agora loga um alerta se a lista estiver vazia.
        # Permitir que o LB seja inicializado com lista vazia e ele proprio lide com isso.
    
    lb = LoadBalancer(listen_port=listen_port, service_addresses=parsed_service_addresses)
    lb.start()

# Modificado para aceitar model_name
def iniciar_service(port, service_time_ms, model_name: str):
    # service_time_ms nao e mais usado diretamente se o tempo de servico e o da IA.
    # Pode ser mantido para outros usos ou removido.
    print(f"Tentando iniciar servico na porta {port} com modelo IA '{model_name}' (service_time_ms={service_time_ms} ignorado).")
    service = Service(listen_port=port, service_time_ms=service_time_ms, model_name=model_name)
    service.start()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Chamada de argumentos invalida. Uso: python main.py [source|load_balancer|service] [opcoes...]")
        sys.exit(1)

    role = sys.argv[1].lower()
    config = carregar_config() # Carrega config geral uma vez

    if role == "source":
        print("Iniciando Source...")
        # Passar a config carregada para a funcao, para que ela possa ser usada/modificada
        iniciar_source(config=config)

    elif role == "load_balancer":
        if len(sys.argv) < 4: # python main.py load_balancer <listen_port> "<ip1>:<port1>,<ip2>:<port2>"
            print("Erro ao executar load balancer. Parametros invalidos.")
            print("Uso: python main.py load_balancer <listen_port> \"ip1:port1,ip2:port2,...\"")
            sys.exit(1)
        try:
            listen_port_arg = int(sys.argv[2])
        except ValueError:
            print(f"Erro: listen_port '{sys.argv[2]}' para load_balancer deve ser um inteiro.")
            sys.exit(1)
            
        service_addresses_arg = sys.argv[3] # String ex: "service1:4001,service2:4002"
        print(f"Iniciando Load_Balancer na porta {listen_port_arg} com servicos backend: {service_addresses_arg}")
        iniciar_load_balancer(listen_port=listen_port_arg, service_addresses_str=service_addresses_arg)

    elif role == "service":
        # Adicionado argumento para model_name
        if len(sys.argv) < 5: # python main.py service <port> <service_time_ms> <model_name>
            print("Erro ao executar service. Parametros invalidos.")
            print("Uso: python main.py service <port> <service_time_ms_dummy> <model_name>")
            sys.exit(1)
        try:
            port_arg = int(sys.argv[2])
            service_time_ms_arg = float(sys.argv[3]) # Ainda passado, mas pode ser ignorado pelo Service
            model_name_arg = sys.argv[4]
        except ValueError:
            print(f"Erro: port ('{sys.argv[2]}') ou service_time_ms ('{sys.argv[3]}') invalidos para service.")
            sys.exit(1)
            
        print(f"Iniciando servico na porta {port_arg} com modelo {model_name_arg}...")
        iniciar_service(port_arg, service_time_ms_arg, model_name_arg)

    else:
        print(f"Opcao desconhecida: {role}")
        sys.exit(1)