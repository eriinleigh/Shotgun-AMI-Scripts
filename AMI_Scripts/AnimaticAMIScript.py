
##############################################
############# Animatic AMI Script ############
########## Moondog Animation Studio ##########
################# Erin Terre #################
##############################################

from shotgun_api3 import Shotgun
from datetime import datetime
from xml.dom import minidom

import os
import re
import sys
import logging
import subprocess


## define the logger that will be used to log all errors
logging.basicConfig(level=logging.INFO, filename=r'W:\DEV\PIPELINE\AFXSCRIPTS\ANIMATICSPLITTER\splitlog.log')

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

	## get the triggered project information
	projectList = getProjectList(sg, logging, project)

	## set the config path
	configPath = projectList['shareDrive'] + r'\DEV\PIPELINE\AFXSCRIPTS\ConfigGeneral.xml'

	## get the episode that status is "anm"
	episodeList = getEpisodeList(sg, logging, projectList['projectID'])

	## for each episode ready for animatic split
	for i in range(0, len(episodeList)):

		## get the episode, episodeName and path to episodes data xml
		episode = episodeList[i]['code']
		episodeName = episode.split('_')
		episodeName = episodeName[1]

		episodeID = episodeList[i]['id']
		
		## get the version from the animatic path
		versionNum = episodeList[i]['sg_animatic_path']
		versionNum = versionNum.split('_')
		versionNum = versionNum[len(versionNum) - 1]
		versionNum = versionNum.split('.')
		versionNum = versionNum[0]

		xmlName = episodeName.lower() + "_cutdata.xml"
		xmlFolder = projectList['pathToProject'] + '\\05_PROD\\EPISODES\\' + episode + "\\02_ANIMATIC\\"
		xmlPath = xmlFolder + xmlName
	 
		## update the config file
		updateConfig(sg, logging, projectList, episodeList[i], configPath)

		## get the sequences from shotgun
		sequenceList = getSequenceList(sg, logging, episodeList[i]['id'])

		## check if cutting a sequence
		sequenceRecutNum = len(episodeList[i]['sg_shot_recut'])
		
		## check if cutting all shots or just a few
		shotRecutNum = len(episodeList[i]['sg_shot_recut'])

		recut = 'false'

		if shotRecutNum > 0 and sequenceRecutNum == 0:
			## get only the recut shots
			shotList = getShotRecutList(sg, logging, episodeList[i]['sg_shot_recut'])
			recut = 'true'
		
		elif shotRecutNum == 0 and sequenceRecutNum > 0:
			## get only the shots of the sequences specific
			shotList = getSequenceRecutList(sg, logging, episodeList[i]['sg_sequence_recut'], None)
			recut = 'true'
		
		elif shotRecutNum > 0 and sequenceRecutNum > 0:
			## get only the shots of the sequences specific
			shotList = getSequenceRecutList(sg, logging, episodeList[i]['sg_sequence_recut'], episodeList[i]['sg_shot_recut'])
			recut = 'true'
		else:
			## get all shots for the episode from shotgun
			shotList = getShotList(sg, logging, episodeList[i]['id'])
			recut = 'false'

		createCutXML(sg, logging, episodeList[i]['code'], episodeList[i]['sg_duration'], sequenceList, shotList, xmlPath)

		cmd = r'"C:\Program Files\Adobe\Adobe After Effects CC 2015\Support Files\AfterFX.exe" -r W:\DEV\PIPELINE\AFXSCRIPTS\ANIMATICSPLITTER\AnimaticSplitter.jsx'
		subprocess.call(cmd)

		logging.info("Splitting Completed")

		## update shotgun with the version
		updateShotgun(sg, logging, shotList, projectList['pathToProject'], projectList['projectID'], episode, episodeID, versionNum, episodeName.lower(), recut)

##############################################
############ updateShotgun Function ##########
#### ARGUMENTS: (9) ##########################
#### RETURNS: (0) ############################
#### INFO: uploads versions to shotgun #######
##############################################

