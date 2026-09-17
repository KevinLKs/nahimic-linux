"""Speaker hardware matching from devices.json."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
import devices


def sink(components, port='[Out] Speaker'):
    return {'active_port': port, 'properties': {'alsa.components': components}}


class DevicesTest(unittest.TestCase):
    def setUp(self):
        self.table = devices.load(user_path=None)

    def test_original_senary_speakers(self):
        entry = devices.match(sink('HDA:14f11f87,1d05e022,00100100'), self.table)
        self.assertTrue(entry['verified'])

    def test_realtek_alc256_speakers_on_both_port_names(self):
        for port in ('[Out] Speaker', 'analog-output-speaker'):
            entry = devices.match(sink('HDA:10ec0256,1c05c022,00100002 HDA:8086280b,80860101,00100000', port), self.table)
            self.assertEqual(entry['codec'], '10ec0256')
            self.assertFalse(entry['verified'])

    def test_other_codecs_and_ports_are_rejected(self):
        self.assertIsNone(devices.match(sink('HDA:10ec0257,17aa3801,00100001'), self.table))
        self.assertIsNone(devices.match(sink('HDA:14f11f87,deadbeef,00100100'), self.table))
        self.assertIsNone(devices.match(sink('HDA:10ec0256,1c05c022,00100002', '[Out] Headphones'), self.table))
        self.assertIsNone(devices.match(sink('HDA:10ec0256,deadbeef,00100002'), self.table))
        self.assertIsNone(devices.match({'active_port': '[Out] Speaker'}, self.table))

    def test_user_entries_take_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'devices.json'
            path.write_text(json.dumps({'devices': [{'name': 'Mine', 'codec': '10ec0256',
                                                     'subsystem': None, 'device_file': '/x.nsx'}]}))
            table = devices.load(user_path=path)
            self.assertEqual(devices.match(sink('HDA:10ec0256,1c05c022,0'), table)['name'], 'Mine')
            self.assertEqual(devices.match(sink('HDA:10ec0256,11111111,0'), table)['name'], 'Mine')


if __name__ == '__main__': unittest.main()
