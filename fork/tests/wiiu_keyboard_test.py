import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
mock = root / 'fork/tests/wiiu_keyboard_mock'
src = root / 'WiiU/src/pc'
with tempfile.TemporaryDirectory() as folder:
    binary = Path(folder) / 'keyboard-test'
    subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror', '-DTARGET_WII_U', '-I' + str(mock), '-I' + str(src), str(src / 'wiiu_keyboard.cpp'), str(mock / 'test_keyboard.cpp'), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print('Wii U keyboard mock tests passed')
