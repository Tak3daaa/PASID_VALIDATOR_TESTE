from typing import Dict, Any


def carregar_config() -> Dict[str, Any]:

    return {
        'model_feeding_stage': False,
        'source_port': 1000,
        'target_ip': 'loadbalancer1',
        'target_port': 2000,
        'max_considered_messages_expected': 10,
        'mrts_from_model': [405597.23, 203892.96],
        'sdvs_from_model': [1245.97, 613.95],
        'arrival_delay': 15000,
        'qtd_services': [1, 2],
        'loadbalancer_addresses': 'loadbalancer1:2000,loadbalancer2:3000'
    }
