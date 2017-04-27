
##############################################
############### Setup AMI Script #############
########## Moondog Animation Studio ##########
################# Erin Terre #################
##############################################

from shotgun_api3 import Shotgun
from datetime import datetime
from xml.dom import minidom
from operator import itemgetter

import os
import re
import sys
import logging
import subprocess


## define the logger that will be used to log all errors
logging.basicConfig(level=logging.INFO, filename=r'W:\DEV\PIPELINE\SHOTGUN\LOGS\setuplog.log')

##############################################
############### main Function ################
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0) ############################
#### INFO: the foundation of the script ######
##############################################

def main(script, project):

	## get shotgun script information && create the shotgun instance
	SERVER_PATH = ""
	SCRIPT_NAME = ''
	SCRIPT_KEY = ''

	sg = Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

	projectList = getProjectList(sg, logging, project)

	if '.xml' not in projectList['setupXML']:
		projectList['setupXML'] = projectList['setupXML'] + ".xml"

	readXMLPath = projectList['pathToProject'] + '\\05_PROD\\DATA\\XML\\' + projectList['setupXML']

	## check if the readXML file exists
	if not os.path.exists(readXMLPath):
		logging.info(str(datetime.now()) + " The Premiere XML file does not exist: " + readXMLPath)
		return False

	## create the minidom to parse the xml
	xmlFile = minidom.parse(readXMLPath)

	## get the episodes name
	episodeName = getEpisodeName(xmlFile)

	## create the arrays to store information for building the xml
	shotList = []
	sequenceList = []

	## get the xmlName and path from the episode
	episode = episodeName.split('_')
	episode = episode[1]
	xmlName = episode.lower() + "_shotdata.xml"
	xmlFolder = projectList['pathToProject'] + '\\05_PROD\\EPISODES\\' + episodeName + "\\99_PIPELINE\\"
	xmlPath = xmlFolder + xmlName

	## check if XMLFolder exisits
	if not os.path.exists(xmlFolder):
		logging.info(str(datetime.now()) + " The Path to 99_PIPELINE does not exist: " + xmlFolder)
		return False

	## get the tracks in the xml
	tracks = getTracks(xmlFile)

	## get only the element nodes from each track, get the tracks children then get the shots and sequences
	for track in tracks: 
		cleanTrack = cleanChildren(track)
		trackChildren = getChildren(cleanTrack)
		shotList = findShots(shotList, trackChildren)
		sequenceList = findSequences(sequenceList, trackChildren)
	
	## update shotlist with the sequences they belong to
	shotList = attachSequences(sequenceList, shotList)

	## set the episodeDuration to the end frame of the last shot + 1
	lastShot = len(shotList) - 1;

	episodeDuration = (shotList[lastShot]['end'] + 1)

	## create the simplified XML
	setupXML(xmlPath, episodeName, episodeDuration, sequenceList, shotList)

	## update shotgun
	checkShotgun(sg, logging, projectList['projectID'], episodeName, episodeDuration, shotList, sequenceList)

##############################################
############ checkShotgun Function ###########
#### ARGUMENTS: (5) ##########################
#### RETURNS: (0) ############################
#### INFO: check shotgun && update/create ####
##############################################

def checkShotgun(sg, logging, projectID, episodeName, episodeDuration, shotList, sequenceList):

	## check to see if episode exists in project
	filters = [
		{
			"filter_operator": "and",
			"filters": [
			[ "project", "is", { "type": "Project", "id": projectID } ],
			[ "code", "is", episodeName]
			]
		}
	]

	episodeList = sg.find_one('Scene', filters, fields=['code', 'shots', 'sg_sequences', 'sg_duration'])

	## if the episode does not exist, create all shotgun information
	if episodeList == None:
		
		## create the episode
		episodeData = getEpisodeData(sg, logging, projectID, episodeName, episodeDuration)
		episode = sg.create('Scene', episodeData)

		## create the sequences for the project
		for i in range(0, len(sequenceList)):
			sequenceData = getSequenceData(sg, logging, projectID, episode, sequenceList[i])
			sequence = sg.create('Sequence', sequenceData)

			## create the shots associated to sequence
			for j in range(0, len(shotList)):
				if shotList[j]['match'] == sequenceList[i]['name']:
					shotData = getShotData(sg, logging, projectID, episode, sequence, shotList[j])
					shot = sg.create('Shot', shotData)

	## else we need to update the information
	else:
		## set episodeID
		episodeID = episodeList['id']

		## get our episode
		episodeFilter = [['id', 'is', episodeID]]
		episode = sg.find_one('Scene', episodeFilter)

		## update the sequences
		for i in range(0, len(sequenceList)):
			sequenceID = getSequenceID(sg, logging, episodeID, sequenceList[i])

			## create the sequence if it doesnt exist
			if sequenceID == None:
				sequenceData = getSequenceData(sg, logging, projectID, episode, sequenceList[i])
				sequence = sg.create('Sequence', sequenceData)

			## update the sequence if it does
			else:
				sequenceData = getSequenceData(sg, logging, projectID, episode, sequenceList[i])
				sequence = sg.update('Sequence', sequenceID, sequenceData)

			## update/create shots associated to the sequence
			for j in range(0, len(shotList)):
				if shotList[j]['match'] == sequenceList[i]['name']:
					shotID = getShotID(sg, logging, episodeID, shotList[j])

					## create the shot if it doesnt exist
					if shotID == None:
						shotData = getShotData(sg, logging, projectID, episode, sequence, shotList[j])
						shot = sg.create('Shot', shotData)

					## update the shot if it does
					else:
						shotData = getShotData(sg, logging, projectID, episode, sequence, shotList[j])
						shot = sg.update('Shot', shotID, shotData)