def updateShotgun(sg, logging, shotList, pathToProject, projectID, episode, episodeID, versionNum, episodeName, recut):

	pathToEpisodes = pathToProject + r'\05_PROD\EPISODES'
	pathToAnimatics = pathToEpisodes + "\\" + episode + "\\02_ANIMATIC\\" + versionNum + "\\"

	for i in range(0, len(shotList)):
		if recut == 'true':
			animaticName = episodeName + '_' + str(shotList[i]['sg_sequence']['name']) + '_' + str(shotList[i]['code']) + '_ATK_' + str(versionNum) + '_recut'
		else:
			animaticName = episodeName + '_' + str(shotList[i]['sg_sequence']['name']) + '_' + str(shotList[i]['code']) + '_ATK_' + str(versionNum)

		pathToMov = pathToAnimatics + animaticName + '.mov'

		## find the shots animatic task id
		taskFilters = [
			{
				"filter_operator": "and",
				"filters": [
				[ "entity", "is", { "type": "Shot", "id": shotList[i]['id']} ],
				[ "content", "is", "Animatic"]
				]
			}
		]

		task = sg.find_one('Task', taskFilters)


		## set the versions data to be created
		versionData = { 'project': {'type': 'Project', 'id' : projectID},
				 'code': animaticName,
				 'description': 'AUTOSPLIT',
				 'sg_status_list': 'rev',
				 'entity': {'type': 'Shot', 'id': shotList[i]['id']},
				 'sg_task': {'type': 'Task', 'id': task['id']},
				 'frame_count': shotList[i]['sg_cut_duration'],
				 'sg_path_to_movie': pathToMov
		}

		print "Uploaded: " + pathToMov

		## create the version and upload the mov
		version = sg.create('Version', versionData)
		version = sg.upload('Version', version['id'], pathToMov, 'sg_uploaded_movie')

	## update the episode to active 
	episodeData = {'sg_status_list': 'act'}
	episodeUpdate = sg.update('Scene', episodeID, episodeData)

##############################################
############ createCutXML Function ###########
#### ARGUMENTS: (7) ##########################
#### RETURNS: (0) ############################
#### INFO: creates the xml for AFX ###########
##############################################

def createCutXML(sg, logging, episodeName, episodeDuration, sequenceList, shotList, xmlPath):

	## create/overwrite previous compositing xml && write the first two lines of it
	xmlFile = open(xmlPath, 'w')
	xmlFile.write('<?xml version="1.0" encoding="utf-8"?>\n')
	xmlFile.write('<episode name="'+episodeName+'" duration="'+str(episodeDuration)+'" >\n')

	## run the function to create the sequence tags
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
		if sequence['id'] == shotList[i]['sg_sequence']['id']:
			buildShotTag(xmlFile, shotList[i])

	xmlFile.write('     </sequence>\n')

##############################################
########### buildShotTag Function ############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0) ############################
#### INFO: build the shot xml ################
##############################################

def buildShotTag(xmlFile, shot):

		xmlFile.write('          <shot name="'+shot['code']+'" framein="'+str(shot['sg_cut_in'])+'" frameout="'+str(shot['sg_cut_out'])+'" duration="'+str(shot['sg_cut_duration'])+'" attachedto="'+shot['sg_sequence']['name']+'">\n')

		buildTransitionTag(xmlFile, shot)

		xmlFile.write('          </shot>\n')

##############################################
######### buildTransitionTag Function ########
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0) ############################
#### INFO: build the transition xml ##########
##############################################

def buildTransitionTag(xmlFile, shot):

	if shot['sg_start_transition_type'] == None:
		return

	if shot['sg_end_transition_type'] == None:
		return

	## check if the shot has a starting transition
	if shot['sg_start_transition_type'].lower() != 'none':
		xmlFile.write('               <starttransition type="'+shot['sg_start_transition_type']+'" duration="'+str(shot['sg_start_transition_duration'])+'" />\n')

	## check if the shot has an ending transition
	if shot['sg_end_transition_type'].lower() != 'none':
		xmlFile.write('               <endtransition type="'+shot['sg_end_transition_type']+'" duration="'+str(shot['sg_end_transition_duration'])+'" />\n')

##############################################
############ updateConfig Function ###########
#### ARGUMENTS: (5) ##########################
#### RETURNS: (0) ############################
#### INFO: update the projects config ########
##############################################

