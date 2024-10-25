

from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class Device(BaseModel):
    configuration_url: Optional[str] = None
    configuration_url: Optional[str] = None
    hw_version: Optional[str] = None
    identifiers: Optional[list[str]] = None
    name: Optional[str] = None
    model: str
    manufacturer: str
    serial_number: str
    sw_version: Optional[str] = None
    via_device: Optional[str] = None


class DeviceClass(str, Enum):
    MOTION = "motion"
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    CONNECTIVITY = "connectivity"
    PROBLEM = "problem"
    POWER = "power"
    RUNNING = "running"
    HEAT = "heat"


class Config(BaseModel):
    name: Optional[str] = None
    state_topic: str
    value_template: Optional[str] = None
    unique_id: Optional[str] = None
    device: Device
    object_id: Optional[str] = None
    json_attributes_topic: Optional[str] = None
    json_attributes_template: Optional[str] = None
    icon: Optional[str] = None
    entity_category: Optional[str] = None


class Sensor(Config):
    device_class: Optional[DeviceClass] = None
    unit_of_measurement: Optional[str] = None


class Number(Sensor):
    step: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    command_topic: str


class BinarySensor(Config):
    device_class: Optional[DeviceClass] = None
    payload_on: Optional[str] = None
    payload_off: Optional[str] = None


class Switch(Config):
    device_class: Optional[DeviceClass] = None
    payload_on: Optional[str] = None
    payload_off: Optional[str] = None
    state_on: Optional[str] = None
    state_off: Optional[str] = None
    command_topic: str
    command_template: Optional[str] = None


class DeviceTrigger(BaseModel):
    automation_type: str  # "trigger"
    topic: str  # command topic
    type: str  # "button_short_press"
    subtype: str  # turn_on | turn_ff
    device: Device
    value_template: str


class WaterHeater(Config):
    payload_on: Optional[str] = None
    payload_off: Optional[str] = None
    current_temperature_template: Optional[str] = None
    current_temperature_topic: Optional[str] = None
    max_temp: Optional[float] = None
    min_temp: Optional[float] = None
    mode_command_topic: Optional[str] = None
    mode_state_template: Optional[str] = None
    mode_state_topic: Optional[str] = None
    modes: Optional[list[str]] = None
    temperature_command_topic: Optional[str] = None
    temperature_command_template: Optional[str] = None
    temperature_state_topic: Optional[str] = None
    temperature_state_template: Optional[str] = None
    temperature_unit: Optional[str] = None
