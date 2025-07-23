# SoundOfSilence - Outputs timestamps based on keyword detection at silence breaks
# Copyright (C) 2025 bengalih
# version: 1.0.0

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import os
import string
import subprocess
import tempfile
import re
import sys
from datetime import timedelta
from tqdm import tqdm
import argparse

# Configuration class
class Config:
    def __init__(self):
        # Environment Options
        self.FFMPEG_PATH = r""
        self.WHISPER_MODEL_PATH = ".\whisper-models"
        # Silence Detection Options
        self.SILENCE_THRESHOLD = "-30dB"
        self.SILENCE_DURATION = 3.0
        self.SNIPPET_DURATION = 5  # in seconds
        # Text Detection Options
        self.TARGET_WORDS = ["chapter", "part", "section"]  # List of words to detect
        self.TARGET_NUMBERS_ONLY = False # Only look for sections starting with numbers.
        self.TARGET_FIRST_WORD_ONLY = True  # Only count target words if they are the first word in transcription
        # Whisper Model Configuration
        self.WHISPER_MODEL = "tiny.en"
        self.WHISPER_DEVICE = "cpu"
        self.WHISPER_COMPUTE_TYPE = "int8"
        # File Options
        self.FILE_OUTPUT = True  # Enable writing silences and chapters to files
        self.FILE_OUTPUT_TEXT = True  # Enable writing transcribed text along with timestamps
        self.TEXT_FIXUP = True  # Enable punctuation and capitalization fixup for transcribed text
        # Testing Options
        self.TEST_RUN = False  # Enable test run mode to process only a portion of audio
        self.TEST_RUN_DURATION = 240  # Duration of test run file in minutes
        self.DEBUG = False  # Set to True to enable verbose output

def format_timestamp(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def to_camel_case(text):
    return ' '.join(word.capitalize() for word in text.split())

def fixup_text(text, config):
    if not config.TEXT_FIXUP:
        return text
    # Standardize chapter/part/section formatting: e.g., "Chapter 1. Title" or "Part Two, Title" -> "Chapter 1: Title"
    pattern = re.compile(r'^(Chapter|Section|Part)\s+(\d+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)[.,]?\s*(.*?)[\.,]?$', re.IGNORECASE)
    match = pattern.match(text)
    if match:
        prefix, number, title = match.groups()
        # Remove trailing punctuation and standardize to colon
        title = title.rstrip('.,')
        return f"{prefix} {number}: {title}"
    # Remove trailing punctuation for non-matching text
    return text.rstrip('.,')

def get_audio_duration(audio_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting audio duration: {e}")
        return None

def create_test_run_file(input_file, config):
    base, ext = os.path.splitext(input_file)
    test_file = f"{base}_testrun{ext}"
    if os.path.exists(test_file):
        print(f"TEST_RUN option enabled. Reusing '{test_file}'.")
        print(f"Manually remove to recreate on run.\n")
        return test_file

    duration_seconds = config.TEST_RUN_DURATION * 60
    print(f"TEST_RUN option enabled. Creating file '{test_file}' using {config.TEST_RUN_DURATION} minutes of audio...")

    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-t", str(duration_seconds),  # Duration in seconds
        "-c", "copy",  # Copy without re-encoding
        test_file
    ]

    total_duration = min(get_audio_duration(input_file) or duration_seconds, duration_seconds)
    time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d+)')

    pbar = tqdm(
        total=total_duration,
        unit="s",
        bar_format="Creating test file: {percentage:3.0f}%|{bar}| Elapsed {elapsed} | ETA: {remaining}",
        ncols=100,
        dynamic_ncols=False,
        leave=True,
        file=sys.stdout
    )

    try:
        with subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, universal_newlines=True) as proc:
            for line in proc.stderr:
                time_match = time_pattern.search(line)
                if time_match:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = int(time_match.group(3))
                    fraction = int(time_match.group(4))
                    current_time = hours * 3600 + minutes * 60 + seconds + fraction / (10 ** len(time_match.group(4)))
                    pbar.n = min(current_time, total_duration)
                    pbar.refresh()

            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=proc.stderr)

        pbar.n = total_duration
        pbar.refresh()
        pbar.close()

        if os.path.exists(test_file):
            print(f"Test file '{test_file}' created successfully.")
            return test_file
        else:
            print(f"Error: Test file '{test_file}' was not created.")
            return input_file
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error during test file creation: {e}")
        pbar.close()
        return input_file
    except Exception as e:
        print(f"Unexpected error during test file creation: {e}")
        pbar.close()
        return input_file

