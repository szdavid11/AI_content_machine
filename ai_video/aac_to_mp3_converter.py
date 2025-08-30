#!/usr/bin/env python3
"""
AAC to MP3 Converter Script

This script converts AAC audio files to MP3 format using the pydub library.
It supports both single file conversion and batch processing of multiple files.

Usage:
    python aac_to_mp3_converter.py input.aac
    python aac_to_mp3_converter.py input.aac output.mp3
    python aac_to_mp3_converter.py --batch /path/to/aac/files/
"""

import os
import sys
import argparse
from pathlib import Path
from pydub import AudioSegment
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_aac_to_mp3(input_file, output_file=None, bitrate='192k'):
    """
    Convert an AAC file to MP3 format.
    
    Args:
        input_file (str): Path to the input AAC file
        output_file (str, optional): Path to the output MP3 file. If None, will use same name with .mp3 extension
        bitrate (str): MP3 bitrate (default: '192k')
    
    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        # Validate input file
        input_path = Path(input_file)
        if not input_path.exists():
            logger.error(f"Input file does not exist: {input_file}")
            return False
        
        if not input_path.suffix.lower() == '.aac':
            logger.warning(f"Input file doesn't have .aac extension: {input_file}")
        
        # Generate output filename if not provided
        if output_file is None:
            output_path = input_path.with_suffix('.mp3')
        else:
            output_path = Path(output_file)
        
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {input_file} to {output_path}")
        
        # Load the AAC file
        audio = AudioSegment.from_file(input_file, format="aac")
        
        # Export as MP3
        audio.export(output_path, format="mp3", bitrate=bitrate)
        
        logger.info(f"Successfully converted {input_file} to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error converting {input_file}: {str(e)}")
        return False

def batch_convert(input_directory, output_directory=None, bitrate='192k'):
    """
    Convert all AAC files in a directory to MP3 format.
    
    Args:
        input_directory (str): Directory containing AAC files
        output_directory (str, optional): Directory to save MP3 files. If None, saves in same directory
        bitrate (str): MP3 bitrate (default: '192k')
    
    Returns:
        tuple: (successful_conversions, total_files)
    """
    input_path = Path(input_directory)
    if not input_path.exists() or not input_path.is_dir():
        logger.error(f"Input directory does not exist: {input_directory}")
        return 0, 0
    
    # Find all AAC files
    aac_files = list(input_path.glob("*.aac"))
    if not aac_files:
        logger.warning(f"No AAC files found in {input_directory}")
        return 0, 0
    
    successful = 0
    total = len(aac_files)
    
    logger.info(f"Found {total} AAC files to convert")
    
    for aac_file in aac_files:
        if output_directory:
            output_file = Path(output_directory) / aac_file.with_suffix('.mp3').name
        else:
            output_file = None
        
        if convert_aac_to_mp3(str(aac_file), str(output_file) if output_file else None, bitrate):
            successful += 1
    
    logger.info(f"Batch conversion complete: {successful}/{total} files converted successfully")
    return successful, total

def main():
    parser = argparse.ArgumentParser(
        description="Convert AAC files to MP3 format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python aac_to_mp3_converter.py input.aac
  python aac_to_mp3_converter.py input.aac output.mp3
  python aac_to_mp3_converter.py --batch /path/to/aac/files/
  python aac_to_mp3_converter.py --batch /path/to/aac/files/ --output /path/to/mp3/files/
        """
    )
    
    parser.add_argument('input', nargs='?', help='Input AAC file or directory (for batch mode)')
    parser.add_argument('output', nargs='?', help='Output MP3 file (optional for single file)')
    parser.add_argument('--batch', action='store_true', help='Batch mode: convert all AAC files in directory')
    parser.add_argument('--bitrate', default='192k', help='MP3 bitrate (default: 192k)')
    parser.add_argument('--output-dir', help='Output directory for batch mode')
    
    args = parser.parse_args()
    
    # Check if pydub is available
    try:
        import pydub
    except ImportError:
        logger.error("pydub library is required. Install it with: pip install pydub")
        logger.error("You may also need to install ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Ubuntu)")
        sys.exit(1)
    
    if args.batch:
        if not args.input:
            logger.error("Input directory required for batch mode")
            sys.exit(1)
        
        successful, total = batch_convert(args.input, args.output_dir, args.bitrate)
        if successful == 0:
            sys.exit(1)
    else:
        if not args.input:
            logger.error("Input file required")
            sys.exit(1)
        
        success = convert_aac_to_mp3(args.input, args.output, args.bitrate)
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main() 