import configparser
import os

class Config:
    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_path, "data", "config.ini")

        self.config = configparser.ConfigParser()
        self.config.read(config_path)

    def get_llm_model(self):
        return self.config["GENERAL"].get("llm_model", "mistral")

    def get_temperature(self):
        return float(self.config["GENERAL"].get("temperature", "0.7"))

    def get_api_base(self):
        return self.config["GENERAL"].get("api_base", "http://localhost:1234/v1")

    def get_api_key(self):
        return self.config["GENERAL"].get("api_key", "lm-studio")

    # Extendable for future: DB URI, quiz settings, etc.


