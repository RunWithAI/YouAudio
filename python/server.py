from flask import Flask, render_template, jsonify, request, g, session, Response, send_file
from flask_cors import CORS
from flask_sock import Sock
import yt_dlp
import os
import logging
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
import json
# from youtube_transcript_api import YouTubeTranscriptApi
import threading
# import asyncio
import websockets
import json
import re
import webbrowser
# from pytube import YouTube
import time
import sys
import pytz
from flask_babel import Babel, gettext as _
import socks
import requests
import subprocess
# from PIL import Image, ImageDraw
# from pystray import Icon, Menu, MenuItem
# import multiprocessing
import signal
# import edge_tts
# import asyncio
import packaging.version


# Current app version - should match the one in youaudio.spec
CURRENT_VERSION = '1.0.0'

def perform_migration(old_version):
    """
    Perform necessary migrations based on version differences.
    Add migration steps here when making breaking changes between versions.
    """
    logger.info(f"Performing migration from version {old_version} to {CURRENT_VERSION}")
    
    try:
        old_ver = packaging.version.parse(old_version)
        current_ver = packaging.version.parse(CURRENT_VERSION)
        
        # Example migration steps - add more as needed
        if old_ver < packaging.version.parse('1.0.0'):
            # Migration for pre-1.0.0 versions
            logger.info("Migrating from pre-1.0.0 version")
            _migrate_pre_1_0_0()
            
        # Add more version-specific migrations here
        # if old_ver < packaging.version.parse('1.1.0'):
        #     _migrate_to_1_1_0()
        
        # Update the version in config after successful migration
        config_path = get_config_path()
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        config['version'] = CURRENT_VERSION
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
            
        logger.info("Migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        raise

def _migrate_pre_1_0_0():
    """
    Migration steps for pre-1.0.0 versions
    Add specific migration logic here
    """
    try:
        app_data_dir = get_app_data_dir()
        db_path = get_db_path()
        
        # Example: Update database schema
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add new columns or tables if needed
        # cursor.execute('ALTER TABLE videos ADD COLUMN new_field TEXT')
        
        conn.commit()
        conn.close()
        
        # Example: Move files to new locations if needed
        old_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
        if os.path.exists(old_config_path):
            import shutil
            shutil.move(old_config_path, get_config_path())
        
    except Exception as e:
        logger.error(f"Error in pre-1.0.0 migration: {str(e)}")
        raise

def check_and_perform_migration():
    """Check if migration is needed and perform it if necessary"""
    try:
        config_path = get_config_path()
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            stored_version = config.get('version', '0.0.0')
            if packaging.version.parse(stored_version) < packaging.version.parse(CURRENT_VERSION):
                logger.info(f"Version upgrade needed: {stored_version} -> {CURRENT_VERSION}")
                perform_migration(stored_version)
            else:
                logger.info(f"No migration needed. Current version: {stored_version}")
    except Exception as e:
        logger.error(f"Error checking version: {str(e)}")
        raise

def init_app_data():
    """Initialize application data directory and files"""
    app_data_dir = get_app_data_dir()
    
    # Ensure config file exists
    config_path = get_config_path()
    if not os.path.exists(config_path):
        default_config = {
            'proxy': None,
            'native_language': 'en',
            'subtitle_language': 'en',
            'openai_key': None,
            'hunyuan_key': None,
            'qianwen_key': None,
            'default_llm': 'none',
            'host_port': 9527,
            'version': CURRENT_VERSION  # Add version to config
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
    
    # Check for and perform any necessary migrations
    check_and_perform_migration()
    
    return app_data_dir

def get_app_path():
    """Get the application base path whether running as script or frozen exe"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def get_app_data_dir():
    """Get the appropriate application data directory based on the platform"""
    if sys.platform == 'darwin':
        # Use macOS standard application support directory
        app_support = Path.home() / 'Library' / 'Application Support' / 'YouAudio'
        app_support.mkdir(parents=True, exist_ok=True)
        return str(app_support)
    elif sys.platform == 'win32':
        # Use Windows standard application data directory
        return os.path.join(get_app_path(), '_internal')
    else:
        # For other platforms, use the current directory
        return os.path.dirname(os.path.abspath(__file__))

def get_config_path():
    """Get the path to the config file"""
    return os.path.join(get_app_data_dir(), 'config.json')

def get_db_path():
    """Get the path to the database file"""
    return os.path.join(get_app_data_dir(), 'audiotube.db')

def setup_logging():
    """Set up logging with both console and file handlers"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(get_app_data_dir(), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # File handler
    log_file = os.path.join(logs_dir, 'server.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Set up logging
logger = setup_logging()

# Log startup
logger.info("Starting AudioTube server...")

app = Flask(__name__,
    template_folder='templates',
    static_folder='static'
)

# Set a secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_change_this')

sock = Sock(app)

# Babel configuration
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
app.config['LANGUAGES'] = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'pt': 'Português',
    'ja': '日本語',
    'ko': '한국어',
    'zh_Hans': '简体中文',
    'zh_Hant': '繁體中文'
}

def get_locale():
    # Get language from session, fallback to default
    language = session.get('language', request.accept_languages.best_match(app.config['LANGUAGES'].keys()))
    # Convert hyphenated codes to underscore format
    if language and '-' in language:
        language = language.replace('-', '_')
    return language

babel = Babel(app, locale_selector=get_locale)

# Make get_locale available to templates
@app.context_processor
def inject_locale():
    return dict(get_locale=get_locale)

@app.route('/set-language/<language>')
def set_language(language):
    if language in app.config['LANGUAGES']:
        session['language'] = language
    return jsonify({'status': 'success'})

# More permissive CORS setup
CORS(app, 
    resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "DELETE", "OPTIONS", "HEAD"],
            "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin"],
            "supports_credentials": True,
            "max_age": 3600
        }
    },
    expose_headers=["Content-Type", "X-CSRFToken"],
    allow_headers=["Content-Type", "Authorization", "Accept", "Origin"],
    supports_credentials=True
)

logger.info("CORS configured")

@app.before_request
def log_request_info():
    # logger.info("=== New Request ===")
    # logger.info(f"Method: {request.method}")
    # logger.info(f"URL: {request.url}")
    # logger.info("Headers:")
    # for header, value in request.headers:
    #     logger.info(f"  {header}: {value}")
    return None

def add_cors_headers(response):
    """Add CORS headers to the response."""
    # logger.info('Adding CORS headers to response')
    
    # If response is a tuple (response, status_code), extract just the response
    if isinstance(response, tuple):
        response_obj = response[0]
        status_code = response[1]
    else:
        response_obj = response
        status_code = 200
    
    # Add CORS headers
    response_obj.headers['Access-Control-Allow-Origin'] = '*'
    response_obj.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response_obj.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    # Return response with status code if it was provided
    if isinstance(response, tuple):
        return response_obj, status_code
    return response_obj

@app.after_request
def after_request(response):
    return add_cors_headers(response)

@app.route('/')
def index():
    return render_template('channels.html', config=app.config)

@app.route('/player')
def player():
    return render_template('player.html')

