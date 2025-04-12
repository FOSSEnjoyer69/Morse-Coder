import cv2
import math
import numpy as np
import time
import os
from PIL import Image, ImageDraw

from scipy.io import wavfile
import moviepy.editor as mpy

from pydub import AudioSegment
from pydub.generators import Sine

from audio_tools import create_tone, create_silence

MORSE_CODE_DICT = { 'A':'.-', 'B':'-...',
                    'C':'-.-.', 'D':'-..', 'E':'.',
                    'F':'..-.', 'G':'--.', 'H':'....',
                    'I':'..', 'J':'.---', 'K':'-.-',
                    'L':'.-..', 'M':'--', 'N':'-.',
                    'O':'---', 'P':'.--.', 'Q':'--.-',
                    'R':'.-.', 'S':'...', 'T':'-',
                    'U':'..-', 'V':'...-', 'W':'.--',
                    'X':'-..-', 'Y':'-.--', 'Z':'--..',
                    '1':'.----', '2':'..---', '3':'...--',
                    '4':'....-', '5':'.....', '6':'-....',
                    '7':'--...', '8':'---..', '9':'----.',
                    '0':'-----', ', ':'--..--', '.':'.-.-.-',
                    '?':'..--..', '/':'-..-.', '-':'-....-',
                    '(':'-.--.', ')':'-.--.-', ' ':'/' # Use / for space between words
                }

def create_frame(size, color):
    """Creates a simple color frame using Pillow."""
    img = Image.new('RGB', size, color=color)
    # Optionally add text or other visuals here
    # draw = ImageDraw.Draw(img)
    # draw.text((10, 10),"Morse", fill="gray")
    return np.array(img) # Return as numpy array for moviepy


def text_to_morse_video(text:str, wpm:int):
    path = f"Outputs/{text}.mp4"
    create_morse_video(text, wpm, path)
    return path

