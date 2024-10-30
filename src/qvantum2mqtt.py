

import argparse
import logging
import sys
import time
import traceback
from mqtt import MqttClient
from ha_classes import Availability, BinarySensor, Device, Number, Sensor, Switch
from config import Config, load_config
from qvantum_api import QvantumApi
from qvantum_classes import Connectivity, MetaData, Setting

log = logging.getLogger(__name__)


class Qvantum2Mqtt:

    def __init__(self, config: Config):

        # Init API class
        self.api = QvantumApi(config.api)

        # Init MQTT class
        self.mqtt = MqttClient(config.mqtt, self.api, config.ha)

        # Authenticate against qvantum
        self.api.authenticate()
        self.devices = self.api.get_pumps().devices
        while self.devices is None:
            self.devices = self.api.get_pumps().devices
            time.sleep(2)

    def refresh_token(self):
        log.info("Refresh token")
        self.api.refresh_access_token()

    def update_states(self):
        count = 0
        while True:
            try:
                log.info("Updating states on all devices.")
                count += 1
                # use refresh token to get new access token
                for pump in self.devices:
                    pump_settings = self.api.get_pump_settings(pump.id)
                    if pump_settings is None:
                        continue
                    self.mqtt.publish_state(pump.id, "settings", "meta",
                                            pump_settings.meta.json())

                    for setting in pump_settings.settings:
                        self.mqtt.publish_state(pump.id, "settings", setting.name,
                                                setting.json())

                    pump_status = self.api.get_pump_status(pump.id)
                    if pump_status is None:
                        continue

                    self.mqtt.publish_state(pump.id, "status", "metrics",
                                            pump_status.metrics.json())

                    self.mqtt.publish_state(pump.id, "status", "connectivity",
                                            pump_status.connectivity.json())

                    # This endpoint doesn't work propwerly. Static data and a lot missing... Skip for now
                    # data = self.api.get_pump_metric(
                    #     pump.id, ["compressorenergy", "indoor_temperature", "tap_water_capacity", "additionalenergy"])
                    # log.info(data.json())
            except Exception as e:
                log.exception("An exception occured")

            time.sleep(10)  # fetch every 10 seconds
            if count % 10 == 0:
                self.refresh_token()
                count = 0

    def configure_metrics(self, pump_id: str, device: Device, availability: Availability):
        metrics_inventory = self.api.get_pump_metrics_inventory(pump_id)

        con_state_topic = self.mqtt.get_state_topic(
            pump_id, "status", "connectivity")
        con_config_topic = self.mqtt.get_config_topic(
            pump_id, "connectivity", "binary_sensor")

        con_config = BinarySensor(device=device,
                                  availability=availability,
                                  name="connectivity",
                                  object_id=f"{pump_id}_connectivity",
                                  unique_id=f"qvantum_{pump_id}_connectivity",
                                  state_topic=con_state_topic,
                                  payload_on="True",
                                  payload_off="False",
                                  json_attributes_topic=con_state_topic,
                                  json_attributes_template=Connectivity.get_attributes_template(),
                                  value_template=self.mqtt.get_value_template(
                                      "connected")
                                  )
        self.mqtt.deploy_config(con_config_topic, con_config)

        state_topic = self.mqtt.get_state_topic(pump_id, "status", "metrics")
        for metric in metrics_inventory.metrics:
            if metric.name == "compressorenergy":
                log.debug("compressorenergy not yet available")
            elif metric.name == "additionalenergy":
                log.debug("additionalenergy not yet available")
            elif metric.name == "tap_water_start":
                log.debug("tap_water_start not yet available")
            elif metric.name == "tap_water_stop":
                log.debug("tap_water_stop not yet available")
            else:
                config_topic = self.mqtt.get_config_topic(
                    pump_id, metric.name, "sensor")
                value_template = self.mqtt.get_value_template(metric.name)

                config = Sensor(device=device,
                                availability=availability,
                                name=metric.name,
                                object_id=f"{pump_id}_{metric.name}",
                                unique_id=f"qvantum_{pump_id}_{metric.name}",
                                state_topic=state_topic,
                                unit_of_measurement=metric.unit,
                                value_template=value_template)
                self.mqtt.deploy_config(config_topic, config)

    def configure_settings(self, pump_id: str, device: Device, availability: Availability):
        # Listen to set topic
        self.mqtt.add_subscribe(f"qvantum/devices/+/settings/+/set")
        settings_inventory = self.api.get_pump_settings_inventory(pump_id)
        for setting in settings_inventory.settings:
            state_topic = self.mqtt.get_state_topic(
                pump_id, "settings", setting.name)
            value_template = self.mqtt.get_value_template(
                Setting.get_value_field_name())
            match setting.data_type:
                case "number":
                    # Config for this entity
                    command_topic = self.mqtt.get_command_topic(
                        pump_id, "settings", setting.name)
                    config_topic = self.mqtt.get_config_topic(
                        pump_id, setting.name, "number")
                    config = Number(device=device,
                                    availability=availability,
                                    name=setting.display_name,
                                    step=setting.get_step(),
                                    min=setting.get_min(),
                                    max=setting.get_max(),
                                    object_id=f"{pump_id}_{setting.name}",
                                    unique_id=f"qvantum_{pump_id}_{setting.name}",
                                    state_topic=state_topic,
                                    command_topic=command_topic,
                                    json_attributes_topic=state_topic,
                                    json_attributes_template=Setting.get_attributes_template(),
                                    value_template=value_template
                                    )
                    self.mqtt.deploy_config(config_topic, config)

                case "boolean":
                    if setting.read_only:
                        config_topic = self.mqtt.get_config_topic(
                            pump_id, setting.name, "binary_sensor")
                        config = BinarySensor(device=device,
                                              availability=availability,
                                              name=setting.display_name,
                                              object_id=f"{pump_id}_{setting.name}",
                                              unique_id=f"qvantum_{pump_id}_{setting.name}",
                                              state_topic=state_topic,
                                              payload_on="on",
                                              payload_off="off",
                                              json_attributes_topic=state_topic,
                                              json_attributes_template=Setting.get_attributes_template(),
                                              value_template=value_template
                                              )
                        self.mqtt.deploy_config(config_topic, config)
                    else:
                        command_topic = self.mqtt.get_command_topic(
                            pump_id, "settings", setting.name)
                        config_topic = self.mqtt.get_config_topic(
                            pump_id, setting.name, "switch")
                        config = Switch(device=device,
                                        availability=availability,
                                        name=setting.display_name,
                                        object_id=f"{pump_id}_{setting.name}",
                                        unique_id=f"qvantum_{pump_id}_{setting.name}",
                                        state_topic=state_topic,
                                        payload_on="on",
                                        payload_off="off",
                                        json_attributes_topic=state_topic,
                                        json_attributes_template=Setting.get_attributes_template(),
                                        value_template=value_template,
                                        command_topic=command_topic,
                                        )
                        self.mqtt.deploy_config(config_topic, config)

                case "string":
                    config_topic = self.mqtt.get_config_topic(
                        pump_id, setting.name, "sensor")
                    config = Sensor(device=device,
                                    availability=availability,
                                    name=setting.display_name,
                                    object_id=f"{pump_id}_{setting.name}",
                                    unique_id=f"qvantum_{pump_id}_{setting.name}",
                                    state_topic=state_topic,
                                    json_attributes_topic=state_topic,
                                    json_attributes_template=Setting.get_attributes_template(),
                                    value_template=value_template)
                    self.mqtt.deploy_config(config_topic, config)

    def configure_alarms(self, pump_id: str, device: Device, availability: Availability):
        # The API does not care about the query category.
        # TODO: rellay have a sensor for each alarm? Gonna be a lot of sensors...
        # Maybe just one sensor "Alarm", with an array of active alarms in the attribute?
        # Not sure how alarm inventory helps. Each alarm already have a description
        # and the current alarm is not mentioned in the inventory...
        alarms = self.api.get_pump_alarm_inventory(pump_id)
        # log.info(alarms.json())

    def configure_devices(self):
        self.refresh_token()
        for pump in self.devices:

            # res = self.api.get_pump_alarm_events(pump.id)
            # log.info(res)

            # Common HA device for this pump
            identifiers = [pump.id]
            name = "Qvantum Värmepump"
            device = Device(identifiers=identifiers, name=name,
                            manufacturer=pump.vendor, serial_number=pump.serial, model=pump.model)

            # Get the metadata for the pump
            pump_status = self.api.get_pump_status(pump.id)
            # if there is data to be set, do so
            if pump_status.device_data is not None:
                meta_data: MetaData = pump_status.device_data
                device.sw_version = meta_data.display_fw_version
                # Use hw version as placeholder
                device.hw_version = meta_data.cc_fw_version
                # meta_data.inv_fw_version is always 0

            # define the availability topic for all sensors
            availability_topic = self.mqtt.get_state_topic(
                pump.id, "status", "connectivity")
            availability = Availability(topic=availability_topic,
                                        value_template=self.mqtt.get_value_template(
                                            "connected"),
                                        payload_available="True",
                                        payload_not_available="False",
                                        )
            self.configure_settings(pump.id, device, availability)
            self.configure_metrics(pump.id, device, availability)
            self.configure_alarms(pump.id, device, availability)


def main(config_path: str = "config.ini"):
    log.info("Starting qvantum2mqtt...")
    config = load_config(config_path)
    q2m = Qvantum2Mqtt(config)
    q2m.configure_devices()
    q2m.mqtt.loop_start()
    q2m.update_states()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Qvantum2MQTT application. Control your heatpump using MQTT.')

    parser.add_argument(
        '-c', '--config',
        help='Path to the config file. Defaults to "config.ini".', type=str,
        default="config.ini",
        required=False,
    )

    parser.add_argument(
        '-d', '--debug',
        help="Print debug info.",
        action="store_const", dest="loglevel", const=logging.DEBUG,
        default=logging.WARNING,
    )

    parser.add_argument(
        '-v', '--verbose',
        help="Be verbose.",
        action="store_const", dest="loglevel", const=logging.INFO,
    )

    args = parser.parse_args()

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - q2m - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    root = logging.getLogger(__name__)

    root.addHandler(handler)
    root.setLevel(args.loglevel)

    main(args.config)
