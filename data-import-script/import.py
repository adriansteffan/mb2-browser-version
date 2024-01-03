"""
This code is hastily pasted together from the data-processing pipeline due
to a restructuring of the data pipeline, so please ignore code quality, thanks!
"""

# TODO: How to import exclusions? For the other trackers, trial wise exclusions live in the respective demo file, but we have a separate one.
# TODO: Keep track of the varying sampling rates?

import json

import shutil
import os
import sys
from pathlib import Path
import shutil
import subprocess
import pandas as pd
import statistics



# information is not present in the data output
STIMULUS_WIDTH = 1280.0
STIMULUS_HEIGHT = 960.0

STIMULUS_ASPECT_RATIO = STIMULUS_WIDTH/STIMULUS_HEIGHT

DATA_DIRECTORY = "./data"
OUTPUT_DIRECTORY = "./output"

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

def remove_suffix(input_string):
    suffixes = ["_adults", "_toddlers"]
    for suffix in suffixes:
        if input_string.endswith(suffix):
            return input_string[:-len(suffix)]
    return input_string

if os.path.exists(OUTPUT_DIRECTORY):
    shutil.rmtree(OUTPUT_DIRECTORY)

os.makedirs(OUTPUT_DIRECTORY)


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
    


labs = [d for d in os.listdir(DATA_DIRECTORY) if os.path.isdir(os.path.join(DATA_DIRECTORY, d))]

for lab in labs:
    
    lab_dir = os.path.join(DATA_DIRECTORY, lab)
    exclusion_file = os.path.join(lab_dir, 'excluded_trials.csv')
    shutil.copy(exclusion_file , os.path.join(OUTPUT_DIRECTORY, f'{lab}_excluded_trials.csv'))

    raw_dir = os.path.join(lab_dir, 'raw')
    json_files = os.listdir(raw_dir)

    df_dict_list = []
    for json_file in json_files:
        parts = json_file.split('_')
        if len(parts) < 3:
            continue
        trial_order = parts[-2]
        subid = '_'.join(parts[:-2])
        
        with open(os.path.join(raw_dir, json_file)) as f:
            data = json.load(f)
        data = [x for x in data if 'task' in x and x['task'] == 'video']
        
        df_dict = dict()
        df_dict['participant_id'] = subid
        df_dict['lab_id'] = remove_suffix(lab)
        df_dict['pupil_left'] = None
        df_dict['pupil_right'] = None

        #df_dict['stim_width'] = STIMULUS_WIDTH
        #df_dict['stim_height'] = STIMULUS_HEIGHT

       
        for index, trial in enumerate(data):

            #df_dict['trial_num'] = index + 1

            # Check if the trial happened after the video fix
            trial_version = trial['stimulus_version'] if "stimulus_version" in trial else 0
            df_dict['media_name'] = f'{trial["stimulus"][0].split("/")[-1].split(".")[0]}{"_new" if trial_version == 1 else ""}'
    
            datapoints = trial['webgazer_data']
            # calculate sampling rate
            #sampling_diffs = [datapoints[i + 1]['t'] - datapoints[i]['t'] for i in range(1, len(datapoints) - 1)]
            #sampling_rates = [1000 / diff for diff in sampling_diffs]
            #df_dict['sampling_rate'] = statistics.mean(sampling_rates)

            
            for datapoint in datapoints:

                df_dict['t'] = datapoint["t"]
                #df_dict['win_width'] = trial['windowWidth']
                #df_dict['win_height'] = trial['windowHeight']

                x_stim, y_stim, outside = translate_coordinates(STIMULUS_ASPECT_RATIO,
                                                    trial['windowHeight'],
                                                    trial['windowWidth'],
                                                    STIMULUS_HEIGHT,
                                                    STIMULUS_WIDTH,
                                                    datapoint["x"],
                                                    datapoint["y"]
                                                    )

                df_dict['x'] = x_stim
                df_dict['y'] = y_stim



                df_dict_list.append(dict(df_dict))


    pd.DataFrame(df_dict_list).to_csv(os.path.join(OUTPUT_DIRECTORY, f'{lab}_xy_timepoints.csv'), index = False ,encoding='utf-8')

