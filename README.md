# PiperSpeech

A simple command-line tool to convert text to natural-sounding speech using the open-source [Piper TTS](https://github.com/rhasspy/piper) system. This project makes it easy to convert large text files into audio files with a natural-sounding voice.

## Features

- Convert text to high-quality speech using Piper TTS
- Support for both direct text input and text files
- Progress bar for tracking conversion status
- Automatic chunking for large texts
- Resume capability for interrupted conversions
- Docker-based for easy setup and cross-platform compatibility

## Prerequisites

1. [Docker](https://docs.docker.com/get-docker/) must be installed and running
2. Python 3.9 or later

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/piperspeech.git
   cd piperspeech
   ```

2. Run the script:
   ```bash
   # Convert text directly
   python text_to_audio.py --text "Hello, this is a test."

   # Convert from a text file
   python text_to_audio.py --file your_text.txt
   ```

The first run will take longer as it downloads the voice model (~60MB).

## Usage Examples

```bash
# Basic usage with default voice
python text_to_audio.py --text "Hello, world!" --output hello.wav

# Convert a text file
python text_to_audio.py --file input.txt --output story.wav

# Resume an interrupted conversion
python text_to_audio.py --file large_text.txt --output story.wav --resume
```

## Voice Models

By default, this project uses the `en_GB-northern_english_male-medium` voice model from Piper TTS. You can specify a different model using the `--model` option:

```bash
python text_to_audio.py --text "Hello" --model en_US-lessac-medium
```

Available voice models can be found in the [Piper Models List](https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0).

## How It Works

1. The script splits large texts into manageable chunks
2. Each chunk is processed using Piper TTS in a Docker container
3. The resulting audio chunks are combined into a single WAV file
4. Progress is saved after each chunk, allowing for resumption if interrupted

## Credits

This project is built on top of several open-source technologies:

- [Piper TTS](https://github.com/rhasspy/piper) - The core text-to-speech engine
- Default voice model: `en_GB-northern_english_male-medium` from [Piper Voices](https://huggingface.co/rhasspy/piper-voices)
- [FFmpeg](https://ffmpeg.org/) - Used for audio file manipulation
- Docker containers for cross-platform compatibility

## Troubleshooting

- **Docker not found**: Make sure Docker is installed and running
- **Permission denied**: Run Docker commands with appropriate permissions
- **Memory issues**: The script automatically chunks large texts, but you might need to adjust chunk size for very large files
- **Interrupted conversion**: Use the `--resume` flag to continue from where it left off

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the [Rhasspy](https://github.com/rhasspy) project for creating Piper TTS
- Voice models are provided by [MycroftAI](https://mycroft.ai/) and the open-source community 