import os
import uuid
import subprocess
import json
import base64
from flask import Flask, request, render_template, jsonify, send_file, send_from_directory
import requests
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from config import Config
from moviepy import VideoFileClip

app = Flask(__name__)
Config.init(app)
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = Config.OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

ALLOWED_EXTENSIONS = Config.ALLOWED_VIDEO_EXTENSIONS


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_video_files():
    """Get list of video files in the upload directory."""
    videos = []
    upload_dir = app.config['UPLOAD_FOLDER']
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            if allowed_file(f):
                videos.append(f)
    return videos


# --- Serve static files ---
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# --- Upload page (index) ---
@app.route('/')
def index():
    videos = get_video_files()
    return render_template('index.html', videos=videos)

# --- API config endpoint ---
@app.route('/api/config')
def api_config():
    return jsonify({
        'openai_url': Config.OPENAI_URL
    })

# --- API video list endpoint ---
@app.route('/api/videos')
def api_videos():
    videos = get_video_files()
    return jsonify({'videos': videos})

# --- Crop page (GET: render form) ---
@app.route('/crop', methods=['GET'])
def crop_page():
    filename = request.args.get('file')
    if not filename:
        # Show video selection list
        videos = get_video_files()
        return render_template('crop.html', filename=None, videos=videos)
    # Validate file exists
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Video not found'}), 404
    videos = get_video_files()
    return render_template('crop.html', filename=filename, videos=videos)


# --- Upload endpoint ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    
    filename = secure_filename(file.filename)
    # Keep the original filename (no UUID prefix or suffix)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    return jsonify({'filename': filename, 'message': 'File uploaded successfully'})


# --- Get video info ---
@app.route('/video_info/<filename>', methods=['GET'])
def video_info(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Video not found'}), 404
    
    try:
        clip = VideoFileClip(filepath)
        info = {
            'width': clip.w,
            'height': clip.h,
            'duration': clip.duration,
            'fps': clip.fps,
            'format': 'mp4'
        }
        clip.close()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Crop video using FFmpeg ---
@app.route('/crop', methods=['POST'])
def crop_video():
    data = request.get_json()
    
    filename = data.get('filename')
    x = int(data.get('x', 0))
    y = int(data.get('y', 0))
    width = int(data.get('width', 0))
    height = int(data.get('height', 0))
    in_time = data.get('in_time', None)
    out_time = data.get('out_time', None)
    target_width = data.get('target_width', None)
    target_height = data.get('target_height', None)
    output_fps = data.get('output_fps', None)
    
    if not filename:
        return jsonify({'error': 'Filename required'}), 400
    if width <= 0 or height <= 0:
        return jsonify({'error': 'Width and height must be positive'}), 400
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Video not found'}), 404
    
    # Generate unique output filename
    output_name = f"{uuid.uuid4().hex}_processed.mp4"
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_name)
    
    try:
        # Build FFmpeg command
        cmd = ['ffmpeg']
        
        # If in_time is set, use -ss BEFORE -i for accurate seeking from source
        if in_time is not None and in_time > 0:
            cmd.extend(['-ss', str(in_time)])
        
        cmd.extend(['-i', filepath])
        
        # If out_time is set, calculate duration and use -t
        if out_time is not None and out_time > 0 and in_time is not None and in_time > 0:
            duration = out_time - in_time
            if duration > 0:
                cmd.extend(['-t', str(round(duration, 3))])
        elif out_time is not None and out_time > 0:
            cmd.extend(['-to', str(out_time)])
        
        # Build video filter chain - combine all filters into a single filtergraph
        filter_parts = []
        
        # Crop filter
        filter_parts.append(f"crop={width}:{height}:{x}:{y}")
        
        # Scale filter if target resolution specified
        if target_width and target_height:
            # Scale to exact target resolution
            scale_filter = f"scale={target_width}:{target_height}:flags=bilinear"
            filter_parts.append(scale_filter)
        
        # FPS filter if specified
        if output_fps:
            filter_parts.append(f"fps={float(output_fps)}")
        
        if filter_parts:
            cmd.extend(['-vf', ','.join(filter_parts)])
        
        cmd.extend([
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            return jsonify({'error': f'FFmpeg error: {result.stderr}'}), 500
        
        if not os.path.exists(output_path):
            return jsonify({'error': 'Output file not created'}), 500
        
        return jsonify({
            'success': True,
            'filename': output_name,
            'message': 'Video processed successfully'
        })
    
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Processing timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Download cropped video ---
@app.route('/download/<filename>')
def download_video(filename):
    return send_from_directory(
        app.config['OUTPUT_FOLDER'],
        filename,
        as_attachment=True
    )


# --- Delete uploaded video ---
@app.route('/delete/<filename>', methods=['POST'])
def delete_video(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'{filename} deleted'})
    return jsonify({'error': 'File not found'}), 404


# --- Delete all uploaded videos ---
@app.route('/delete_all', methods=['POST'])
def delete_all_videos():
    upload_dir = app.config['UPLOAD_FOLDER']
    count = 0
    if os.path.exists(upload_dir):
        for f in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, f)
            if os.path.isfile(filepath):
                os.remove(filepath)
                count += 1
    return jsonify({'success': True, 'deleted_count': count, 'message': f'{count} video(s) deleted'})


