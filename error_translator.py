import json
        

class ErrorTranslator:
    def __init__(self, config: dict) -> None:
        self.config: dict = config
        
    def translate(self, name: str) -> tuple[int, str]:
        #Level Zero
        if name not in self.config:
            return 500,"something went wrong please try again."
        return self.config[name]["status_code"], self.config[name]["detail"]