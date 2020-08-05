


import git
import gnupg
import os
import tempfile
from shutil import copy
import datetime
import subprocess
import configparser
import argparse


class configFile_Error(Exception):
    """Error that is raised when a Problem with the configuration file is encountered"""
    pass

class repo_Error(Exception):
    """Error that is raised when a Problem with the git repo is encountered"""
    pass

def parseInputArguments():
    parser = argparse.ArgumentParser(description="Retrieves a APT filelist from Github,  searches for new Experiments which are not yet listed in the file and updates the List. Then pushes updated list to Github.")
    parser.add_argument("--configFile", required=True)
    pargs = parser.parse_args()
    pathToConfigFile = pargs.configFile
    return pathToConfigFile

def getConfigFromFile(pathToConfigFile):
    """Rread the config File and return config object. Throws Exceptions if problems with File or contents"""
    
    # Step 1: read file,  error if problems whilst doing so
    config = configparser.ConfigParser()
    try:
        readfiles = config.read(pathToConfigFile)
    except:
        print("\n Error while reading configuration File. \n")
        raise 
    if len(readfiles) == 0:
        raise configFile_Error("Could not read config File " + pathToConfigFile + " . Does the File exist?")
    configsections = config.sections()

    # Step 2: check the "General Settings Section"
    if not("General Settings" in configsections):
        raise configFile_Error('Could not find a "General Settings" sections in the provided config File.')
    expectedparams = ["maxFilesPerUpdate"]
    for param in expectedparams:
        try: 
            value = config["General Settings"][param]
        except KeyError:
            raise configFile_Error("Could not read parameter " + param + " from section 'General Settings' in config File")
        if value == None:
            raise configFile_Error("Could not read value of parameter " + param + "from section 'General Settings' in config file. Is it specified?")

    # Step 3: check the individual machine sections
    machines = configsections
    machines.remove("General Settings")
    if len(machines) < 1:
        raise configFile_Error("Could not find at least one section for a machine in the config File")
    expectedparams = ["gitRepo", "listFileInRepo", "dirFile", "pythonCommand", "fileUpdaterPath", "gpg_keyid", "gpg_key_passphrase"] # params that need to be listed in the config file
    requiredvalues = ["gitRepo", "listFileInRepo", "dirFile", "pythonCommand", "fileUpdaterPath", "gpg_keyid"] # parames where a values is required, ie that cannot be empty
    for machine in machines:
        for param in expectedparams:
            try: 
                value = config[machine][param]
            except KeyError:
                raise configFile_Error("Could not read parameter " + param + " from section " + machine + " in config File")
            if (value in requiredvalues) and (value == None):
                raise configFile_Error("Could not read value of parameter " + param + "from section " + machine + " in config file. Is it specified?")
    return config

def read_config_file(pathToConfigFile, machineName):
    config = configparser.ConfigParser()
    config.read(pathToConfigFile)

def configFile_getMachines(config):
    machines = config.sections()
    machines.remove("General Settings")
    return machines





pathToConfigFile = parseInputArguments()
config = getConfigFromFile(pathToConfigFile=pathToConfigFile)

machines = configFile_getMachines(config)

for machine in machines:
    
    #Clone Repo to temp folder 
    tmp_clonedRepoPath = tempfile.mkdtemp(prefix='APTFileTrack_tmpRepo_')
    repo = git.Repo.clone_from(config[machine]["gitRepo"], to_path=tmp_clonedRepoPath, multi_options=["--config core.autocrlf=false"])

    # Get the old APTExperimentsFile from cloned repo
    APTExperimentsFile = os.path.join(tmp_clonedRepoPath, config[machine]["listFileInRepo"])
    if not(os.path.isfile(APTExperimentsFile)):
        raise repo_Error("Could not find Experiments list " + config[machine]["listFileInRepo"] + " in repository " + config[machine]["gitRepo"] + "\n If you were planning on adding a new machine,  you need to manually add this folder and an empty experiments list to the repo first.")

    
    #make temp directory for output file of updater script
    tmp_dir = tempfile.mkdtemp(prefix='APTFileTrack_tmpFiles_')
    newFilePath = os.path.join(tmp_dir,"tmp_outfile.txt")

    #run updater script
    fileUpdaterPath = config[machine]["fileUpdaterPath"]
    pythonCommand = config[machine]["pythonCommand"]
    dir_File = config[machine]["dirFile"]
    maxFilesPerUpdate = config["General Settings"]["maxFilesPerUpdate"]
    commandToRun = pythonCommand + ' "'  + fileUpdaterPath + '" --inputFile "' + APTExperimentsFile + '" --outputFile "' + newFilePath + '" --dirFile "' + dir_File + '" --maxFiles ' + maxFilesPerUpdate
    print("Will run: " + commandToRun)
    process = subprocess.Popen(commandToRun, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout,stderr = process.communicate()
    process.wait()
    print("Returned: " + str(stdout) + "\n" + str(stderr))

    #copy output file of updater script to local repo, overwrite old APTExperimentsFile
    copy(src=newFilePath, dst=APTExperimentsFile)


    #create a signature file. Requires a default key to be set up on the computer.
    try:
        keyid = config[machine]["gpg_keyid"]
        key_passphrase = config[machine]["gpg_key_passphrase"]
        gpg = gnupg.GPG()
        with open(APTExperimentsFile, 'rb') as fid:
            signed_data = gpg.sign_file(fid, keyid = keyid, detach=True, clearsign=False, binary=True, passphrase=key_passphrase) 
        sigFile = APTExperimentsFile + ".gpg"
        with open(sigFile, 'wb+') as fid:
            fid.write(signed_data.data)
    except:
        print(" \n Error while creating gpg signature file \n")
        raise

    #also add a public key file to the repo
    try:
        #apfolder = os.path.dirname(APTExperimentsFile) #this puts the key in the machine folder - useful if different machines have different keys
        apfolder = tmp_clonedRepoPath
        publicKeyFile = os.path.join(apfolder, "publickey.pub")
        ascii_armored_public_keys = gpg.export_keys(keyids = config[machine]["gpg_keyid"])
        with open(publicKeyFile, 'w+') as fid:
            fid.write(str(ascii_armored_public_keys))
    except:
        print(" \n Error while adding public key to repo \n")
        raise

    #Stage changes in local repository
    try:
        index = repo.index
        index.add(APTExperimentsFile)
        index.add(sigFile)
        index.add(publicKeyFile)
    except:
        print(" \n Error while staging changes in local repo clone \n")
        raise

    # Commit
    try:
        CommitMessage = "Auto update on " + datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
        index.commit(CommitMessage)
    except:
        print(" \n Error while committing changes in local repo clone \n")
        raise

    #git push
    try:
        origin = repo.remote(name='origin')
        origin.push()
    except:
        print(" \n Error while pushing changes to remote repository \n")
        raise




















