##############################################
############## getShotID Function ############
#### ARGUMENTS: (4) ##########################
#### RETURNS: (1) shotID #####################
#### INFO: get the shots ID ##################
##############################################

def getShotID(sg, logging, episodeID, shotInfo):

	## find the id of the shot
	filters = [
		{
			"filter_operator": "and",
			"filters": [
			[ "sg_scene", "is", { "type": "Scene", "id": episodeID } ],
			[ "code", "is", shotInfo['name']]
			]
		}
	]

	shotList = sg.find_one('Shot', filters, fields=['id'])

	## check if the sequence does exist
	if shotList == None:
		shotID = None
	else:
		shotID = shotList['id']

	return shotID

##############################################
########### getSequenceID Function ###########
#### ARGUMENTS: (4) ##########################
#### RETURNS: (1) sequenceID #################
#### INFO: get the sequence ID ###############
##############################################

def getSequenceID(sg, logging, episodeID, sequenceInfo):

	## find the id of the sequence
	filters = [
		{
			"filter_operator": "and",
			"filters": [
			[ "sg_episode", "is", { "type": "Scene", "id": episodeID } ],
			[ "code", "is", sequenceInfo['name']]
			]
		}
	]

	sequenceList = sg.find_one('Sequence', filters, fields=['id'])

	## check if the sequence does exist
	if sequenceList == None:
		sequenceID = None
	else:
		sequenceID = sequenceList['id']

	return sequenceID

##############################################
########### getEpisodeData Function ##########
#### ARGUMENTS: (5) ##########################
#### RETURNS: (1) episodeData ################
#### INFO: get the episodes data #############
##############################################

def getEpisodeData(sg, logging, projectID, episodeName, episodeDuration):

	## create episode data
	episodeData = { 'project': {'type': 'Project', 'id' : projectID},
			 'code': episodeName,
			 'sg_duration': episodeDuration
	}

	return episodeData

##############################################
########## getSequenceData Function ##########
#### ARGUMENTS: (5) ##########################
#### RETURNS: (1) sequenceData ###############
#### INFO: get the sequences data ############
##############################################

def getSequenceData(sg, logging, projectID, episode, sequenceInfo):

	## create sequence data
	sequenceData = { 'project': {'type': 'Project', 'id' : projectID},
			 'code': sequenceInfo['name'], 
			 'sg_episode': episode
	}

	return sequenceData

##############################################
############# getShotData Function ###########
#### ARGUMENTS: (6) ##########################
#### RETURNS: (1) shotData ###################
#### INFO: get the shots data ################
##############################################

def getShotData(sg, logging, projectID, episode, sequence, shotInfo):

	## get the task template
	filters = [['code', 'is', 'Basic Shot Template']]
	template = sg.find_one('TaskTemplate', filters)

	shotData = { 'project': {'type': 'Project', 'id' : projectID},
			 'code': shotInfo['name'], 
			 'sg_scene': episode, 
			 'sg_sequence': sequence,
			 'sg_cut_duration': int(shotInfo['duration']),
			 'sg_cut_in': int(shotInfo['start']),
			 'sg_cut_out': int(shotInfo['end']),
			 'task_template': template,
			 'sg_start_transition_duration': int(shotInfo['start transition duration']),
			 'sg_start_transition_type': shotInfo['start transition type'],
			 'sg_end_transition_duration': int(shotInfo['end transition duration']),
			 'sg_end_transition_type': shotInfo['end transition type']
	}

	return shotData


##############################################
########## getProjectList Function ###########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) projectList ################
#### INFO: gets all project data #############
##############################################

