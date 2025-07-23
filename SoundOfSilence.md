# SoundOfSilence – Chapter Detection using Whisper

SoundOfSilence is a Python script that analyzes audio files for supplied keywords (phrases) for purpposes of detecting section breaks.

It functions by first detecting silences using [ffmpeg](https://ffmpeg.org/) and then extracting relevant segments for transcribing  using [faster-whisper](https://github.com/guillaumekln/faster-whisper).
It outputs a listing of timestamps based on detected section breaks.

Very useful for chapterizing poorly marked audiobooks which use keywords in narration to separate sections.

---

## 📌 Features

- Detects **silences** using FFmpeg
- Extracts audio **snippets** following each silence
- Uses **faster-whisper** to transcribe audio
- Matches **target keywords** (e.g., "Chapter", "Section")
- Matches on **numbers only** to detect sections using only numbers in narration
- Saves **chapter timestamps** and **transcriptions** to files
- Supports **test-run** mode for quicker processing
- Optional **text cleanup** (capitalization, punctuation)

---

## 🚀 Requirements

- Python 3.7+
- `faster-whisper`
- `ffmpeg` and `ffprobe`
- `tqdm` for progress visualization

Install required Python packages:

```bash
pip install faster-whisper tqdm
```

⚠️ Ensure FFmpeg and FFprobe are installed and added to your system path, or specify the directory via `FFMPEG_PATH` or `--ffmpeg-path`.
This is important, especially for faster-whisper.  When in doubt, manually specify the path!

⚠️ Newer ffmpeg versions (post 6.x) have a bug where they do not properly update the time stampes with the `silencedetect` filter and a `null` output (as is standard way to run `silencedetect`).

e.g.:
`frame=    1 fps=0.1 q=-0.0 Lsize=N/A time=00:00:00.00 bitrate=N/A speed=1.12e-06x elapsed=0:00:09.81`

I am trying to work filing a bug with ffmpeg to fix this, but for now, using 7.x+ may mean the progress bar does not work for silence detection.
The only solution is to also download a pre 7 version and use the `FFMPEG_PATH` to specify the path to that for purposes of this script.
Note this might have peformance implications and you should see the Performance section below for more info.

Also, without the progress bar it is still possible to estimate the length of progress by comparing the duration to the last reported silence found.

```
Detecting silences (Duration: 66:11:41) ...
Progress:   0%|                                   | Elapsed 00:08 | ETA: ? | 5 silence(s) (02:33:13)
```

📝 Set `WHISPER_MODEL_PATH` or `--whisper-model-path` for location of storage for whisper models.
Placing this in a static location will ensure it won't need to be downloaded when script is moved.
Defaults to current directory `.\whisper-models`

---

## 📥 Download

To get started with SoundOfSilence, download the script and related files from the official repository:

- **Source Repository**: Clone or download the script from [SoundOfSilence.py](SoundOfSilence.py).
  ```bash
  git clone https://github.com/bengalih/ABS-scripts.git

---

## ⚙️ Configuration

Configuration can be done by supplying command line paramaeters (see Common Options below).
Alternatively, edititing the script’s configuration class block before running will save all values.
Most of the defaults should not need changing.
See below sections for more information

```python
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
```



## 🛠️ Usage

Basic usage is simply
```bash
python SoundOfSilence.py your_audio_file.mp3
```
You can set config options within the python file (recommended), or use command line options to set/override.

Default settings should be fine for standard detection, but you should familiarize yourself with some options.
See the note on FFMpeg path configuration under Requirements.

### Common Options

| Option                      | Description                                                                 |
|-----------------------------|-----------------------------------------------------------------------------|
| `--ffmpeg-path`             | Path to FFmpeg `bin` directory                                              |
| `--whisper-model-path`      | Local path for Whisper models                                               |
| `--silence-threshold`       | Silence level (e.g., `-30dB`)                                               |
| `--silence-duration`        | Minimum silence duration (seconds)                                         |
| `--snippet-duration`        | Duration of extracted audio (seconds)                                      |
| `--target-words`            | Target keyword(s) (e.g., `chapter`, `section`)                              |
| `--target-numbers-only`     | Only search for numbers                                                     |
| `--target-first-word-only`  | Only detect keyword/number if it’s the first word                          |
| `--file-output`             | Save silence and chapter data to files                                     |
| `--file-output-text`        | Include transcribed text in chapter output                                 |
| `--text-fixup`              | Capitalize and fix punctuation in text                                     |
| `--test-run`                | Create shorter audio file for testing                                      |
| `--test-run-duration`       | Duration (in minutes) for test audio                                       |
| `--debug`                   | Enable verbose debugging output                                            |


> 📝 When using  `--target-numbers-only` or `TARGET_NUMBERS_ONLY` the `TARGET_WORDS` are ignored and instead only numbers are searched.
>
> This is a useful option if section headings are simply spoken as numbers like "Five" or "32".
> 
> When using this option, it is recommended to set `--target-first-word-only` or `TARGET_FIRST_WORD_ONLY` to `True` for accuracy.
> However this will only detect sections up to 100.  Setting to `False` may be less accurate, but find sections numbered above 100.


---

## 🧪 Examples

### Basic transcription preview:
Will add specified `--target-words` onto `TARGET_WORDS` list
```bash
python SoundOfSilence.py audio.mp3 --target-words Introduction --target-words Epilogue
```

### Detect numbers only for section headings and debug:
```bash
python SoundOfSilence.py audio.mp3  --target-numbers-only true  --debug true
```

### Save full results to files:
```bash
python SoundOfSilence.py audio.mp3 --file-output --file-output-text
```

### Use custom silence threshold and snippet duration:
```bash
python SoundOfSilence.py audio.mp3 --silence-threshold -40dB --snippet-duration 8
```

---

## 📂 Output

When `--file-output` is enabled, the script generates:
- `*_silences.txt` – List of silence break timestamps
- `*_chapters.txt` – List of detected chapter timestamps and optionally the transcribed text

---

## 🚀 Performance

Setting the `SILENCE_THRESHOLD` longer will decrease the number of silences found and thus increase overall speed of execution.
However, this may miss some section breaks.

Setting the `SNIPPET_DURATION` longer will also signigicantly decrease performance as `faster-whisper` needs more time to transcribe a longer segment.
Setting it shorter may improve performance, but miss out on keywords.

The version of `ffmpeg` you have on a system may also severely impact performance.
Versions of 7.x should offer good performance, but at the cost of a broken progress bar for silence detection.
Versions 6.x seem to have a working progress bar, but perform silence detection 3-4x slower.
Versions prior to this appear to work in all respects.
You may wish to use an older version (I've tested with 4.x with good results).
Simply specify the proper directory in `FFMPEG_PATH` or `--ffmpeg-path` for the version to use with the script.

e.g:

 `--ffmpeg-path "c:\Program Files\ffmpeg\bin4"`

 Windows users may have difficulty finding older releases.  I recommend searching for `ffmpeg-4.4.1-full_build.7z` to find an older version that seems to work fully and quickly.
 While this version may be years old, its functions for the purpose of this script seem sufficient.

The script is designed as a single thread/process/queue.  After silence detection, it extracts each detected silence in turn via `ffmpeg` and then transcribes with `faster-whisper`.
Some testing was done doing tasks in parallel, but no major improvements were found for an overly complex change in code.
Best performance will come with better system specs, and utilizing the best `WHISPER_DEVICE` and `WHISPER_COMPUTE_TYPE` for your setup.

The `tiny.en` model was chosen for speed, and seems sufficient for purposes of this script.

Other running processes on a system may also severly impact transcription performance which is CPU heavy.

---

## 🧾 License

This project is licensed under the **GNU General Public License v3.0**.

You are free to use, modify, and distribute this software under the following conditions:

- You **must credit** the original author  
- Any **modified versions must also be open source** under the same license  
- You **must include a copy** of the license in any distributions  

📄 See the full license at [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html)

---

## 🙋‍♂️ Author

**bengalih**

Questions or improvements?
Contributions welcome!
