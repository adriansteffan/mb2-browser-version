import cv2
import json

import shutil
import os
import sys
from os import listdir
from pathlib import Path
from os.path import isfile, join
import subprocess
import pandas as pd
import statistics
from io import StringIO
import zipfile


# information is not present in the data output, fix this at some point in time
STIMULUS_WIDTH = 1280.0
STIMULUS_HEIGHT = 960.0

STIMULUS_ASPECT_RATIO = STIMULUS_WIDTH/STIMULUS_HEIGHT

# sampling rate parameters in Hz
## sampling rate that all sata gets resampled to - for visualization purposes only
RESAMPLE_SAMPLING_RATE = 15

data_directory = "../prod_mb2-browser-version/data"
media_directory = "../media/video"
output_directory = "./output"

exclusion_csv_path = "./excluded_trials.csv"

target_aoi_location = {
    "FAM_LL": "left",
    "FAM_LR": "right",
    "FAM_RL": "left",
    "FAM_RR": "right",
    "KNOW_LL": "right",
    "KNOW_LR": "left",
    "KNOW_RL": "right",
    "KNOW_RR": "left",
    "IG_LL": "right",
    "IG_LR": "left",
    "IG_RL": "right",
    "IG_RR": "left"
}

list_of_stimuli_endings = [stimulus + ".webm" for stimulus in target_aoi_location.keys()]

if not os.path.exists(output_directory):
    os.makedirs(output_directory)


def translate_coordinates(video_aspect_ratio, win_height, win_width, vid_height, vid_width, winX, winY):
    """translate the output coordinates of the eye-tracker onto the stimulus video"""
    if win_width/win_height > video_aspect_ratio:  # full height video
        vid_on_screen_width = win_height*video_aspect_ratio
        outside = False

        if winX < (win_width - vid_on_screen_width)/2 or winX > ((win_width - vid_on_screen_width)/2 + vid_on_screen_width):
            outside = True
        # scale x
        vidX = ((winX - (win_width - vid_on_screen_width)/2) / vid_on_screen_width) * vid_width
        # scale y
        vidY = (winY/win_height)*vid_height
        return int(vidX), int(vidY), outside
    else:  # full width video - not used in current study
        # TODO cutoff for other aspect ratios
        vidX = (winX / win_width) * vid_width
        return None, None, True


