import os
import discord
import spotipy
import tidalapi
from discord.ext import commands
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')

# --- SETUP CLIENTS ---

# 1. Discord Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Spotify Setup
# Uses Client Credentials Flow (no user login required, just app keys)
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET
))

# 3. TIDAL Setup
# Note: TIDAL API is stricter. We use a Session factory.
# specific quality can be set, 'HI_RES' is usually safe for metadata.
tidal_session = tidalapi.Session()
# We will login lazily in the on_ready event or rely on script execution

def get_tidal_url(artist, track_name):
    """Searches TIDAL for a track and returns the URL."""
    try:
        # Search for the track on TIDAL
        query = f"{artist} - {track_name}"
        search_results = tidal_session.search(query, models=[tidalapi.media.Track], limit=1)
        
        if search_results['tracks']:
            track = search_results['tracks'][0]
            # specific TIDAL link format
            return f"https://tidal.com/browse/track/{track.id}"
    except Exception as e:
        print(f"Error searching TIDAL: {e}")
    return None

def get_spotify_url(artist, track_name):
    """Searches Spotify for a track and returns the URL."""
    try:
        query = f"artist:{artist} track:{track_name}"
        results = sp.search(q=query, limit=1, type='track')
        
        items = results['tracks']['items']
        if items:
            return items[0]['external_urls']['spotify']
    except Exception as e:
        print(f"Error searching Spotify: {e}")
    return None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    # --- TIDAL AUTHENTICATION ---
    # TidalAPI requires a login session. The most robust way for a bot 
    # is to try to load a saved session or prompt for OAuth login on startup.
    # For simplicity, we trigger the OAuth flow here if not loaded.
    try:
        # Attempt to load a previous session if you implement file saving
        # Otherwise, start a new OAuth flow
        print("Authenticating with TIDAL... check your terminal.")
        tidal_session.login_oauth_simple()
        print("TIDAL Login Successful.")
    except Exception as e:
        print(f"TIDAL Login failed: {e}")

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    content = message.content.strip()
    
    # --- CASE 1: SPOTIFY LINK DETECTED ---
    if "open.spotify.com/track/" in content:
        try:
            # Extract ID usually found after 'track/'
            # Handling URL parameters (like ?si=...) by splitting
            track_id = content.split("track/")[1].split("?")[0]
            
            # Get Metadata from Spotify
            track_info = sp.track(track_id)
            artist_name = track_info['artists'][0]['name']
            track_title = track_info['name']
            
            print(f"Detected Spotify: {artist_name} - {track_title}")
            
            # Search on TIDAL
            tidal_link = get_tidal_url(artist_name, track_title)
            
            if tidal_link:
                await message.reply(f"🎵 **TIDAL Conversion:**\n{tidal_link}")
            else:
                print("Match not found on TIDAL.")

        except Exception as e:
            print(f"Error processing Spotify link: {e}")

    # --- CASE 2: TIDAL LINK DETECTED ---
    elif "tidal.com/browse/track/" in content:
        try:
            track_id = content.split("track/")[1].split("?")[0]
            
            # Get Metadata from TIDAL
            tidal_track = tidal_session.track(track_id)
            artist_name = tidal_track.artist.name
            track_title = tidal_track.name
            
            print(f"Detected TIDAL: {artist_name} - {track_title}")
            
            # Search on Spotify
            spotify_link = get_spotify_url(artist_name, track_title)
            
            if spotify_link:
                await message.reply(f"💚 **Spotify Conversion:**\n{spotify_link}")
            else:
                print("Match not found on Spotify.")

        except Exception as e:
            print(f"Error processing TIDAL link: {e}")

    # Allow other commands to run
    await bot.process_commands(message)

# Run the bot
bot.run(DISCORD_TOKEN)