
from datetime import datetime
from enum import Enum
import json
from typing import Any, Optional
from pydantic import BaseModel, Field


class QvantumBaseModel(BaseModel):

    @classmethod
    def get_field_names(cls, by_alias=False) -> list[str]:
        field_names = []
        for k, v in cls.__fields__.items():
            if by_alias and isinstance(v, Field):
                field_names.append(v.alias)
            else:
                field_names.append(k)
        return field_names

    @classmethod
    def get_attributes_template(cls) -> str:
        res = dict()
        for name in cls.get_field_names():
            value_template = "{a} value_json.{value_key} {b}".format(
                a="{{", value_key=name, b="}}")
            res[name] = value_template
        return json.dumps(res)


class ApiError(QvantumBaseModel):
    message: Optional[str] = None


class Token(QvantumBaseModel):
    access_token: Optional[str] = None
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None


class TokenUser(QvantumBaseModel):
    email: Optional[str] = None
    isQvantum: Optional[bool] = None
    uid: Optional[str] = None
    you: Optional[str] = None


class Pump(QvantumBaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    vendor: Optional[str] = None
    serial: Optional[str] = None
    model: Optional[str] = None


class SensorMode(str, Enum):
    off = "off"
    bt2 = "bt2"
    bt3 = "bt3"
    btx = "btx"


class Meta(QvantumBaseModel):
    last_reported: Optional[str] = None
    validity: Optional[str] = None

    def get_value_field_name() -> str:
        return "validity"


class Setting(QvantumBaseModel):
    name: Optional[str] = None
    value: int | float | Optional[str] = None
    read_only: Optional[bool] = None

    def get_value_field_name() -> str:
        return "value"


class DevicesResponse(QvantumBaseModel):
    user_id: Optional[str] = None
    devices: Optional[list[Pump]] = None


class Connectivity(QvantumBaseModel):
    connected: Optional[bool] = None
    timestamp: Optional[str] = None
    disconnect_reason: Optional[str] = None

    def get_value_field_name() -> str:
        return "connected"


class Metrics(QvantumBaseModel):
    time: Optional[str] = None
    outdoor_temperature: int | Optional[float] = None
    indoor_temperature: int | Optional[float] = None
    heating_flow_temperature: int | Optional[float] = None
    heating_flow_temperature_target: int | Optional[float] = None
    tap_water_tank_temperature: int | Optional[float] = None
    tap_water_capacity: int | Optional[float] = None


class PumpSettingsResponse(QvantumBaseModel):
    meta: Optional[Meta] = None
    settings: Optional[list[Setting]] = None


class MetaData(QvantumBaseModel):
    uptime_hours: Optional[int] = 0
    display_fw_version: Optional[str] = "0.0.0"
    cc_fw_version: Optional[str] = "0.0.0"
    inv_fw_version: Optional[str] = "0.0.0"


class PumpStatusResponse(QvantumBaseModel):
    connectivity: Optional[Connectivity] = None
    metrics: Optional[Metrics] = None
    device_data: Optional[MetaData] = Field(
        default=None, alias='device_metadata')


class SettingsInventory(QvantumBaseModel):
    name: Optional[str] = None
    read_only: Optional[bool] = None
    data_type: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None

    def get_min(self) -> float:
        if self.name == "tap_water_capacity_target":
            return 0
        elif self.name == "tap_water_start":
            return 40
        elif self.name == "tap_water_stop":
            return 40
        elif self.name == "indoor_temperature_target":
            return 15
        elif self.name == "indoor_temperature_offset":
            return -9
        else:
            return 0

    def get_max(self) -> float:
        if self.name == "tap_water_capacity_target":
            return 5
        elif self.name == "tap_water_start":
            return 70
        elif self.name == "tap_water_stop":
            return 99
        elif self.name == "indoor_temperature_target":
            return 25
        elif self.name == "indoor_temperature_offset":
            return 9
        else:
            return 0

    def get_step(self) -> float:
        if self.name == "tap_water_capacity_target":
            return 1
        elif self.name == "tap_water_start":
            return 1
        elif self.name == "tap_water_stop":
            return 1
        elif self.name == "indoor_temperature_target":
            return 1
        elif self.name == "indoor_temperature_offset":
            return 1
        else:
            return 0


class SettingsInventoryResponse(QvantumBaseModel):
    settings: Optional[list[SettingsInventory]] = None


class AlarmCategory(str, Enum):
    HEATPUMP = "HEATPUMP"
    COM = "COM"
    CLOUD = "CLOUD"
    WIFI = "WIFI"
    INVERTER = "INVERTER"


class AlarmInventory(QvantumBaseModel):
    type: Optional[AlarmCategory] = None
    code: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None


class AlarmInventoryResponse(QvantumBaseModel):
    alarms: Optional[list[AlarmInventory]] = None


class Alarm(QvantumBaseModel):
    id: Optional[str] = None
    device_alarm_id: Optional[str] = None
    type: Optional[AlarmCategory] = None
    code: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None
    is_acknowledged: Optional[bool] = None
    triggered_timestamp: Optional[datetime] = None
    reset_timestamp: Optional[datetime] = None
    acknowledged_timestamp: Optional[str] = None
    data: Optional[Any] = None


class AlarmEventsResponse(QvantumBaseModel):
    alarms: Optional[list[Alarm]] = None


class MetricsInventory(QvantumBaseModel):
    name: Optional[str] = None
    unit: Optional[str] = None
    value_kind: Optional[str] = None
    description: Optional[str] = None


class MetricsInventoryResponse(QvantumBaseModel):
    metrics: Optional[list[MetricsInventory]] = None


# TODO:
# Hardcoded. Api limitation?
class MetricData(QvantumBaseModel):
    time: Optional[datetime] = None
    hpid: Optional[str] = None
    compressorenergy: Optional[float] = None
    indoor_temperature: Optional[float] = None
    tap_water_capacity: Optional[float] = None
    additionalenergy: Optional[float] = None


class MetricsResponse(QvantumBaseModel):
    metadata: Optional[Any] = None
    # metrics: list[MetricData]] = None
    metrics: Optional[list[Any]] = None


class SetSetting(QvantumBaseModel):
    name: str
    value: Any


class SetSettingsRequest(QvantumBaseModel):
    settings: list[SetSetting]