def tag_video(path, json_data, media_name, participant_name):

    """ add the webcam footage as an overlay to the stimulus media file (if footage exists),
        add a frame counter, and visualize the gaze location from the eyetracking data
    """

    base_path = output_directory+"/"+participant_name
    media_file_name = media_name + ".mp4"

    pre1_path = base_path+"/pre1_" + media_file_name
    # audio_path = base_path+"/audio_" + media_name + ".mp3"
    pre2_path = base_path+"/audio_no_dot_" + media_file_name
    # pre3_path = base_path + "/pre3_" + media_file_name
    final_path = base_path + "/tagged_" + media_file_name

    if True:
        # combine media and webcam video, extract audio

        if os.path.isfile(data_directory+"/"+participant_name+"_"+media_name+".webm"):
            p1 = subprocess.Popen(['ffmpeg',
                             '-y',
                             '-i',
                             media_directory+"/"+media_name+".mp4",
                             "-i",
                             data_directory+"/"+participant_name+"_"+media_name+".webm",
                             "-filter_complex",
                             "[1:v]scale=350:-1,hflip [inner];[0:v][inner]overlay=10:10:shortest=1[out]",
                             "-map",
                             "[out]",
                             "-map",
                             "1:a",
                             pre1_path
                             ])

            p1.wait()

            # Extract audio from file for later merging - uncomment when the merging is fixed
            #p1a = subprocess.Popen(['ffmpeg',
            #                        '-y',
            #                        '-i',
            #                        data_directory+"/"+participant_name+"_"+media_name+".webm",
            #                        '-f',
            #                        'mp3',
            #                        '-ab',
            #                        '192000',
            #                        '-vn',
            #                        audio_path
            #                        ])
            #p1a.wait()

        else:
            shutil.copy(media_directory+"/"+media_name+".mp4", pre1_path)

        # add frame counter to video
        p2 = subprocess.Popen(['ffmpeg',
                         '-y',
                         '-i',
                         pre1_path,
                         '-vf',
                         "drawtext=fontfile=Arial.ttf: text='%{frame_num} / %{pts}': start_number=1: x=(w-tw)/2: y=h-lh: fontcolor=black: fontsize=(h/20): box=1: boxcolor=white: boxborderw=5",
                         "-c:a",
                         "copy",
                         "-c:v",
                         "libx264",
                         "-crf",
                         "23",
                         pre2_path,
                         ])
        p2.wait()

    # tag the video with eye tracking data (dot for gaze coordinates)

    win_width = json_data['windowWidth']
    win_height = json_data['windowHeight']
    gaze_points = json_data['webgazer_data']
    gaze_point_index = 1

    video = cv2.VideoCapture(pre2_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    vid_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vid_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))

    video_writer = cv2.VideoWriter(final_path, cv2.VideoWriter_fourcc('m','p','4','v'), fps, (vid_width, vid_height), True)
    success, frame = video.read()
    index = 1

    while success:

        if gaze_point_index < len(gaze_points) - 1 and gaze_points[gaze_point_index + 1]['t'] <= (index/fps)*1000:
            gaze_point_index += 1

        curr_gaze_point = gaze_points[gaze_point_index]
        x, y, outside = translate_coordinates(STIMULUS_ASPECT_RATIO,
                                     win_height,
                                     win_width,
                                     vid_height,
                                     vid_width,
                                     curr_gaze_point['x'],
                                     curr_gaze_point['y']
                                     )

        if not outside:
            cv2.circle(frame, (x, y), radius=10, color=(255, 0, 0), thickness=-1)

        cv2.waitKey(int(1000 / int(fps)))
        video_writer.write(frame)
        success, frame = video.read()
        index += 1
    video.release()

    # add audio to the rendered Video
    # currently broken, as moov atom is missing from the mp4 generated by cv2.VideoWriter
    #p3 = subprocess.Popen(['ffmpeg',
    #                       '-y',
    #                       '-i',
    #                       pre3_path,
    #                       '-i',
    #                       audio_path,
    #                       '-c',
    #                       'copy',
    #                       final_path
    #                       ])
    #p3.wait()

    os.remove(pre1_path)
    #os.remove(pre2_path) # do not remove the precursor video (that has audio) while audio merge does not work
    #os.remove(pre3_path) # doesnt exist while audio merge does not work
    #os.remove(audio_path) # doesnt exist while audio merge does not work

files = [f for f in listdir(data_directory) if isfile(join(data_directory, f))]
participants = set()
trials = set()

for filename in files:
    if filename.startswith("."):# or filename.endswith(".json"):
        continue
    try:

        # fix for unknown number of _ in subject id
        filename_split = filename.split("_")

        split_pos = -2 if filename.endswith(tuple(list_of_stimuli_endings)) else -1

        participant = "_".join(filename_split[:split_pos])

        participants.add(participant)
        trial = ".".join("_".join(filename_split[split_pos:]).split(".")[:-1])

    except:
        continue

    trials.add(trial)


videos = [t for t in trials if "_" in t]

interval_len_of_interest = 8000


exclusion_dict = dict()
exclusion_comments = dict()
checked_participants = []  # list of participants listed in the exclusion_csv, used to only include the checked ones

# If it exists, parse the csv for exclusions due to manual inspection
if os.path.exists(exclusion_csv_path):
    exclusion_check_colnames = ["FAM1_OK", "FAM2_OK", "FAM3_OK", "FAM4_OK", "TEST1_OK", "TEST2_OK"]

    with open(exclusion_csv_path) as f:
        # check if ";" is used as delimiter
        pos = f.tell()
        header = f.readline()
        f.seek(pos)
        if header.count(";") > header.count(","):
            csv_string = ''.join(l.replace(',', '').replace(';', ',') for l in f)
        else:
            csv_string = ''.join(l for l in f)

        exclusion_df = pd.read_csv(StringIO(csv_string))

    checked_participants = list(exclusion_df['id'])

    for p_id in exclusion_df['id']:
        if p_id not in exclusion_dict:
            exclusion_dict[p_id] = []

    for trial_index, colname in enumerate(exclusion_check_colnames):
        for index, value in enumerate(exclusion_df[colname]):
            if not isinstance(value, str) or value.lower() != "yes":
                exclusion_dict[exclusion_df['id'][index]].append(trial_index+1)
                exclusion_comments[exclusion_df['id'][index]] = exclusion_df['comment'][index]

                # data about manual exclusions
    merged_exclusion_list = []
    for key, value in exclusion_dict.items():
        merged_exclusion_list += value

    
