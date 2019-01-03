import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile
import numpy as np
import pyaudio, sys, threading, math, time
import tkinter as tk

RATE = 44100
CHUNK = 2048

con = 0




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
        p = pyaudio.PyAudio()

        def callback(in_data, frame_count, time_info, status):
            data = np.array(self.master.output_waveform()).astype(np.float32).tostring()
            return data, pyaudio.paContinue

        stream = p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=RATE,
                        output=True,
                        stream_callback=callback,
                        frames_per_buffer=CHUNK
                        )

        if not self.end_now:

            stream.start_stream()
            while not self.end_now:
                time.sleep(0.01)
            stream.stop_stream()
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
        self.harmonic_list = []
        self.harmonic_number = len(self.harmonic_list)
        self.shape_list = [("sine", "sin", 0), ("square", "sqr", 1), ("sawtooth", "saw", 2), ("triangular", "tri", 3)]
        self.wave_shape = tk.StringVar()
        self.wave_shape.set("sin")
        # Create sound, wave control buttons
        self.start_button = tk.Button(self, text="Play sound", padx=5, pady=5, command=(lambda: self.start_sound()))
        self.start_button.grid(row=0, column=0)

        self.stop_button = tk.Button(self, text="Stop sound", padx=5, pady=5, command=(lambda: self.stop_sound()))
        self.stop_button.grid(row=1, column=0)

        self.plot_button = tk.Button(self, text="Plot wave", padx=5, pady=5, command=(lambda: self.plot_wave()))
        self.plot_button.grid(row=2, column=0)

        self.add_wave_button = tk.Button(self, text="Add harmonic", padx=5, pady=5,
                                         command=(lambda: self.add_harmonic()))
        self.add_wave_button.grid(row=0, column=1)

        self.remove_wave_button = tk.Button(self, text="Remove wave", padx=5, pady=5,
                                            command = lambda: self.remove_wave())
        self.remove_wave_button.grid(row=1, column=1)

        self.clear_button = tk.Button(self, text="Clear waves", padx=5, pady=5, command=(lambda: self.clear_waves()))
        self.clear_button.grid(row=2, column=1)

        # Create Radiobuttons for selecting wave shape

        for shape, shp, row in self.shape_list:
            tk.Radiobutton(self, text=shape, variable=self.wave_shape, value=shp).grid(row=row, column=2)

        # Create sliders to control frequency, volume
        self.frequency_slider = tk.Scale(self, from_=1, to_=500, label="Frequency", orient=tk.VERTICAL, length=200)
        self.frequency_slider.grid(row=0,rowspan=5, column=3, columnspan=2)
        self.frequency_slider.set(220)
        self.volume_slider = tk.Scale(self, from_=1, to_=0, resolution=0.05, label="Volume", orient=tk.VERTICAL, length=200)
        self.volume_slider.grid(row=0,rowspan=5,column=5,columnspan=2)
        self.volume_slider.set(1)

    def setup_worker(self):

        worker = LoopWave(self)
        self.worker = worker

    def start_sound(self):
        if len(self.harmonic_list) == 0:
            self.harmonic_list.append(Wave(self.frequency_slider.get(), self.volume_slider.get(), self.wave_shape.get(), 0))
        if not hasattr(self, "worker") and len(self.harmonic_list) > 0:
            self.setup_worker()
            self.worker.start()

    def stop_sound(self):
        if hasattr(self, "worker"):
            self.worker.end_now = True
            del self.worker

    def stop_sound_exit(self):
        if hasattr(self, "worker"):
            self.worker.end_now=True
            sys.exit()
        else:
            sys.exit()

    def add_harmonic(self):
        volume = 1/2**self.harmonic_number
        print(volume)
        self.harmonic_list.append(Wave((2 ** self.harmonic_number) * self.frequency_slider.get(),
                                       volume * self.volume_slider.get(),
                                       self.wave_shape.get(),
                                       0))
        self.harmonic_number += 1

    def remove_wave(self):
        del self.harmonic_list[self.harmonic_number]
        self.harmonic_number -= 1

    def clear_waves(self):
        self.stop_sound()
        self.harmonic_list = []
        self.harmonic_number = 0

    def output_waveform(self):
        outwave = self.harmonic_list[0].waveform()
        if len(self.harmonic_list) > 1:
            for wave in self.harmonic_list[1:]:
                outwave = np.add(wave.waveform(), outwave)
        return (1/len(self.harmonic_list)) * outwave

    def plot_wave(self):
        plt.plot(self.output_waveform())
        plt.show()


class Wave():
    def __init__(self, frequency, volume, shape, phase):
        self.frequency = frequency
        self.volume = volume
        self.shape = shape
        self.phase = phase

    def waveform(self):
        """
        Generates wave as data array - frequency of datapoints dependent on rate (quality of waveform)
        :param frequency: Frequency of wave
        :param waveshape: Shape of wave (square, sine, sawtooth)
        :return: Returns array containing wave data
        """
        ti = CHUNK / RATE

        t = np.linspace(0, ti, int(ti * RATE))
        f = self.frequency

        if self.shape == "sin":
            sig = self.volume * (np.sin(2 * np.pi * (f * t + self.phase)))
            self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
        elif self.shape == "sqr":
            sig = self.volume * np.array(signal.square(2 * np.pi * (f * t + self.phase)), dtype=np.float32)
            self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
        elif self.shape == "saw":
            sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * t + self.phase)), dtype=np.float32)
            self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
        elif self.shape == "tri":
            sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * t + self.phase), width=0.5), dtype=np.float32)
            self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
        return sig




root = Synthesiser()

# Stop LoopAudio thread on window exit
root.protocol("WM_DELETE_WINDOW", root.stop_sound_exit)

root.mainloop()