def updateConfig(sg, logging, projectList, episodeList, configPath):

	## update config xml with project name, episode name && animatic name
	fileData = None
	
	## create the values for the project, episode and animatic tags
	newProjectXML = "<project value=" + '"' + projectList['projectNameXML'] + '"' + " />"
	newProjectXML = newProjectXML.replace("\\\\", "\\\\\\\\")

	newEpisodeXML = "<episode value=" + '"' + episodeList['code'] + '"' + " />"
	newAnimaticXML = "<animatic value=" + '"' + episodeList['sg_animatic_path'] + '"' + " />"

	config = open(configPath, 'r')
	fileData = config.read()

	## using regular expressions replace the project line, episode line && animatic line
	fileData = re.sub('<project value="?.*', newProjectXML, fileData)
	fileData = re.sub('<episode value="?.*', newEpisodeXML, fileData)
	fileData = re.sub('<animatic value="?.*', newAnimaticXML, fileData)

	config = open(configPath, 'w')
	config.write(fileData)

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

	## find shots based on episodeID
	filters = [['sg_scene', 'is', { "type": "Scene", "id": episodeID }]]
	shotList = sg.find('Shot', filters, fields=['code', 'sg_cut_in', 'sg_cut_out', 'sg_cut_duration', 'sg_sequence', 'sg_start_transition_type', 'sg_start_transition_duration', 'sg_end_transition_duration', 'sg_end_transition_type'])

	return shotList

##############################################
######### getShotRecutList Function ##########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) shotRecutList ##############
#### INFO: get shot recut list from shotgun ##
##############################################

def getShotRecutList(sg, logging, shotRecuts):

	shotRecutList = []

	## find each shot by shotID's in the episode field 'Shot Recut' && return a list of the shots
	for i in range(0, len(shotRecuts)):
		filters = [[ 'id', 'is', shotRecuts[i]['id']]]
		shot = sg.find_one('Shot', filters, fields=['code', 'sg_cut_in', 'sg_cut_out', 'sg_cut_duration', 'sg_sequence', 'sg_start_transition_type', 'sg_start_transition_duration', 'sg_end_transition_duration', 'sg_end_transition_type'])
		shotRecutList.append(shot)

	return shotRecutList

##############################################
######## getSequenceRecutList Function #######
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) sequenceRecutList ##########
#### INFO: get sequence recuts from shotgun ##
##############################################

def getSequenceRecutList(sg, logging, sequenceRecuts, shotRecuts):

	sequenceRecutList = []

	## if there are shot recuts then run getShotRecutList()
	if shotRecuts != None:
		sequenceRecutList = getShotRecutList(sg, logging, shotRecuts)

	## for each item in episode field 'Sequence Recut' find the sequences by their ID
	for i in range(0, len(sequenceRecuts)):
		filters = [[ 'sg_sequence', 'is', { "type": "Sequence", "id": sequenceRecuts[i]['id']}]]
		sequenceList = sg.find('Shot', filters, fields=['code', 'sg_cut_in', 'sg_cut_out', 'sg_cut_duration', 'sg_sequence', 'sg_start_transition_type', 'sg_start_transition_duration', 'sg_end_transition_duration', 'sg_end_transition_type'])
		
		## if there are shots already added to sequenceRecutList
		## compare each item in sequenceList and do not add duplicates
		if len(sequenceRecutList) > 0:
			for j in range(0, len(sequenceList)):
				if sequenceList[j] not in sequenceRecutList:
					sequenceRecutList.append(sequenceList[j])
		else: 
			for h in range(0, len(sequenceList)):
				sequenceRecutList.append(sequenceList[h])

	return sequenceRecutList


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
	projectList['shareDrive'] = project['sg_share_drive_path']

	## check if clientName was given && if clientName is blank set both to only projectName
	if project['sg_client_name'] != None:
		projectList['projectNameXML'] = project['sg_client_name'] + "\\\\" + projectName
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + project['sg_client_name'] + "\\" + projectName
	else:
		projectList['projectNameXML'] = projectName
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + projectName

	return projectList

##############################################
########## getEpisodeList Function ###########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) episodeList ################
#### INFO: gets all episode data #############
##############################################

def getEpisodeList(sg, logging, projectID):

	## set a filter that will limit results by projectID and 'anm' status
	filters = [
		{
			"filter_operator": "and",
			"filters": [
			[ "project", "is", { "type": "Project", "id": projectID } ],
			[ "sg_status_list", "is", "anm"]
			]
		}
	]

	episodeList = sg.find('Scene', filters, fields=['code', 'sg_animatic_path', 'sg_duration', 'sg_shot_recut', 'sg_sequence_recut'])

	return episodeList


if __name__ == '__main__':
		try:
			logging.info(str(datetime.now()) + " Animatic Started")
			main(*sys.argv)
			logging.info(str(datetime.now()) + " Animatic Completed")
		except Exception, e:
			logging.exception(str(datetime.now()) + " There was an error running the script")
