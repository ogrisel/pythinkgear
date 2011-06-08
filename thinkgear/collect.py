# Copyright (c) 2011, Olivier Grisel
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Interface module to dump raw packet into numpy arrays for analysis"""

import logging
import sys
import os
from datetime import datetime

import numpy as np
import pylab as pl

from .thinkgear import ThinkGearProtocol
from .thinkgear import ThinkGearRawWaveData
from .thinkgear import ThinkGearPoorSignalData


# The Mindset samples at 512Hz
SAMPLING_FREQUENCY = 512

# One file per 1 minute of collected data
BUFFER_SIZE = SAMPLING_FREQUENCY * 60


class DataCollector(object):
    """Read data from the device and serialize it on disk

    This tool is meant to work in it's own python process and communicate
    the raw data arrays to analyzing processes through memmaped arrays.
    """

    def __init__(self, device, data_folder, prefix='pythinkgear_',
                 chunk_size=BUFFER_SIZE, dtype=np.double,
                 protocol=ThinkGearProtocol, packet_type=ThinkGearRawWaveData,
                 monitor=None):
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        self.data_folder = data_folder
        self.device = device
        self.prefix = prefix
        self.dtype = dtype
        self.chunk_size = chunk_size
        self.protocol = protocol
        self.packet_type = packet_type
        self.monitor = monitor
        if monitor is not None:
            monitor.init(self)

    def get_timestamp(self):
        """Up to the second, filename same timestamp"""
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def make_buffer(self, session_id, dtype=None):
        session_folder = os.path.join(self.data_folder, session_id)
        dtype = dtype if dtype is not None else self.dtype

        # build a non existing filename based on a timestamp and a integer
        # increment
        ts = self.get_timestamp()
        incr = 0
        pattern = self.prefix + ts + '_%03d.memmap'
        while True:
            filename = pattern % incr
            filepath = os.path.join(session_folder, filename)
            if os.path.exists(filepath):
                incr += 1
            else:
                break

        logging.info("Creating new buffer: %s", filepath)
        buffer = np.memmap(filepath, dtype=dtype, mode='w+',
                           shape=(self.chunk_size,))
        # set all the buffer values to zero to be able to detect partially
        # filled buffers
        buffer[:] = 0.0
        return buffer

    @staticmethod
    def trim_buffer(buffer, size):
        """Trim the buffer to only keep the 'size' first elements"""
        if size >= buffer.shape[0] or size == 0:
            # nothing to do
            return buffer

        filename = buffer.filename
        logging.info("Trim %s from %d down to %d",
                     filename, buffer.shape[0], size)

        # load the interesting buffer data in memory
        data = buffer[:size].copy()
        buffer.close()
        os.unlink(filename)

        # copy the data into a smaller memmaped array at the same location
        new_buffer = np.memmap(filename, dtype=buffer.dtype, mode='w+',
                               shape=(size,))
        new_buffer[:] = data
        return new_buffer

    def check_buffer(self, cursor, buffer, session_id):
        """Check that the cursor is not overflowing the buffer

        Close the current buffer and create a new one with the cursor at
        the beginning in case of overflow.
        """
        if cursor >= buffer.shape[0]:
            buffer.flush()
            buffer = self.make_buffer(session_id)
            cursor = 0
        return cursor, buffer

    def make_session(self):
        """Make a new session folder and return its id"""
        incr = 0
        while True:
            session_id = self.get_timestamp() + "_%03d" % incr
            session_folder = os.path.join(self.data_folder, session_id)
            if os.path.exists(session_folder):
                incr += 1
            else:
                os.makedirs(session_folder)
                return session_id

    def collect(self, n_samples=None):
        """Collect samples from the device using the protocol instance

        Instance are buffered in memory mapped arrays of fixed size.
        """
        session_id = self.make_session()
        collected = 0
        logging.info("Opening connection to %s", self.device)
        cursor = 0
        buffer = self.make_buffer(session_id)
        try:
            for pkt in self.protocol(self.device).get_packets():
                cursor, buffer = self.check_buffer(cursor, buffer, session_id)
                for d in pkt:
                    # TODO: store the poor signal data packets in a boolean mast
                    # array
                    if isinstance(d, ThinkGearPoorSignalData):
                        if d.value:
                            logging.warn("Poor signal: please adjust headset")
                    elif isinstance(d, self.packet_type):
                        cursor, buffer = self.check_buffer(
                            cursor, buffer, session_id)
                        buffer[cursor] = d.value
                        cursor += 1
                        collected += 1
                        if (self.monitor is not None
                            and cursor % self.monitor.period == 0):
                            # flush every second so that readers can collect
                            # the data in almost real time
                            buffer.flush()
                            self.monitor.update(
                                buffer[cursor - self.monitor.period:cursor])
                        if n_samples is not None and collected >= n_samples:
                            # early stopping
                            raise StopIteration()

        except (KeyboardInterrupt, StopIteration), e:
            if cursor > 0:
                self.trim_buffer(buffer, cursor)
            logging.info('Closing connection to %s', self.device)

        return session_id

    def list_sessions(self):
        """Return the list of recorded session ids, sorted by date"""
        sessions = os.listdir(self.data_folder)
        sessions.sort()
        return sessions

    def get_session(self, session=-1):
        """Return the aggregate data array of a session

        If the session consists in many buffers, they are concatenated into a
        single buffer loaded in memory.

        If the data is a single file, it is memmaped as an array.
        """
        sessions = self.list_sessions()
        if isinstance(session, int):
            session_id = sessions[session]
        elif session in sessions:
            session_id = session
        else:
            raise ValueError("No such session %r" % session)

        session_folder = os.path.join(self.data_folder, session_id)
        data_files = os.listdir(session_folder)
        if len(data_files) == 0:
            return np.array([])
        elif len(data_files) == 1:
            return np.memmap(os.path.join(session_folder, data_files[0]),
                             dtype=self.dtype)
        else:
            return np.concatenate([np.memmap(os.path.join(session_folder, f),
                                             dtype=self.dtype)
                                   for f in data_files])


def main():
    from .monitor import MatplotlibMonitor
    logging.basicConfig(level=logging.INFO)
    device = '/dev/rfcomm9'
    if len(sys.argv) > 1:
        device = sys.argv[1]

    collector = DataCollector(device, os.path.expanduser('~/pythinkgear_data'),
                              monitor=MatplotlibMonitor(period=128))
    session_id = collector.collect(SAMPLING_FREQUENCY * 60 * 10)
    data = collector.get_session(session_id)
    print "collected %d samples" % data.shape[0]
    print "mean: %0.3f" % data.mean()
    print "standard deviation: %0.3f" % data.std()
    pl.subplot(211)
    pl.title("Raw signal from the MindSet")
    pl.plot(data)
    pl.subplot(212)
    pl.specgram(data)
    pl.title("Spectrogram")
    pl.show()

if __name__ == '__main__':
    main()