@app.route('/api/videos', methods=['GET'])
def get_videos():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM videos')
        total = cursor.fetchone()[0]
        
        # Get paginated videos
        cursor.execute('''
            SELECT video_id, title, created_at, channel_name, upload_date,duration 
            FROM videos 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        
        videos = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'status': 'success',
            'videos': videos,
            'total': total
        })
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/videos/<video_id>', methods=['DELETE', 'OPTIONS'])
def delete_video(video_id):
    if request.method == 'OPTIONS':
        logger.info("Received OPTIONS request")
        response = make_response()
        return add_cors_headers(response)
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # First delete all marked segments for this video
        c.execute('DELETE FROM marked_segments WHERE video_id = ?', (video_id,))
        
        # Then delete the video
        c.execute('DELETE FROM videos WHERE video_id = ?', (video_id,))
        
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Video deleted successfully'})
    except Exception as e:
        app.logger.error(f"Error deleting video: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/transcript', methods=['POST', 'OPTIONS'])
def save_transcript():
    logger.debug('Received request to /api/transcript')
    logger.debug('Request method: %s', request.method)
    logger.debug('Request headers: %s', request.headers)
    
    if request.method == 'OPTIONS':
        logger.info("Received OPTIONS request for /api/transcript")
        response = make_response()
        return add_cors_headers(response)

    try:
        data = request.json
        logger.debug('Received data: %s', data)
        video_id = data.get('video_id')
        transcript = data.get('transcript')
        title = data.get('title')
        channel_name = request.json.get('channel_name')
        uploaded_at = request.json.get('uploaded_at')
 
        if not all([video_id, transcript, title,channel_name, uploaded_at]):
            logger.error('Missing required fields')
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM videos WHERE video_id = ?", (video_id,))
        if c.fetchone()[0] > 0:
            logger.error('Transcript already exists')
            return jsonify({'status': 'error', 'message': 'Transcript already exists'}), 409

        c.execute('''
            INSERT OR REPLACE INTO videos (video_id, title, transcript, channel_name, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, title, transcript, channel_name, uploaded_at))
        conn.commit()

        response = jsonify({'status': 'success'})
        return add_cors_headers(response)
    except Exception as e:
        logger.error(f"Error saving transcript: {str(e)}")
        response = jsonify({'status': 'error', 'message': str(e)}), 500
        return add_cors_headers(response)
    finally:
        if conn:
            conn.close()

@app.route('/api/transcript/<video_id>', methods=['GET', 'OPTIONS'])
def get_transcript(video_id):
    logger.debug('Received request to /api/transcript/<video_id>')
    logger.debug('Request method: %s', request.method)
    logger.debug('Request headers: %s', request.headers)
    if request.method == 'OPTIONS':
        
        response = make_response()
        return add_cors_headers(response)

    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT transcript FROM videos WHERE video_id = ?', (video_id,))
        result = c.fetchone()
        if result:
            response = jsonify({'status': 'success', 'transcript': result[0]})
        else:
            response = jsonify({'status': 'error', 'message': 'Transcript not found'}), 404
        return add_cors_headers(response)
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        response = jsonify({'status': 'error', 'message': str(e)}), 500
        return add_cors_headers(response)
    finally:
        if conn:
            conn.close()

