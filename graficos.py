import re
import matplotlib.pyplot as plt
import os

def parse_log_file(log_file_path):
    
    if not os.path.exists(log_file_path):
        print(f"Erro: Arquivo de log não encontrado em {log_file_path}")
        return []

    results = []
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

    
        pattern = re.compile(
            r"Iniciando Ciclo \d+ com (\d+) servi[çc]os\."  # Captura o número de serviços
            r".*?"  # Correspondência não gulosa para qualquer coisa entre eles
            r"MRT médio: ([\d.]+)\s*ms",  # Captura o MRT médio
            re.DOTALL  # . corresponde a nova linha
        )
        
        matches = pattern.findall(content)
        
        for match in matches:
            num_services = int(match[0])
            avg_mrt = float(match[1])
            results.append((num_services, avg_mrt))
            
    except Exception as e:
        print(f"Erro ao analisar o arquivo de log: {e}")
    
    return results

def plot_mrt_vs_num_services(data, log_file_name="log.txt"):
    if not data:
        print("Sem dados para plotar.")
        return

    # Ordena os dados pelo número de serviços para um gráfico mais limpo
    data.sort(key=lambda x: x[0])

    num_services = [item[0] for item in data]
    avg_mrts = [item[1] for item in data]

    plt.figure(figsize=(10, 6))
    plt.plot(num_services, avg_mrts, marker='o', linestyle='-')
    
    plt.title(f'Tempo Médio de Resposta (MRT) vs. Número de Serviços\n(Fonte: {log_file_name})')
    plt.xlabel("Número de Serviços no Ciclo")
    plt.ylabel("Tempo Médio de Resposta (MRT) (ms)")
    plt.xticks(num_services) # Garante que todas as contagens de serviço sejam mostradas como ticks
    plt.grid(True, which="both", ls="--")
    plt.tight_layout()
    
    # Salva o gráfico em um arquivo
    plot_filename = f"mrt_vs_num_servicos_{log_file_name.replace('.txt', '').replace('.', '_')}.png"
    plt.savefig(plot_filename)
    print(f"Gráfico salvo como {plot_filename}")
    

def plot_mrt_vs_generation_rate(experimental_data):

    if not experimental_data:
        print("Sem dados experimentais para plotar.")
        return

    plt.figure(figsize=(12, 7))
    
    # Determina todos os números únicos de serviços em todos os experimentos para plotagem consistente
    all_num_services = sorted(list(set(
        item[0] for delay_data in experimental_data.values() for item in delay_data
    )))

    for num_s in all_num_services:
        rates = []
        mrts_for_num_s = []
        
        # Ordena os arrival_delays para garantir que as taxas sejam plotadas em ordem
        sorted_arrival_delays = sorted(experimental_data.keys())

        for arrival_delay in sorted_arrival_delays:
            data_for_delay = experimental_data[arrival_delay]
            for services, mrt in data_for_delay:
                if services == num_s:
                    # Converte arrival_delay (ms) para taxa de geração (mensagens/seg)
                    # Se arrival_delay for 0, trata para evitar divisão por zero
                    generation_rate = 1000.0 / arrival_delay if arrival_delay > 0 else float('inf')
                    rates.append(generation_rate)
                    mrts_for_num_s.append(mrt)
        
        if rates: # Apenas plota se houver dados para este número de serviços
            # Ordena pela taxa antes de plotar para garantir que as linhas sejam desenhadas corretamente
            sorted_points = sorted(zip(rates, mrts_for_num_s))
            rates_sorted = [p[0] for p in sorted_points]
            mrts_sorted = [p[1] for p in sorted_points]
            plt.plot(rates_sorted, mrts_sorted, marker='o', linestyle='-', label=f'{num_s} Serviço(s)')

    plt.title('Tempo Médio de Resposta (MRT) vs. Taxa de Geração de Mensagens')
    plt.xlabel("Taxa de Geração de Mensagens (mensagens/segundo)")
    plt.ylabel("Tempo Médio de Resposta (MRT) (ms)")
    if any(all_num_services): # Adiciona legenda apenas se houver serviços para diferenciar
        plt.legend(title="Número de Serviços")
    plt.grid(True, which="both", ls="--")
    plt.tight_layout()

    plot_filename = "mrt_vs_taxa_geracao.png"
    plt.savefig(plot_filename)
    print(f"Gráfico salvo como {plot_filename}")
    # plt.show() # Comente plt.show() se estiver executando em um ambiente não interativo ou salvando múltiplos gráficos


log_file_to_parse = 'log.txt' 
parsed_data_single_log = parse_log_file(log_file_to_parse)

if parsed_data_single_log:
    plot_mrt_vs_num_services(parsed_data_single_log, os.path.basename(log_file_to_parse))
else:
    print(f"Não foi possível analisar os dados de {log_file_to_parse} para o primeiro gráfico.")

print("\n---\n")


simulated_experimental_data = {}

arrival_delay_for_current_log = 15000 # ms 

if parsed_data_single_log:
     simulated_experimental_data[arrival_delay_for_current_log] = parsed_data_single_log

if parsed_data_single_log: 
    # Vamos supor que um experimento com arrival_delay = 10000ms resultou em MRTs ligeiramente menores
    hypothetical_data_delay_10000 = []
    for services, mrt in parsed_data_single_log:
        hypothetical_data_delay_10000.append((services, mrt * 0.8)) # MRT é 80% do original
    
    if hypothetical_data_delay_10000:
        simulated_experimental_data[10000] = hypothetical_data_delay_10000

    # E outro para arrival_delay = 5000ms (MRTs ainda menores)
    hypothetical_data_delay_5000 = []
    for services, mrt in parsed_data_single_log:
        hypothetical_data_delay_5000.append((services, mrt * 0.6)) # MRT é 60% do original
    
    if hypothetical_data_delay_5000:
        simulated_experimental_data[5000] = hypothetical_data_delay_5000

if simulated_experimental_data:
    print("Dados experimentais simulados para plotar MRT vs. Taxa de Geração:")
    for delay, data in sorted(simulated_experimental_data.items()): # Ordena pelo delay para saída consistente
        print(f"  Atraso de Chegada: {delay}ms, Dados: {data}")
    plot_mrt_vs_generation_rate(simulated_experimental_data)
else:
    print("Não há dados suficientes para demonstrar o gráfico MRT vs. Taxa de Geração.")


if plt.get_fignums(): # Verifica se alguma figura foi criada
    plt.show()