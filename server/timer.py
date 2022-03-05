import time


class Timer(object):
    TIMER_Timeout = -1

    def __init__(self, runtime):
        self.staring_time = self.TIMER_Timeout
        self.runtime = runtime

    def isRunning(self):
        return self.staring_time != self.TIMER_Timeout

    def wasTimeout(self):
        if not self.isRunning():
            return False
        else:
            return time.time() - self.staring_time >= self.runtime

    def startTimer(self):
        if self.staring_time == self.TIMER_Timeout:
            self.staring_time = time.time()

    def stopTimer(self):
        if self.staring_time != self.TIMER_Timeout:
            self.staring_time = self.TIMER_Timeout

