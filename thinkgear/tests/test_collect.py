import os
import tempfile
import shutil
import numpy as np
from numpy.testing import assert_array_equal
from nose.tools import with_setup
from nose.tools import assert_equal

from ..collect import DataCollector
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


def setup_data_folder():
    global data_folder
    data_folder = tempfile.mkdtemp(prefix='pythingear_')


def teardown_data_folder():
    shutil.rmtree(data_folder)


@with_setup(setup_data_folder, teardown_data_folder)
def test_data_collector():
    collector = DataCollector('/fake/device', data_folder,
                              protocol=RandomProtocol, packet_type=MockData)
    collector.collect(n_samples=(collector.chunk_size * 3 + 10))

    # expect one session folder
    session_folders = os.listdir(data_folder)
    assert len(session_folders) == 1
    signal_folder = os.path.join(data_folder, session_folders[0], 'data')

    # 3 full buffers + one partially filled fourth memmapable buffer
    data_files = os.listdir(signal_folder)
    assert len(data_files) == 4

    # last buffer should be mostly filled with zeros
    data_files.sort()
    last_buffer = np.memmap(os.path.join(signal_folder, data_files[-1]),
                            dtype=collector.dtype)
    assert np.all(last_buffer[11:] == 0.0)


@with_setup(setup_data_folder, teardown_data_folder)
def test_session_management():
    collector = DataCollector('/fake/device', data_folder,
                              protocol=RandomProtocol, packet_type=MockData)
    collector.collect(n_samples=(collector.chunk_size * 2))
    assert_equal(len(collector.list_sessions()), 1)

    collector.collect(n_samples=42)
    assert_equal(len(collector.list_sessions()), 2)

    collector.collect(n_samples=43)
    assert_equal(len(collector.list_sessions()), 3)

    # fetches the last session by default
    assert_equal(collector.get_session().shape[0], 43)

    # lookup by index an in memory aggregate of the first, multi-buffer
    # session
    data_session_0 = collector.get_session(0)
    assert_equal(data_session_0.shape[0], collector.chunk_size * 2)

    # the fake packet generator does not send any bad poor packet signal hence
    # the quality is always good
    expected = np.array([True] * 43, dtype=np.bool)
    assert_array_equal(collector.get_session(signal='quality'), expected)

    quality_session_0 = collector.get_session(0, signal='quality')
    assert_equal(quality_session_0.shape, data_session_0.shape)
    assert np.all(quality_session_0)