# --- Serve uploaded videos for preview ---
@app.route('/watch/<filename>')
def watch_video(filename):
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename,
        as_attachment=False
    )


# --- Error Handlers ---
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size: 2GB'}), 413


@app.errorhandler(414)
def request_uri_too_long(error):
    return jsonify({'error': 'Request URL too long'}), 414


@app.errorhandler(429)
def too_many_requests(error):
    return jsonify({'error': 'Too many requests, please try again later'}), 429


@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# --- Extract frames from video ---
@app.route('/extract_frames', methods=['POST'])
def extract_frames():
    data = request.get_json()
    filename = data.get('filename')
    num_frames = int(data.get('num_frames', 10))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Video not found'}), 404

    try:
        # Get video duration using ffprobe
        probe_cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json', filepath
        ]
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
        if probe_result.returncode != 0:
            return jsonify({'error': 'Failed to probe video'}), 500

        probe_data = json.loads(probe_result.stdout)
        duration = float(probe_data['format']['duration'])

        if duration <= 0:
            return jsonify({'error': 'Invalid video duration'}), 500

        # Extract evenly spaced frames using ffmpeg
        # Calculate timestamps for each frame
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], '.frames', uuid.uuid4().hex)
        os.makedirs(output_dir, exist_ok=True)

        frame_pattern = os.path.join(output_dir, 'frame_%04d.jpg')

        # Build select filter for evenly spaced frames
        # Select frame at timestamp: (duration / num_frames) * index
        timestamps = []
        for i in range(num_frames):
            ts = (duration * (i + 0.5)) / num_frames  # Middle of each segment
            ts = min(ts, duration - 0.01)  # Don't exceed duration
            timestamps.append(ts)

        # Use -ss with multiple seeks to extract specific timestamps
        ffmpeg_parts = ['ffmpeg', '-i', filepath]
        select_conditions = []
        for i, ts in enumerate(timestamps):
            select_conditions.append(f'teq(t\\,{ts})')

        select_filter = '+'.join(select_conditions)
        ffmpeg_parts.extend([
            '-vf', f'select=\'{select_filter}\',setpts=N/(FRAME_RATE*TB)',
            '-q:v', '2',
            '-frames:v', str(num_frames),
            '-y',
            frame_pattern
        ])

        result = subprocess.run(ffmpeg_parts, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            # Fallback: simple approach with fps filter
            fps_rate = num_frames / duration
            output_dir2 = os.path.join(app.config['UPLOAD_FOLDER'], '.frames', uuid.uuid4().hex)
            os.makedirs(output_dir2, exist_ok=True)
            frame_pattern2 = os.path.join(output_dir2, 'frame_%04d.jpg')

            ffmpeg_cmd2 = [
                'ffmpeg', '-i', filepath,
                '-vf', f'fps={fps_rate:.4f}',
                '-q:v', '2',
                '-frames:v', str(num_frames),
                '-y',
                frame_pattern2
            ]

            result = subprocess.run(ffmpeg_cmd2, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                return jsonify({'error': f'FFmpeg extraction failed: {result.stderr}'}), 500
            output_dir = output_dir2

        # Collect frame files and encode to base64
        frame_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.jpg')])
        frames_b64 = []

        for frame_file in frame_files[:num_frames]:
            frame_path = os.path.join(output_dir, frame_file)
            with open(frame_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                frames_b64.append(f"data:image/jpeg;base64,{encoded}")

        return jsonify({
            'success': True,
            'frames': frames_b64,
            'num_frames': len(frames_b64)
        })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Frame extraction timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/system_prompt')
def api_system_prompt():
    return jsonify({'system_prompt': Config.get_system_prompt()})

def purge_uploaded_videos():
    """Remove all uploaded videos from the upload directory on launch."""
    upload_dir = app.config['UPLOAD_FOLDER']
    output_dir = app.config['OUTPUT_FOLDER']
    
    # Purge upload folder
    if os.path.exists(upload_dir):
        count = 0
        for f in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, f)
            if os.path.isfile(filepath):
                os.remove(filepath)
                count += 1
        if count > 0:
            print(f"  Purged {count} uploaded video(s) from {upload_dir}")
    else:
        os.makedirs(upload_dir, exist_ok=True)
    
    # Purge output folder
    if os.path.exists(output_dir):
        count = 0
        for f in os.listdir(output_dir):
            filepath = os.path.join(output_dir, f)
            if os.path.isfile(filepath):
                os.remove(filepath)
                count += 1
        if count > 0:
            print(f"  Purged {count} processed video(s) from {output_dir}")


if __name__ == '__main__':
    print("=" * 60)
    print("  Video Tools App")
    print("=" * 60)
    print(f"  →  http://localhost:5000")
    print("=" * 60)
    
    # Purge old uploaded and processed videos on launch
    purge_uploaded_videos()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
