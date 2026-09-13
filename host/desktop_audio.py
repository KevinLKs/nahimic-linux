"""Desktop routing and real endpoint volume for the installed application."""
import json
from pathlib import Path
import subprocess


def pulse(*args):
    return subprocess.run(["pactl", *args], check=True, capture_output=True,
                          text=True, timeout=5).stdout.strip()


def atomic_json(path, value):
    path = Path(path)
    pending = path.with_suffix(".pending")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    pending.replace(path)


def level(sink):
    return (tuple(sink["volume"][ch]["value"] for ch in ("front-left", "front-right")), sink["mute"])


def set_level(name, desired, current):
    if desired[0] != current[0]:
        pulse("set-sink-volume", name, *(str(v) for v in desired[0]))
    if desired[1] != current[1]:
        pulse("set-sink-mute", name, str(int(desired[1])))


class DesktopAudio:
    def __init__(self, work, sink, target):
        self.work, self.sink, self.target = Path(work), sink, target
        self.enabled = None
        self.last_physical = self.last_virtual = None
        self.last_status = None

    def sinks(self):
        return {s["name"]: s for s in json.loads(pulse("--format=json", "list", "sinks"))}

    def tick(self):
        preferences = json.loads((self.work / "preferences.json").read_text())
        if type(preferences.get("enabled")) is not bool:
            raise ValueError("Missing boolean enabled preference")
        enabled = preferences["enabled"]
        sinks = self.sinks()
        physical, virtual = sinks[self.target], sinks[self.sink]
        actual, shown = level(physical), level(virtual)
        if self.last_physical is None:
            set_level(self.sink, actual, shown)
            shown = actual
        elif shown != self.last_virtual:
            # Propagate only controls that changed, retaining independently
            # changed hardware controls. Read back device quantization.
            requested = (shown[0] if shown[0] != self.last_virtual[0] else actual[0],
                         shown[1] if shown[1] != self.last_virtual[1] else actual[1])
            set_level(self.target, requested, actual)
            physical = self.sinks()[self.target]
            actual = level(physical)
            set_level(self.sink, actual, shown)
            shown = actual
        elif actual != self.last_physical:
            set_level(self.sink, actual, shown)
            shown = actual
        self.last_physical, self.last_virtual = actual, shown
        default = pulse("get-default-sink")
        streams = json.loads(pulse("--format=json", "list", "sink-inputs"))
        renderers = [s for s in streams if s.get("properties", {}).get("node.name") == self.sink + "_render"]
        if len(renderers) != 1 or renderers[0]["sink"] != physical["index"]:
            raise RuntimeError("Original audio playback link is missing")
        renderer = renderers[0]
        selected = default in (self.sink, self.target)
        if selected and (enabled != self.enabled or default == self.sink):
            desired = self.sink if enabled else self.target
            if default != desired:
                pulse("set-default-sink", desired)
                default = desired
        active = enabled and default == self.sink
        if renderer["mute"] != (not active):
            pulse("set-sink-input-mute", str(renderer["index"]), str(int(not active)))
        target_index = virtual["index"] if active else physical["index"]
        applications = 0
        for stream in streams:
            if stream["index"] == renderer["index"]:
                continue
            if stream["sink"] in (virtual["index"], physical["index"]):
                applications += 1
                if selected and stream["sink"] != target_index:
                    pulse("move-sink-input", str(stream["index"]), self.sink if active else self.target)
        self.enabled = enabled
        status = {"enabled": enabled, "active": active, "volume": round(max(actual[0]) / 65536 * 100),
                  "muted": actual[1], "applications": applications, "output": physical["description"]}
        if status != self.last_status:
            atomic_json(self.work / "desktop-state.json", status)
            self.last_status = status

    def close(self):
        # Detach the filter before destroying its streams, preserving sound.
        default = pulse("get-default-sink")
        if default == self.sink:
            pulse("set-default-sink", self.target)
        sinks = self.sinks()
        if self.sink in sinks:
            index = sinks[self.sink]["index"]
            for stream in json.loads(pulse("--format=json", "list", "sink-inputs")):
                if stream["sink"] == index:
                    pulse("move-sink-input", str(stream["index"]), self.target)
