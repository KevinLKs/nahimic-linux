"""Exercise the native shared-memory ABI used across Linux and Wine."""
import os
from pathlib import Path
import shlex
import subprocess
from tempfile import TemporaryDirectory
import unittest

class VolumeStateTest(unittest.TestCase):
    def test_publication_under_preemption_and_concurrent_access(self):
        source = Path(__file__).with_name('volume_state_test.c')
        with TemporaryDirectory(prefix='nahimic-volume-test-', dir='/tmp') as directory:
            binary = Path(directory) / 'volume-state-test'
            command = shlex.split(os.environ.get('CC', 'cc'))
            subprocess.run(command + ['-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                                      str(source), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True, timeout=15)

if __name__ == '__main__': unittest.main()
