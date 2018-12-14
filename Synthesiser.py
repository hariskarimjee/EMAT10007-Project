import matplotlib.pyplot as plt
from scipy import signal
import numpy as np
import pyaudio, sys, threading
import tkinter as tk

BITRATE = 44100


def waveform(frequency, waveshape):
    """
    Generates wave as data array - frequency of datapoints dependend on bitrate (quality of waveform)
    :param frequency: Frequency of wave
    :param waveshape: Shape of wave (square, sine, sawtooth)
    :return: Returns array containing wave data
    """
    t = 2
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
    """
    Streams wave to audio output using PyAudio
    :param wavef: Array containing wave data
    :return:
    """
    p = pyaudio.PyAudio()
    wav = wavef.tobytes()
    stream = p.open(format=pyaudio.paFloat32, channels=2, rate=BITRATE, output=True)
    stream.write(wav)
    stream.stop_stream()
    stream.close()
    p.terminate()


class LoopWave(threading.Thread):
    """
    Subclass of Thread to allow concurrent running of tkinter GUI and sound playback in seperate threads

    :method run: Loop to playback audio in seperate thread
    """
    def __init__(self, master):
        super().__init__()
        self.master = master

        self.force_quit = False
        self.end_now = False

    def run(self):
        """
        Loops audio from waveform in seperate thread from tkinter GUI
        """
        wave = waveform(200, "sin")
        if not self.end_now:
            while not self.end_now:
                play_wave(0.5 * wave)
        elif self.end_now:
            self.master.stop_sound()


class Synthesiser(tk.Tk):
    """
    Subclass of Tk which adds widgets for synthesiser control.

    :method setup_worker: Creates new LoopWave thread, assigns as class attribute
    :method start_sound: Run on button press, creates worker if one doesn't exist, starts wave sound loop
    :method stop_sound: Run on button press, stops wave sound loop, deletes worker so future worker can be created
    :method stop_sound_exit: Run when close button pressed, ends thread if necessary
    """
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
