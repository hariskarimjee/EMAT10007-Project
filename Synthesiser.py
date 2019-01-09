import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile
import numpy as np
import pyaudio, sys, threading, math, time
import tkinter as tk


RATE = 44100
CHUNK = 1024
NOTES = {'a': 261.6, 'w': 277, 's': 293.66, 'e': 311, 'd': 329.63, 'f': 349.23, 't':370, 'g': 392, 'y': 415, 'h': 440,
         'u': 466, 'j': 493.88, 'k': 523.85, 'o': 554, 'l': 587.33, 'p': 622, ';': 659.26}
"""
:int RATE: playback sample rate
:int CHUNK: playback frame size, containing CHUNK samples
:dict NOTES: corresponding frequencies for piano style keyboard playback
"""

class LoopWave(threading.Thread):
    """
    Subclass of Thread to allow concurrent running of tkinter GUI and sound playback in seperate threads

    :method run: Loop to playback audio in seperate thread
    """
    def __init__(self, master, frequency):
        """
        Initialise class
        :param master: Master tk window
        :param frequency: frequency of playback
        """
        super().__init__()
        self.master = master
        self.frequency = frequency
        self.force_quit = False
        self.end_now = False

    def run(self):
        """
        Loops audio from waveform in seperate thread from tkinter GUI
        """
        p = pyaudio.PyAudio()

        def callback(in_data, frame_count, time_info, status):
            """

            :param in_data: PyAudio backend usage
            :param frame_count: PyAudio backend usage
            :param time_info: PyAudio backend usage
            :param status: PyAudio backend usage
            :return: frame of data, continue instruction for PyAudio
            """
            data = np.array(self.master.output_waveform(self.frequency)).astype(np.float32).tostring()
            return data, pyaudio.paContinue

        # Create pyaudio stream
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
    Subclass of Tk, adds widgets for synthesiser control.
    :method setup_worker: Creates new LoopWave thread, assigns as class attribute
    :method start_sound: Run on button press, creates worker if one doesn't exist, starts wave sound loop
    :method stop_sound: Run on button press, stops wave sound loop, deletes worker so future worker can be created
    :method stop_sound_exit: Run when close button pressed, ends thread if necessary
    """
    def __init__(self):
        super().__init__()

        # Create operator grid
        self.op_list = []
        for i in range(0,6):
            self.op_list.append([])
            for j in range(0,6):
                self.op_list[i].insert(j, Operator(self))

        # Create shape radiobuttons
        self.shape_list = [("sine", "sin", 0), ("triangular", "tri", 1)]
        self.wave_shape = tk.StringVar()
        self.wave_shape.set("sin")
        for shape, shp, row in self.shape_list:
            tk.Radiobutton(self, text=shape, variable=self.wave_shape, value=shp).grid(row=row, column=2)

        # Create sliders to control frequency, volume, modulator
        self.frequency_slider = tk.Scale(self, from_=150, to_=0.1, resolution=0.1, bigincrement=1, label="Frequency",
                                         orient=tk.VERTICAL, length=400)
        self.frequency_slider.grid(row=0,rowspan=5, column=5, columnspan=2)
        self.frequency_slider.set(10)
        self.volume_slider = tk.Scale(self, from_=1, to_=0, resolution=0.05, label="Volume",
                                      orient=tk.VERTICAL, length=400)
        self.volume_slider.grid(row=0,rowspan=5,column=3,columnspan=2)
        self.volume_slider.set(1)
        self.modulation_slider = tk.Scale(self, from_=10, to_=1, label="Modulation Index",
                                          orient=tk.VERTICAL, length=400)
        self.modulation_slider.grid(row=0, column=16, rowspan=5, columnspan=2)
        self.modulation_slider.set(5)

        # Modulator control canvas
        self.mod_canvas = tk.Canvas(self, width=430, height=430, bg="white")
        self.mod_canvas.grid(row=0, column=11, rowspan=10, columnspan=5)
        for i in range(6):
            for j in range(6):
                tag = str(i) + "," + str(j)
                self.mod_canvas.create_rectangle(((i + 1) * 10 + i * 60), ((j + 1) * 10 + j * 60),
                                                 ((i + 1) * 70, ((j + 1) * 70)), fill="gray", tags=tag)
                self.mod_canvas.tag_bind(tag, "<Button-1>", lambda event=None, q = tag: self.activate_op(q))
                self.mod_canvas.tag_bind(tag, "<Button-3>", lambda event=None, q = tag: self.deactivate_op(q))
                if j == 0:
                    self.mod_canvas.itemconfig(tag, fill="white", activefill="light gray")

        # Keyboard mapping to notes
        self.bind("<KeyPress>", self.start_sound)
        self.bind("<KeyRelease>", lambda event=None: self.stop_sound())

    def setup_worker(self, frequency):
        """
        Create new thread to play sound concurrently to GUI, creates class attribute "worker" for control
        :param frequency: frequency of note to be played
        :return: None
        """
        if not hasattr(self, "worker"):
            worker = LoopWave(self, frequency)
            self.worker = worker

    def start_sound(self, event):
        """
        Create worker, start sound outpit
        :param event: Key pressed, corresponds to dictionary frequency
        :return: None
        """
        if not hasattr(self, "worker"):
            self.setup_worker(NOTES[event.char.lower()])
            self.worker.start()

    def stop_sound(self):
        """
        Stop sound if worker exists
        :return: None
        """
        if hasattr(self, "worker"):
            self.worker.end_now = True
            del self.worker

    def stop_sound_exit(self):
        """
        Stop sound safely on exit window
        :return: None
        """
        if hasattr(self, "worker"):
            self.worker.end_now=True
            sys.exit()
        else:
            sys.exit()

    def activate_op(self, tag):
        """
        Activate operator and set necessary attributes
        :param tag: Corresponding square on canvas widget to operator
        :return: None
        """
        i = int(tag[0])
        j = int(tag[2])
        if (j == 0 and not self.op_list[i][j].active) or self.op_list[i][j-1].active:
            if j == 0:
                self.op_list[i][j] = Operator(self, None, self.volume_slider.get(), self.wave_shape.get())
                self.op_list[i][j].activate(tag)
            elif j > 0 and not self.op_list[i][j].active:
                self.op_list[i][j] = Operator(self, self.frequency_slider.get(), self.volume_slider.get(),
                                              self.wave_shape.get())
                self.op_list[i][j].activate(tag)
                self.op_list[i][j-1].modulator = self.op_list[i][j]
                self.op_list[i][j-1].mod_amp = self.modulation_slider.get()
            elif j > 0 and self.op_list[i][j].active:
                modamp = self.op_list[i][j].mod_amp
                self.op_list[i][j] = Operator(self, self.frequency_slider.get(), self.volume_slider.get(),
                                              self.wave_shape.get(), active=True)
                self.op_list[i][j].modulator = self.op_list[i][j+1]
                self.op_list[i][j - 1].modulator = self.op_list[i][j]
                self.op_list[i][j].mod_amp = modamp
        elif j == 0 and self.op_list[i][j].active:
            modamp = self.op_list[i][j].mod_amp
            self.op_list[i][j] = Operator(self, None, self.volume_slider.get(), self.wave_shape.get(), active=True)
            self.op_list[i][j].modulator = self.op_list[i][j+1]
            self.op_list[i][j].mod_amp = modamp

    def deactivate_op(self, tag):
        """
        Deactivate operator and remove necessary attributes
        :param tag: Corresponding square on canvas widget to operator
        :return: None
        """
        i = int(tag[0])
        j = int(tag[2])
        if self.op_list[i][j].active:
            self.op_list[i][j].deactivate(tag)
            self.op_list[i][j-1].modulator = np.zeros(CHUNK)
            self.mod_canvas.itemconfig(tag, fill="white", activefill="light gray")
            for k in range(j + 1, 6):
                self.op_list[i][k] = Operator(self)
                self.op_list[i][k].deactivate(tag[0:2] + str(k))

    def output_waveform(self, frequency):
        """
        Adds all active carrier waveforms together
        :param frequency: Frequency of note for playback
        :return: Numpy array containing audio data
        """
        self.op_list[0][0].frequency = frequency
        outwave = self.op_list[0][0].waveform()
        v = 1
        for ops in self.op_list[1:]:
            if ops[0].active:
                ops[0].frequency = frequency
                outwave = np.add(ops[0].waveform(), outwave)
                v += 1
        return self.volume_slider.get() * 1/v * outwave


class Operator:
    """
    Stores information required to generate smooth wave

    :method waveform: generates waveform based on class attributes

    """
    def __init__(self, master, frequency=None, volume=1, shape=None, modulator=np.zeros(CHUNK), active=False):
        """
        Initialise class
        :param master: Master tk window
        :param frequency: Frequency of wave playback
        :param volume: Volume of waveform
        :param shape: Shape of waveform
        :param modulator: Modulating operator, by default empty array
        :param active: Wave activator
        """
        self.master = master
        self.frequency = frequency
        self.volume = volume
        self.shape = shape
        self.phase = 0
        self.t = np.linspace(0, CHUNK / RATE, CHUNK)
        self.modulator = modulator
        self.mod_amp = 1
        self.active = active

    def waveform(self):
        """
        Generates wave as ndarray with properties depending on class attributes
        :return: ndarray containing wave data
        """
        f = self.frequency
        if type(self.modulator) == np.ndarray:
            if self.shape == "sin":
                sig = self.volume * (np.sin(2 * np.pi * (f * self.t + self.phase)))
                self.phase = math.modf(f * (CHUNK + 1) / RATE + self.phase)[0]
            elif self.shape == "tri":
                sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * self.t + self.phase), width=0.5),
                                             dtype=np.float32)
                self.phase = math.modf(f * (CHUNK + 1) / RATE + self.phase)[0]
            else:
                sig = np.zeros(CHUNK)
            return sig
        elif type(self.modulator) == Operator:
            if self.shape == "sin":
                sig = self.volume * (np.sin(2 * np.pi * (f * self.t + self.phase) + self.mod_amp *
                                            self.modulator.waveform()))
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "tri":
                sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * self.t + self.phase) + self.mod_amp *
                                                             self.modulator.waveform(), width=0.5), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            else:
                sig = np.zeros(CHUNK)
            return sig

    def activate(self, tag):
        """
        Activates operator corresponding to tag, sets square properties
        :param tag: Corresponding square on canvas widget to operator
        """
        self.active = True
        self.master.mod_canvas.itemconfig(tag, fill="yellow", activefill="#fcffa5")
        active_next_tag = tag[0:2] + str(int(tag[2]) + 1)
        self.master.mod_canvas.itemconfig(active_next_tag, fill="white", activefill="light gray")

    def deactivate(self, tag):
        """
        Deactivates operator corresponding to tag, sets square properties
        :param tag: Corresponding square on canvas widget to operator
        """
        if tag == "0,0":
            self.master.stop_sound()
        self.master.mod_canvas.itemconfig(tag, fill="gray", activefill="gray")
        self.active = False
        self.modulator = np.zeros(CHUNK)
        self.shape = None


# Create Synthesiser object
root = Synthesiser()

# Stop LoopAudio thread on window exit
root.protocol("WM_DELETE_WINDOW", root.stop_sound_exit)

root.mainloop()
