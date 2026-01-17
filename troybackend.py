# Backend Python untuk TroyNet Web
# Jalankan dengan: python troybackend.py
# Kemudian buka browser ke http://localhost:5000

from flask import Flask, render_template_string, jsonify, request
import threading
import time
import random

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Status global
status = {
    'running': False,
    'current_action': '',
    'progress': 0,
    'logs': [],
    'current_guild': '',
    'completed': False,
    'error': None
}

def add_log(message, color='info'):
    timestamp = time.strftime("%H:%M:%S")
    status['logs'].append({
        'time': timestamp,
        'message': message,
        'color': color
    })
    if len(status['logs']) > 100:
        status['logs'] = status['logs'][-100:]

def simulate_nuke(token, channel_name, guild_id=None):
    global status
    status.update({
        'running': True,
        'completed': False,
        'error': None,
        'progress': 0
    })
    
    try:
        # Simulasi proses nuke
        actions = [
            ('Connecting to Discord...', 10, 'info'),
            ('Authenticating bot token...', 20, 'info'),
            ('Fetching server list...', 30, 'info'),
            ('Banning members...', 50, 'info'),
            ('Deleting channels...', 70, 'info'),
            ('Deleting roles...', 85, 'info'),
            (f'Creating channels named "{channel_name}"...', 95, 'info'),
            ('Cleanup...', 100, 'info')
        ]
        
        for action, progress, log_type in actions:
            if not status['running']:
                break
                
            status['current_action'] = action
            status['progress'] = progress
            
            if 'Banning' in action:
                add_log(f'Banned {random.randint(10, 50)} members', 'success')
            elif 'Deleting channels' in action:
                add_log(f'Deleted {random.randint(5, 20)} channels', 'success')
            elif 'Deleting roles' in action:
                add_log(f'Deleted {random.randint(3, 15)} roles', 'success')
            elif 'Creating channels' in action:
                add_log(f'Created {random.randint(20, 30)} channels', 'success')
            
            add_log(action, log_type)
            time.sleep(random.uniform(0.5, 2))
        
        if status['running']:
            status['completed'] = True
            add_log('Nuke operation completed successfully!', 'success')
            add_log(f'Total actions performed: {random.randint(50, 150)}', 'info')
        else:
            add_log('Nuke operation stopped by user', 'warning')
            
    except Exception as e:
        status['error'] = str(e)
        add_log(f'Error: {str(e)}', 'error')
    finally:
        status['running'] = False

@app.route('/')
def index():
    # Serve the HTML file
    with open('troyweb.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    return html_content

@app.route('/api/status')
def get_status():
    return jsonify(status)

@app.route('/api/start', methods=['POST'])
def start_nuke():
    if status['running']:
        return jsonify({'error': 'Nuke is already running'}), 400
    
    data = request.json
    token = data.get('token', '').strip()
    channel_name = data.get('channel_name', 'NUKED').strip()
    guild_id = data.get('guild_id', '').strip()
    
    if not token:
        return jsonify({'error': 'Token is required'}), 400
    
    # Reset logs
    status['logs'] = []
    add_log('Starting nuke simulation...', 'info')
    
    # Start simulation in background
    thread = threading.Thread(target=simulate_nuke, args=(token, channel_name, guild_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({'message': 'Nuke simulation started'})

@app.route('/api/stop', methods=['POST'])
def stop_nuke():
    status['running'] = False
    return jsonify({'message': 'Stop command sent'})

@app.route('/api/clear', methods=['POST'])
def clear_logs():
    status['logs'] = []
    return jsonify({'message': 'Logs cleared'})

if __name__ == '__main__':
    print("TroyNet Web Interface starting...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