def create_morse_video(text, wpm, output_filename="morse_video.mp4"):
    """

    Converts plain text to a Morse code video with audio.

    Args:
        text (str): The input text string.
        wpm (str): Words Per Minute
        output_filename (str): The desired name for the output video file.
    """

    # Duration of one unit (dot duration) in seconds:
    unit_duration_sec = 1.2 / wpm
    unit_duration_ms = int(unit_duration_sec * 1000)

    dot_duration = unit_duration_ms
    dash_duration = 3 * unit_duration_ms
    intra_symbol_gap = unit_duration_ms # Gap between dots/dashes within a letter
    inter_letter_gap = 3 * unit_duration_ms
    word_gap = 7 * unit_duration_ms

    # Audio settings
    TONE_FREQ = 700  # Hz

    # Video settings
    VIDEO_FPS = 30 # Frames per second
    IMG_SIZE = (320, 240) # Video resolution (width, height)
    BG_COLOR_OFF = "black"
    BG_COLOR_ON = "white"

    print(f"Converting text: '{text}'")
    text = text.upper() # Morse is case-insensitive

    morse_elements = [] # Stores tuples of (type, duration_ms)
    audio_segments = []
    total_duration_ms = 0

    # 1. Generate Morse sequence and calculate durations
    print("Generating Morse sequence and audio segments...")
    for i, char in enumerate(text):
        if char in MORSE_CODE_DICT:
            code = MORSE_CODE_DICT[char]
            print(f"  Char: {char} -> {code}")

            if code == '/': # Word space
                silence = create_silence(word_gap - inter_letter_gap) # Adjust because loop adds inter_letter_gap
                audio_segments.append(silence)
                morse_elements.append(('gap', word_gap - inter_letter_gap))
                total_duration_ms += (word_gap - inter_letter_gap)
            else:
                for j, symbol in enumerate(code):
                    if symbol == '.':
                        duration = dot_duration
                        tone = create_tone(TONE_FREQ, duration)
                        audio_segments.append(tone)
                        morse_elements.append(('dot', duration))
                        total_duration_ms += duration
                    elif symbol == '-':
                        duration = dash_duration
                        tone = create_tone(TONE_FREQ, duration)
                        audio_segments.append(tone)
                        morse_elements.append(('dash', duration))
                        total_duration_ms += duration

                    # Add intra-symbol gap if not the last symbol of the letter
                    if j < len(code) - 1:
                        silence = create_silence(intra_symbol_gap)
                        audio_segments.append(silence)
                        morse_elements.append(('gap', intra_symbol_gap))
                        total_duration_ms += intra_symbol_gap

            # Add inter-letter gap if not the last char and not a space already handled
            if i < len(text) - 1 and MORSE_CODE_DICT.get(text[i+1]) != '/':
                # Check if current char is not a space before adding letter gap
                if code != '/':
                    silence = create_silence(inter_letter_gap)
                    audio_segments.append(silence)
                    morse_elements.append(('gap', inter_letter_gap))
                    total_duration_ms += inter_letter_gap

        else:
            print(f"  Skipping unsupported character: {char}")
            # Optionally add a longer pause for unknown chars
            # silence = create_silence(word_gap)
            # audio_segments.append(silence)
            # morse_elements.append(('gap', word_gap))
            # total_duration_ms += word_gap


    # 2. Combine Audio Segments
    print("Combining audio...")
    if not audio_segments:
        print("No audio generated.")
        final_audio = AudioSegment.silent(duration=10) # Create dummy audio if empty
    else:
        final_audio = sum(audio_segments)

    # Use a temporary file for the audio track
    temp_audio_filename = f"temp_morse_audio_{int(time.time())}.wav"
    final_audio.export(temp_audio_filename, format="wav")
    print(f"Audio duration: {total_duration_ms / 1000:.2f} seconds")


    # 3. Generate Video Frames
    print("Generating video frames...")
    frames = []
    frame_duration_ms = 1000 / VIDEO_FPS

    frame_on = create_frame(IMG_SIZE, BG_COLOR_ON)
    frame_off = create_frame(IMG_SIZE, BG_COLOR_OFF)

    for element_type, duration_ms in morse_elements:
        num_frames = max(1, round(duration_ms / frame_duration_ms)) # Ensure at least 1 frame

        if element_type == 'dot' or element_type == 'dash':
            frames.extend([frame_on] * num_frames)
        else: # 'gap'
            frames.extend([frame_off] * num_frames)

    if not frames:
        print("No frames generated. Adding a single black frame.")
        frames.append(frame_off) # Add placeholder if no morse elements


    # 4. Create Video Clip and Add Audio
    print("Creating video clip...")
    video_clip = mpy.ImageSequenceClip(frames, fps=VIDEO_FPS)

    print("Loading audio into clip...")
    audio_clip = mpy.AudioFileClip(temp_audio_filename)

    # Ensure video duration matches calculated audio duration (or slightly longer)
    # This can sometimes be needed due to rounding in frame calculation
    final_clip_duration = max(video_clip.duration, total_duration_ms / 1000.0)
    video_clip = video_clip.set_duration(final_clip_duration)
    print(f"Video clip duration set to: {video_clip.duration:.2f} seconds")

    final_clip = video_clip.set_audio(audio_clip.set_duration(video_clip.duration)) # Match audio duration to video


    # 5. Write Video File
    print(f"Writing video file: {output_filename}...")
    try:
        final_clip.write_videofile(
            output_filename,
            codec='libx264', # Common video codec
            audio_codec='aac', # Common audio codec
            fps=VIDEO_FPS,
            temp_audiofile=f'temp-audio_{int(time.time())}.m4a', # Explicit temp audio for muxing
            remove_temp=True # Clean up temp audio file
        )
        print("Video creation successful!")
    except Exception as e:
        print(f"Error writing video file: {e}")
        print("Ensure FFmpeg is installed and accessible.")
    finally:
        # Clean up the main temporary audio file
        if os.path.exists(temp_audio_filename):
            os.remove(temp_audio_filename)
        # Clean up potential moviepy temp files manually if needed
        if final_clip and hasattr(final_clip, 'audio') and final_clip.audio:
             if hasattr(final_clip.audio, 'temp_audiofile') and os.path.exists(final_clip.audio.temp_audiofile):
                 try:
                      os.remove(final_clip.audio.temp_audiofile)
                 except: pass # Ignore error if file already gone
        if 'temp_audiofile' in locals() and os.path.exists(temp_audiofile):
             try:
                  os.remove(temp_audiofile)
             except: pass