def getProjectList(sg, logging, project):

	projectList = {}

	## get the triggered projects name using regular expressions
	projectName = re.search('(&)+project_name=+[^&]*', project).group()
	projectName = projectName.replace('&project_name=', '')
	projectName = projectName.replace('%20', ' ')

	## get the triggered projects ID && change it to an int uding regular expressions
	projectID = re.search('(&)+project_id=+[^&]*', project).group()
	projectID = projectID.replace('&project_id=', '')
	projectID = int(projectID)

	## get the project by project id
	filters = [['id', 'is', projectID]]
	project = sg.find_one('Project', filters, fields=['sg_client_name', 'sg_share_drive_path', 'sg_setup_xml'])
	
	projectList['projectID'] = projectID
	projectList['setupXML'] = project['sg_setup_xml']

	## check if clientName was given && if clientName is blank set both to only projectName
	if project['sg_client_name'] != None:
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + project['sg_client_name'] + "\\" + projectName
	else:
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + projectName

	return projectList

##############################################
########### getEpisodeName Function ##########
#### ARGUMENTS: (1) ##########################
#### RETURNS: (1) name.firstChild.data #######
#### INFO: return the name of episode ########
##############################################

def getEpisodeName(xmlFile):

	name = xmlFile.getElementsByTagName('name')[0]
	return name.firstChild.data

##############################################
############# getTracks Function #############
#### ARGUMENTS: (1) ##########################
#### RETURNS: (1) tracks #####################
#### INFO: return tracks in xml ##############
##############################################

def getTracks(xmlFile):

	tracks = xmlFile.getElementsByTagName('track')
	return tracks

##############################################
############ getChildren Function ############
#### ARGUMENTS: (1) ##########################
#### RETURNS: (1) track.childNodes ###########
#### INFO: return children of track ##########
##############################################

def getChildren(track):

		return track.childNodes

##############################################
############ cleanChildren Function ##########
#### ARGUMENTS: (1) ##########################
#### RETURNS: (1) track ######################
#### INFO: return track w/ only elements #####
##############################################

def cleanChildren(track):

	trackChildren = getChildren(track)

	## for each child ...
	for child in trackChildren:
		## clean the children (keep only element nodes)
		if child.nodeType != 1:
			track.removeChild(child)

	return track

##############################################
########### attachSequence Function ##########
#### ARGUMENTS: (2) ##########################
#### RETURNS: (1) shotList ###################
#### INFO: return shotList with sequences ####
##############################################

def attachSequences(sequenceList, shotList):
		
	## get the sequence each shot is attached to
	for j in range(0, len(sequenceList)):
		for i in range(0, len(shotList)):
			if shotList[i]['start'] >= sequenceList[j]['start'] and shotList[i]['end'] <= sequenceList[j]['end']:
				shotList[i]['match'] = sequenceList[j]['name']

	return shotList

##############################################
############## findShots Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (1) shotList ###################
#### INFO: return list of shots ##############
##############################################

def findShots(shotList, trackChildren):

	for child in trackChildren:

		shot = {}
		## if child is a shot
		if child.tagName == "clipitem" and re.match('[s,S]{1}[h,H]{1}\d{4}', child.getElementsByTagName('name')[0].firstChild.data):
			shot['type'] = 'shot'
			shot['name'] = str(child.getElementsByTagName('name')[0].firstChild.data)
			shot['match'] = ''
			shot['start transition'] = 'False'
			shot['end transition'] = 'False'
			shot['start transition duration'] = 0
			shot['end transition duration'] = 0
			shot['start transition type'] = 'None'
			shot['end transition type'] = 'None'

			## check if START has a transition by looking for '-1' value
			if child.getElementsByTagName('start')[0].firstChild.data == "-1":
				shot = getStartValue(child, shot)
			else: 
				shot['start'] = int(child.getElementsByTagName('start')[0].firstChild.data)

			## check if END has a transition by looking for '-1' value
			if child.getElementsByTagName('end')[0].firstChild.data == "-1":
				shot = getEndValue(child, shot)
			else: 
				shot['end'] = (int(child.getElementsByTagName('end')[0].firstChild.data) - 1)

			shot['duration'] = getDuration(shot['start'], shot['end'])
			
			shotList.append(shot)

	## sort the shotList by name
	shotList = sorted(shotList, key=itemgetter('name'))
	return shotList

##############################################
########### findSequence Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (1) sequenceList ###############
#### INFO: return list of sequences ##########
##############################################

