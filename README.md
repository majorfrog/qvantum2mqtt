# qvantum2mqtt

Simple python app that communicates with the qvantum api: https://api.qvantum.com/

Publishes the data on the configured mqtt broker and makes it possible to monitor all your devices.

Written to work with home assistant for easy integration.


## To run

Copy config_example.ini
```console
> cp src/config_example.ini src/config.ini
```

Edit the file per your setup. mqtt options is requried be modified to match your broker config. The rest can be left as is. More info about the options can be found in the config_example.ini file.

```console
> cd src
> python3 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt
> python3 qvantum2mqtt.py
```

Authorize the app in the browser, and it'll be running!
