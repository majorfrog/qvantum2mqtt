

import json
from typing import Any
import requests
from config import QvantumApiConfig
from qvantum_classes import AlarmCategory, AlarmEventsResponse, AlarmInventoryResponse, DevicesResponse, MetricsInventoryResponse, MetricsResponse, PumpSettingsResponse, PumpStatusResponse, QvantumBaseModel, SetSetting, SetSettingsRequest, SettingsInventoryResponse, Token, TokenUser

from http.server import BaseHTTPRequestHandler
from io import BytesIO
import json
import os
import socket
import sys
from urllib.parse import parse_qs, urlparse
import webbrowser

import requests
from qvantum_classes import Token, TokenUser


class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = BytesIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


class QvantumApi:
    def __init__(self, config: QvantumApiConfig):
        self.config = config
        self.tokens = None
        self.token_user = None

    def get_request(self, endpoint: str) -> Any:
        url = f"{self.config.api_endpoint}/{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {self.tokens.access_token}"
        }
        res = requests.get(url=url, headers=headers)
        if res.status_code != 200:
            print(f"Potential server error: {res.status_code} {res.text}")
            return None
        return json.loads(res.text)

    def request_access_token(self, code):
        print("Requesting access token - after this, refresh token can be used to renew")
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        # api spec not clear about this...
        body = f"client_id={self.config.client_id}&grant_type=authorization_code&code={code}"
        url = f"{self.config.api_endpoint}/api/auth/v1/oauth2/token"
        res = requests.post(url=url, data=body, headers=headers)
        if res.status_code != 200:
            print("Could not be authenticated!")
            sys.exit()

        res_dict = json.loads(res.text)
        self.tokens = Token(**res_dict)
        # update the file in case we need to restart
        f = open(self.config.auth_file_path, "w")
        f.write(self.tokens.json())
        f.close()

    def load_user_id(self):
        path = "api/auth/v1/whoami"
        res = self.get_request(path)
        if res is None:
            sys.exit()
        self.token_user = TokenUser(**res)

    def refresh_access_token(self) -> bool:
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = f"client_id={self.config.client_id}&grant_type=refresh_token&refresh_token={self.tokens.refresh_token}"
        url = f"{self.config.api_endpoint}/api/auth/v1/oauth2/token"
        res = requests.post(url=url, data=body, headers=headers)
        if res.status_code != 200:
            print("Refresh token is invalid.")
            # Get a new access code
            return False
        res_dict = json.loads(res.text)
        self.tokens = Token(**res_dict)
        # update the file in case we need to restart
        f = open(self.config.auth_file_path, "w")
        f.write(self.tokens.json())
        f.close()
        return True

    def get_pumps(self) -> DevicesResponse:
        path = f"api/inventory/v1/users/{self.token_user.uid}/devices"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return DevicesResponse(**res_dict)

    def get_pump_settings(self, device_id: str) -> PumpSettingsResponse:
        path = f"api/device-info/v1/devices/{device_id}/settings"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return PumpSettingsResponse(**res_dict)

    def get_pump_status(self, device_id: str) -> PumpStatusResponse:
        path = f"api/device-info/v1/devices/{device_id}/status?metrics=now"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return PumpStatusResponse(**res_dict)

    def get_pump_metrics_inventory(self, device_id: str) -> MetricsInventoryResponse:
        path = f"api/inventory/v1/devices/{device_id}/metrics"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return MetricsInventoryResponse(**res_dict)

    def get_pump_metric(self, device_id: str, metrics: list[str]) -> MetricsResponse:
        metrics_str = ','.join(metrics)
        path = f"api/metrics/v1/devices/{device_id}/timelines?metric_names={metrics_str}&tz=Europe%2FStockholm&resolution=hourly"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return MetricsResponse(**res_dict)

    def get_pump_settings_inventory(self, device_id: str) -> SettingsInventoryResponse:
        path = f"api/inventory/v1/devices/{device_id}/settings"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return SettingsInventoryResponse(**res_dict)

    # api does not care about category?
    def get_pump_alarm_inventory(self, device_id: str) -> AlarmInventoryResponse:
        # ?&category={category.value}" <- No usage
        path = f"api/inventory/v1/devices/{device_id}/alarms"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return AlarmInventoryResponse(**res_dict)

    def get_pump_alarm_events(self, device_id: str) -> AlarmEventsResponse:
        # defualt limit is 10
        # filter? to set in diferent topics?
        # ?category={category.value}&limit=10"
        path = f"api/events/v1/devices/{device_id}/alarms&limit=10"
        res_dict = self.get_request(path)
        if res_dict is None:
            return None
        return AlarmEventsResponse(**res_dict)

    def set_pump_setting(self, device_id: str, setting: str, value: Any) -> QvantumBaseModel:
        """
        Send a patch request and update a setting on the machine.
        """
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {self.tokens.access_token}"
        }
        # Try cast to int. If int value is sent as string, the API will return 200 (OK)
        # but the request will have no effect. The server should either check payload validity
        # and return 400 with a proper description or try to cast itself.
        value = int(value) if value.lstrip('-').isdigit() else value

        payload = SetSettingsRequest(
            settings=[SetSetting(name=setting, value=value)])

        url = f"{self.config.api_endpoint}/api/device-info/v1/devices/{device_id}/settings?dispatch=false"
        res = requests.patch(url=url, data=payload.json(), headers=headers)
        if res.status_code != 200:
            print(f"Potential server error: {res.status_code} {res.text}")
            return None
        else:
            print(f"Successful set: {res.status_code} {res.text}")

        res_dict = json.loads(res.text)

        return QvantumBaseModel(**res_dict)

    def get_tokens(self) -> Token:
        return self.tokens

    def authenticate(self):
        authenticated = False
        # if auth file exists, use referesh token to fetch new access
        if os.path.isfile(self.config.auth_file_path):
            print("Auth file exist. Read and use refresh token.")
            f = open(self.config.auth_file_path, "r")
            self.tokens = Token(**json.loads(f.read()))
            if self.refresh_access_token():
                authenticated = True

        if not authenticated:
            print("No authenticated. Get code from auth server.")
            # open up listening on port
            print(f"Listening on port {self.config.port}")
            serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                serversocket.bind(('', self.config.port))
                serversocket.listen(1)

            except socket.error as msg:
                # Port might be taken...
                print('Bind failed. Error Code : ' +
                      str(msg[0]) + ' Message ' + msg[1])
                sys.exit()

            # Open a browser to authorize the app
            url = f"{self.config.auth_server}/authorize?response_type=code&client_id={self.config.client_id}&state={self.config.state}&redirect_uri={self.config.redirect}:{self.config.port}"
            print("Follow this link to complete this step:")
            print(url)
            if self.config.open_browser:
                print("Opening browser for authentication.")
                webbrowser.open(url, new=0, autoraise=True)

            # recv the data and get the code
            conn, addr = serversocket.accept()
            incoming_data = conn.recv(4096)
            # We have the data. Close server.
            conn.close()
            serversocket.close()
            # parse the request
            request = HTTPRequest(incoming_data)
            parsed_url = urlparse(request.path)
            qs = parse_qs(parsed_url.query)
            if qs["code"]:
                self.request_access_token(qs["code"][0])
            else:
                print("No code returned. Exiting.")
                sys.exit()

        self.load_user_id()
