"""Hardware table: which speaker endpoints are supported and which tuning file each one uses."""
import json
import os
from pathlib import Path

BUILTIN = Path(__file__).with_name("devices.json")
USER = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "nahimic-linux" / "devices.json"


def load(user_path=USER):
    table = json.loads(BUILTIN.read_text())
    devices, ports = list(table["devices"]), list(table["speaker_ports"])
    if user_path and Path(user_path).is_file():
        local = json.loads(Path(user_path).read_text())
        devices = list(local.get("devices", [])) + devices
        ports = list(local.get("speaker_ports", [])) + [p for p in ports if p not in local.get("speaker_ports", [])]
    for device in devices:
        if not device.get("codec") or not device.get("device_file"):
            raise ValueError("Device entries need codec and device_file: " + json.dumps(device))
    return devices, ports


def components(sink):
    """Return (codec, subsystem) from alsa.components, e.g. HDA:10ec0256,1028087c,00100002."""
    value = sink.get("properties", {}).get("alsa.components", "").lower()
    for part in value.split():
        if part.startswith("hda:"):
            fields = part[4:].split(",")
            if len(fields) >= 2:
                return fields[0], fields[1]
    return None, None


def match(sink, table=None):
    """Return the device entry for a speaker sink on its speaker port, or None."""
    devices, ports = table or load()
    if sink.get("active_port") not in ports:
        return None
    codec, subsystem = components(sink)
    if codec is None:
        return None
    for device in devices:
        if device["codec"].lower() != codec:
            continue
        if device.get("subsystem") in (None, "", "*") or device["subsystem"].lower() == subsystem:
            return device
    return None
