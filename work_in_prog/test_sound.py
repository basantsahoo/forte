import os
print('\007')
print("\a")
os.system('afplay /System/Library/Sounds/Sosumi.aiff')

def play_call_sound():
    duration = 1  # seconds
    freq = 440  # Hz
    os.system('play -nq -t alsa synth {} sine {}'.format(duration, freq))
play_call_sound()

