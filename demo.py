#!/usr/bin/env python3
"""
Demo script for text-to-audio conversion using Piper TTS via Docker.
"""

from text_to_audio import text_to_audio, check_docker_installed

def main():
    # Check if Docker is installed
    if not check_docker_installed():
        print("Error: Docker is not installed or not running. Please install Docker and try again.")
        return
    
    print("=== Text-to-Audio Conversion Demo ===")
    
    # Example 1: Convert simple text to audio
    print("\nExample 1: Converting simple text to audio")
    text = "Hello, this is a test of the Piper TTS system."
    output_file = "demo_output1.wav"
    
    success = text_to_audio(text, output_file)
    if success:
        print(f"Example 1 completed successfully. Audio saved to {output_file}")
    else:
        print("Example 1 failed.")
    
    # Example 2: Read from a file and convert to audio
    print("\nExample 2: Reading from a file and converting to audio")
    try:
        with open("example.txt", "r") as f:
            file_text = f.read()
        
        output_file = "demo_output2.wav"
        success = text_to_audio(file_text, output_file)
        
        if success:
            print(f"Example 2 completed successfully. Audio saved to {output_file}")
        else:
            print("Example 2 failed.")
    except Exception as e:
        print(f"Error reading file: {e}")
    
    # Example 3: Using a different voice model
    print("\nExample 3: Using a different voice model")
    text = "This is an example of using a different voice model."
    output_file = "demo_output3.wav"
    model_name = "en_US-lessac-medium"  # Different voice model
    
    try:
        success = text_to_audio(text, output_file, model_name)
        if success:
            print(f"Example 3 completed successfully. Audio saved to {output_file}")
        else:
            print("Example 3 failed.")
    except Exception as e:
        print(f"Error using different voice model: {e}")
    
    print("\nDemo completed.")

if __name__ == "__main__":
    main() 