@app.route('/api/prepare/<video_id>', methods=['GET', 'OPTIONS'])
def prepare_video_route(video_id):
    """Check video status and prepare it if needed."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Check current status
        c.execute('SELECT download_status, download_error FROM videos WHERE video_id = ?', (video_id,))
        result = c.fetchone()
        
        if not result:
            return jsonify({
                'status': 'error',
                'message': 'Video not found'
            }), 404
            
        download_status, download_error = result
        
        # Check if file exists
        audio_path = os.path.join('downloads', f'{video_id}.mp3')
        file_exists = os.path.exists(audio_path)
        
        response_data = {
            'status': download_status,
            'message': None,
            'error': download_error,
            'audio_url': f'/api/audio/{video_id}' if download_status == 'completed' and file_exists else None
        }
        
        if download_status == 'completed' and not file_exists:
            # File was marked as completed but is missing, restart download
            c.execute('''
                UPDATE videos 
                SET download_status = 'downloading',
                    download_error = NULL
                WHERE video_id = ?
            ''', (video_id,))
            conn.commit()
            
            thread = threading.Thread(target=download_audio, args=(video_id,))
            thread.daemon = True
            thread.start()
            
            response_data['status'] = 'downloading'
            response_data['message'] = 'Restarting download'
            
        elif download_status == 'downloading':
            response_data['message'] = 'Download in progress'
            
        elif download_status == 'completed' and file_exists:
            response_data['message'] = 'Ready to play'
            
        elif download_status == 'failed':
            response_data['message'] = 'Download failed'
            
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error preparing video: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/audio/<video_id>')
def get_audio(video_id):
    try:
        # Get file path from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT file_path FROM videos WHERE video_id = ?', (video_id,))
        result = cursor.fetchone()
        
        if result and result['file_path']:
            audio_path = result['file_path']
            if os.path.exists(audio_path):
                return send_file(audio_path, mimetype='audio/mpeg')
        
        return jsonify({
            'status': 'error',
            'message': 'Audio file not found'
        }), 404
        
    except Exception as e:
        logger.error(f"Error getting audio file: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/video/<video_id>', methods=['GET', 'DELETE', 'OPTIONS'])
def handle_video(video_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET,DELETE,OPTIONS')
        return response
        
    if request.method == 'GET':
        try:
            # Get video details from database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get video info and transcript in one query
            query = '''
                SELECT video_id, title, created_at, transcript 
                FROM videos 
                WHERE video_id = ?
            '''
            logger.info(f"Executing query: {query} with video_id: {video_id}")
            cursor.execute(query, (video_id,))
            row = cursor.fetchone()
            
            # logger.info(f"Query result: {dict(row) if row else None}")
            
            if not row:
                logger.error(f"Video not found: {video_id}")
                return jsonify({
                    'status': 'error',
                    'message': 'Video not found'
                }), 404
            
            # Convert row to dict for easier access
            video_data = dict(row)
            # logger.info(f"Video data: {video_data}")
            
            # Parse the transcript JSON string
            transcript_data = json.loads(video_data['transcript']) if video_data['transcript'] else []
            
            return jsonify({
                'status': 'success',
                'video': {
                    'video_id': video_data['video_id'],
                    'title': video_data['title'],
                    'created_at': video_data['created_at']
                },
                'transcript': transcript_data
            }) 
            
        except Exception as e:
            logger.error(f"Error getting video details: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        finally:
            if conn:
                conn.close()
            
    elif request.method == 'DELETE':
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Delete transcript entries
            cursor.execute('DELETE FROM marked_segments WHERE video_id = ?', (video_id,))
            
            # Delete video entry
            cursor.execute('DELETE FROM videos WHERE video_id = ?', (video_id,))
            
            # Delete audio file
            audio_path = os.path.join(app.root_path, 'audio_files', f'{video_id}.mp3')
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Video deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting video: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        finally:
            if conn:
                conn.close()

active_downloads = {}  # Track active downloads
connected_clients = set()

# Global lock for file operations
file_locks = {}
file_locks_lock = threading.Lock()

def get_file_lock(filename):
    with file_locks_lock:
        if filename not in file_locks:
            file_locks[filename] = threading.Lock()
        return file_locks[filename]

@sock.route('/ws')
def websocket(ws):
    connected_clients.add(ws)
    while True:
        try:
            # Keep the connection alive and wait for messages
            message = ws.receive()
            # Echo back any received messages (optional)
            if message:
                ws.send(message)
        except Exception as e:
            print(f"WebSocket error: {e}")
            connected_clients.discard(ws)
            break

def progress_hook(d):
    status = d['status']
    progress_message = {
        'video_id': d.get('info_dict', {}).get('id'),
        'filename': d['filename'],
    }

    if status == 'downloading':
        # Extract clean percentage from the colored string
        percent_str = d.get('_percent_str', '0%')
        clean_percent = re.search(r'(\d+\.?\d*)%', percent_str)
        clean_percent = f"{clean_percent.group(1)}%" if clean_percent else '0%'
        progress_message['percent'] = clean_percent
    elif status == 'finished':
        progress_message['percent'] = '100%'
        progress_message['status'] = 'Converting to MP3...'

    # Store progress in active_downloads
    if 'info_dict' in d and 'id' in d['info_dict']:
        active_downloads[d['info_dict']['id']] = progress_message
        # Broadcast progress to all connected clients
        for client in connected_clients:
            try:
                client.send(json.dumps(progress_message))
            except Exception as e:
                print(f"Error sending to client: {e}")
                connected_clients.discard(client)

# Start download in a separate thread
def download_audio(video_id):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'downloads/%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook],
            # Subtitle options
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [PROXY_CONFIG['subtitle_language']],  # Download subtitles in configured language
            'subtitlesformat': 'json3',
            'skip_download': False,
        }

        channel_name = ""
        upload_date = ""
        title = ""
        transcript_json = None

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading audio for video ID: {video_id}")
            info_dict = ydl.extract_info(video_id, download=True)
            channel_name = info_dict.get('uploader', '')
            upload_date = info_dict.get('upload_date', '')
            title = info_dict.get('title', '')
            print(f"Finished downloading audio for video ID: {video_id}")

            # Process subtitles after download
            transcript_json = process_subtitles(video_id)

            # Send final completion message
            final_message = {
                'video_id': video_id,
                'status': 'completed',
                'has_subtitles': transcript_json is not None,
                'title': title
            }
            for client in connected_clients:
                try:
                    client.send(json.dumps(final_message))
                except Exception as e:
                    print(f"Error sending to client: {e}")
                    connected_clients.discard(client)

        # Update status to completed and save transcript
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE videos 
            SET download_status = 'completed',
                channel_name = ?,
                upload_date = ?,
                transcript = ?,
                title = ?
            WHERE video_id = ?
        ''', (channel_name, upload_date, 
             json.dumps(transcript_json) if transcript_json else None,
             title, 
             video_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error downloading audio: {str(e)}")
        # Update status to failed with error message
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE videos 
            SET download_status = 'failed',
                download_error = ?
            WHERE video_id = ?
        ''', (str(e), video_id))
        conn.commit()
    finally:
        if conn:
            conn.close()

def process_subtitles(video_id):
    """Process the downloaded subtitles into a simplified format"""
    try:
        # Read the downloaded subtitle file
        subtitle_file = f'downloads/{video_id}.{PROXY_CONFIG["subtitle_language"]}.json3'
        if not os.path.exists(subtitle_file):
            logger.warning(f"Subtitles not found for video ID: {video_id}")
            return None
            
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            raw_subtitles = json.load(f)
        
        # Process subtitles into simplified format
        processed_subtitles = []
        for event in raw_subtitles.get('events', []):
            # Convert milliseconds to seconds
            start = event.get('tStartMs', 0) / 1000
            duration = event.get('dDurationMs', 0) / 1000
            
            # Combine all text segments
            text = ' '.join(
                segment.get('utf8', '')
                for segment in event.get('segs', [])
                if segment.get('utf8')
            ).strip()
            
            if text:  # Only add if there's actual text
                processed_subtitles.append({
                    'text': text,
                    'start': round(start, 2),
                    'duration': round(duration, 2)
                })
        
        # Save processed subtitles
        output_file = f'downloads/{video_id}_processed.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_subtitles, f, ensure_ascii=False, indent=2)
            
        # Optionally delete the original subtitle file
        os.remove(subtitle_file)
        
        return processed_subtitles
    except Exception as e:
        logger.error(f"Error processing subtitles: {str(e)}")
        return None

@app.route('/api/channel/<channel_id>/latest', methods=['GET'])
def get_latest_videos(channel_id):
    """API endpoint to get latest videos from a channel."""
    try:
        limit = request.args.get('limit', default=10, type=int)
        videos = get_channel_latest_videos(channel_id, limit)
        
        if not videos:
            return jsonify({
                'status': 'error',
                'message': 'No videos found or invalid channel'
            }), 404

        return jsonify({
            'status': 'success',
            'videos': videos
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def check_new_videos():
    """Background task to check for new videos from tracked channels."""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Get all tracked channels
        c.execute('SELECT channel_id, last_check_time FROM tracked_channels')
        channels = c.fetchall()
        
        for channel_id, last_check in channels:
            # Get latest videos
            latest_videos = get_channel_latest_videos(channel_id, limit=5)
            
            for video in latest_videos:
                # Check if video is newer than last check and not already in database
                c.execute('SELECT 1 FROM videos WHERE video_id = ?', (video['video_id'],))
                if not c.fetchone():
                    # Add new video to database
                    c.execute('''
                        INSERT INTO videos (video_id, title, download_status, created_at)
                        VALUES (?, ?, 'pending', ?)
                    ''', (video['video_id'], video['title'], get_local_datetime()))
                    
                    # Start download in background
                    thread = threading.Thread(target=download_audio, args=(video['video_id'],))
                    thread.daemon = True
                    thread.start()
            
            # Update last check time
            c.execute('''
                UPDATE tracked_channels 
                SET last_check_time = CURRENT_TIMESTAMP 
                WHERE channel_id = ?
            ''', (channel_id,))
            
        conn.commit()
    except Exception as e:
        logger.error(f"Error checking new videos: {str(e)}")
    finally:
        if conn:
            conn.close()

# Database setup
def get_db_connection():
    """Get a database connection"""
    db_path = get_db_path()
    logger.info(f"Opening database connection to: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def check_column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    return any(col[1] == column for col in columns)

def migrate_db():
    """Migrate database schema to latest version."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add new columns to videos table if they don't exist
        required_columns = {
            'duration': 'INTEGER',
            'file_path': 'TEXT',
            'transcript': 'TEXT',
            'channel_name': 'TEXT',
            'upload_date': 'TEXT',
            'created_at': 'TEXT',
            'download_status': 'TEXT'
        }
        
        for column, type in required_columns.items():
            if not check_column_exists(cursor, 'videos', column):
                logger.info(f"Adding column {column} to videos table")
                cursor.execute(f'ALTER TABLE videos ADD COLUMN {column} {type}')
        
        # Add new columns to channels table if they don't exist
        channel_columns = {
            'channel_name': 'TEXT',
            'thumbnail_url': 'TEXT',
            'subscriber_count': 'INTEGER',
            'video_count': 'INTEGER',
            'last_checked': 'TEXT'
        }
        
        for column, type in channel_columns.items():
            if not check_column_exists(cursor, 'favorite_channels', column):
                logger.info(f"Adding column {column} to favorite_channels table")
                cursor.execute(f'ALTER TABLE favorite_channels ADD COLUMN {column} {type}')
        
        # Add new columns to marked_segments table if they don't exist
        segment_columns = {
            'start_time': 'REAL',
            'end_time': 'REAL',
            'text': 'TEXT',
            'created_at': 'TEXT'
        }
        
        for column, type in segment_columns.items():
            if not check_column_exists(cursor, 'marked_segments', column):
                logger.info(f"Adding column {column} to marked_segments table")
                cursor.execute(f'ALTER TABLE marked_segments ADD COLUMN {column} {type}')
        
        # Create statistics table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                audio_play_time INTEGER DEFAULT 0,
                target_play_time INTEGER DEFAULT 0,
                words_collected INTEGER DEFAULT 0,
                words_removed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        ''')

        # Create word_collections table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS word_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                selected_text TEXT NOT NULL,
                translation TEXT,
                audio_path TEXT NOT NULL,
                segment_start REAL NOT NULL,
                segment_end REAL NOT NULL,
                context_text TEXT,
                collected_date TEXT NOT NULL,
                is_removed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                updated_at TIMESTAMP DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                UNIQUE(selected_text, audio_path, segment_start, segment_end)
            )
        ''')

        words_columns = {
            'updated_at': 'TIMESTAMP'
        }
        
        for column, type in words_columns.items():
            if not check_column_exists(cursor, 'word_collections', column):
                logger.info(f"Adding column {column} to word_collections table")
                cursor.execute(f'ALTER TABLE word_collections ADD COLUMN {column} {type}')

        conn.commit()
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize the database."""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Videos table (updated)
        c.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            channel_name TEXT,
            upload_date TEXT,
            download_status TEXT DEFAULT 'pending',
            download_error TEXT,
            transcript TEXT,
            created_at TEXT
        )
        ''')
        
        # Create marked_segments table
        c.execute('''
            CREATE TABLE IF NOT EXISTS marked_segments (
                video_id TEXT,
                segment_start INTEGER,
                segment_end INTEGER,
                segment_text TEXT,
                PRIMARY KEY (video_id, segment_start)
            )
        ''')
        
        # Create favorite_channels table
        c.execute('''
            CREATE TABLE IF NOT EXISTS favorite_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT NOT NULL,
                created_at TEXT
            )
        ''')
        
        # Tracked channels table
        c.execute('''
        CREATE TABLE IF NOT EXISTS tracked_channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT,
            last_check_time TEXT
        )
        ''')

        # Create summary table
        c.execute('''
            CREATE TABLE IF NOT EXISTS summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                summary_text TEXT,
                llm_service TEXT,
                created_at DATETIME
            )
        ''')
        
        conn.commit()
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

    # Run migration after initial setup
    migrate_db()

@app.route('/api/mark-segment', methods=['POST'])
def mark_segment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400

        # Validate required fields
        required_fields = ['video_id', 'segment_start', 'segment_text']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        video_id = data['video_id']
        segment_start = float(data['segment_start'])  # Convert to float as it comes as string from JS
        segment_text = data['segment_text']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the transcript from videos table
        cursor.execute('SELECT transcript FROM videos WHERE video_id = ?', (video_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            return jsonify({
                'status': 'error',
                'message': 'Video or transcript not found'
            }), 404
            
        # Parse the transcript JSON
        transcript = json.loads(result[0])
        
        # Find the current segment and next segment
        current_segment = None
        next_segment = None
        for i, segment in enumerate(transcript):
            if segment['start'] == segment_start:
                current_segment = segment
                if i < len(transcript) - 1:
                    next_segment = transcript[i + 1]
                break
        
        if not current_segment:
            return jsonify({
                'status': 'error',
                'message': 'Segment not found in transcript'
            }), 404
            
        # Calculate segment end time
        segment_end = next_segment['start'] if next_segment else segment_start + 5
        
        # Insert the marked segment
        cursor.execute('''
            INSERT OR REPLACE INTO marked_segments (video_id, segment_start, segment_end, segment_text, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, segment_start, segment_end, segment_text, get_local_datetime()))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Segment marked successfully'
        })
    except Exception as e:
        logger.error(f"Error marking segment: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/unmark-segment', methods=['POST'])
def unmark_segment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400

        # Validate required fields
        required_fields = ['video_id', 'segment_start']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        video_id = data['video_id']
        segment_start = float(data['segment_start'])  # Convert to float as it comes as string from JS
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM marked_segments 
            WHERE video_id = ? AND segment_start = ?
        ''', (video_id, segment_start))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Segment unmarked successfully'
        })
    except Exception as e:
        logger.error(f"Error unmarking segment: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/marked-segments/<video_id>', methods=['GET'])
def get_marked_segments(video_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT segment_start, segment_end, segment_text, created_at 
            FROM marked_segments 
            WHERE video_id = ? 
            ORDER BY segment_start
        ''', (video_id,))
        segments = [{'start': row[0], 'end': row[1], 'text': row[2], 'created_at': row[3]} for row in c.fetchall()]
        return jsonify({'status': 'success', 'segments': segments})
    except Exception as e:
        app.logger.error(f"Error getting marked segments: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/channels')
def channels():
    return render_template('channels.html', config=app.config)

@app.route('/api/search-channel/<query>')
def search_channel(query):
    try:
        # Use yt-dlp to search for channels
        ydl_opts = {
            'proxy': PROXY_CONFIG['proxy'],
            'extract_flat': True,
            'force_generic_extractor': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f'ytsearch5:{query}', download=False)
            channels = []
            seen_channels = set()
            
            for entry in result['entries']:
                channel_id = entry.get('channel_id')
                if channel_id and channel_id not in seen_channels:
                    seen_channels.add(channel_id)
                    channels.append({
                        'channel_id': channel_id,  
                        'name': entry.get('channel', 'Unknown Channel'),
                        'subscriber_count': entry.get('subscriber_count', 'N/A'),
                        'video_count': entry.get('video_count', 'N/A')
                    })
            
            return jsonify({
                'status': 'success',
                'channels': channels
            })
    except Exception as e:
        logger.error(f"Error searching channel: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/suggested-channels', methods=['GET'])
def get_suggested_channels():
    channels = {
        'en': [
            {'name': 'English with Lucy', 'channel_id': '@EnglishwithLucy'},
            {'name': 'Rachel\'s English', 'channel_id': '@rachelsenglish'},
            {'name': 'BBC Learning English', 'channel_id': '@bbclearningenglish'},
            {'name': 'EnglishClass101', 'channel_id': '@EnglishClass101'},
            {'name': 'VOA Learning English', 'channel_id': '@voalearningenglish'}
            ],
        'es': [
            {'name': 'Easy Spanish', 'channel_id': '@EasySpanish'},
            {'name': 'Butterfly Spanish', 'channel_id': '@ButterflySpanish'},
            {'name': 'Dreaming Spanish', 'channel_id': '@DreamingSpanish'},
            {'name': 'SpanishPod101', 'channel_id': '@spanishpod101'},
            {'name': 'Spanish and Go', 'channel_id': '@SpanishandGo'}
        ],        
        'fr': [
            {'name': 'FrenchPod101', 'channel_id': '@frenchpod101'},
            {'name': 'Oh La La, I Speak French!', 'channel_id': '@ohlalafrench'},
            {'name': 'Parlez-vous French?', 'channel_id': '@ParlezvousFRENCH'},
            {'name': 'Comme Une Française', 'channel_id': '@Commeunefrancaise'},
            {'name': 'Easy French', 'channel_id': '@EasyFrench'}
        ],
        'de': [
            {'name': 'Easy German', 'channel_id': '@EasyGerman'},
            {'name': 'Learn German with Anja', 'channel_id': '@LearnGermanwithAnja'},
            {'name': 'Deutsch mit Rieke', 'channel_id': '@deutschmitrieke'},
            {'name': 'lingoni GERMAN', 'channel_id': '@lingoniGERMAN'},
            {'name': 'Deutsch für Euch', 'channel_id': '@DeutschFuerEuch'}
        ],        
        'it': [
            {'name': 'Learn Italian with Lucrezia', 'channel_id': 'UCqFTnpDIBRzQTh7m3JvL8A'},
            {'name': 'ItalianPod101', 'channel_id': 'UCsXVk37bltHxD1rDPwtNM8Q'},
            {'name': 'Italy Made Easy', 'channel_id': 'UC7d-l7wJ6Amz9B9Be38yNUQ'},
            {'name': 'LearnAmo', 'channel_id': 'UCz4tgANd4yy8Oe0iCXxP6jQ'},
            {'name': 'Learn Italian with ItalianPod101.com', 'channel_id': 'UCsXVk37bltHxD1rDPwtNM8Q'}
        ],
        'pt': [
            {'name': 'Learn Portuguese with PortuguesePod101', 'channel_id': '@portuguesepod101'},
            {'name': 'Speaking Brazilian Language School', 'channel_id': '@SpeakingBrazilian'},
            {'name': 'Portuguese with Carla', 'channel_id': '@portuguesewithcarla'},
            {'name': 'BrazilianPodClass', 'channel_id': '@BrazilianPodClass'}
        ],
        'jp': [
            {'name': 'JapanesePod101', 'channel_id': '@JapanesePod101'},
            {'name': 'Japanese Ammo with Misa', 'channel_id': '@JapaneseAmmowithMisa'},
            {'name': 'Miku Real Japanese', 'channel_id': '@mikurealjapanese'},
            {'name': 'Nihongo no Mori', 'channel_id': '@nihongonomori2013'},
            {'name': 'Yuko Sensei', 'channel_id': '@YukoSensei'}
        ],
        'ko': [
            {'name': 'Talk To Me In Korean', 'channel_id': '@talktomeinkorean'}, 
            {'name': 'GO! Billy Korean', 'channel_id': '@GoBillyKorean'}, 
            {'name': 'KoreanClass101', 'channel_id': '@KoreanClass101'},  
            {'name': 'Korean From Zero!', 'channel_id': '@koreanfromzero'}
        ],
        'zh_Hans':[],
        'zh_Hant': []
    }

    return jsonify({
        'status': 'success',
        'channels': channels
    })

@app.route('/api/favorite-channels', methods=['GET'])
def get_favorite_channels():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT channel_id, channel_name FROM favorite_channels ORDER BY created_at DESC')
        channels = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'status': 'success',
            'channels': channels
        })
    except Exception as e:
        logger.error(f"Error getting favorite channels: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/favorite-channel/<channel_id>', methods=['POST', 'DELETE'])
def manage_favorite_channel(channel_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if request.method == 'POST':
            data = request.get_json()
            channel_name = data.get('channel_name')
            
            cursor.execute('''
                INSERT INTO favorite_channels (channel_id, channel_name, created_at)
                VALUES (?, ?, ?)
            ''', (channel_id, channel_name, get_local_datetime()))
            
        else:  # DELETE
            cursor.execute('DELETE FROM favorite_channels WHERE channel_id = ?', (channel_id,))
        
        conn.commit()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logger.error(f"Error managing favorite channel: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/channel-videos/<channel_id>')
def get_channel_videos(channel_id):
    """Get videos from a YouTube channel with client-side pagination support."""

    print(f"get_channel_videos({channel_id}) with proxy {PROXY_CONFIG['proxy']}")
    try:
        # Get query parameters
        sort_by = request.args.get('sort', 'date')  # date, view_count, or rating
        
        ydl_opts = {
            'proxy': PROXY_CONFIG['proxy'],
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
            'playlist_items': '1-50',  # Get first 50 videos
            'date': 'today-1years'
        }

        # Add sorting
        # if sort_by == 'date':
        #     ydl_opts['playlistreverse'] = True  # Newest first
        # elif sort_by == 'view_count':
        #     ydl_opts['playlistsort'] = 'view_count'
        # elif sort_by == 'rating':
        #     ydl_opts['playlistsort'] = 'rating'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            channel_url = f'https://www.youtube.com/{channel_id}/videos' if channel_id.startswith('@') else f'https://www.youtube.com/channel/{channel_id}/videos'
            result = ydl.extract_info(channel_url, download=False)
            
            if not result:
                return jsonify({'error': 'Channel not found'}), 404

            videos = result.get('entries', [])

            # Format video data
            formatted_videos = []
            for video in videos:
                if not video:
                    continue
                    
                formatted_videos.append({
                    'id': video.get('id', ''),
                    'title': video.get('title', ''),
                    'thumbnail': video.get('thumbnail', ''),
                    'duration': str(timedelta(seconds=int(video.get('duration', 0)))),
                    'duration_seconds': video.get('duration', 0),
                    'view_count': video.get('view_count', 0),
                    'upload_date': video.get('upload_date', ''),
                    'channel_id': video.get('channel_id', ''),
                    'channel_title': video.get('channel', '')
                })

            return jsonify({
                'status': 'success',
                'videos': formatted_videos
            })

    except Exception as e:
        logger.error(f"Error fetching channel videos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save-video/<video_id>', methods=['POST'])
def save_video(video_id):
    try:
        # Use yt-dlp to get video info and download audio
        audio_dir = os.path.join(app.root_path, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        output_path = os.path.join(audio_dir, f'{video_id}.mp3')
        logger.info(f"Saving video to: {output_path}")
        
        # Get the path to the bundled ffmpeg
        if getattr(sys, 'frozen', False):
            # Running in a bundle
            if sys.platform == 'darwin':
                ffmpeg_path = os.path.join(sys._MEIPASS, 'ffmpeg', 'ffmpeg')
            else:
                ffmpeg_path = os.path.join(sys._MEIPASS, 'ffmpeg', 'ffmpeg.exe')
        else:
            # Running in normal Python environment
            ffmpeg_path = '/usr/local/bin/ffmpeg'  # Use system ffmpeg
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': ffmpeg_path,  # Specify ffmpeg location
            'outtmpl': os.path.join(audio_dir, video_id),
            'writesubtitles': True,  # Enable subtitle download
            'writeautomaticsub': True,  # Enable auto-generated subtitles
            'subtitleslangs': [PROXY_CONFIG['subtitle_language']],  # Download subtitles in configured language
            'subtitlesformat': 'json3',  # Use JSON format for subtitles            
            'quiet': True,
            'no_warnings': True
        }
        if sys.platform == 'win32':
            ydl_opts['ffmpeg_location'] = get_ffmpeg_path()
        
        logger.info(f"begin to save video {video_id} to {output_path} with ffmpeg path {ydl_opts['ffmpeg_location']}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download video info and subtitles
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=True)
                logger.info(f"Download completed for: {video_id}")
                
                # Check for subtitle file
                subtitle_path = os.path.join(audio_dir, f'{video_id}.{PROXY_CONFIG["subtitle_language"]}.json3')
                transcript = None
                
                if os.path.exists(subtitle_path):
                    logger.info(f"Found subtitle file: {subtitle_path}")
                    with open(subtitle_path, 'r', encoding='utf-8') as f:
                        subtitle_data = json.load(f)
                        # Convert subtitle format to match your needs
                        transcript = []
                        for event in subtitle_data.get('events', []):
                            if 'segs' in event:
                                text = ' '.join(seg.get('utf8', '') for seg in event.get('segs', []))
                                if text.strip():
                                    transcript.append({
                                        'text': text,
                                        'start': event.get('tStartMs', 0) / 1000,  # Convert to seconds
                                        'duration': (event.get('dDurationMs', 0) / 1000)
                                    })
                    
                    # Clean up subtitle file if you don't need it
                    os.remove(subtitle_path)
                else:
                    logger.info(f"Subtitle file not found: {subtitle_path}")
                
                # Store video info in database
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Check if we need to add the transcript column
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS videos (
                        video_id TEXT PRIMARY KEY,
                        title TEXT,
                        duration INTEGER,
                        file_path TEXT,
                        transcript TEXT,
                        channel_name TEXT,
                        upload_date TEXT,
                        created_at TEXT,
                        download_status TEXT
                    )
                ''')
                
                cursor.execute('''
                    INSERT OR REPLACE INTO videos (
                        video_id, title, duration, file_path, transcript,
                        channel_name, upload_date, created_at, download_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    info.get('title', ''),
                    info.get('duration', 0),
                    output_path,
                    json.dumps(transcript) if transcript else None,
                    info.get('channel', ''),
                    info.get('upload_date', ''),
                    get_local_datetime(),
                    'completed'
                ))
                conn.commit()

        except Exception as download_error:
            logger.error(f"Download error: {str(download_error)}")
            if not os.path.exists(output_path):
                raise download_error
        
        return jsonify({
            'status': 'success',
            'message': 'Video saved successfully',
            'file_path': output_path,
            'has_transcript': transcript is not None
        })
        
    except Exception as e:
        logger.error(f"Error saving video: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/preview-video/<video_id>', methods=['POST'])
def preview_video(video_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if the audio has already been downloaded
        cursor.execute('SELECT file_path FROM videos WHERE video_id = ? AND download_status = ?', (video_id, 'completed'))
        result = cursor.fetchone()
        if result:
            file_path = result['file_path']
            if os.path.exists(file_path):
                return jsonify({
                    'status': 'success',
                    'stream_url': '/api/audio/' + video_id,  # Assuming file_path is the URL or path to the audio file
                    'mime_type': 'mp3',
                    'title': '',  # Add any other metadata if stored
                    'duration': 0,
                    'quality': '',
                    'needs_proxy': False  # Local file does not need proxy
                })
            else:
                raise Exception(f"Audio file not found: {file_path}")
    except Exception as db_error:
        print(f"Database error: {str(db_error)}")
    finally:
        if conn:
            conn.close()

    # Proceed with yt-dlp logic if not found in database
    try:
        print(f"Getting stream URL for: {video_id} with proxy {PROXY_CONFIG['proxy']}")
        
        # Configure yt-dlp to get the best audio stream URL
        ydl_opts = {
            'proxy': PROXY_CONFIG['proxy'],
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            
            # Extract video information including formats
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            
            if not info:
                raise Exception("Could not fetch video information")
            
            # Get all formats
            formats = info.get('formats', [])
            if not formats:
                raise Exception("No formats available")
            
            # Filter audio-only formats
            audio_formats = []
            for f in formats:
                # Check if it's an audio-only format
                if (f.get('acodec') != 'none' and 
                    f.get('vcodec') in ['none', None] and 
                    'url' in f):
                    # Add format to list with safe bitrate value
                    f['abr'] = f.get('abr', 0) or 0  # Handle None values
                    audio_formats.append(f)
            
            if not audio_formats:
                raise Exception("No audio stream found")
            
            # Sort by quality (audio bitrate)
            audio_formats.sort(key=lambda x: (x.get('abr', 0) or 0), reverse=True)
            best_audio = audio_formats[0]
            
            # Get format details
            format_note = best_audio.get('format_note', 'unknown quality')
            ext = best_audio.get('ext', 'unknown format')
            abr = best_audio.get('abr', 0)
            
            logger.info(f"Found audio stream: {format_note} - {ext} ({abr}kbps)")
            
            # Determine MIME type based on extension
            mime_type = {
                'm4a': 'audio/mp4',
                'mp3': 'audio/mpeg',
                'opus': 'audio/opus',
                'ogg': 'audio/ogg',
                'webm': 'audio/webm',
            }.get(ext, 'audio/mp4')
            
            # Return both stream URL and proxy status
            return jsonify({
                'status': 'success',
                'stream_url': best_audio['url'],
                'mime_type': mime_type,
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'quality': f"{format_note} ({abr}kbps)",
                'needs_proxy': bool(PROXY_CONFIG['proxy'])  # Tell client if proxy is needed
            })
            
    except Exception as e:
        print(f"Error in preview_video: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/proxy-stream/<video_id>')
def proxy_stream(video_id):
    # Only allow proxy streaming if proxy is configured
    if not PROXY_CONFIG['proxy']:
        return jsonify({'status': 'error', 'message': 'Proxy not configured'}), 400
        
    try:
        # Get the stream URL using yt-dlp with proxy
        ydl_opts = {
            'proxy': PROXY_CONFIG['proxy'],
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            
            # Extract video information including formats
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
            
            if not info:
                raise Exception("Could not fetch video information")
            
            # Get all formats
            formats = info.get('formats', [])
            if not formats:
                raise Exception("No formats available")
            
            # Filter audio-only formats
            audio_formats = []
            for f in formats:
                # Check if it's an audio-only format
                if (f.get('acodec') != 'none' and 
                    f.get('vcodec') in ['none', None] and 
                    'url' in f):
                    # Add format to list with safe bitrate value
                    f['abr'] = f.get('abr', 0) or 0  # Handle None values
                    audio_formats.append(f)
            
            if not audio_formats:
                raise Exception("No audio stream found")
            
            # Sort by quality (audio bitrate)
            audio_formats.sort(key=lambda x: (x.get('abr', 0) or 0), reverse=True)
            best_audio = audio_formats[0]
            
            # Get format details
            format_note = best_audio.get('format_note', 'unknown quality')
            ext = best_audio.get('ext', 'unknown format')
            abr = best_audio.get('abr', 0)
            
            logger.info(f"Found audio stream: {format_note} - {ext} ({abr}kbps)")
            
            # Determine MIME type based on extension
            mime_type = {
                'm4a': 'audio/mp4',
                'mp3': 'audio/mpeg',
                'opus': 'audio/opus',
                'ogg': 'audio/ogg',
                'webm': 'audio/webm',
            }.get(ext, 'audio/mp4')
            
            # Configure proxy for requests
            proxies = None
            if PROXY_CONFIG['proxy']:
                proxies = {
                    'http': PROXY_CONFIG['proxy'],
                    'https': PROXY_CONFIG['proxy']
                }
            
            # Stream the audio through our server
            def generate():
                try:
                    # Make request with proxy and stream=True
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                    response = requests.get(best_audio['url'], 
                                         stream=True, 
                                         proxies=proxies,
                                         headers=headers)
                    
                    # Get content length if available
                    content_length = response.headers.get('content-length')
                    if content_length:
                        logger.info(f"Content length: {content_length} bytes")
                    
                    # Stream in chunks
                    chunk_size = 32 * 1024  # 32KB chunks
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            yield chunk
                            
                except Exception as e:
                    logger.error(f"Error streaming audio: {str(e)}")
                    yield b''  # Empty yield on error
            
            # Return streaming response with proper headers
            response = Response(generate(), mimetype=mime_type)
            response.headers['Content-Type'] = mime_type
            
            # Add other useful headers
            if 'content-length' in response.headers:
                response.headers['Content-Length'] = response.headers['content-length']
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Cache-Control'] = 'no-cache'
            
            return response
            
    except Exception as e:
        logger.error(f"Error proxying stream: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/temp_audio/<path:filename>')
def serve_temp_audio(filename):
    temp_dir = os.path.join(app.root_path, 'temp_audio')
    file_path = os.path.join(temp_dir, filename)
    
    # Get lock for this file
    lock = get_file_lock(filename)
    
    with lock:
        if not os.path.exists(file_path):
            print(f"Audio file not found at: {file_path}")
            return jsonify({
                'status': 'error',
                'message': 'Audio file not found'
            }), 404
            
        try:
            print(f"Serving audio file: {filename}")
            response = send_from_directory(temp_dir, filename)
            response.headers['Content-Type'] = 'audio/mpeg'
            response.headers['Accept-Ranges'] = 'bytes'
            return response
        except Exception as e:
            print(f"Error serving temp audio: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Error serving audio file'
            }), 500

def cleanup_temp_files():
    """Remove temporary audio files older than 1 hour"""
    temp_dir = os.path.join(app.root_path, 'temp_audio')
    if not os.path.exists(temp_dir):
        return
        
    current_time = datetime.now()
    min_age = timedelta(hours=1)
    
    for filename in os.listdir(temp_dir):
        # Get lock for this file
        lock = get_file_lock(filename)
        
        # Try to acquire lock - skip if file is in use
        if not lock.acquire(blocking=False):
            print(f"Skipping {filename} - file is in use")
            continue
            
        try:
            file_path = os.path.join(temp_dir, filename)
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            file_age = current_time - file_modified
            
            if file_age > min_age:
                os.remove(file_path)
                print(f"Removed old temporary file: {filename} (age: {file_age})")
                
                # Clean up the lock
                with file_locks_lock:
                    del file_locks[filename]
        except Exception as e:
            print(f"Error checking/removing temporary file {filename}: {str(e)}")
        finally:
            lock.release()

def run_cleanup():
    while True:
        cleanup_temp_files()
        time.sleep(3600)  # Run every hour

# Start cleanup in a background thread
# cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
# cleanup_thread.start()

def open_browser(port=9527):
    webbrowser.open(f'http://localhost:{port}/')

@app.route('/api/check-saved-videos', methods=['POST', 'OPTIONS'])
def check_saved_videos():
    if request.method == 'OPTIONS':
        logger.info("Received OPTIONS request")
        response = make_response()
        return add_cors_headers(response)
        
    try:
        video_ids = request.json.get('video_ids', [])
        if not video_ids:
            return jsonify({'status': 'error', 'message': 'No video IDs provided'}), 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all saved video IDs
        placeholders = ','.join(['?' for _ in video_ids])
        cursor.execute(f'SELECT video_id FROM videos WHERE video_id IN ({placeholders})', video_ids)
        saved_videos = {row['video_id'] for row in cursor.fetchall()}
        
        return jsonify({
            'status': 'success',
            'saved_videos': list(saved_videos)
        })
        
    except Exception as e:
        logger.error(f"Error checking saved videos: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

# Proxy configuration
PROXY_CONFIG = {
    'proxy': None,  # Example: 'socks5://127.0.0.1:1080'
    'native_language': 'en',  # Default to English
    'subtitle_language': 'en',  # Default to English
    'openai_key': None,
    'hunyuan_key': None,
    'qianwen_key': None,
    'default_llm': 'none',
    'host_port': 9527
}

def format_proxy_url(proxy_url):
    """Format proxy URL to ensure it has the correct scheme."""
    if not proxy_url:
        return None
    
    # If URL doesn't start with a scheme, assume it's HTTPS
    if not any(proxy_url.startswith(scheme) for scheme in ['http://', 'https://', 'socks4://', 'socks5://']):
        proxy_url = 'http://' + proxy_url
    
    return proxy_url

def load_config():
    """Load configuration from config.json file."""
    global PROXY_CONFIG
    config_path = get_config_path()
    
    try:
        # Create default config if it doesn't exist
        if not os.path.exists(config_path):
            default_config = {
                'proxy': None,
                'native_language': 'en',
                'subtitle_language': 'en',
                'openai_key': None,
                'hunyuan_key': None,
                'qianwen_key': None,
                'default_llm': 'none',
                'host_port': 9527,
                'version': CURRENT_VERSION  # Add version to config
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            PROXY_CONFIG.update(default_config)
            logger.info("Created default config file")
            return
            
        # Load existing config
        with open(config_path, 'r') as f:
            config = json.load(f)
            PROXY_CONFIG.update(config)
            logger.info(f"Loaded config: {PROXY_CONFIG}")
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        # If there's an error, ensure we have default values
        PROXY_CONFIG.update({
            'proxy': None,
            'native_language': 'en',
            'subtitle_language': 'en',
            'openai_key': None,
            'hunyuan_key': None,
            'qianwen_key': None,
            'default_llm': 'none',
            'host_port': 9527
        })

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get application settings from config file."""
    try:
        config_path = get_config_path()
        with open(config_path, 'r') as f:
            config = json.load(f)
            return jsonify(config)
    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return jsonify(PROXY_CONFIG), 200  # Return default config on error

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save application settings to config file."""
    global PROXY_CONFIG
    try:
        config_path = get_config_path()
        new_settings = request.json
        
        # Update PROXY_CONFIG with new settings
        PROXY_CONFIG.update(new_settings)
        
        # Save to file
        with open(config_path, 'w') as f:
            json.dump(PROXY_CONFIG, f, indent=4)
            
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Error saving settings: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_ffmpeg_path():
    """Get the path to ffmpeg executable"""
    if getattr(sys, 'frozen', False):
        # If we're running in a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # If we're running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    if sys.platform == 'win32':
        ffmpeg_path = os.path.join(base_path, 'ffmpeg', 'ffmpeg.exe')
    else:
        # On Unix systems, assume ffmpeg is in PATH
        ffmpeg_path = 'ffmpeg'
    
    return ffmpeg_path

def get_yt_dlp_opts():
    """Get yt-dlp options with proxy if configured"""
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'logger': logger,
        'progress_hooks': [progress_hook],
    }
    
    if PROXY_CONFIG['proxy']:
        opts['proxy'] = PROXY_CONFIG['proxy']
    
    # Set ffmpeg location for Windows
    if sys.platform == 'win32':
        opts['ffmpeg_location'] = get_ffmpeg_path()
    
    return opts

# Load proxy config at startup
load_config()

def get_local_datetime():
    """Get current datetime in local timezone."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_local_date():
    """Get current date in local timezone."""
    return datetime.now().strftime('%Y-%m-%d')

