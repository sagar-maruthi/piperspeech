#!/usr/bin/env python3
import argparse
import os
import subprocess
import tempfile
import shutil
import sys
import time
import threading
import re
import math
import json
import signal

def check_docker_installed():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def progress_bar(stop_event, current_chunk, total_chunks, description="Converting"):
    """Display a progress bar while the conversion is running."""
    while not stop_event.is_set():
        progress = min(100, int((current_chunk.value / total_chunks) * 100))
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Print progress bar
        sys.stdout.write(f'\r{description}: [{bar}] {progress}% (Chunk {current_chunk.value}/{total_chunks})')
        sys.stdout.flush()
        time.sleep(0.5)
    
    # Clear the line when done
    sys.stdout.write('\r' + ' ' * 80 + '\r')
    sys.stdout.flush()

class Counter:
    """A simple thread-safe counter class."""
    def __init__(self, initial_value=0):
        self.value = initial_value
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:
            self.value += 1

def split_text_into_chunks(text, max_chunk_size=1000):
    """Split text into chunks of approximately max_chunk_size characters.
    Try to split at sentence boundaries."""
    chunks = []
    current_chunk = ""
    
    # Split by sentences (roughly)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def process_text_chunk(chunk, output_dir, chunk_number, model_name):
    """Process a single chunk of text and return the path to the output file."""
    chunk_output = os.path.join(output_dir, f"chunk_{chunk_number}.wav")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
        temp_file.write(chunk)
        input_file = temp_file.name
    
    try:
        # Create models directory in the workspace if it doesn't exist
        models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
        os.makedirs(models_dir, exist_ok=True)
        
        # Use our pre-built Docker image with piper-tts installed
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{os.path.abspath(input_file)}:/input/text.txt:ro",
            "-v", f"{output_dir}:/output",
            "-v", f"{models_dir}:/models",
            "piper-tts-runner",
            "bash", "-c",
            f"cat /input/text.txt | piper --model {model_name} --output_file /output/chunk_{chunk_number}.wav"
        ]
        
        # Run the Docker command
        result = subprocess.run(docker_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return chunk_output
    
    finally:
        # Clean up temporary file
        if os.path.exists(input_file):
            os.remove(input_file)

def check_docker_image():
    """Check if our Docker image exists, build it if not."""
    try:
        # Check if image exists
        result = subprocess.run(
            ["docker", "image", "inspect", "piper-tts-runner"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode != 0:
            print("Building Docker image with piper-tts...")
            subprocess.run(
                ["docker", "build", "-t", "piper-tts-runner", "."],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error with Docker image: {e}")
        return False

def combine_audio_files(audio_files, output_file):
    """Combine multiple WAV files into a single file using ffmpeg or a simple concatenation."""
    try:
        # Verify all files exist and are readable
        existing_files = []
        for audio_file in audio_files:
            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                existing_files.append(audio_file)
            else:
                print(f"Warning: Audio file {audio_file} does not exist or is empty")
        
        if not existing_files:
            print("Error: No valid audio files to combine")
            return False
        
        # Create a temporary directory for the file list and combined output
        with tempfile.TemporaryDirectory() as temp_dir:
            # First try using ffmpeg via Docker
            try:
                # Create a text file listing all input files
                file_list = os.path.join(temp_dir, "file_list.txt")
                with open(file_list, 'w') as f:
                    for i, audio_file in enumerate(existing_files):
                        # Copy each audio file to the temp directory with a simple name
                        temp_audio = os.path.join(temp_dir, f"chunk_{i}.wav")
                        shutil.copy2(audio_file, temp_audio)
                        # Use the simple name in the file list
                        f.write(f"file '/audio/chunk_{i}.wav'\n")
                
                # Create the output directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
                
                # Use ffmpeg to concatenate the files
                cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{temp_dir}:/audio:ro",
                    "-v", f"{os.path.dirname(os.path.abspath(output_file))}:/output",
                    "jrottenberg/ffmpeg:latest",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", "/audio/file_list.txt",
                    "-c", "copy",
                    f"/output/{os.path.basename(output_file)}"
                ]
                
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"Successfully combined {len(existing_files)} audio files using ffmpeg")
                return True
                
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to combine audio files using ffmpeg ({str(e)}). Falling back to simple concatenation.")
            
            # Simple concatenation approach (works for WAV files with the same format)
            try:
                # Calculate total size and create header
                total_data_size = 0
                for audio_file in existing_files:
                    total_data_size += os.path.getsize(audio_file) - 44  # Subtract header size
                
                # Read the first file to get the header
                with open(existing_files[0], 'rb') as f:
                    header = bytearray(f.read(44))  # WAV header is 44 bytes
                    
                # Update header with total data size
                total_size = total_data_size + 36  # Add header size minus 8 bytes
                header[4:8] = total_size.to_bytes(4, 'little')  # Update RIFF chunk size
                header[40:44] = total_data_size.to_bytes(4, 'little')  # Update data chunk size
                
                # Create the output file with the updated header
                temp_output = os.path.join(temp_dir, "combined.wav")
                with open(temp_output, 'wb') as outfile:
                    outfile.write(header)
                    
                    # Append the data from each file (skipping the header)
                    for audio_file in existing_files:
                        try:
                            with open(audio_file, 'rb') as infile:
                                infile.seek(44)  # Skip the header
                                while True:
                                    chunk = infile.read(1024 * 1024)  # Read 1MB at a time
                                    if not chunk:
                                        break
                                    outfile.write(chunk)
                        except Exception as e:
                            print(f"Warning: Error reading {audio_file}: {str(e)}")
                            return False
                
                # Move the combined file to the final location
                shutil.move(temp_output, output_file)
                print(f"Successfully combined {len(existing_files)} audio files using simple concatenation")
                return True
                
            except Exception as e:
                print(f"Error: Failed to combine audio files using simple concatenation: {str(e)}")
                return False
        
    except Exception as e:
        print(f"Error: Failed to combine audio files: {str(e)}")
        return False

def save_progress(progress_file, completed_chunks, total_chunks, model_name, output_file):
    """Save progress to a JSON file."""
    progress_data = {
        "completed_chunks": completed_chunks,
        "total_chunks": total_chunks,
        "model_name": model_name,
        "output_file": output_file,
        "timestamp": time.time()
    }
    
    with open(progress_file, 'w') as f:
        json.dump(progress_data, f)

def load_progress(progress_file):
    """Load progress from a JSON file."""
    if not os.path.exists(progress_file):
        return None
    
    try:
        with open(progress_file, 'r') as f:
            return json.load(f)
    except:
        return None

def handle_interrupt(signum, frame, stop_progress=None):
    """Handle keyboard interrupt (Ctrl+C)."""
    if stop_progress and not stop_progress.is_set():
        stop_progress.set()
    print("\nInterrupted. Progress has been saved and can be resumed later.")
    sys.exit(1)

def text_to_audio(text, output_file="output.wav", model_name="en_GB-northern_english_male-medium", resume=False):
    """
    Convert text to audio using Piper TTS via Docker.
    
    Args:
        text (str): The text to convert to speech
        output_file (str): Path to the output audio file
        model_name (str): Name of the Piper voice model to use
        resume (bool): Whether to resume from previous progress
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not check_docker_installed():
        print("Error: Docker is not installed or not running. Please install Docker and try again.")
        return False
    
    if not check_docker_image():
        print("Error: Failed to prepare Docker image. Please check Docker installation and try again.")
        return False
    
    try:
        # Get absolute paths for mounting in Docker
        abs_output_path = os.path.abspath(output_file)
        output_dir = os.path.dirname(abs_output_path)
        output_filename = os.path.basename(abs_output_path)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Progress file path
        progress_file = os.path.join(output_dir, f"{os.path.splitext(output_filename)[0]}_progress.json")
        
        # Create a temporary directory for chunk processing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Split text into manageable chunks
            chunks = split_text_into_chunks(text, max_chunk_size=2000)
            total_chunks = len(chunks)
            
            # Check for existing progress
            start_chunk = 0
            if resume:
                progress_data = load_progress(progress_file)
                if progress_data and progress_data["model_name"] == model_name and progress_data["output_file"] == output_file:
                    start_chunk = progress_data["completed_chunks"]
                    print(f"Resuming from chunk {start_chunk}/{total_chunks}")
            
            print(f"Converting text to speech using {model_name} model...")
            print(f"Text length: {len(text)} characters, split into {total_chunks} chunks")
            
            # Start progress bar in a separate thread
            current_chunk = Counter(start_chunk)
            stop_progress = threading.Event()
            progress_thread = threading.Thread(
                target=progress_bar, 
                args=(stop_progress, current_chunk, total_chunks, "Converting text to audio")
            )
            progress_thread.start()
            
            # Set up interrupt handler
            original_handler = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, lambda signum, frame: handle_interrupt(signum, frame, stop_progress))
            
            try:
                # Process each chunk
                chunk_files = []
                for i, chunk in enumerate(chunks):
                    if i < start_chunk:
                        # Skip already processed chunks
                        chunk_files.append(os.path.join(temp_dir, f"chunk_{i}.wav"))
                        continue
                    
                    chunk_output = process_text_chunk(chunk, temp_dir, i, model_name)
                    if chunk_output and os.path.exists(chunk_output):
                        chunk_files.append(chunk_output)
                        current_chunk.increment()
                        
                        # Save progress after each chunk
                        save_progress(progress_file, current_chunk.value, total_chunks, model_name, output_file)
                    else:
                        print(f"\nError: Failed to process chunk {i}")
                        return False
            finally:
                # Restore original interrupt handler
                signal.signal(signal.SIGINT, original_handler)
            
            # Stop the progress bar
            stop_progress.set()
            progress_thread.join()
            
            print("\nCombining audio chunks...")
            
            # Combine all chunks into the final output file
            if not combine_audio_files(chunk_files, abs_output_path):
                print("Error: Failed to combine audio chunks")
                return False
            
            # Remove progress file when done
            if os.path.exists(progress_file):
                os.remove(progress_file)
            
            print(f"Audio saved to {output_file}")
            return True
    
    except subprocess.CalledProcessError as e:
        # Stop the progress bar if it's running
        if 'stop_progress' in locals() and not stop_progress.is_set():
            stop_progress.set()
            progress_thread.join()
            
        print(f"\nError running Piper TTS: {e}")
        print(f"Command output: {e.stdout.decode() if e.stdout else ''}")
        print(f"Command error: {e.stderr.decode() if e.stderr else ''}")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Convert text to audio using Piper TTS via Docker")
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--text", help="Text to convert to speech")
    input_group.add_argument("--file", help="Text file to convert to speech")
    
    # Output options
    parser.add_argument("--output", default="output.wav", help="Output audio file (default: output.wav)")
    
    # Model options
    parser.add_argument("--model", default="en_GB-northern_english_male-medium", 
                        help="Piper voice model name (default: en_GB-northern_english_male-medium)")
    
    # Resume option
    parser.add_argument("--resume", action="store_true", help="Resume from previous progress if available")
    
    args = parser.parse_args()
    
    # Get text from file or command line
    if args.file:
        try:
            with open(args.file, 'r') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading file {args.file}: {e}")
            return 1
    else:
        text = args.text
    
    # Convert text to audio
    success = text_to_audio(text, args.output, args.model, args.resume)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())