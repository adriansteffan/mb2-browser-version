# ManyBabies2 Browser Based Eyetracking

This repository contains the code to run a webcam-powered, browser-based eye-tracking experiment to participate in [ManyBabies2](https://manybabies.github.io/MB2/).

This README contains technical documentation and details to make the data pipeline retracable. Information on how to participate in the experiment using this software can be found in the official [MB2 Webgazer Manual](https://docs.google.com/document/d/1A0PweKqvWuFw-rm1qcIMNiQAZ669XIjsLc7c-F2sobI/edit).

<p align="center">
<img src="demo.gif" width="500" >
</p>

## Table of Contents

* [Installation](#Prerequisites)
  * [Prerequisites](#Prerequisites)
  * [Deployment](#Deployment)
  * [Development Setup](#Prerequisites)
* [Usage](<#Usage-Instructions>)
  * [URL parameters](<#URL-parameters>)
  * [Saved data](<#Saved-data>)
  * [Visualization](<#Visualizing the eye tracking data >)
* [Misc](<#Built-with>)
  * [Built with](<#Built-with>)
  * [Changes to jsPsych-6.3.1](<#Changes-to-jsPsych-6.3.1>)
  * [Authors](#Authors)
  * [License](#License)



## Prerequisites

As this repository contains video files served over github lfs, the [git-lfs](https://git-lfs.github.com/) extension needs to be installed and activated.

[Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/) are needed for both deployment and development (you can deploy this app without docker, but we highly recommend running separate containers for different experiments). 

If you want to use the visualization tool, you will need an [ffmpeg](https://www.ffmpeg.org/) installation and a [Python3.7](https://www.python.org/downloads/) installation. You will also need to run 
```
python3.7 -m pip install -r requirements.txt
``` 
in the `data-processing` directory to install the necessary dependencies.


## Deployment

If you are partaking in a manybabies project and need a domain or assistance with setting up this experiment, contact [adriansteffan](https://github.com/adriansteffan) via [mail](mailto:adrian.steffan@hotmail.de).

If you want to provide a link where participants can upload their trial data if the upload to the server fails, you need to specify the link in `config.js`.

### With Docker (recommended)

After cloning the repository, you can build the project by running 

```
./build-container.sh
```

in the [prod_mb2-browser-version](prod_mb2-browser-version/) directory. 
This will automatically start the webserver serving the app, you can stop it with
```
docker-compose down
```

and later restart it with

```
docker-compose up -d
```

in the [prod_mb2-browser-version](prod_mb2-browser-version/) directory.

To make the container reachable from the internet, refer to [these instructions](https://gist.github.com/adriansteffan/48c9bda7237a8a7fcc5bb6987c8e1790) on how to set up your apache reverse proxy. Depending on your setup, you might want to change the ip mapping in [prod_mb2-browser-version/docker-compose.yml](prod_mb2-browser-version/docker-compose.yml).

### Without Docker 

Alternatively, you can use a webserver (like apache) running and configured on your machine. This server needs to be reachable via HTTPS and support PHP. 

On a fresh install, this would be achieved by running:
```
apt-get install -y apache2 php && a2enmod ssl
```

After cloning the repository, run

```
./build.sh
```

in the root directory. Afterwards, copy the contents of `local-server/webroot` to the webroot of your webserver by running 

```
cp local-server/webroot/* /var/www/html
```

Finally, the folder for the experiment data needs to be created by running

```
mkdir /var/www/data && chown -R www-data:www-data /var/www/data
```
(adjust the filepaths of the commands and in `writedata.php` to suit your particular setup)


## Development

### Setup 

As webgazers requires the usage of the https protocol, you will need a local server for development. This project comes with a [docker-compose.yml](docker-compose.yml) file that takes care of the setup and configuration.

In order for https to work, we need an installation of open-ssl to create and sign a ssl certificate for localhost.

After installing open-ssl, run the following commands in the `local-server/config` directory:

```
openssl genrsa -des3 -out rootCA.key 2048

openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 1024 -out rootCA.pem

openssl req -new -sha256 -nodes -out server.csr -newkey rsa:2048 -keyout server.key -config <( cat server.csr.cnf )

openssl x509 -req -in server.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial -out server.crt -days 500 -sha256 -extfile v3.ext
```

Afterwards, you need to add your newly created CA (rootca.pem) to the list of trusted CAs of your operating system. Instructions for that can be found [here](https://google.com).

As a final step, build the docker container for the webserver by running 
```
docker-compose build
```
in the root directory of the repository.

### Running the server

In order to run the development server, run 
```
docker-compose up -d
```

in the root directory. You can stop the server with 
```
docker-compose down
```

When initially cloning the project and after making changes , update the files in the local webroot by running

```
./build.sh
```

in the root directory.

## Usage Instructions

### URL parameters
After deploying the container, there are a few options for the execution of the online experiment that can be configured using url paramters.

For example, to if you want the output data to be linked to a participant with the id "participant1", and want to choose the stimulus order "Trial order 3", you use the following link: 


```
yoururl.com?id=participant1&trial_order=3
```

The following table gives you an overview of all available parameters:

| url parameter  | possible values| default value |  description |
| ------------- | ------------- | ------------- | ------------- |
| lang  | string ("de", "en", or "ko") | "en"  | the language in which the instructions will be displayed |
| id  | string | a randomly generated uuid  | the id that is attached to the output data, used to identify a participant|
| trial_order  | integer (1-32) | a random number between 1 and 32 | the choice and order of stimuli as specified by the proposal paper |
| key  | string | null | A key in the [ManyKeys](https://github.com/adriansteffan/manykeys) format, used to encrypt the data before being transmitted to the server. If not present, the data will be stored on the server without encryption |
| show_aoi  | true/false | false | a flag to indicate whether the aois should be overlayed over the stimuli (for debugging purposes) |
| download_data  | true/false | false | a flag to indicate whether the browser should download a the generated data after the trial finishes |
| prevent_upload  | true/false | false | a flag to indicate if the upload of trial data to the server should be prevented|
| print_data  | true/false | false | a flag to indicate if the trial data json should be displayed in the browser after the trial finishes|

### Saved data

The data that was uploaded by the participants browsers can be found in `prod_mb2-browser-version/data` (or var/www/data of you run the dockerless setup). There are two types of files, generated for every participant:

* A **json** data file containing all of the experiment data generated by jsPsych. It is named `[id]_[trial_order]_data.json`
* **Video** data files containing the webcam recording for each of the individual trials. They are named `[id]_[trial_order]_[trialname].webm`

Note: If you are running ManyKeys, each User will have a seperate folder, filled with ciphered `.enc` files. Archive this folder and send it to the respective user for decryption.


## Data Processing Pipeline

This section describes how the output data from the experiment's software is processed into the final data format for the MB2 analysis.

As the study was a collaborative effort across multiple labs, handled sensitive data, and was restructured during data collection, these steps could be trimmed down in simpler setups. For retracability, we depict the pipeline exactly how it worked in the study.

The first steps of the processing pipeline are explained in [Part 3 of the MB2 Webgazer Manual](https://docs.google.com/document/d/1A0PweKqvWuFw-rm1qcIMNiQAZ669XIjsLc7c-F2sobI/edit#heading=h.y5vqykpbkcez). These steps were performed decentralized by each collecting lab and use the files in the [data-processing](data-processing/) folder.

Afterwards, the collected files were sent to a single lab that prepared the data for import into the joined mb2 dataset. These steps are explained in the following section and files for these are found in [data-import-script](data-import-script/).




### Data import

To run the script, you will need a [Python3.7](https://www.python.org/downloads/) installation. You will also need to run 
```
python3.7 -m pip install -r requirements.txt
``` 
in the `data-import-script` directory to install the necessary dependencies.

Next, create a `data` folder in the [data-import-script](data-import-script/) directory and arrange the labs data in the following structure: 

```
data-import-script
│
├── import.py
├── requirements.txt
└── data
    ├── LABNAME_01
    │   ├── excluded_trials.csv
    │   └── raw
    │       ├── PARTICIPANTID01_TRIALORDER_data.json
    │       ├── PARTICIPANTID02_TRIALORDER_data.json
    │       └── ...
    ├── LABNAME_02
    │   └── ...
    ...
```

(To separate adult and toddlerdata for labs, include the data via separate directories names LABNAME01_adult or LABNAME01_toddler)

Then, run
```
python3.7 import.py
``` 
in the `data-import-script` directory to perform data import. The resulting files will appear in `data-import-script/output`.


## Built With

  - [jsPsych](https://www.jspsych.org/) - A modified version of jspsych-6.3.1 is used for the general trial structure and webgazers integration
  - [webgazers.js](https://webgazer.cs.brown.edu/) - The eye tracking library used to capture gaze coordinated via a webcam

## Changes to jspsych-6.3.1

* Changed the `webgazer` extension in `jspsych-6.3.1/extensions/jspsych-ext-webgazer.js`. It now has additional parameters for defining areas of interest (AOI). These AOIs tag all datapoints of the webgazer output that fall into the correspong AOI. With an url paramter flag they can also be displayed for debugging purposes.

* Added a `webcam-recorder` extension in `jspsych-6.3.1/extensions/jspsych-ext-webcam-recorder.js`. It can be used to record the participants webcam on a trial by trial basis. (Until a better solution is found, the video blobs get saved to window.webcamVideoBlobs for further processing)

* Added a `background-audio` extension in `jspsych-6.3.1/extensions/jspsych-ext-background-audio.js`. It can be used to add a looping audio file (currently hardcoded) to the background of any trial.

* Changed `jspsych-6.3.1/plugins/jspsych-webgazer-calibrate.js` and `jspsych-6.3.1/plugins/jspsych-webgazer-validate.js` to optionally replace the dot with something more attention grabbing and add background audio, making it better suited for infant research.

## Authors

- **Adrian Steffan** [adriansteffan](https://github.com/adriansteffan) [website](https://adriansteffan.com/)

## License

This project is licensed under the [GNU GPLv3](LICENSE.md) - see the [LICENSE.md](LICENSE.md) file for
details


