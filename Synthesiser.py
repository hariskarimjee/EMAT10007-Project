import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile
import numpy as np
import pyaudio, sys, threading, math, time
import tkinter as tk

BITRATE = 44100
CHUNK = 1024

phase = 0

def waveform(frequency, waveshape):
    """
    Generates wave as data array - frequency of datapoints dependend on bitrate (quality of waveform)
    :param frequency: Frequency of wave
    :param waveshape: Shape of wave (square, sine, sawtooth)
    :return: Returns array containing wave data
    """
    global phase
    ti = 1
    f = frequency
    t = np.linspace(0, ti, int(ti * BITRATE))

    if waveshape == "sin":
        sig = (np.sin(2 * np.pi * (f * t + phase)))
        phase = math.modf(f * CHUNK / BITRATE)[0]
    elif waveshape == "sqr":
        sig = np.array(signal.square(2 * np.pi * (f * t + phase)),dtype=np.float32)
        phase = math.modf(f * CHUNK / BITRATE)[0]
    elif waveshape == "saw":
        sig = np.array(signal.sawtooth(2 * np.pi * (f * t + phase)),dtype=np.float32)
        phase = math.modf(f * CHUNK / BITRATE)[0]
    elif waveshape == "tri":
        sig = np.array(signal.sawtooth(2 * np.pi * (f * t + phase), width=0.5), dtype = np.float32)
        phase = math.modf(f * CHUNK / BITRATE)[0]

    return sig


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
        if not self.end_now:
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paFloat32, channels=2, rate=BITRATE, output=True, frames_per_buffer=CHUNK)
            while not self.end_now:
                stream.write(np.array(self.master.output_waveform()).astype(np.float32).tostring())
            stream.stop_stream()
            stream.close()
            p.terminate()
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
        self.frequency = tk.IntVar()
        self.frequency.set(220)
        self.wave_list = []
        self.shape_list = [("sine", "sin"), ("square", "sqr"), ("sawtooth", "saw"), ("triangular", "tri")]
        self.wave_shape = tk.StringVar()
        self.wave_shape.set("sin")
        # Create sound, wave control buttons
        self.start_button = tk.Button(self, text="Play sound", padx=5, pady=5, command=(lambda: self.start_sound()))
        self.start_button.pack()

        self.stop_button = tk.Button(self, text="Stop sound", padx=5, pady=5, command=(lambda: self.stop_sound()))
        self.stop_button.pack()

        self.add_wave_button = tk.Button(self, text="Add wave", padx=5, pady=5,
                                         command=(lambda: self.add_wave(int(self.frequency_slider.get()),
                                                                        self.wave_shape.get(),
                                                                        self.volume_slider.get())))
        self.add_wave_button.pack()

        self.remove_wave_button = tk.Button(self, text="Remove wave", padx=5, pady=5,
                                            command = lambda: self.remove_wave(self.wave_list_box.curselection()[0]))
        self.remove_wave_button.pack()

        self.clear_button = tk.Button(self, text="Clear waves", padx=5, pady=5, command=(lambda: self.clear_waves()))
        self.clear_button.pack()

        # Create Radiobuttons for selecting wave shape
        for shape, shp in self.shape_list:
            tk.Radiobutton(self, text=shape, variable=self.wave_shape, value=shp).pack()

        # Create sliders to control frequency, volume
        self.frequency_slider = tk.Scale(self, from_=1, to_=500, label="Frequency", orient=tk.HORIZONTAL, length=200, variable=self.frequency)
        self.frequency_slider.pack()
        self.volume_slider = tk.Scale(self, from_=0, to_=1, resolution=0.05, label="Volume", orient=tk.HORIZONTAL, length=200)
        self.volume_slider.pack()
        self.volume_slider.set(1)

        self.wave_list_box = tk.Listbox()
        self.wave_list_box.pack()

    def setup_worker(self):

        worker = LoopWave(self)
        self.worker = worker

    def start_sound(self):

        if not hasattr(self, "worker"):
            self.setup_worker()
            self.worker.start()

    def stop_sound(self):

        self.worker.end_now = True
        del self.worker

    def stop_sound_exit(self):
        if hasattr(self, "worker"):

            self.worker.end_now=True
            sys.exit()
        else:
            sys.exit()

    def add_wave(self, frequency, shape, volume):
        self.wave_list.append(volume * waveform(frequency, shape))
        self.wave_list_box.insert(tk.END, "Freq: " + str(frequency) + "Hz" + " " + "Shape: " + str(shape))

    def remove_wave(self, wave_index):
        del self.wave_list[wave_index]
        self.wave_list_box.delete(wave_index)

    def clear_waves(self):
        self.wave_list = []
        self.wave_list_box.delete(0,tk.END)

    def plot_waveform(self):
        plt.plot(self.output_waveform())
        plt.show()

    def output_waveform(self):
        wave = self.wave_list[0]
        for wavef in self.wave_list[1:]:
            wave = np.add(wave, wavef)
        return (1/len(self.wave_list))*wave


root = Synthesiser()

root.protocol("WM_DELETE_WINDOW", root.stop_sound_exit)

root.mainloop()
