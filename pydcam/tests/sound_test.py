

import sys
import time
from pysinewave import SineWave, BeatWave, BeatWaveGenerator, SineWaveGenerator
import numpy
# from scipy import signal
# import pygame
# from matplotlib import pyplot

def plot_wave():
    swg = SineWaveGenerator(12,10)
    bwg = BeatWaveGenerator(12,50,10)

    pyplot.plot(swg.next_data(44100))
    pyplot.plot(bwg.next_data(44100))
    pyplot.show()

def play_beat():
    sw = BeatWave(12,50,3)

    sw.play()

    time.sleep(1)

    # for i in range(40):
    #     sw.set_beat_frequency(5+2*i)
    #     time.sleep(0.1)
    # j = 5+2*i
    # for i in range(40):
    #     sw.set_beat_frequency(j-2*i)
    #     time.sleep(0.1)

    sw.set_beat_frequency(5)

    time.sleep(1)

    sw.set_beat_frequency(10)

    time.sleep(2)

    sw.set_beat_frequency(25)

    time.sleep(2)

    sw.set_pitch(5)

    time.sleep(2)

    sw.stop()

def play_tone():
    bw = BeatWave(12,5,50)
    sw = SineWave(12,50)

    bw.play()

    time.sleep(1)

    # for i in range(40):
    #     sw.set_beat_frequency(5+2*i)
    #     time.sleep(0.1)
    # j = 5+2*i
    # for i in range(40):
    #     sw.set_beat_frequency(j-2*i)
    #     time.sleep(0.1)

    bw.set_beat_frequency(0)

    time.sleep(1)

    bw.stop()
    sw.play()

    time.sleep(1)

    sw.stop()
    bw.play()

    time.sleep(1)

    bw.set_pitch(5)

    time.sleep(1)

    bw.set_pitch(10)

    time.sleep(2)

    bw.set_pitch(-7)

    time.sleep(1)

    bw.set_beat_frequency(10)

    time.sleep(2)

    bw.set_pitch(5)

    time.sleep(2)

    bw.stop()

def pygame_test():

    sampleRate = 44100
    freq1 = 300
    freq2 = 301

    pygame.mixer.init(44100,-16,2,512)
    # sampling frequency, size, channels, buffer

    # Sampling frequency
    # Analog audio is recorded by sampling it 44,100 times per second, 
    # and then these samples are used to reconstruct the audio signal 
    # when playing it back.

    # size
    # The size argument represents how many bits are used for each 
    # audio sample. If the value is negative then signed sample 
    # values will be used.

    # channels
    # 1 = mono, 2 = stereo

    # buffer
    # The buffer argument controls the number of internal samples 
    # used in the sound mixer. It can be lowered to reduce latency, 
    # but sound dropout may occur. It can be raised to larger values
    # to ensure playback never skips, but it will impose latency on sound playback. 

    arr0 = numpy.array([4096 * numpy.sin(2.0 * numpy.pi * freq1 * x / sampleRate) for x in range(0, sampleRate)]).astype(numpy.int16)

    arr2 = numpy.array([4096 * numpy.sin(2.0 * numpy.pi * freq2 * x / sampleRate) for x in range(0, sampleRate)]).astype(numpy.int16)

    # arr2 = numpy.abs(arr2)

    # arr2n = arr2/numpy.amax(arr2)

    # arr = (arr0*arr2n).astype(numpy.int16)
    arr = arr0+arr2

    pyplot.plot(arr0)
    pyplot.plot(arr2+arr0)
    pyplot.show()
    # ddd
    
    arr2 = numpy.c_[arr,arr]
    sound = pygame.sndarray.make_sound(arr2)
    sound.play(-1)
    pygame.time.delay(4000)
    sound.stop()

    freq2 = 304

    arr2 = numpy.array([4096 * numpy.sin(2.0 * numpy.pi * freq2 * x / sampleRate) for x in range(0, sampleRate)]).astype(numpy.int16)

    arr = arr0+arr2



    # arr2 = numpy.array([4096 * numpy.sin(2.0 * numpy.pi * freq/100 * x / sampleRate) for x in range(0, sampleRate)]).astype(numpy.int16)

    # arr2 = numpy.abs(arr2)

    # arr2n = arr2/numpy.amax(arr2)

    # arr = (arr0*arr2n).astype(numpy.int16)*4
    # arr2 = numpy.c_[arr,arr]
    # sound = pygame.sndarray.make_sound(arr2)
    # sound.play(-1)
    # pygame.time.delay(2000)
    # sound.stop()

if __name__ == "__main__":
    # play_beat()
    play_tone()

