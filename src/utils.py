from datetime import datetime

def get_current_timestamp() -> str:
    now = datetime.now().timestamp()
    return str(now)

def add_timestamp_to_message(message: str) -> str:
    timestamp = get_current_timestamp()
    return f"{message};{timestamp}"
