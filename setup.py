#!/usr/bin/env python
"""
Setup helper script for Video Cropping App.
Checks for required dependencies and provides installation instructions.
"""
import subprocess
import sys
import os

def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Get first line of version output
            first_line = result.stdout.split('\n')[0]
            print(f"  ✓ FFmpeg is installed: {first_line}")
            return True
        else:
            raise Exception("FFmpeg returned error")
    except FileNotFoundError:
        print("  ✗ FFmpeg is NOT installed")
        print("\n  To install FFmpeg on Windows:")
        print("    1. Download from: https://ffmpeg.org/download.html")
        print("    2. Extract to C:\\ffmpeg")
        print("    3. Add C:\\ffmpeg\\bin to PATH:")
        print("       Right-click This PC → Properties → Advanced → Environment Variables")
        print("       Under System Variables, find 'Path' → Edit → New → Add C:\\ffmpeg\\bin")
        print("\n  Or use Chocolatey:")
        print("    choco install ffmpeg")
        print("\n  Or use winget:")
        print("    winget install FFmpeg")
        return False
    except Exception as e:
        print(f"  ✗ FFmpeg check failed: {e}")
        return False


def check_python_deps():
    """Check if Python dependencies are installed."""
    deps = {'flask': 'Flask', 'moviepy': 'MoviePy'}
    all_ok = True
    
    print("\nPython Dependencies:")
    for pkg, name in deps.items():
        try:
            __import__(pkg)
            print(f"  ✓ {name} is installed")
        except ImportError:
            print(f"  ✗ {name} is NOT installed")
            all_ok = False
    
    return all_ok


def main():
    print("=" * 50)
    print("  Video Cropping App - Setup Check")
    print("=" * 50)
    
    print("\n1. Python Version:")
    print(f"  ✓ Python {sys.version.split()[0]}")
    
    ffmpeg_ok = check_ffmpeg()
    deps_ok = check_python_deps()
    
    print("\n" + "=" * 50)
    if ffmpeg_ok and deps_ok:
        print("  ✓ All dependencies are ready!")
        print("\n  Start the app with: python app.py")
        print("  Then open: http://localhost:5000")
    else:
        if not ffmpeg_ok:
            print("  ⚠ FFmpeg is required for video cropping")
        if not deps_ok:
            print("  ⚠ Install missing dependencies with: pip install -r requirements.txt")
    print("=" * 50)


if __name__ == '__main__':
    main()