class AbstractProxy:
    
    def __init__(self, log_file="log.txt"):
        self.log_file = log_file
        self.init_log_file()

    def init_log_file(self):
        with open(self.log_file, 'w') as f:
            f.write("")

    def log(self, message: str):
        print(message)
        with open(self.log_file, 'a') as f:
            f.write(message + "\n")