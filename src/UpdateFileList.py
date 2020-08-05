#Takes in a list of files, or a director set, and thenproduces a list of hashes
#You may need to tweak the SEARCHLIST value for non Cameca instruments

import sys
import os
import warnings
import hashlib
import tempfile
import datetime
import argparse
import warnings



def parseInputArguments():
#parse the input. Return [InputFile, OutputFile, DirecoryFile] as a list
    parser = argparse.ArgumentParser(description="Updates a provided Inputfile with APT data files on the directories given in dirFile and writes the result to outputfile")
    parser.add_argument("--inputFile", required=True)
    parser.add_argument("--outputFile", required=True)
    parser.add_argument("--dirFile", required=True)
    parser.add_argument("--maxFiles", default=float('inf'), required=False, type=int)
    pargs = parser.parse_args()
    InputFile = pargs.inputFile
    OutputFile = pargs.outputFile
    DirectoryFile = pargs.dirFile
    maxFiles = pargs.maxFiles
    if not(os.path.isfile(InputFile)):
        raise ValueError("Input file doesn't exist.")
    if not(os.path.isfile(DirectoryFile)):
        raise ValueError("Directory file doesn't exist.")
    if os.path.isfile(OutputFile):
        raise ValueError("Output File already exists. Won't overwrite.")
    return [InputFile, OutputFile, DirectoryFile, maxFiles]


#Find all the files that match a given glob
def getAPTDataFilePaths(DirectoriesToCheck):
# gets the full file paths of all .rhit 'hits files on the given paths, non-recursive search
# DirectoriesToCheck is a lost of paths
    AllFiles = []
    SEARCHLIST=(".rhit", ".hits", ".str", ".rraw")
    for directory in DirectoriesToCheck:
        try:
            ObjectsInDirectory = os.listdir(directory)
        except FileNotFoundError:
            warnings.warn("Error reading directory " + directory + " .  Is the path correct an accessible? Skipping.")
        else:
            fullpaths = [os.path.abspath(os.path.join(directory, dirobj)) for dirobj in ObjectsInDirectory]
            APTfilesInDirectory = [f for f in fullpaths if os.path.isfile(f) and f.lower().endswith(SEARCHLIST)]
            AllFiles.extend(APTfilesInDirectory)
    return AllFiles


def getDirectoriesFromFile(DirectoryFile):
# returns a list with all Directories from the provided directory file.
# ignores lins starting with # in the file
    with open(DirectoryFile) as fid:
        DirectoriesToCheck = fid.read().splitlines()
    Directories = [di for di in DirectoriesToCheck if (not(di.startswith("#")) and not(di.isspace()))]    
    return Directories



def createTempFile(InputFile):
    # creates a temporary file, copies content of given input file to it
    tmpfile = tempfile.SpooledTemporaryFile(mode='w+')
    with open(InputFile) as fid:
        tmpfile.write(fid.read())
    return tmpfile



def writeOutputFile(tempFile, outputFilePath):
#compies the temporary file to the output file that will be writte to the disk
    tempFile.seek(0) 
    if os.path.isfile(outputFilePath):
        raise ValueError("Output File already exists. Won't overwrite.")
    with open(outputFilePath, "w+") as fid:
        fid.write(tempFile.read())


def getKnownFiles(inputFile):
# Get all files and hashes that are listed in the input file as lists
# Would probably be nicer if it returned sth like a multidimensional array
# or dict with filenames and hashes but the two lists we have here are
# fine for now.
    with open(inputFile) as fid:
        inputFileContent = fid.read().splitlines()
    knownFileNames = list()
    knownHashes = list()
    for line in inputFileContent:
        if not(line.lstrip().startswith("#")): # skip lines starting with "#
            splitted = line.split(';') # 
            if len(splitted) >= 2:
                knownFileNames.append(splitted[0]) # 1st column: Filename
                knownHashes.append(splitted[1]) # 2nd column: Hash
    return knownFileNames, knownHashes



