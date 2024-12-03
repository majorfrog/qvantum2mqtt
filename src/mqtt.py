import logging
import sys
import paho.mqtt.client as mqtt

from ha_classes import Config, Device, Q2mState
from config import HomeAssistantConfig, MqttConfig
from qvantum_api import QvantumApi

log = logging.getLogger(__name__)


class MqttClient(mqtt.Client):

    def __init__(self, config: MqttConfig, api: QvantumApi, ha: HomeAssistantConfig):
        super().__init__()
        # TODO: for local mqtt connections this is fine. Add support for TLS
        self.config = config
        self.ha = ha
        # need reference to Api to set values (incoming commands over mqtt)
        self.api = api
        state_topic = self.get_state_topic(
            "q2m", "status", "running")

        self.will_set(topic=state_topic,
                      payload=Q2mState(running=False).model_dump_json())
        self.username_pw_set(self.config.user, self.config.password)
        self.subs = []
        self.connected = False
        if self.connect(self.config.server, self.config.port, 60) != 0:
            log.error("Couldn't connect to the mqtt broker")
            sys.exit(1)

    def on_connect(self, client, userdata, flags, reason_code):
        log.debug("Connected")
        self.connected = True
        for topic in self.subs:
            log.debug(f"sub topic {topic}")
            self.subscribe(topic)
        self.publish_state("q2m",  "status", "running",
                           Q2mState().model_dump_json())

    def on_message(self, client, userdata, message):
        log.debug("received message =", str(message.payload.decode("utf-8")))
        log.debug(f"on topic: {message.topic}")
        parts = message.topic.split("/")
        device_id = parts[2]
        setting = parts[4]
        self.api.set_pump_setting(
            device_id, setting, message.payload.decode("utf-8"))

    def publish_msg(self, topic: str, value, retain: bool = False):
        self.publish(topic, value, qos=0, retain=retain)

    def disconnect(self):
        self.disconnect()

    def add_subscribe(self, topic: str):
        if topic not in self.subs:
            self.subs.append(topic)

    def deploy_config(self, config_topic: str, config: Config):
        self.publish_msg(config_topic, config.model_dump_json(
            exclude_none=True), retain=True)

    def publish_state(self, pump_id: str, category: str, name: str, value):
        self.publish_msg(self.get_state_topic(
            pump_id, category, name), value=value, retain=False)

    def get_state_topic(self, pump_id: str, category: str, name: str) -> str:
        return f"qvantum/devices/{pump_id}/{category}/{name}/value"

    def get_command_topic(self, pump_id: str, category: str, name: str) -> str:
        topic = f"qvantum/devices/{pump_id}/{category}/{name}/set"
        return topic

    def get_config_topic(self, pump_id: str, name: str, entity_type: str) -> str:
        return f"{self.ha.topic_prefix}/{entity_type}/{pump_id}/{name}/config"

    def get_value_template(self, value_key) -> str:
        return "{a} value_json.{value_key} {b}".format(a="{{", value_key=value_key, b="}}")

    def clear_topic(self, topic):
        self.publish_msg(topic, None)