def detect_silences(audio_path, config):
    total_duration = get_audio_duration(audio_path)
    if total_duration is None:
        print("Could not determine audio duration. Progress bar disabled.")
        total_duration = 0

    print("Detecting silences...")

    cmd = [
        "ffmpeg", "-hide_banner", "-i", audio_path,
        "-af", f"silencedetect=noise={config.SILENCE_THRESHOLD}:d={config.SILENCE_DURATION}",
        "-f", "null", "-"
    ]

    silence_ends = []
    time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d+)')
    silence_end_pattern = re.compile(r"silence_end: ([0-9.]+)")

    pbar = tqdm(
        total=total_duration,
        unit="",
        bar_format="Progress: {percentage:3.0f}%|{bar}| Elapsed {elapsed} | ETA: {remaining} | {unit}",
        ncols=100,
        dynamic_ncols=False,
        leave=True,
        file=sys.stdout
    )
    pbar.unit = "(none yet)"

    try:
        with subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, universal_newlines=True) as proc:
            for line in proc.stderr:
                time_match = time_pattern.search(line)
                if time_match and total_duration > 0:
                    hours = int(time_match.group(1))
                    minutes = int(time_match.group(2))
                    seconds = int(time_match.group(3))
                    fraction = int(time_match.group(4))
                    current_time = hours * 3600 + minutes * 60 + seconds + fraction / (10 ** len(time_match.group(4)))
                    pbar.n = min(current_time, total_duration)
                    pbar.unit = f"{len(silence_ends)} silence(s) ({format_timestamp(silence_ends[-1]) if silence_ends else '(none yet)'})"
                    pbar.refresh()

                silence_match = silence_end_pattern.search(line)
                if silence_match:
                    silence_time = float(silence_match.group(1)) - 1.0
                    silence_ends.append(silence_time)

            proc.wait()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=proc.stderr)

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error during silence detection: {e}")
        silence_ends = []
    except Exception as e:
        print(f"Unexpected error during silence detection: {e}")
        silence_ends = []
    finally:
        pbar.n = total_duration
        pbar.unit = f"{len(silence_ends)} silence(s) ({format_timestamp(silence_ends[-1]) if silence_ends else '(none yet)'})"
        pbar.refresh()
        pbar.close()

    if silence_ends:
        print("\nSilence timestamps:")
        formatted_silences = [format_timestamp(se) for se in silence_ends]
        for ts in formatted_silences:
            print(ts)

        if config.FILE_OUTPUT:
            base = os.path.splitext(audio_path)[0]
            silences_file = f"{base}_silences.txt"
            try:
                with open(silences_file, "w") as f:
                    for ts in formatted_silences:
                        f.write(ts + "\n")
                print(f"Silence timestamps saved to '{silences_file}'\n")
            except Exception as e:
                print(f"Error writing silences file: {e}")

    return silence_ends

def extract_segment(input_file, start_time, duration, output_file, config):
    if config.DEBUG:
        print(f"Extracting {duration}-second snippet at {start_time}s...")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", str(start_time), "-t", str(duration),
        "-i", input_file,
        "-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le",
        "-f", "wav", output_file
    ]
    if config.DEBUG:
        print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        return os.path.exists(output_file)
    except Exception as e:
        if config.DEBUG:
            print(f"Error extracting snippet: {e}")
        return False

def transcribe_and_check_word(model, audio_file, config):
    if config.DEBUG:
        print(f"Transcribing {audio_file}...")
    try:
        segments, _ = model.transcribe(audio_file, language="en", vad_filter=False)
        text = " ".join([seg.text for seg in segments]).strip()
        found = False

        if config.TARGET_FIRST_WORD_ONLY:
            # Check if the first word matches any target word (case-insensitive)
            first_word = text.split()[0].strip(string.punctuation).lower() if text else ""
            found = first_word in [word.lower() for word in config.TARGET_WORDS]
        else:
            # Original behavior: check if any target word is in the text
            found = any(word.lower() in text.lower() for word in config.TARGET_WORDS)
        if config.DEBUG:
            print(f"\nTranscription: {text}")
            print(f"Target word found: {found}\n")
        return found, text  # Return whether a target word was found and the full transcription
    except Exception as e:
        if config.DEBUG:
            print(f"\nError during transcription: {e}\n")
        return False, ""

def str2bool(v):
    return str(v).lower() in ("yes", "true", "t", "1")

