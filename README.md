# PASID Validator (Python)
---

## 📌 Visão Geral

- Geração de dados simulados
- Balanceamento de carga entre múltiplos proxies
- Validação dos dados (simulada)
- Registro de resultados e tempo de resposta

---

## 🚀 Como Executar

1. Clone o repositório:

```bash
  git clone git@github.com:MarcosAndreLS/Pasid-Validator-Python.git
  cd Pasid-Validator-Python-main
```

2. Rode os arquivos separadamente

```bash
  # Para rodar os serviços em suas respectivas portas e valor do service_time_ms
  #(o tempo do service_time_ms pode ser mudado)
  
  > python main.py service 4001 100
  > python main.py service 4002 100
  
  # Para rodar os load balances com suas respectivas portas 
  
  > python main.py load_balancer 2000
  > python main.py load_balancer 3000
  
  # Por fim, rodar o source
  
  > python main.py source
  
```

## 📁 Estruturação dos arquivos

```text
  Pasid-Validator-Python-main/
  │
  ├── main.py                      # Script principal que executa a validação
  ├── log.txt                      # Arquivo gerado com os resultados (tempo e status)
  ├── README.md                    # Este arquivo
  └── src/
      ├── abstract_proxy.py        # Interface base para proxies de validação
      ├── config.py                # Configurações gerais do sistema
      ├── load_balance.py          # Balanceador de carga (round-robin)
      ├── service.py               # Orquestrador do sistema de validação
      ├── source.py                # Proxies concretos que validam os dados
      └── utils.py                 # Funções auxiliares (geração, logs, etc.)

```
