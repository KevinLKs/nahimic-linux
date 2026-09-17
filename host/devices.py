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
    """Return every (codec, subsystem) pair in alsa.components.

    A sink can list several codecs, e.g. on Intel SOF/DSP machines where the
    HDMI codec and the analog codec both appear:
    "HDA:8086281c,80860101,00100000 HDA:10ec0256,1c05c022,00100002 cfg-dmics:2".
    """
    value = sink.get("properties", {}).get("alsa.components", "").lower()
    found = []
    for part in value.split():
        if part.startswith("hda:"):
            fields = part[4:].split(",")
            if len(fields) >= 2:
                found.append((fields[0], fields[1]))
    return found


def match(sink, table=None):
    """Return the device entry for a speaker sink on its speaker port, or None."""
    devices, ports = table or load()
    if sink.get("active_port") not in ports:
        return None
    present = components(sink)
    for device in devices:
        for codec, subsystem in present:
            if device["codec"].lower() != codec:
                continue
            if device.get("subsystem") in (None, "", "*") or device["subsystem"].lower() == subsystem:
                return device
    return None
