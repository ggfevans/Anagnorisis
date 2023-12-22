from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from pydub import AudioSegment
import base64

import os
#import eyed3
import hashlib

import datetime

from tqdm import tqdm
import numpy as np
import traceback
import src.db_models

from tinytag import TinyTag
import llm_engine
from TTS.api import TTS
from unidecode import unidecode
import scipy.io.wavfile
import io

from mutagen.id3 import ID3, ID3NoHeaderError, USLT

# Function to calculate the SHA-256 hash of audio data
def calculate_audiodata_hash(mp3_file_path):
    # Load the MP3 file using pydub
    audio = AudioSegment.from_file(mp3_file_path)

    # Extract the raw audio data as bytes
    audio_data = audio.raw_data

    # Initialize the hash object
    audio_hash = hashlib.sha256()

    # Update the hash with the audio data
    audio_hash.update(audio_data)

    # Return the hexadecimal representation of the hash
    return audio_hash.hexdigest()

def get_audiofile_data(file_path, url_path):
  metadata = {
    'file_path': file_path,
    'url_path': url_path,
    'hash': calculate_audiodata_hash(file_path),
  }

  '''tag.album         # album as string
  tag.albumartist   # album artist as string
  tag.artist        # artist name as string
  tag.audio_offset  # number of bytes before audio data begins
  tag.bitdepth      # bit depth for lossless audio
  tag.bitrate       # bitrate in kBits/s
  tag.comment       # file comment as string
  tag.composer      # composer as string 
  tag.disc          # disc number
  tag.disc_total    # the total number of discs
  tag.duration      # duration of the song in seconds
  tag.filesize      # file size in bytes
  tag.genre         # genre as string
  tag.samplerate    # samples per second
  tag.title         # title of the song
  tag.track         # track number as string
  tag.track_total   # total number of tracks as string
  tag.year          # year or date as string'''

  #audiofile = eyed3.load(file_path)

  tag = TinyTag.get(file_path, image=True)

  metadata['title'] = tag.title or "N/A"
  metadata['artist'] = tag.artist or "N/A"
  metadata['album'] = tag.album or "N/A"
  metadata['track_num'] = tag.track if tag.track else "N/A"
  metadata['genre'] = tag.genre if tag.genre else "N/A"
  metadata['date'] = str(tag.year) if tag.year else "N/A"

  metadata['duration'] = tag.duration #(seconds)
  metadata['bitrate'] = tag.bitrate #(kbps)

  metadata['lyrics'] = tag.extra.get('lyrics', "")

  img = tag.get_image()
  if img is not None:
    base64_image = base64.b64encode(img).decode('utf-8')

    #buffer = io.BytesIO()
    #img.save(buffer, format='PNG')
    #buffer.seek(0)
    
    #data_uri = base64.b64encode(buffer.read()).decode('ascii')
    metadata['image'] = f"data:image/png;base64,{base64_image}"
  else:
    metadata['image'] = None

    # Get all available tags and their values as a dictionary
    #tag_dict = audiofile.tag.frame_set

    # If there are multiple artists, they will be stored in a list
    #if audiofile.tag.artist:
    #    print("Artists:", ", ".join(audiofile.tag.artist))

    # If there are multiple genres, they will be stored in a list
    #if audiofile.tag.genre:
    #    print("Genres:", ", ".join(audiofile.tag.genre))

    # You can access other tag fields in a similar way

    # To print all tags and their values, you can iterate through them
    #for tag in audiofile.tag.frame_set:
    #    print(tag, ":", audiofile.tag.frame_set[tag][0])

    # If you want to access additional metadata, you can use audiofile.tag.file_info
    #print("Sample Width (bits):", audiofile.tag.file_info.sample_width)
    #print("Channel Mode:", audiofile.tag.file_info.mode)

    # To print the entire tag as a dictionary
    #print("Tag Dictionary:", audiofile.tag.frame_set)

    #for frame in audiofile.tag.frameiter(["TXXX"]):
    #  print(f"{frame.description}: {frame.text}")
  
  return metadata

def get_music_list_metadata():
  return []
  
  
def sigmoid(x):
  return 1 / (1 + np.exp(-x))

