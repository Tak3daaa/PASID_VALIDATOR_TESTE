from typing import Dict, Any

def carregar_config() -> Dict[str, Any]:
    return {
        'model_feeding_stage_enabled': True,  # Ou False se nao quiser rodar a alimentacao
        'validation_stage_enabled': True,     # Ou False se nao quiser rodar a validacao

        'model_feeding_stage': False, # Este e usado pelo Source para saber qual logica interna rodar, nao para habilitar/desabilitar a chamada
        'source_port': 1000, # Nao parece estar sendo usado
        'target_ip': 'loadbalance1', # IP/hostname do alvo para o model_feeding_stage
        'target_port': 2000,         # Porta do alvo para o model_feeding_stage
        
        'max_considered_messages_expected': 10, # Mensagens por ciclo/etapa
        
        # 'mrts_from_model': [405597.23, 203892.96], # Parece ser referencia, nao usado pelo codigo diretamente
        # 'sdvs_from_model': [1245.97, 613.95], # Parece ser referencia, nao usado
        
        'arrival_delay': 100, # ms - Atraso entre envio de mensagens pelo source
        
        'qtd_services': [1, 2], # Usado pelo source para enviar msg de config para LBs sobre N de servicos a usar
                                 # Ex: no ciclo 0, LBs devem usar 1 servico; no ciclo 1, LBs devem usar 2 servicos.
        
        'loadbalancer_addresses': 'loadbalance1:2000,loadbalance2:3000' # Enderecos dos LBs para a etapa de validacao
    }