else:
    print("No file containing manual trial exclusions found. Is this intended?")



samplingrate_exlusion_trials = []

df_dict_list = []
df_dict_resampled_list = []

# Transformation to fit the analysis scripts used by the manybabies study
for p in participants:

    json_path = data_directory + "/" + p + "_data.json"
    try:
        with open(json_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        continue
    data = [x for x in data if 'task' in x and x['task'] == 'video']

    if not os.path.exists(output_directory+"/"+p):
        os.makedirs(output_directory+"/"+p)
        
    # process data for participants

    df_dict = dict()
    df_dict['subid'] = p

    df_dict['stim_width'] = STIMULUS_WIDTH
    df_dict['stim_height'] = STIMULUS_HEIGHT

    df_dict_resampled = dict()
    df_dict_resampled['subid'] = p

    for index, trial in enumerate(data):

        df_dict['trial_num'] = index + 1
        # Exclusion criteria
        # Exclusion criterion 1: tracking malfunction picked by human rater

        name_without_trialorder = "_".join(p.split("_")[:-1])

        # if an exclusion file is present, only consider participants listed in the exclusion file
        if os.path.exists(exclusion_csv_path) and name_without_trialorder not in checked_participants:
            continue

        df_dict['manual_exclusion'] = "no"
        df_dict['manual_exclusion_reason'] = ""
        df_dict_resampled['manual_exclusion'] = "no"
        df_dict_resampled['manual_exclusion_reason'] = ""
        if name_without_trialorder in exclusion_dict and df_dict['trial_num'] in exclusion_dict[name_without_trialorder]:
            df_dict['manual_exclusion'] = "yes"
            df_dict['manual_exclusion_reason'] = exclusion_comments[name_without_trialorder]
            df_dict_resampled['manual_exclusion'] = "yes"
            df_dict_resampled['manual_exclusion_reason'] = exclusion_comments[name_without_trialorder]


        df_dict['stimulus'] = trial['stimulus'][0].split("/")[-1].split(".")[0]
        df_dict_resampled['stimulus'] = df_dict['stimulus']

        # calculate sampling rate
        datapoints = trial['webgazer_data']
        sampling_diffs = [datapoints[i + 1]['t'] - datapoints[i]['t'] for i in range(1, len(datapoints) - 1)]
        sampling_rates = [1000 / diff for diff in sampling_diffs]
        df_dict['sampling_rate'] = statistics.mean(sampling_rates)
        df_dict['condition'] = "fam" if "FAM" in df_dict['stimulus'] else ("knowledge" if "KNOW" in df_dict['stimulus'] else "ignorance")
        df_dict['stimulus_version'] = trial['stimulus_version'] if "stimulus_version" in trial else 0  # Check if the trial happened after the video fix

        # Resampled data - only important for visualizations
        last_time_point = datapoints[-1]["t"]
        timestep = 1000/RESAMPLE_SAMPLING_RATE
        t = 0
        last_index = 0
        while t <= last_time_point:

            if last_index + 1 == len(datapoints):
                break

            while t >= datapoints[last_index + 1]["t"] and t <= last_time_point:
                last_index += 1

            df_dict_resampled['x'] = datapoints[last_index]['x']
            df_dict_resampled['y'] = datapoints[last_index]['y']
            df_dict_resampled['t'] = int(t)
            df_dict_resampled['win_width'] = trial['windowWidth']
            df_dict_resampled['win_height'] = trial['windowHeight']
            df_dict_resampled_list.append(dict(df_dict_resampled))

            t += timestep

        # Non-resampled data - important for analysis of the critical time period
        for datapoint in datapoints:

            df_dict['t'] = datapoint["t"]
            df_dict['x'] = datapoint["x"]
            df_dict['y'] = datapoint["y"]
            df_dict['win_width'] = trial['windowWidth']
            df_dict['win_height'] = trial['windowHeight']

            x_stim, y_stim, outside = translate_coordinates(STIMULUS_ASPECT_RATIO,
                                                  trial['windowHeight'],
                                                  trial['windowWidth'],
                                                  STIMULUS_HEIGHT,
                                                  STIMULUS_WIDTH,
                                                  datapoint["x"],
                                                  datapoint["y"]
                                                  )

            df_dict['x_stim'] = x_stim
            df_dict['y_stim'] = y_stim

            df_dict['internal_aoi_hit'] = "none"
            if "hitAois" in datapoint:
                df_dict['internal_aoi_hit'] = datapoint["hitAois"]


            df_dict_list.append(dict(df_dict))

    for v in videos:
        # only get the data of the correct stimulus
        filtered = [x for x in data if x['stimulus'][0].split("/")[-1].split(".")[0] == v]
        if len(filtered) < 1:
            continue

        video_path = data_directory + "/" + p + "_" + v + ".webm"
        output_path = "."
        if len(sys.argv) == 1 or sys.argv[1] == "t":
            tag_video(video_path, filtered[0], v, p)


df = pd.DataFrame(df_dict_list)
df_resampled = pd.DataFrame(df_dict_resampled_list)


df.to_csv(output_directory + "/transformed_data.csv", encoding='utf-8')
df_resampled.to_csv(output_directory+"/transformed_data_resampled.csv", encoding='utf-8')

with zipfile.ZipFile(output_directory + '/raw.zip', 'w') as zipObj:
    for file in Path(data_directory).glob('*.json'):
        print(file)
        zipObj.write(os.path.join(os.getcwd(), str(file)),arcname=os.path.split(str(file))[-1])


def create_beeswarm(media_name, resampled_df, name_filter, show_sd_circle):

    """ create a beeswarm plot for a stimulus given a df with the resampled gaze data"""

    pre_path = output_directory+"/"+media_name+"_beeswarm_tobedeleted_" + name_filter + ".mp4"
    final_path = output_directory + "/" + media_name + "_beeswarm_" + ("sd_" if show_sd_circle else "")+ name_filter + ".mp4"

    # add frame counter to video
    p1 = subprocess.Popen(['ffmpeg',
                     '-y',
                     '-i',
                     media_directory+"/"+media_name+".mp4",
                     '-vf',
                     "drawtext=fontfile=Arial.ttf: text='%{frame_num} / %{pts}': start_number=1: x=(w-tw)/2: y=h-lh: fontcolor=black: fontsize=(h/20): box=1: boxcolor=white: boxborderw=5",
                     "-c:a",
                     "copy",
                     "-c:v",
                     "libx264",
                     "-crf",
                     "23",
                     pre_path,
                     ])
    p1.wait()

    #filter dataframe by name_filter and trial
    clean_df = resampled_df[(resampled_df['stimulus'] == media_name) & (resampled_df['subid'].str.contains(name_filter)) & (resampled_df['manual_exclusion'] != "yes")]

    # tag the video with eye tracking data
    video = cv2.VideoCapture(pre_path)
    fps = video.get(cv2.CAP_PROP_FPS)
    vid_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vid_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))

    video_writer = cv2.VideoWriter(final_path, cv2.VideoWriter_fourcc('m','p','4','v'), fps, (vid_width, vid_height), True)
    success, frame = video.read()
    index = 1
    timestep = 1000 / RESAMPLE_SAMPLING_RATE
    t = 0

    while success:

        relevant_rows = clean_df[clean_df['t'] == int(t)]

        if t <= (index/fps)*1000:
            t += timestep

        x_values = []
        y_values = []
        for i, row in relevant_rows.iterrows():

            x, y, outside = translate_coordinates(STIMULUS_ASPECT_RATIO,
                                         row['win_height'],
                                         row['win_width'],
                                         vid_height,
                                         vid_width,
                                         row['x'],
                                         row['y']
                                         )

            x_values.append(x)
            y_values.append(y)

            if not outside:
                cv2.circle(frame, (x, y), radius=10, color=(255, 0, 0), thickness=-1)
        try:
            cv2.circle(frame, (int(statistics.mean(x_values)), int(statistics.mean(y_values))), radius=15, color=(0, 0, 255), thickness=-1)
        except Exception:
            pass

        try:
            if show_sd_circle:
                cv2.ellipse(frame,
                            (int(statistics.mean(x_values)), int(statistics.mean(y_values))),
                            (int(statistics.stdev(x_values)), int(statistics.stdev(y_values))), 0., 0., 360, (255, 255, 255), thickness=3)
        except Exception:
            pass

        #cv2.imshow(media_name, frame)
        cv2.waitKey(int(1000 / int(fps)))
        video_writer.write(frame)
        success, frame = video.read()
        index += 1

    video.release()
    os.remove(pre_path)


# create beeswarm plots
if len(sys.argv) == 1 or sys.argv[1] == "b":
    for v in videos:
        create_beeswarm(v, df_resampled, "", True)
        create_beeswarm(v, df_resampled, "", False)