def get_or_create_daily_stats():
    """Get or create statistics record for today."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = get_local_date()
    
    try:
        # Try to get today's record
        cursor.execute('SELECT * FROM statistics WHERE date = ?', (today,))
        stats = cursor.fetchone()
        
        if not stats:
            # Create new record for today
            cursor.execute('''
                INSERT INTO statistics (date)
                VALUES (?)
            ''', (today,))
            conn.commit()
            cursor.execute('SELECT * FROM statistics WHERE date = ?', (today,))
            stats = cursor.fetchone()
        
        return dict(stats) if stats else None
    finally:
        if conn:
            conn.close()

def update_play_time(seconds):
    """Update audio play time for today."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = get_local_date()
    
    try:
        # Ensure today's record exists
        get_or_create_daily_stats()
        
        # Update play time
        cursor.execute('''
            UPDATE statistics 
            SET audio_play_time = audio_play_time + ?
            WHERE date = ?
        ''', (seconds, today))
        conn.commit()
    finally:
        if conn:
            conn.close()

@app.route('/statistics')
def statistics():
    """Render statistics page."""
    return render_template('statistics.html', config=app.config)

@app.route('/api/statistics/today')
def get_today_stats():
    """Get today's statistics."""
    return get_or_create_daily_stats()

@app.route('/api/statistics/week')

