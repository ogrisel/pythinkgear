import time
import threading
import gobject

import numpy as np
import matplotlib.pyplot as plt



class MatplotlibMonitor(object):
    """Periodically draw a windowing updated view of the signal"""

    def __init__(self, period=128, window_size=4096):
        self.window_size = window_size
        self.period = period

    def init(self, collector):
        self.collector = collector
        fig = plt.figure()
        self.ax = fig.add_subplot(111)
        self.canvas = fig.canvas
        self.ax.grid() # to ensure proper background restore

        # create the initial line
        rng = np.random.RandomState(42)
        self.window = np.zeros(self.window_size)
        self.window[0] = 1000.0
        self.window[1] = -1000.0
        self.line, = self.ax.plot(np.arange(self.window_size),
                                  self.window, animated=True, lw=2)
        self.canvas.draw()
        self.background = None
        fig.canvas.mpl_connect('draw_event', self.on_draw)

        class AsyncDisplay(threading.Thread):
            def run(self):
                plt.show()
        AsyncDisplay().start()

    def update(self, data_slice):
        self.window = np.concatenate(
            (self.window, data_slice))[-self.window_size:]

    def on_draw(self, event):
        background = self.canvas.copy_from_bbox(self.ax.bbox)
        if self.background is None:
            gobject.idle_add(self.update_line)
        self.background = background

    def update_line(self, *args):
        if self.background is None:
            return True

        # restore the clean slate background
        self.canvas.restore_region(self.background)

        # update the data
        #print self.window.mean()
        #print self.window.std()
        self.line.set_ydata(self.window)

        # just draw the animated artist
        self.ax.draw_artist(self.line)

        # just redraw the axes rectangle
        self.canvas.blit(self.ax.bbox)
        time.sleep(0.100)

        return True
