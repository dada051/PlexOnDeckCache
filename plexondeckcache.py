import os
import psutil
import subprocess
from subprocess import check_call
from itertools import chain
from plexapi.server import PlexServer
from plexapi.video import Episode
from datetime import datetime

##################################################################
# Plex URL and TOKEN                                             #
##################################################################
PLEX_URL = 'https://plex.yourdomain.domain'
PLEX_TOKEN = 'tokentokentoken'

##################################################################
# Cache name                                                     #
##################################################################
CACHE_NAME = 'cache'

##################################################################
# Number of episodes                                             #
##################################################################
number_episodes = 24

##################################################################
# Set the Sections we want to evaluate.                          #
##################################################################
valid_sections = [1,2]

##################################################################
# How many days of On Deck do we want to consider?               #
##################################################################
DAYS_TO_MONITOR = 999

plex = PlexServer(PLEX_URL, PLEX_TOKEN)
processed_files = []
files = []

def otherusers(user, number_episodes):
    user_plex = PlexServer(PLEX_URL, user.get_token(plex.machineIdentifier))
    user_files = []
    for video in user_plex.library.onDeck():
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if delta.days <= DAYS_TO_MONITOR:
                if isinstance(video, Episode): #TV Series
                    for media in video.media:
                        for part in media.parts:
                            show = video.grandparentTitle 
                            # Get the library the video belongs to
                            library_section = video.section()
                            # Get the episodes of the show in the library
                            episodes = [e for e in library_section.search(show)[0].episodes()] #Fetches the next 5 episodes
                            next_episodes = []
                            current_season = video.parentIndex
                            user_files.append((part.file))
                            for episode in episodes: 
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) < number_episodes:
                                    next_episodes.append(episode) 
                                if len(next_episodes) == number_episodes:
                                    break
                            for episode in next_episodes: #Adds the episodes to the list
                                for media in episode.media:
                                    for part in media.parts:
                                        user_files.append((part.file))        
                else: #Movies
                    for media in video.media:
                        for part in media.parts:
                            user_files.append((part.file))
    return user_files or []

def mainuser(number_episodes):
    user_files = []
    for video in plex.library.onDeck():
        # Apply section filter
        if video.section().key in valid_sections:
            delta = datetime.now() - video.lastViewedAt
            if delta.days <= DAYS_TO_MONITOR:
                if isinstance(video, Episode): #TV Series
                    for media in video.media:
                        for part in media.parts:
                            show = video.grandparentTitle 
                            # Get the library the video belongs to
                            library_section = video.section()
                            # Get the episodes of the show in the library
                            episodes = [e for e in library_section.search(show)[0].episodes()] #Fetches the next 5 episodes
                            next_episodes = []
                            current_season = video.parentIndex
                            files.append((part.file))
                            for episode in episodes: 
                                if episode.parentIndex > current_season or (episode.parentIndex == current_season and episode.index > video.index) and len(next_episodes) < number_episodes:
                                    next_episodes.append(episode) 
                                if len(next_episodes) == number_episodes:
                                    break
                            for episode in next_episodes: #Adds the episodes to the list
                                for media in episode.media:
                                    for part in media.parts:
                                        files.append((part.file)) 
                else: #Movies
                    for media in video.media:
                        for part in media.parts:
                            files.append((part.file))
    return user_files or []

files.extend(mainuser(number_episodes)) #Main user

for user in plex.myPlexAccount().users(): #All the other users
    files.extend(otherusers(user, number_episodes))

def find_file_path(user_file_name):
    filetofind = '"' + user_file_name + '"'
    for d in sorted([x for x in os.listdir("/mnt/") if x.startswith("disk")]):
        path = os.path.join("/mnt/" + d, filetofind.replace('/mnt/user/', ''))
        if os.path.exists(path):
            return os.path.dirname(path)
    return ''


#Search for subtitle files (any file with similar file name but different extension)
processed_files = set()
for count, fileToCache in enumerate(files): 
    if fileToCache in processed_files:
        continue
    processed_files.add(fileToCache)
    directory_path = os.path.dirname(fileToCache)
    directory_path = directory_path.replace("/media/", "/mnt/user/")
    file_name, file_ext = os.path.splitext(os.path.basename(fileToCache))
    files_in_dir = os.listdir(directory_path)
    subtitle_files = [os.path.join(directory_path, file) for file in files_in_dir if file.startswith(file_name) and file != file_name+file_ext]
    if subtitle_files:
        for subtitle in subtitle_files:
            if subtitle not in files:
                files.append(subtitle)

#Correct all paths locating the file in the unraid array and move the files to the cache drive                
processed_files = set()
for count, fileToCache in enumerate(files): 
    if fileToCache in processed_files:
        continue
    media_file_path = os.path.dirname(fileToCache)
    user_path = media_file_path.replace("/media/", "/mnt/user/")
    cache_path = user_path.replace("/user/", "/" + CACHE_NAME + "/")
    user_file_name = user_path + "/" + os.path.basename(fileToCache)
    cache_file_name = cache_path + "/" + os.path.basename(fileToCache)
    if not os.path.exists(cache_path): #If the path that will end up containing the media file does not exist, this lines will create it
        os.makedirs(cache_path)
        print("Directory created successfully")
    if not os.path.isfile(cache_file_name): 
        #locatefile = f"/mnt/user/system/./locatefileinarray.sh \"{user_file_name}\"" #Locate the file in the array
        locatefile = find_file_path(user_file_name)
        disk_path = subprocess.check_output(locatefile, shell=True).strip().decode() 
        disk_file_name = disk_path + "/" + os.path.basename(fileToCache)
        print("______________________________________")
        print(os.path.basename(fileToCache))
        print("File not in the cache drive, beginning the moving process")         
        # ***** Actual command that moves the file(s) *****
        move = f"mv -v \"{disk_file_name}\" \"{cache_path}\"" # Comment this if you want to test it first (add the "#" before "move")
        os.system(move) #Comment this if you are debugging
        if os.system(move) == 0: #Also this
            print("File moved successfully") #And this one           
        # ****** Debug command, useful if you want to test the script frist, otherwise, ignore ****
        #print("mv -v", disk_file_name, "--> TO -->", cache_path)
print("The End")