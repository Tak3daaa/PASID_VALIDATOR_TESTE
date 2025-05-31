from datetime import datetime

def calculate_mrt(messages: list[str]) -> float:
    total_mrt = 0
    for message in messages:
        total_mrt += parse_mrt(message)
    return total_mrt / len(messages) if messages else 0

def parse_mrt(message: str) -> float:
    parts = message.split(";")
    return float(parts[-1])

def extract_mrts(messages: list[str]) -> list[float]:
    return [parse_mrt(message) for message in messages]

def display_results(mrt_from_experiment: float, standard_deviation: float) -> None:
    print(f"MRT From Experiment: {mrt_from_experiment}; SD From Experiment: {standard_deviation}")


def calculate_standard_deviation(mrts: list[float]) -> float:
    if not mrts:
        return 0.0
    mean = sum(mrts) / len(mrts)
    variance = sum((x - mean) ** 2 for x in mrts) / len(mrts)
    return variance ** 0.5

def calculate_mrt_from_messages(messages: list[str]) -> float:
    if not messages:
        return 0.0
    total_mrt = sum(parse_mrt(message) for message in messages)
    return total_mrt / len(messages)

def calculate_mrt_from_experiment(messages: list[str]) -> float:
    if not messages:
        return 0.0
    total_mrt = sum(parse_mrt(message) for message in messages)
    return total_mrt / len(messages)

def get_current_timestamp() -> str:
    now = datetime.now().timestamp()
    return str(now)

def add_timestamp_to_message(message: str) -> str:
    timestamp = get_current_timestamp()
    return f"{message};{timestamp}"
