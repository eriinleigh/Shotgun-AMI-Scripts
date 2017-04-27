
##############################################
############## Update AMI Script #############
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
logging.basicConfig(level=logging.INFO, filename=r'W:\DEV\PIPELINE\SHOTGUN\LOGS\updatelog.log')

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

	## get list of episodes to update
	episodeList = getEpisodeList(sg, logging, projectList['projectID'])

	## for each episode in episode list
	## set its path to XML && get shotList and sequenceList
	for i in range(0, len(episodeList)):

		## get the full episode name, episodeID, && duration
		episodeName = episodeList[i]['code']
		episodeID = episodeList[i]['id']
		episodeDuration = episodeList[i]['sg_duration']

		## get the episode, xmlName, xmlFolder and path for the episode
		episode = episodeName.split('_')
		episode = episode[1]
		xmlName = episode.lower() + "_shotdata.xml"
		xmlFolder = projectList['pathToProject'] + '\\05_PROD\\EPISODES\\' + episodeName + "\\99_PIPELINE\\"
		xmlPath = xmlFolder + xmlName

		## get the sequences and shot info
		sequenceList = getSequenceList(sg, logging, episodeID)
		shotList = getShotList(sg, logging, episodeID)

		## update the XML
		updateXML(xmlPath, episodeName, episodeDuration, sequenceList, shotList)

		## update the episode to active 
		episodeData = {'sg_status_list': 'act'}
		episodeUpdate = sg.update('Scene', episodeID, episodeData)

##############################################
########## getEpisodeList Function ###########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) episodeList ################
#### INFO: gets all episode data #############
##############################################

def getEpisodeList(sg, logging, projectID):

	## set a filter that will limit results by projectID and 'update' status
	filters = [
		{
			"filter_operator": "and",
			"filters": [
			[ "project", "is", { "type": "Project", "id": projectID } ],
			[ "sg_status_list", "is", "update"]
			]
		}
	]

	episodeList = sg.find('Scene', filters, fields=['code', 'sg_duration'])

	return episodeList

##############################################
########## getSequenceList Function ##########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) sequenceList ###############
#### INFO: get sequence list from shotgun ####
##############################################

def getSequenceList(sg, logging, episodeID):

	## find sequences based on episodeID
	filters = [['sg_episode', 'is', { "type": "Scene", "id": episodeID }]]
	sequenceList = sg.find('Sequence', filters, fields=['code'])

	return sequenceList

##############################################
############ getShotList Function ############
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) shotList ###################
#### INFO: get shot list from shotgun ########
##############################################

def getShotList(sg, logging, episodeID):

	shotList = []

	## find shots based on episodeID
	filters = [['sg_scene', 'is', { "type": "Scene", "id": episodeID }]]
	shotInfo = sg.find('Shot', filters, fields=['code', 'sg_cut_in', 'sg_cut_out', 'sg_cut_duration', 'sg_sequence', 'sg_start_transition_type', 'sg_start_transition_duration', 'sg_end_transition_duration', 'sg_end_transition_type'])

	## for each shot set any missing variables to undefined && append the shot to shotList
	for i in range(0, len(shotInfo)):
		shot = {}

		shot['name'] = shotInfo[i]['code']

		## check if the shot has a cut in && set the variables
		if shotInfo[i]['sg_cut_in'] == None:
			shot['start'] = 'Undefined'
		else:
			shot['start'] = shotInfo[i]['sg_cut_in']

		## check if the shot has a cut out && set the variables
		if shotInfo[i]['sg_cut_out'] == None:
			shot['end'] = 'Undefined'
		else:
			shot['end'] = shotInfo[i]['sg_cut_out']

		## check if the shot has a cut duration && set the variables
		if shotInfo[i]['sg_cut_duration'] == None:
			shot['duration'] = 'Undefined'
		else:
			shot['duration'] = shotInfo[i]['sg_cut_duration']

		## check if the shot is attached to a sequence && set the variables
		if shotInfo[i]['sg_sequence'] == None:
			shot['match'] = 'Undefined'
		else:
			shot['match'] = shotInfo[i]['sg_sequence']['name']

		## check if the shot has a start transition && set the variables
		if shotInfo[i]['sg_start_transition_type'] == None:
			shot['start transition'] = 'False'
			shot['start transition duration'] = 0
			shot['start transition type'] = 'None'

		elif shotInfo[i]['sg_start_transition_type'] == 'None':
			shot['start transition'] = 'False'
			shot['start transition duration'] = 0
			shot['start transition type'] = 'None'

		else:
			shot['start transition'] = 'True'
			shot['start transition duration'] = shotInfo[i]['sg_start_transition_duration']
			shot['start transition type'] = shotInfo[i]['sg_start_transition_type']
		
		## check if the shot has an end transition && set the variables
		if shotInfo[i]['sg_end_transition_type'] == None:
			shot['end transition'] = 'False'
			shot['end transition duration'] = 0
			shot['end transition type'] = 'None'

		elif shotInfo[i]['sg_end_transition_type'] == 'None':
			shot['end transition'] = 'False'
			shot['end transition duration'] = 0
			shot['end transition type'] = 'None'

		else:
			shot['end transition'] = 'True'
			shot['end transition duration'] = shotInfo[i]['sg_start_transition_duration']
			shot['end transition type'] = shotInfo[i]['sg_start_transition_type']

		shotList.append(shot)

	return shotList

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

	## check if clientName was given && if clientName is blank set both to only projectName
	if project['sg_client_name'] != None:
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + project['sg_client_name'] + "\\" + projectName
	else:
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + projectName

	return projectList


##############################################
############# updateXML Function #############
#### ARGUMENTS: (4) ##########################
#### RETURNS: (0) ############################
#### INFO: update the episode xml ############
##############################################

def updateXML(xmlPath, episodeName, episodeDuration, sequenceList, shotList):

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

	xmlFile.write('     <sequence name="'+sequence['code']+'">\n')
	
	for i in range(0, len(shotList)):
		if sequence['code'] == shotList[i]['match']:
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
			logging.info(str(datetime.now()) + " Update Started")
			main(*sys.argv)
			logging.info(str(datetime.now()) + " Update Completed")
		except Exception, e:
			logging.exception(str(datetime.now()) + " There was an error running the script")