def findSequences(sequenceList, trackChildren):

	for child in trackChildren:
	
		sequence = {}

		## if child is a sequence
		if child.tagName == "clipitem" and re.match('[s,S]{1}[q,Q]{1}\d{3}', child.getElementsByTagName('name')[0].firstChild.data):
			sequence['type'] = 'sequence'
			sequence['name'] = str(child.getElementsByTagName('name')[0].firstChild.data)
			sequence['start'] = int(child.getElementsByTagName('start')[0].firstChild.data)
			sequence['end'] = (int(child.getElementsByTagName('end')[0].firstChild.data) - 1)

			sequenceList.append(sequence)

	## sort the sequenceList by name
	sequenceList = sorted(sequenceList, key=itemgetter('name'))
	return sequenceList

##############################################
########## getStartValue Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (1) shot #######################
#### INFO: return shot with start transition #
##############################################

def getStartValue(child, shot):

	## get transitions start or end value
	startValue = int(child.previousSibling.getElementsByTagName('start')[0].firstChild.data)
	endValue = int(child.previousSibling.getElementsByTagName('end')[0].firstChild.data)
	transitionType = str(child.previousSibling.getElementsByTagName('effect')[0].getElementsByTagName('name')[0].firstChild.data)

	## set transition variables for shot
	shot['start'] = startValue
	shot['start transition'] = 'True'
	shot['start transition duration'] = endValue - startValue
	shot['start transition type'] = transitionType
	
	return shot

##############################################
############ getEndValue Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (1) shot #######################
#### INFO: return shot with end transition ###
##############################################

def getEndValue(child, shot):

	## get transitions start or end value
	startValue = int(child.nextSibling.getElementsByTagName('start')[0].firstChild.data)
	endValue = int(child.nextSibling.getElementsByTagName('end')[0].firstChild.data)
	transitionType = str(child.nextSibling.getElementsByTagName('effect')[0].getElementsByTagName('name')[0].firstChild.data)

	## set transition variables for shot
	shot['end'] = endValue - 1
	shot['end transition'] = 'True'
	shot['end transition duration'] = endValue - startValue
	shot['end transition type'] = transitionType
	
	return shot

##############################################
############ getDuration Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (1) duration ###################
#### INFO: return shot duration ##############
##############################################

def getDuration(start, end):

	## NOTE: The Frames start at 0 so you must +1 to each total to get an accurate duration
	duration = (int(end) - int(start)) + 1
	return duration

##############################################
############## setupXML Function #############
#### ARGUMENTS: (4) ##########################
#### RETURNS: (0) ############################
#### INFO: create the episode xml ############
##############################################

def setupXML(xmlPath, episodeName, episodeDuration, sequenceList, shotList):

	## create/overwrite previous compositing xml && write the first two lines of it
	xmlFile = open(xmlPath, 'w')
	xmlFile.write('<?xml version="1.0" encoding="utf-8"?>\n')
	xmlFile.write('<episode name="'+episodeName+'" duration="'+str(episodeDuration)+'" >\n')

	for i in range(0, len(sequenceList)):
		buildSequenceTag(xmlFile, sequenceList[i], shotList)

	xmlFile.write('</episode>')

##############################################
######### buildSequenceTag Function ##########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (0) ############################
#### INFO: build the sequence xml ############
##############################################

def buildSequenceTag(xmlFile, sequence, shotList):

	xmlFile.write('     <sequence name="'+sequence['name']+'" framein="'+str(sequence['start'])+'" frameout="'+str(sequence['end'])+'">\n')
	
	for i in range(0, len(shotList)):
		if sequence['name'] == shotList[i]['match']:
			buildShotTag(xmlFile, shotList[i])

	xmlFile.write('     </sequence>\n')

##############################################
########### buildShotTag Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0) ############################
#### INFO: build the shot xml ################
##############################################

def buildShotTag(xmlFile, shot):

		xmlFile.write('          <shot name="'+shot['name']+'" framein="'+str(shot['start'])+'" frameout="'+str(shot['end'])+'" duration="'+str(shot['duration'])+'" attachedto="'+shot['match']+'">\n')

		buildTransitionTag(xmlFile, shot)

		xmlFile.write('          </shot>\n')

##############################################
######## buildTransitionTag Function #########
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0) ############################
#### INFO: build the shot xml ################
##############################################

def buildTransitionTag(xmlFile, shot):

	## check if the shot has a starting transition
	if shot['start transition'] == 'True':
		xmlFile.write('               <starttransition type="'+shot['start transition type']+'" duration="'+str(shot['start transition duration'])+'" />\n')

	## check if the shot has an ending transition
	if shot['end transition'] == 'True':
		xmlFile.write('               <endtransition type="'+shot['end transition type']+'" duration="'+str(shot['end transition duration'])+'" />\n')

if __name__ == '__main__':
		try:
			logging.info(str(datetime.now()) + " Setup Started")
			main(*sys.argv)
			logging.info(str(datetime.now()) + " Setup Completed")
		except Exception, e:
			logging.exception(str(datetime.now()) + " There was an error running the script")
