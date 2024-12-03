

from pydantic import BaseModel
import configparser


class HomeAssistantConfig(BaseModel):
    topic_prefix: str = "homeassistant"


class MqttConfig(BaseModel):
    server: str = "127.0.0.1"
    port: int = 1883
    user: str = None
    password: str = None


class QvantumApiConfig(BaseModel):
    api_endpoint: str = "https://api.qvantum.com"
    port: int = 5173
    redirect: str = "http://localhost"
    auth_file_path: str = "auth_tokens.json"
    auth_server: str = "https://account.qvantum.com"
    client_id: str = "qvantum2mqtt"
    state: str = "abc123"
    open_browser: bool = True
    refresh_interval: int = 30


class Config(BaseModel):
    api: QvantumApiConfig
    mqtt: MqttConfig
    ha: HomeAssistantConfig


def load_config(config_path: str = "config.ini") -> Config:
    # Load the config file and return Config class
    config = configparser.ConfigParser()
    with open(config_path) as fd:
        config.read_file(fd)
    return Config(**config)