def extendAPTExperimentTempList(fileToBeExtended, APTdataFileName, hashSum):
# Extends a APT experiment list, given as python temporary file that is opened for writing (not a path! a tempfile!) with another line containing Name (first letters of hash), FileName, hash entry time and full hashsum
# fileToBeExtended must be opened in w+ mode, not in w+b
    lineToAdd = "\n" + APTdataFileName + ";" + hashSum
    fileToBeExtended.write(lineToAdd)


def calcFileHash(filepath):
    # calculates a hash file
    # using this smart technique to read the file in chunks instead of putting it all in the RAM: https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    attempts = 0
    while True:    
        attempts += 1
        fileHasher = hashlib.sha256()
        try:
            with open(filepath, "rb") as fid:
                chunk = fid.read(294400)
                while chunk:
                    fileHasher.update(chunk)
                    chunk = fid.read(294400)  
        except OSError:  # This error sometimes just happens. Try again up to four times. Error if still not working after that       
            if attempts < 4:
                warnings.warn(" Problem reading File " + filepath + "will try again.")
            else:
                print("\n failed to read file " + filepath + " 4 times in a row. Giving up. \n")
                raise
        else:
            hashSum = fileHasher.hexdigest()
            return hashSum




def main():

    pargs = parseInputArguments()
    InputFile = pargs[0]
    OutputFile = pargs[1]
    DirectoryFile = pargs[2]
    maxFilesToAdd = pargs[3]
    
    # Get List of Directories
    print("\nReading directory file ", end = '')
    DirectoriesToCheck = getDirectoriesFromFile(DirectoryFile)
    print("...done")

    # Get List of Files, absolute paths
    # File suffix needs to be .rhit or .hits, case-insensitive
    print("Getting List of APT Files ", end = '')
    AptFilePaths = getAPTDataFilePaths(DirectoriesToCheck)
    print("...done")

    # Get List of known hashes from the InputFile
    print("Reading Input File, getting lists of known Hashes and known Filenames", end = '')
    knownFilenames, knownHashes = getKnownFiles(inputFile = InputFile)
    print("...done")

    #Get A temp file to work with
    print("Create temporary file to work on ", end = '')
    tmpFile = createTempFile(InputFile)
    print("...done")

    #Loop through all APT files in AptFilePaths and check wether the filename is already in the ExperimentsList
    #If no, add it as a new line to the temp file
    print("Calculating hashes, updating list", end = '')
    NumFilesAdded = 0
    for APTdataFile in AptFilePaths:
        currentFilename = os.path.basename(APTdataFile)
        if not(currentFilename in knownFilenames): # true if the filename is not yet in the experimentslist!
            hashSum = calcFileHash(filepath=APTdataFile)
            if not(hashSum in knownHashes): # true if the hash is not yet known!
                extendAPTExperimentTempList(fileToBeExtended=tmpFile, APTdataFileName=currentFilename, hashSum=hashSum)
                knownHashes.append(hashSum)
                knownFilenames.append(currentFilename)
                NumFilesAdded = NumFilesAdded + 1
            else:
                warnings.warn("File " + currentFilename + " at " + APTdataFile + " has a filename that is not contained in the ExperimentsList, but the Hash is" + hashSum + " which belongs to a file with another name that is already in the list. Skipping this file.") 
                #with open(" - Filename here - ",'at') as fid: # can be used for debug - prints all filenames with duplicate hashes into a file
                #    filewithhash_id = knownHashes.index(hashSum)
                #    filewithhash = knownFilenames[filewithhash_id]
                #    fid.write(currentFilename + "->" + filewithhash + ":" + str(hashSum) + "\n")
        if NumFilesAdded >= maxFilesToAdd:
            warnings.warn("Reached maximum number of Files to be added. Will stop adding more files to Experiments list.")
            break
    print("...done")

    #copy the temp file to the output file
    print("Writing results to output file", end = '')
    writeOutputFile(tmpFile, OutputFile)
    print("...done")

    print("Success! Added " + str(NumFilesAdded) + " new files to the output file.")





main()
