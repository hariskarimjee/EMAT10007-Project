import matplotlib.pyplot as plt
from scipy import signal
import numpy as np
import pyaudio, sys, threading
import tkinter as tk

BITRATE = 44100


def waveform(frequency, waveshape):
    t = 1
    f = frequency
    time = np.linspace(0, t, int(t * BITRATE))

    if waveshape == "sin":
        sig = np.array(np.sin(2 * np.pi * f * time),dtype=np.float32)
    elif waveshape == "sqr":
        sig = np.array(signal.square(2 * np.pi * f * time),dtype=np.float32)
    elif waveshape == "saw":
        sig = np.array(signal.sawtooth(2 * np.pi * f * time),dtype=np.float32)
    return sig


def play_wave(wavef):
    p = pyaudio.PyAudio()
    wav = wavef.tobytes()
    stream = p.open(format=pyaudio.paFloat32, channels=2, rate=BITRATE, output=True)
    stream.write(wav)
    stream.stop_stream()
    stream.close()
    p.terminate()


class LoopWave(threading.Thread):
    def __init__(self, master):
        super().__init__()
        self.master = master

        self.force_quit = False
        self.end_now = False

    def run(self):

        if not self.end_now:
            wave = waveform(200, "sin")
            while not self.end_now:
                play_wave(0.5 * wave)
        elif self.end_now:
            self.master.stop_sound()


class Synthesiser(tk.Tk):

    def __init__(self):
        super().__init__()

        self.start_button = tk.Button(self, text="Play sound", padx=5, pady=5, command=(lambda: self.start_sound()))
        self.start_button.pack()

        self.stop_button = tk.Button(self, text="Stop sound", padx=5, pady=5, command=(lambda: self.stop_sound()))
        self.stop_button.pack()

    def setup_worker(self):
        worker = LoopWave(self)
        self.worker = worker

    def start_sound(self):

        if not hasattr(self, "worker"):
            self.setup_worker()
            self.worker.start()


    def stop_sound(self):
        self.worker.end_now=True
        del self.worker

    def stop_sound_exit(self):
        if hasattr(self, "worker"):

            self.worker.end_now=True
            sys.exit()
        else:
            sys.exit()


root = Synthesiser()

root.protocol("WM_DELETE_WINDOW", root.stop_sound_exit)

root.mainloop()
