import os
import tempfile
import shutil
import numpy as np

from ..analysis import DataCollector
from ..thinkgear import ThinkGearRawWaveData


class MockData(object):
    """Mock ThinkGear*Data packet to contain arbitrary value"""

    def __init__(self, value):
        self.value = value


class RandomProtocol(object):
    """Generate random packets"""

    def __init__(self, device):
        self.rng = np.random.RandomState(42)
        self.device = device

    def get_packets(self):
        while True:
            yield [MockData(self.rng.normal())
                   for _ in range(self.rng.randint(10))]


def test_data_collector():
    data_folder = tempfile.mkdtemp()
    collector = DataCollector('/fake/device', data_folder,
                              protocol=RandomProtocol, packet_type=MockData)
    collector.collect(n_samples=(collector.chunk_size * 3 + 10))

    # 3 full buffers + one partially filled fourth memmapable buffer
    data_files = os.listdir(data_folder)
    assert len(data_files) == 4

    # last buffer should be mostly filled with zeros
    data_files.sort()
    last_buffer = np.memmap(os.path.join(data_folder, data_files[-1]),
                            dtype=collector.dtype)
    assert np.all(last_buffer[11:] == 0.0)

    shutil.rmtree(data_folder)
