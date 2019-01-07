import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import wavfile
import numpy as np
import pyaudio, sys, threading, math, time
import tkinter as tk
from tkinter import messagebox

RATE = 44100
CHUNK = 2048

con = 0
# mod_index = int()



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
        self.op_list = []
        self.shape_list = [("sine", "sin", 0), ("square", "sqr", 1), ("sawtooth", "saw", 2), ("triangular", "tri", 3)]
        self.wave_shape = tk.StringVar()
        self.wave_shape.set("sin")
        # Create sound control buttons
        self.start_button = tk.Button(self, text="Play sound", padx=5, pady=5, command=(lambda: self.start_sound()))
        self.start_button.grid(row=0, column=0)
        self.stop_button = tk.Button(self, text="Stop sound", padx=5, pady=5, command=(lambda: self.stop_sound()))
        self.stop_button.grid(row=1, column=0)
        # Create plot wave button
        self.plot_button = tk.Button(self, text="Plot wave", padx=5, pady=5, command=(lambda: self.plot_wave()))
        self.plot_button.grid(row=2, column=0)
        # Wave modulation section

        self.add_op_button = tk.Button(self, text="Add operator", padx=5, pady=5, command=(lambda: self.add_op(self.frequency_slider.get(), self.volume_slider.get(), self.wave_shape.get(), phase=0)))
        self.add_op_button.grid(row=0, column=8)
        self.remove_op_button = tk.Button(self, text="Remove operator", padx=5, pady=5, command=(lambda: self.remove_op(self.op_listbox.curselection()[0])))
        self.remove_op_button.grid(row=1, column=8)
        self.modulate_op_button = tk.Button(self, text="Modulate operator", padx=5, pady=5, command=(lambda: self.modulate_op(self.op_list[self.op_listbox.curselection()[0]])))
        self.modulate_op_button.grid(row=2, column=8)
        self.op_listbox = tk.Listbox(self)
        self.op_listbox.grid(row=0, column=9, rowspan=7, columnspan=2)

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
        if not hasattr(self, "worker") and self.op_listbox.curselection():
            self.setup_worker()
            self.worker.start()
        elif not self.op_listbox.curselection():
            messagebox.showinfo("Error", "Please select an operator to play")

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

    def add_op(self, frequency, volume, shape, phase):
        self.op_list.append(Operator(frequency, volume, shape, phase))
        self.op_listbox.insert(tk.END, ("Freq=%sHz" % frequency, "Shape=%s" % shape))

    def remove_op(self, op_index):
        del self.op_list[op_index]
        self.op_listbox.delete(op_index)

    def modulate_op(self, carrier):
        self.mod_index = int()
        self.mod_amp = int()
        mod = ModulatorSelect(self)
        root.wait_window(mod)
        carrier.modulator = self.op_list[self.mod_index]
        carrier.mod_amp = self.mod_amp

    def output_waveform(self):
        outwave = self.op_list[self.op_listbox.curselection()[0]].waveform()
        return outwave

    def plot_wave(self):
        plt.plot(np.concatenate((self.output_waveform(), self.output_waveform())))
        plt.show()


class Operator:
    """
    Stores information required to generate smooth wave

    :method waveform: generates waveform based on class attributes
    """
    def __init__(self, frequency, volume, shape, phase=0, modulator=np.zeros(CHUNK)):
        self.frequency = frequency
        self.volume = volume
        self.shape = shape
        self.phase = phase
        self.t = np.linspace(0, CHUNK / RATE, int(CHUNK))
        self.modulator = modulator
        self.mod_amp = 1

    def waveform(self):
        """
        Generates wave as ndarray - frequency of datapoints dependent on rate

        :return: Returns ndarray containing wave data
        """
        f = self.frequency
        if type(self.modulator) == np.ndarray:
            if self.shape == "sin":
                sig = self.volume * (np.sin(2 * np.pi * (f * self.t + self.phase)))
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "sqr":
                sig = self.volume * np.array(signal.square(2 * np.pi * (f * self.t + self.phase)), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "saw":
                sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * self.t + self.phase)), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "tri":
                sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * self.t + self.phase), width=0.5), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            else:
                sig = np.zeros(CHUNK)
            return sig
        elif type(self.modulator) == Operator:
            if self.shape == "sin":
                sig = self.volume * (np.sin(2 * np.pi * (f * self.t + self.phase) + self.mod_amp * self.modulator.waveform()))
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "sqr":
                sig = self.volume * np.array(signal.square(2 * np.pi * (f * self.t + self.phase) + self.mod_amp * self.modulator.waveform()), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "saw":
                sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * self.t + self.phase) + self.mod_amp * self.modulator.waveform()), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            elif self.shape == "tri":
                sig = self.volume * np.array(signal.sawtooth(2 * np.pi * (f * self.t + self.phase) + self.mod_amp * self.modulator.waveform(), width=0.5), dtype=np.float32)
                self.phase = math.modf(f * CHUNK / RATE + self.phase)[0]
            else:
                sig = np.zeros(CHUNK)
            return sig


class ModulatorSelect(tk.Toplevel):
    def __init__(self, master):
        super().__init__()
        self.master = master

        self.op_box = tk.Listbox(self)
        self.op_box.grid(row=0, column=0)
        for op in self.master.op_list:
            self.op_box.insert(tk.END, ("Freq=%sHz" % op.frequency, "Shape=%s" % op.shape))

        self.ok_button = tk.Button(self, text="OK", padx=5, pady=5, command=(lambda: self.exit()))
        self.ok_button.grid(row=1, column=0, rowspan=2)

        self.amp_slider = tk.Scale(self, from_=20, to_=1, label="Modulation amplitude", orient=tk.VERTICAL, length=200)
        self.amp_slider.grid(row=0,column=2)

    def exit(self):
        self.master.mod_index = self.op_box.curselection()[0]
        self.master.mod_amp = self.amp_slider.get()
        self.destroy()


root = Synthesiser()

# Stop LoopAudio thread on window exit
root.protocol("WM_DELETE_WINDOW", root.stop_sound_exit)

root.mainloop()