def get_week_stats():
    """Get the last 7 days of statistics."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = get_local_date()
    
    try:
        # Get the last 7 days of records
        cursor.execute('''
            SELECT date, audio_play_time, words_collected, words_removed
            FROM statistics
            WHERE date >= date('now', '-6 days')
            ORDER BY date ASC
        ''')
        rows = cursor.fetchall()
        
        # Prepare data for chart
        dates = []
        play_times = []
        words_collected = []
        words_removed = []
        
        # Fill in missing dates with zeros
        current = datetime.now().date()
        for i in range(6, -1, -1):
            date = (current - timedelta(days=i)).strftime('%Y-%m-%d')
            dates.append(date)
            
            # Find matching row or use 0
            matching_row = next((row for row in rows if row['date'] == date), None)
            play_times.append(matching_row['audio_play_time'] if matching_row else 0)
            words_collected.append(matching_row['words_collected'] if matching_row else 0)
            words_removed.append(matching_row['words_removed'] if matching_row else 0)
        
        return jsonify({
            'dates': dates,
            'play_times': play_times,
            'words_collected': words_collected,
            'words_removed': words_removed
        })
    finally:
        if conn:
            conn.close()

@app.route('/api/statistics/play-time', methods=['POST'])
def update_statistics_play_time():
    """Update play time statistics."""
    data = request.get_json()
    seconds = data.get('seconds', 0)
    
    if seconds > 0:
        update_play_time(seconds)
    
    return jsonify({'status': 'success'})

@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({'status': 'success'})

@app.route('/api/quit', methods=['GET'])
def quit():
    """ Gracefully shuts down the Flask app. """
    os.kill(os.getpid(), signal.SIGINT)
    return 'Shutting down...', 200

@app.route('/api/word_collections', methods=['POST'])
def add_word_collection():
    """Add a new word collection."""
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        current_time = get_local_datetime()
        cursor.execute('''
            INSERT INTO word_collections (
                selected_text,
                translation,
                audio_path,
                segment_start,
                segment_end,
                context_text,
                collected_date,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['selected_text'],
            data['translation'],
            data['audio_path'],
            data['segment_start'],
            data['segment_end'],
            data['context_text'],
            data['collected_date'],
            current_time,
            current_time
        ))
        
        # Update words_collected in statistics table
        cursor.execute('''
            INSERT INTO statistics (date, words_collected)
            VALUES (?, 1)
            ON CONFLICT(date) DO UPDATE SET
            words_collected = words_collected + 1
            WHERE date = ?
        ''', (data['collected_date'], data['collected_date']))
        
        conn.commit()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error adding word collection: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/words')
def words():
    return render_template('words.html', config=app.config)

@app.route('/api/word_collections', methods=['GET'])
def get_word_collections():
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        sort_field = request.args.get('sort_field', 'collected_date')
        sort_order = request.args.get('sort_order', 'desc')
        filter_type = request.args.get('filter', 'all')
        
        # Validate and sanitize inputs
        page = max(1, page)  # Ensure page is at least 1
        page_size = min(max(10, page_size), 100)  # Limit page_size between 10 and 100
        
        # Build the base query
        base_query = '''
            SELECT id, selected_text, translation, context_text, audio_path, 
                   segment_start, segment_end, collected_date, is_removed 
            FROM word_collections
        '''
        
        # Add filter condition
        where_clause = ''
        if filter_type == 'active':
            where_clause = ' WHERE is_removed = 0'
        elif filter_type == 'removed':
            where_clause = ' WHERE is_removed = 1'
        
        # Add sorting
        allowed_sort_fields = {'text': 'selected_text', 'collected_date': 'collected_date'}
        sort_field = allowed_sort_fields.get(sort_field, 'collected_date')
        sort_order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'
        order_clause = f' ORDER BY {sort_field} {sort_order}'
        
        # Add pagination
        limit_clause = f' LIMIT ? OFFSET ?'
        offset = (page - 1) * page_size
        
        # Get total count for pagination
        conn = get_db_connection()
        cursor = conn.cursor()
        count_query = f'SELECT COUNT(*) FROM word_collections{where_clause}'
        cursor.execute(count_query)
        total_items = cursor.fetchone()[0]
            
        # Get paginated data
        final_query = base_query + where_clause + order_clause + limit_clause
        cursor.execute(final_query, (page_size, offset))
        words = cursor.fetchall()
            
        # Calculate pagination metadata
        total_pages = (total_items + page_size - 1) // page_size
            
        return jsonify({
            'items': [{
                'id': word[0],
                'text': word[1],
                'translation': word[2],
                'context_text': word[3],
                'audio_path': word[4],
                'segment_start': word[5],
                'segment_end': word[6],
                'collected_date': word[7],
                'is_removed': bool(word[8])
            } for word in words],
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'page_size': page_size,
                'total_items': total_items
            }
        })
    except Exception as e:
        print(f"Error getting word collections: {e}")
        return jsonify({'error': 'Failed to get word collections'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/word_collections/<int:word_id>/toggle', methods=['POST'])
def toggle_word_status(word_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = get_local_datetime()
        today = get_local_date()
        
        # Get current status and collected_date
        cursor.execute('SELECT is_removed, collected_date FROM word_collections WHERE id = ?', (word_id,))
        result = cursor.fetchone()
        
        if result is not None:
            current_is_removed = result[0]
            collected_date = result[1]
            new_is_removed = 0 if current_is_removed else 1
            
            # Update word status
            cursor.execute('''
                UPDATE word_collections 
                SET is_removed = ?, updated_at = ?
                WHERE id = ?
            ''', (new_is_removed, current_time, word_id))
            
            # Update statistics
            if new_is_removed:
                # Word was marked as removed
                cursor.execute('''
                    UPDATE statistics 
                    SET words_removed = words_removed + 1
                    WHERE date = ?
                ''', (today,))
            else:
                # Word was unmarked as removed
                cursor.execute('''
                    UPDATE statistics 
                    SET words_collected = words_collected + 1
                    WHERE date = ?
                ''', (today,))
            
            conn.commit()
            return jsonify({'status': 'success', 'is_removed': new_is_removed})
        else:
            return jsonify({'status': 'error', 'message': 'Word not found'}), 404
            
    except Exception as e:
        print(f"Error toggling word status: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/translate/hunyuan', methods=['POST'])
def translate_hunyuan():
    try:
        data = request.json
        response = requests.post(
            'https://api.hunyuan.cloud.tencent.com/v1/chat/completions',
            json=data,
            headers={
                'Authorization': 'Bearer sk-9CjAx1v7fO7uzVaardTZMgVkSTp3ZmfVBppDcPVJ9aAqBian',
                'Content-Type': 'application/json'
            }
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary/<video_id>', methods=['GET'])
def get_summary(video_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT summary_text, llm_service, created_at FROM summary WHERE video_id = ? ORDER BY created_at DESC', (video_id,))
    summaries = cursor.fetchall()
    return jsonify([{
        'summary_text': s[0],
        'llm_service': s[1],
        'created_at': s[2]
    } for s in summaries])

@app.route('/api/summary/<video_id>', methods=['POST'])
def save_summary(video_id):
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO summary (video_id, summary_text, llm_service, created_at)
        VALUES (?, ?, ?, ?)
    ''', (video_id, data['summary_text'], data['llm_service'], get_local_datetime()))
    conn.commit()
    # print(f"begin tts for {video_id}")
    # audio = edge_tts.Communicate(data['summary_text'], "en-GB-SoniaNeural")
    # asyncio.run(audio.save('./audio/' + video_id + '_summary.mp3'))
    # print(f"end tts for {video_id}")
    return jsonify({'status': 'success'})

@app.route('/api/word_collections/<int:word_id>', methods=['DELETE'])
def delete_word_collection(word_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First check if the word exists
        cursor.execute('SELECT audio_path FROM word_collections WHERE id = ?', (word_id,))
        word = cursor.fetchone()
        
        if not word:
            return jsonify({'error': 'Word not found'}), 404
                
        # Delete the word
        cursor.execute('DELETE FROM word_collections WHERE id = ?', (word_id,))
        conn.commit()
        
        # If there's an associated audio file, delete it
        # audio_path = word[0]
        # if audio_path and os.path.exists(audio_path):
        #     try:
        #         os.remove(audio_path)
        #     except Exception as e:
        #         print(f"Error deleting audio file: {e}")
            
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"Error deleting word collection: {e}")
        return jsonify({'error': 'Failed to delete word'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/statistics/<time_range>')
def get_time_range_stats(time_range):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    end_date = datetime.now(pytz.UTC).date()
    
    if time_range == 'week':
        start_date = end_date - timedelta(days=6)  # Last 7 days including today
    elif time_range == 'month':
        start_date = end_date - timedelta(days=29)  # Last 30 days including today
    elif time_range == 'quarter':
        start_date = end_date - timedelta(days=89)  # Last 90 days including today
    elif time_range == 'year':
        start_date = end_date - timedelta(days=364)  # Last 365 days including today
    else:
        return jsonify({'error': 'Invalid time range'}), 400
    
    cursor.execute('''
        SELECT date, audio_play_time, words_collected, words_removed
        FROM statistics 
        WHERE date BETWEEN ? AND ?
        ORDER BY date ASC
    ''', (start_date.isoformat(), end_date.isoformat()))
    
    rows = cursor.fetchall()
    
    # Initialize data for all dates in range
    date_range = []
    play_times = []
    words_collected = []
    words_removed = []
    
    current_date = start_date
    data_dict = {row[0]: row[1:] for row in rows}
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        date_range.append(date_str)
        
        if date_str in data_dict:
            play_times.append(data_dict[date_str][0])
            words_collected.append(data_dict[date_str][1])
            words_removed.append(data_dict[date_str][2])
        else:
            play_times.append(0)
            words_collected.append(0)
            words_removed.append(0)
        
        current_date += timedelta(days=1)
    
    return jsonify({
        'dates': date_range,
        'play_times': play_times,
        'words_collected': words_collected,
        'words_removed': words_removed
    })

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

def is_server_running():
    """Check if another instance of the server is running"""
    import psutil
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid != current_pid:  # Don't match ourselves
                # Check for python running server.py
                cmdline = proc.cmdline()
                if len(cmdline) >= 2 and 'server.py' in cmdline[1]:
                    return True
                    
                # Check for YouAudio.exe
                if proc.name().lower() in ['youaudio.exe', 'youaudio']:
                    return True
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def get_app_path():
    """Get the application base path whether running as script or frozen exe"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def main():
    # Handle PyInstaller multiprocessing
    import multiprocessing
    if sys.platform.startswith('win'):
        # Ensure multiprocessing works with PyInstaller on Windows
        multiprocessing.freeze_support()
    
    # Set up signal handlers
    import signal
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
        
    try:
        logger.info("Starting YouAudio server...")
        
        # Initialize application data and perform migrations if needed
        app_data_dir = init_app_data()
        logger.info(f"Using application data directory: {app_data_dir}")
        
        # Check if another instance is running
        if is_server_running():
            logger.info("Another server instance is already running")
            sys.exit(0)
            
        # Initialize database
        init_db()

        # Load configuration
        config_path = get_config_path()
        host_port = 9527
        
        try:
            logger.info(f"Loading config from: {config_path}")
            with open(config_path, 'r') as f:
                config = json.load(f)
                if config.get('host_port'):
                    host_port = config['host_port']
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            pass

        if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
            import threading
            from macos_app import YouAudioDelegate
            from AppKit import NSApp, NSApplication, NSApplicationActivationPolicyAccessory
            from PyObjCTools.AppHelper import runEventLoop
            
            # Initialize NSApplication
            app_instance = NSApplication.sharedApplication()
            # app_instance.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            
            # Run Flask in a separate thread
            def run_flask():
                app.run(debug=False, port=host_port)
            
            flask_thread = threading.Thread(target=run_flask)
            flask_thread.daemon = True
            flask_thread.start()
            
            # Open browser in a separate thread
            browser_thread = threading.Thread(target=lambda: open_browser(host_port))
            browser_thread.daemon = True
            browser_thread.start()
            
            delegate = YouAudioDelegate.alloc().init(host_port)
            # delegate.setHostPort(host_port)
            app_instance.setDelegate_(delegate)
            app_instance.activateIgnoringOtherApps_(True)
            runEventLoop()
            # Run the NSApplication main loop
            # app_instance.run()
        else:
            # Start Flask app normally on other platforms
            app.run(debug=False, port=host_port)
    except KeyboardInterrupt:
        logger.info("Received signal 2, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        sys.exit(0)

if __name__ == '__main__':
    main()