def init_socket_events(socketio, predictor, app=None, cfg=None):
  # Determine the absolute path to the media file
  media_directory = cfg.media_directory
  music_list = []
  music_ratings = None
  play_history = ""
  AIDJ_history = ""
  AIDJ_tts = TTS(cfg.tts_model_path) #'tts_models/en/ljspeech/vits'
  AIDJ_tts_index = 0
  

  def _music_list():
    nonlocal music_list
    if (music_list is not None) and (len(music_list)>0): return music_list
    
    music_list = src.db_models.MusicLibrary.query.all()
    music_list = [music.as_dict() for music in music_list]

  # necessary to allow web application access to music files
  @app.route('/media/<path:filename>')
  def serve_media(filename):
    nonlocal media_directory
    return send_from_directory(media_directory, filename)

  @socketio.on('emit_music_page_refresh_music_library')
  def refresh_music_library():
    nonlocal media_directory
  
    music_files = []
    for root, dirs, files in os.walk(media_directory):
      for file in files:
        #MP3, OGG, OPUS, MP4, M4A, FLAC, WMA, Wave and AIFF
        if file.lower().endswith((".mp3", ".flac")):
          full_path = os.path.join(root, file)
          music_files.append(full_path)

    #music_list = []
    for full_path in tqdm(music_files):   
      try: 
        url_path = 'media/' + full_path.replace(media_directory, '')
        audiofile_data = get_audiofile_data(full_path, url_path)

        # Check if a row with the same primary key (hash) exists
        existing_music = src.db_models.MusicLibrary.query.get(audiofile_data['hash'])

        if existing_music:
          # Update the existing row with the new data
          for key, value in audiofile_data.items():
            setattr(existing_music, key, value)
        else:
          # Create a new row
          new_music = src.db_models.MusicLibrary(**audiofile_data)
          src.db_models.db.session.add(new_music)

        # Commit the changes to the database
        src.db_models.db.session.commit()
      except Exception as ex:
        print('Something went wrong with', full_path)
        print(traceback.format_exc())


  @socketio.on('emit_music_page_get_music_list')
  def get_music_list():

    #music_list = get_music_list_metadata()
    socketio.emit('emit_music_page_send_music_list', _music_list())  

  @socketio.on('emit_music_page_set_song_play_rate')
  def request_new_song(data):
    cur_song_hash = None
    song_score_change = None
    
    if len(data) > 0:
      cur_song_hash = data[0]
      skip_score_change = data[1]

    if cur_song_hash is not None:
      song = src.db_models.MusicLibrary.query.get(cur_song_hash)
      if skip_score_change == 1:
        song.full_play_count += 1
      if skip_score_change == -1:
        song.skip_count += 1
      
      #song.skip_score += skip_score_change
      src.db_models.db.session.commit()

  @socketio.on('emit_music_page_set_song_rating')
  def set_song_rating(data):
    song_hash = data['hash'] 
    song_score = data['score']

    print('Set song rating:', song_hash, song_score)

    song = src.db_models.MusicLibrary.query.get(song_hash)
    song.user_rating = int(song_score)
    src.db_models.db.session.commit()

    music = next((item for item in _music_list() if item['hash'] == song_hash), None)
    music['user_rating'] = song_score

  @socketio.on('emit_music_page_set_song_skip_score')
  def set_song_skip_score(data): 
    cur_song_hash = None
    song_score_change = None
    
    if len(data) > 0:
      cur_song_hash = data[0]
      skip_score_change = data[1]

    if cur_song_hash is not None:
      song = src.db_models.MusicLibrary.query.get(cur_song_hash)
      if skip_score_change == 1:
        song.full_play_count += 1
      if skip_score_change == -1:
        song.skip_count += 1
      
      #song.skip_score += skip_score_change
      src.db_models.db.session.commit()

  def select_random_music():
    # Convert the list to a NumPy array to work with numerical values
    not_none_scores = np.array([music['user_rating'] for music in _music_list() if music['user_rating'] is not None])
    print('Not none ratings:', list(not_none_scores))
    # Calculate the median of the existing values
    median_value = np.median(not_none_scores)
    print('Median song rating:', median_value)

    # Replace None values with the calculated median
    
    scores = np.array([median_value * 0.3 if music['user_rating'] is None else music['user_rating'] for music in _music_list()])
    scores = np.minimum(0.1, scores) # we make a minimum small value to the rating so songs with 0 rating have some small chance to be played
    scores = (scores / 10) ** 2 # normalize scores and make songs with high rating much more likely to occur

    #skip_score = np.array([music['skip_score'] for music in _music_list()])
    full_play_count = np.array([music['full_play_count'] for music in _music_list()])
    skip_count = np.array([music['skip_count'] for music in _music_list()])
  
    skip_score = sigmoid((10 + full_play_count - skip_count) / 10) # meaningful rage for skip_score [-30, 30] that result in a value ~ [0, 1]
    scores = scores * skip_score

    # Generate a random index based on the weights
    sampled_index = np.random.choice(len(scores), p=scores/np.sum(scores))

    return _music_list()[sampled_index]

  def seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format the string
    time_string = ""
    if hours > 0:
        time_string += f"{int(hours)} {'hour' if int(hours) == 1 else 'hours'} "
    if minutes > 0:
        time_string += f"{int(minutes)} {'minute' if int(minutes) == 1 else 'minutes'} "
    if seconds > 0:
        time_string += f"{int(seconds)} {'second' if int(seconds) == 1 else 'seconds'}"

    return time_string.strip()
  
  @socketio.on('emit_music_page_AIDJ_get_next_song')
  def request_new_song(data):
    nonlocal predictor, AIDJ_history, AIDJ_tts, AIDJ_tts_index, play_history
    if predictor is None: 
      state = {
        "hidden": False,
        "head": f"System:",
        "body": f"Loading LLM to system memory..."
      }
      socketio.emit('emit_music_page_board_add_state', state) 
      predictor = llm_engine.TextPredictor(socketio)

    _music_list() # Find a better way to initialize the list if it is not yet exist

    if len(_music_list())>0:
      for i in range(30):
        #if i==0:
        #  music_item = next((x for x in _music_list() if x['hash'] == '3166336a479d2e50a397269c31991cd1998dc61027c72fdcdbaa1afd92bbbb4d'), None)
        #else:
        music_item = select_random_music()
          
        try: 
          audiofile_data = get_audiofile_data(music_item['file_path'], music_item['url_path'])
          # Add information from meta data of audio file
          music_item['lyrics'] = audiofile_data['lyrics']
          
          state = {
            "hidden": True,
            "head": f"Next song selected:",
            "body": f"{music_item['artist']} - {music_item['title']} | {music_item['album']}"
          }
          socketio.emit('emit_music_page_board_add_state', state) 

          current_time = datetime.datetime.now()
          current_time_str = current_time.strftime("%A, %B %d, %Y, %H:%M")

          AIDJ_history = AIDJ_history[-1000:]

          if AIDJ_history == "":
            AIDJ_history += f"### HUMAN:\n{cfg.aidj_first_prompt}"
          else:
            prompt = np.random.choice(cfg.aidj_consecutive_prompts)
            AIDJ_history += f"### HUMAN:\n{prompt}"

          #AIDJ_history += f" Do not use hackneyed phrases like 'So, sit back, relax, and enjoy..' and others like that."
          user_rating = 'Not rated yet' if music_item['user_rating'] is None else str(music_item['user_rating']) + '/10'
          AIDJ_history += f'''\nCurrent time: {current_time_str};\n\nInformation about current song:\nBand/Artist: {music_item['artist']};\nSong title: {music_item['title']};\nAlbum: {music_item['album']};\nRelease year: {music_item['date']};\nLength: {seconds_to_hms(music_item['duration'])};'''
          AIDJ_history += f'''\nFull play count: {int(music_item['full_play_count'])};\nSkip count: {int(music_item['skip_count'])};\nUser rating: {user_rating};'''

          if len(music_item['lyrics']) > 0: AIDJ_history += f"\nLyrics:\n{music_item['lyrics']}"


          AIDJ_history += f"\n### RESPONSE:\n"

          state = {
            "hidden": True,
            "head": f"LLM Prompt generated:",
            "body": AIDJ_history
          }
          socketio.emit('emit_music_page_board_add_state', state) 

          state = {
            "hidden": True,
            "head": f"System:",
            "body": f"Running LLM..."
          }
          socketio.emit('emit_music_page_board_add_state', state) 

          # Predict AI DJ remark before playing the song
          llm_text = predictor.predict_from_text(AIDJ_history, temperature = cfg.llm_temperature)
          AIDJ_history += llm_text

          state = {
            "hidden": True,
            "head": f"LLM output:",
            "body": llm_text
          }
          socketio.emit('emit_music_page_board_add_state', state) 

          if len(llm_text.strip()) > 0:
            state = {
              "hidden": True,
              "head": f"System:",
              "body": f"Generating audio based on LLM output..."
            }
            socketio.emit('emit_music_page_board_add_state', state) 
            
            # Use TTS to speak the text and save it to temporary file storage
            AIDJ_tts_filename = f"static/tmp/AIDJ_{AIDJ_tts_index:04d}.wav"
            AIDJ_tts_index += 1
            AIDJ_tts.tts_to_file(llm_text, file_path=AIDJ_tts_filename, speaker_wav=cfg.tts_model_speaker_sample, language=cfg.tts_model_language)

            # Icreasing the volume of TTS output
            # Load the audio file
            sound = AudioSegment.from_wav(AIDJ_tts_filename)
            # Increase the volume
            sound = sound + 3 # plus 10db
            # Save the modified audio to the same file
            sound.export(AIDJ_tts_filename, format="wav")

            state = {
              "hidden": False,
              "image": "/static/AI.jpg",
              "head": f"AI DJ:",
              "body": f"{llm_text}",
              "audio_element": AIDJ_tts_filename
            }
            socketio.emit('emit_music_page_board_add_state', state) 

          user_rating_str = 'Not rated yet' if music_item['user_rating'] is None else '★' * music_item['user_rating'] + '☆' * (10 - music_item['user_rating'])
          skip_multiplier = sigmoid((10 + music_item['full_play_count'] - music_item['skip_count']) / 10)

          song_info = f"\n{music_item['artist']} - {music_item['title']} | {music_item['album']}"
          song_info += f"\nSong rating: {user_rating_str}"
          song_info += f"\nFull plays: {music_item['full_play_count']}\nSkips: {music_item['skip_count']}\nSkip multiplier: {skip_multiplier:0.4f}"
          state = {
            "hidden": False,
            "image": audiofile_data['image'], #link to the cover or bit64 image?
            "head": f"Now playing:",
            "body": song_info,
            "audio_element": music_item
          }
          socketio.emit('emit_music_page_board_add_state', state) 

          #play_history += f"\n{music_item['artist']} - {music_item['title']} | {music_item['album']}"
          #AIDJ_history += f"\n### SYSTEM:\nPlay history: {play_history}\n"

          #socketio.emit('emit_music_page_AIDJ_append_messages', AIDJ_messages) 

          #ind = np.random.randint(len(music_list))
          #socketio.emit('emit_music_page_send_next_song', _music_list()[sampled_index])  
        except Exception as error:
          state = {
            "hidden": False,
            "head": f"Error:",
            "body": f"{music_item['artist']} - {music_item['title']} | {music_item['album']}\n{str(error)}\n\n{traceback.format_exc()}",
          }
          socketio.emit('emit_music_page_board_add_state', state) 

    predictor.unload_model()
    predictor = None
    print('Predictor:', predictor)

  def edit_lyrics(file_path, new_lyrics):
    try:
        # Load the audio file
        audio = ID3(file_path)
    except ID3NoHeaderError:
        # If there's no existing metadata, create a new one
        audio = ID3()

    # Remove existing lyrics (if any)
    audio.delall('USLT')
    # Add new lyrics
    audio.add(USLT(text=new_lyrics))

    # Save changes
    audio.save()

  @socketio.on('emit_music_page_update_song_info')
  def update_song_info(data):
    print('update_song_info', data)
    edit_lyrics(data['file_path'], data['lyrics'])
  
if __name__ == "__main__":
  print('start')
  hash_1 = calculate_audiodata_hash('src/music_1.mp3')
  hash_2 = calculate_audiodata_hash('src/music_2.mp3')
  print(hash_1, hash_2, hash_1 == hash_2)