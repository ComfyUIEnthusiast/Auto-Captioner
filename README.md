# Video Cropping App

A Flask-based web application that allows users to upload videos and crop them using a drag-and-drop interface. The cropping is processed using FFmpeg in the background.

## Features

- Video upload with drag and drop
- Video preview in browser
- Interactive crop region selection (drag and drop)
- FFmpeg-based video cropping
- Download cropped video

## Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript (vanilla)
- **Backend**: Python Flask
- **Video Processing**: FFmpeg (via subprocess)
- **Video Handling**: moviepy

## Project Structure

```
Auto-Tagger/
├── app.py                  # Main Flask application
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore           # Docker ignore file
├── static/
│   └── css/
│       └── style.css       # Styling
├── templates/
│   ├── index.html          # Main page
│   └── crop.html           # Crop editor page
├── uploads/                # Uploaded videos (gitignored)
└── output/                 # Processed videos (gitignored)
```

## Setup

### Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up --build

# The application will be available at http://localhost:5000
```

```bash
# Run in background
docker-compose up -d --build

# Stop the container
docker-compose down

# View logs
docker-compose logs -f
```

### Local Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Install FFmpeg (system dependency)
3. Run: `python app.py`
4. Open: `http://localhost:5000`

## FFmpeg Installation

Required for local development. When using Docker, FFmpeg is included in the image.

- Windows: `choco install ffmpeg` or download from https://ffmpeg.org/download.html
- macOS: `brew install ffmpeg`
- Linux: `apt install ffmpeg` or `yum install ffmpeg`