# Copyright (c) 2011, Olivier Grisel
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#     * Neither the name of the Kai Groner nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Interface module to dump raw packet into numpy arrays for analysis"""

import logging
import sys
import os
from datetime import datetime

import numpy as np
import pylab as pl

from .thinkgear import ThinkGearProtocol
from .thinkgear import ThinkGearRawWaveData


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
                 protocol=ThinkGearProtocol, packet_type=ThinkGearRawWaveData):
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        self.data_folder = data_folder
        self.device = device
        self.prefix = prefix
        self.dtype = dtype
        self.chunk_size = chunk_size
        self.protocol = protocol
        self.packet_type = packet_type

    def get_timestamp(self):
        """Up to the second, filename same timestamp"""
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def make_buffer(self):

        # build a non existing filename based on a timestamp and a integer
        # increment
        ts = self.get_timestamp()
        incr = 0
        while True:
            filename = self.prefix + ts + '_%03d.memmap' % incr
            filepath = os.path.join(self.data_folder, filename)
            if os.path.exists(filepath):
                incr += 1
            else:
                break

        buffer = np.memmap(filepath, dtype=self.dtype, mode='w+',
                           shape=(self.chunk_size,))
        # set all the buffer values to zero to be able to detect partially
        # filled buffers
        buffer[:] = 0.0
        return buffer

    def check_buffer(self, cursor, buffer):
        """Check that the cursor is not overflowing the buffer

        Close the current buffer and create a new one with the cursor at
        the beginning in case of overflow.
        """
        if cursor >= buffer.shape[0]:
            buffer.flush()
            buffer = self.make_buffer()
            cursor = 0
        return cursor, buffer

    def collect(self, n_samples=None):
        """Collect samples from the device using the protocol instance

        Instance are buffered in memory mapped arrays of fixed size.
        """
        collected = 0
        logging.info("Opening connection to %s", self.device)
        cursor = 0
        buffer = self.make_buffer()
        try:
            for pkt in self.protocol(self.device).get_packets():
                cursor, buffer = self.check_buffer(cursor, buffer)
                for d in pkt:
                    if isinstance(d, self.packet_type):
                        buffer[cursor] = d.value
                        cursor += 1
                        collected += 1
                        if cursor % SAMPLING_FREQUENCY == 0:
                            # flush every second so that readers can collect
                            # the data in almost real time
                            buffer.flush()
                        cursor, buffer = self.check_buffer(cursor, buffer)
                        if n_samples is not None and collected > n_samples:
                            # early stopping
                            raise StopIteration()

        except (KeyboardInterrupt, StopIteration), e:
            buffer.flush()
            logging.info('Closing connection to %s', self.device)


def main():
    logging.basicConfig(level=logging.INFO)
    device = '/dev/rfcomm9'
    if len(sys.argv) > 1:
        device = sys.argv[1]

    collector = DataCollector(device, os.path.expanduser('~/pythinkgear_data'))
    collector.collect()
    #pl.subplot(211)
    #pl.title("Raw signal from the MindSet")
    #pl.plot(data)
    #pl.subplot(212)
    #pl.specgram(data)
    #pl.title("Spectrogram")
    #pl.show()

if __name__ == '__main__':
    main()

