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

import numpy as np
import pylab as pl
import logging
import sys

from .thinkgear import ThinkGearProtocol
from .thinkgear import ThinkGearRawWaveData

# The Mindset samples at 512Hz
BUFFER_SIZE = 512 * 10


def collect_buffer(device, buffer_size=BUFFER_SIZE):
    logging.info("Opening connection to %s", device)
    raw_signal_buffer = np.empty(buffer_size)

    i = 0
    for pkt in ThinkGearProtocol(device).get_packets():
        if i == raw_signal_buffer.shape[0]:
            break
        for d in pkt:
            if isinstance(d, ThinkGearRawWaveData):
                raw_signal_buffer[i] = d.value
                i += 1
                if i == raw_signal_buffer.shape[0]:
                    break
    return raw_signal_buffer

def main():
    logging.basicConfig(level=logging.INFO)
    device = '/dev/rfcomm9'
    if len(sys.argv) > 1:
        device = sys.argv[1]

    b = collect_buffer(device)
    pl.subplot(211)
    pl.title("Raw signal from the MindSet")
    pl.plot(b)
    pl.subplot(212)
    pl.specgram(b)
    pl.title("Spectrogram")
    pl.show()

if __name__ == '__main__':
    main()

