# AAC to MP3 Converter

A Python script that converts AAC audio files to MP3 format using the `pydub` library.

## Features

- Convert single AAC files to MP3
- Batch conversion of multiple AAC files
- Configurable MP3 bitrate
- Comprehensive error handling and logging
- Command-line interface with helpful usage examples

## Prerequisites

### 1. Install FFmpeg

The script requires FFmpeg to be installed on your system for audio processing.

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**Windows:**
Download from [FFmpeg official website](https://ffmpeg.org/download.html) or install via Chocolatey:
```bash
choco install ffmpeg
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install pydub directly:
```bash
pip install pydub
```

## Usage

### Single File Conversion

Convert a single AAC file to MP3:
```bash
python aac_to_mp3_converter.py input.aac
```

Convert with custom output filename:
```bash
python aac_to_mp3_converter.py input.aac output.mp3
```

### Batch Conversion

Convert all AAC files in a directory:
```bash
python aac_to_mp3_converter.py --batch /path/to/aac/files/
```

Convert with custom output directory:
```bash
python aac_to_mp3_converter.py --batch /path/to/aac/files/ --output-dir /path/to/mp3/files/
```

### Custom Bitrate

Set custom MP3 bitrate (default is 192k):
```bash
python aac_to_mp3_converter.py input.aac --bitrate 320k
```

### Help

View all available options:
```bash
python aac_to_mp3_converter.py --help
```

## Examples

Convert the AAC files in your current directory:
```bash
python aac_to_mp3_converter.py gear.aac
python aac_to_mp3_converter.py towel.aac
```

Convert both files with custom bitrate:
```bash
python aac_to_mp3_converter.py gear.aac --bitrate 256k
python aac_to_mp3_converter.py towel.aac --bitrate 256k
```

## Output

- The script will create MP3 files in the same directory as the input files (unless specified otherwise)
- Progress and status messages are displayed during conversion
- Error messages are shown if conversion fails

## Troubleshooting

### Common Issues

1. **"pydub library is required" error:**
   - Install pydub: `pip install pydub`

2. **FFmpeg not found:**
   - Install FFmpeg using the instructions above
   - Make sure FFmpeg is in your system PATH

3. **Permission errors:**
   - Make sure you have write permissions in the output directory

4. **File not found errors:**
   - Check that the input file path is correct
   - Use absolute paths if needed

### Getting Help

Run the script with `--help` to see all available options:
```bash
python aac_to_mp3_converter.py --help
``` 