def main():
    parser = argparse.ArgumentParser(description='Detect silences in an audio file and transcribe segments to identify chapters.')
    parser.add_argument('audio_file', type=str, help='Path to the input audio file')

    parser.add_argument('--ffmpeg-path', type=str, default=Config().FFMPEG_PATH, help='Path to FFmpeg bin directory')
    parser.add_argument('--whisper-model-path', type=str, default=Config().WHISPER_MODEL_PATH, help='Path to Whisper model directory')
    parser.add_argument('--silence-threshold', type=str, default=Config().SILENCE_THRESHOLD, help='Silence detection threshold (e.g., -30dB)')
    parser.add_argument('--silence-duration', type=float, default=Config().SILENCE_DURATION, help='Minimum silence duration in seconds')
    parser.add_argument('--snippet-duration', type=int, default=Config().SNIPPET_DURATION, help='Duration of audio snippets to transcribe in seconds')
    parser.add_argument('--target-words', type=str, action='append', default=[], help='Target words to detect (can repeat)')
    parser.add_argument('--target-first-word-only', type=str2bool, default=Config().TARGET_FIRST_WORD_ONLY, help='Only match if target word is the first word (true/false)')
    parser.add_argument('--target-numbers-only', type=str2bool, default=Config().TARGET_NUMBERS_ONLY, help='Use numeric-only detection (true/false)')
    parser.add_argument('--whisper-model', type=str, default=Config().WHISPER_MODEL, help='Whisper model to use (e.g., tiny.en)')
    parser.add_argument('--whisper-device', type=str, default=Config().WHISPER_DEVICE, help='Device to use for inference (cpu/cuda)')
    parser.add_argument('--whisper-compute-type', type=str, default=Config().WHISPER_COMPUTE_TYPE, help='Compute type (int8, float16, etc.)')
    parser.add_argument('--file-output', type=str2bool, default=Config().FILE_OUTPUT, help='Write silence/chapter output to files (true/false)')
    parser.add_argument('--file-output-text', type=str2bool, default=Config().FILE_OUTPUT_TEXT, help='Include transcribed text with chapter output (true/false)')
    parser.add_argument('--text-fixup', type=str2bool, default=Config().TEXT_FIXUP, help='Enable text punctuation/capitalization fixup (true/false)')
    parser.add_argument('--test-run', type=str2bool, default=Config().TEST_RUN, help='Enable test run mode (true/false)')
    parser.add_argument('--test-run-duration', type=int, default=Config().TEST_RUN_DURATION, help='Duration of test run in minutes')
    parser.add_argument('--debug', type=str2bool, default=Config().DEBUG, help='Enable verbose debug output (true/false)')

    args = parser.parse_args()

    # Update config with command-line arguments
    config = Config()
    config.FFMPEG_PATH = args.ffmpeg_path
    config.WHISPER_MODEL_PATH = args.whisper_model_path
    config.SILENCE_THRESHOLD = args.silence_threshold
    config.SILENCE_DURATION = args.silence_duration
    config.SNIPPET_DURATION = args.snippet_duration
    config.TARGET_WORDS = args.target_words or Config().TARGET_WORDS
    config.TARGET_FIRST_WORD_ONLY = args.target_first_word_only
    config.TARGET_NUMBERS_ONLY = args.target_numbers_only
    config.WHISPER_MODEL = args.whisper_model
    config.WHISPER_DEVICE = args.whisper_device
    config.WHISPER_COMPUTE_TYPE = args.whisper_compute_type
    config.FILE_OUTPUT = args.file_output
    config.FILE_OUTPUT_TEXT = args.file_output_text
    config.TEXT_FIXUP = args.text_fixup
    config.TEST_RUN = args.test_run
    config.TEST_RUN_DURATION = args.test_run_duration
    config.DEBUG = args.debug


    os.environ["PATH"] += os.pathsep + config.FFMPEG_PATH
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    audio_path = args.audio_file
    print(f"Processing audio file: '{audio_path}'\n")
    if not os.path.exists(audio_path):
        print(f"Error: Audio file {audio_path} does not exist.")
        return

    # Handle test run mode
    processing_path = audio_path
    if config.TEST_RUN:
        processing_path = create_test_run_file(audio_path, config)
        if processing_path == audio_path:
            print("Continuing with original file due to test file creation failure.")
        else:
            print(f"Processing test file: '{processing_path}'")

    print("Initializing WhisperModel...")
    from faster_whisper import WhisperModel

    silence_ends = detect_silences(processing_path, config)
    if not silence_ends:
        print("No silences detected. Exiting.")
        return

    try:
        if config.DEBUG:
            print(f"Loading faster-whisper '{config.WHISPER_MODEL}' model...")
        model = WhisperModel(
            config.WHISPER_MODEL,
            compute_type=config.WHISPER_COMPUTE_TYPE,
            download_root=config.WHISPER_MODEL_PATH,
            device=config.WHISPER_DEVICE
        )

    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return

    chapter_timestamps = []
    total = len(silence_ends)

    if config.TARGET_NUMBERS_ONLY:
        config.TARGET_WORDS = [
            "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
            "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
            "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
            "31", "32", "33", "34", "35", "36", "37", "38", "39", "40",
            "41", "42", "43", "44", "45", "46", "47", "48", "49", "50",
            "51", "52", "53", "54", "55", "56", "57", "58", "59", "60",
            "61", "62", "63", "64", "65", "66", "67", "68", "69", "70",
            "71", "72", "73", "74", "75", "76", "77", "78", "79", "80",
            "81", "82", "83", "84", "85", "86", "87", "88", "89", "90",
            "91", "92", "93", "94", "95", "96", "97", "98", "99", "100",
            "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
            "twenty one", "twenty two", "twenty three", "twenty four", "twenty five",
            "twenty six", "twenty seven", "twenty eight", "twenty nine", "thirty",
            "thirty one", "thirty two", "thirty three", "thirty four", "thirty five",
            "thirty six", "thirty seven", "thirty eight", "thirty nine", "forty",
            "forty one", "forty two", "forty three", "forty four", "forty five",
            "forty six", "forty seven", "forty eight", "forty nine", "fifty",
            "fifty one", "fifty two", "fifty three", "fifty four", "fifty five",
            "fifty six", "fifty seven", "fifty eight", "fifty nine", "sixty",
            "sixty one", "sixty two", "sixty three", "sixty four", "sixty five",
            "sixty six", "sixty seven", "sixty eight", "sixty nine", "seventy",
            "seventy one", "seventy two", "seventy three", "seventy four", "seventy five",
            "seventy six", "seventy seven", "seventy eight", "seventy nine", "eighty",
            "eighty one", "eighty two", "eighty three", "eighty four", "eighty five",
            "eighty six", "eighty seven", "eighty eight", "eighty nine", "ninety",
            "ninety one", "ninety two", "ninety three", "ninety four", "ninety five",
            "ninety six", "ninety seven", "ninety eight", "ninety nine", "one hundred"
        ]
    if config.TARGET_NUMBERS_ONLY:
        target_words_text = "{TARGET_NUMBERS_ONLY}"
    else:
        target_words_text = config.TARGET_WORDS
        
    print(f'Target words {target_words_text} found:')

    pbar = tqdm(
        total=total,
        bar_format="Progress: {percentage:3.0f}%|{bar}| Silence {n}/{total} | Elapsed {elapsed} | ETA: {remaining}",
        ncols=100,
        dynamic_ncols=False,
        file=sys.stdout,
        leave=True
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        for idx, silence_end in enumerate(silence_ends, 1):
            tmp_file = os.path.join(temp_dir, f"segment_{idx}.wav")
            success = extract_segment(processing_path, silence_end, config.SNIPPET_DURATION, tmp_file, config)
            found = False
            transcribed_text = ""
            if success:
                found, transcribed_text = transcribe_and_check_word(model, tmp_file, config)
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            if found:
                ts = format_timestamp(silence_end)
                # Apply CamelCase and then regex fixup
                camel_case_text = to_camel_case(transcribed_text)
                fixed_text = fixup_text(camel_case_text, config)
                if (fixed_text, ts) not in chapter_timestamps:
                    chapter_timestamps.append((fixed_text, ts))
                    tqdm.write(f"{fixed_text}\t{ts}")
            pbar.update(1)
            pbar.set_postfix_str(f"Silence {idx}/{total}")
            pbar.refresh()

    pbar.close()

    if config.FILE_OUTPUT and chapter_timestamps:
        base = os.path.splitext(processing_path)[0]
        chapters_file = f"{base}_chapters.txt"
        try:
            with open(chapters_file, "w") as f:
                if config.FILE_OUTPUT_TEXT:
                    for text, ts in sorted(chapter_timestamps, key=lambda x: x[1]):
                        f.write(f"{text}\t{ts}\n")
                else:
                    for ts in sorted(set(ts for _, ts in chapter_timestamps)):
                        f.write(ts + "\n")
            print(f"\nChapter timestamps saved to '{chapters_file}'")
        except Exception as e:
            print(f"Error writing chapters file: {e}")

if __name__ == "__main__":
    main()
