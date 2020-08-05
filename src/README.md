# AptListUpdater

Python scripts for updating APT experiment lists. 

## Licence 
Available under the GNU GPLv2 licence

## Get started


### Prerequisites

1. Have a Computer with Windows or Linux. 
	- Script has been tested on windows and on a Raspberry pi with raspbian
2. Have python 3 interpreter installed (Tested with Python 3.8.2)
3. Have git and gnupgp installed
4. The python modules GitPython and python-gnupg. To install these you might want to use
```
apt install python-git
apt install python-gnupg
```
or from pip
```
pip install gitpython
pip install python-gnupg
```


### Set up a git repository for your experiment files

The updater scripts can only update experiment files on an existing
repository, but not create a new repository for you. 

You therefore need to create a suitable repository first.

1. Create a new repository on github or elsewhere
2. In the repository, create one subfolder per atomprobe machine that you have
3. In every atomprobe subfolder, add one text file. These will be the AptExperimentLists. You can add comments to the list by starting lines with #


### Set up the updater script

Once your git repository is ready you can set up the updater script

1. Download the files from this repository or clone
2. For every atomprobe machine that you have, create text file with all directories where the experiment data files are stored. These are the directories where the updater script will search for new Experiment files and add them to the experiments list. The directories are searched non-recursively. You can check the provided dirFile_testmachine_example.txt
3. Create a gpg key that you will use to sign you files. You can also use anm existing key, or create different keys for different machines 
4. Create a config.ini file or edit the provided ListUpdaterConfig_example.ini file
5. Run the ManageFileList_Multimachine list and hand the configuration file as parameter. For example
```
python3 ManageFileList_Multimachine.py --configFile /path/to/ListUpdaterConfig_example.ini
```
This will update the empty lists on the git repository with you experiment files!
6. Set up you computer to start the updater script regularly in order to keep you file lists up to date.


## TODO
The script works, but is clearly not yet perfect. Here are some important things that I still need to look into:

1. The parameters in the config files (ListUpdaterConfig_example.ini) are not well explained. Need to add some documentation for these

2. The publickey is stored on the repo root path. This will cause confusion if different keys are used for different machines in the same repository.

3. UpdateFileList.py can be used as standalone update that just updates an existing file list and does not care for uploads to github or signature. You can use it if you intend to publish file lists elsewhere than on github. 



