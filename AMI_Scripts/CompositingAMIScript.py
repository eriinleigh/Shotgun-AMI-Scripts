
##############################################
########### Compositing AMI Script ###########
########## Moondog Animation Studio ##########
################# Erin Terre #################
##############################################

from shotgun_api3 import Shotgun
from datetime import datetime

import os
import re
import sys
import logging
import subprocess

## define the logger that will be used to log all errors
logging.basicConfig(level=logging.INFO, filename=r'W:\DEV\PIPELINE\AFXSCRIPTS\AUTOCOMPOSITING\complog.log')

##############################################
############### main Function ################
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0) ############################
#### INFO: the foundation of the script ######
##############################################

def main(script, project):

	## get shotgun script information && create the shotgun instance
	SERVER_PATH = "https://moondog.shotgunstudio.com"
	SCRIPT_NAME = 'Automatic_Script'
	SCRIPT_KEY = '1e619c54443fd7e8ab23fb25dbea866fdaf5d3eb3092c35364b08a48b987fb40'

	sg = Shotgun(SERVER_PATH, SCRIPT_NAME, SCRIPT_KEY)

	projectList = getProjectList(sg, logging, project)

	logging.info(str(datetime.now()) + " Building the XML")
	variablesList = setup(sg, logging, projectList)

	logging.info(str(datetime.now()) + " Running the Compositor")
	cmd = r'"C:\Program Files\Adobe\Adobe After Effects CC 2015\Support Files\AfterFX.exe" -r W:\DEV\PIPELINE\AFXSCRIPTS\AUTOCOMPOSITING\Autocompositor.jsx'
	subprocess.call(cmd)

	logging.info(str(datetime.now()) + " Updating Shotgun")
	updateShotgun(sg, logging, variablesList, projectList['projectID'], projectList['pathToProject'])

##############################################
############## setup Function ################
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) variablesList ##############
#### INFO: gets all variables && builds XML ##
##############################################

def setup(sg, logging, projectList):

	## update config xml with new project name
	fileData = None
	newProjectXML = "<project value=" + '"' + projectList['projectNameXML'] + '"' + " />"
	newProjectXML = newProjectXML.replace("\\\\", "\\\\\\\\")
	
	configPath = "W:\\DEV\\PIPELINE\\AFXSCRIPTS\\ConfigGeneral.xml"
	config = open(configPath, 'r')
	fileData = config.read()

	## using regular expressions replace the project line in config with the new project name
	fileData = re.sub('<project value="?.*', newProjectXML, fileData)

	config = open(configPath, 'w')
	config.write(fileData)

	## run getTaskList to get the list of ready tasks
	taskList = getTaskList(sg, logging, projectList['projectID'])

	## setup the xmlFile
	xmlPath = projectList['pathToProject'] + r'\07_COMPOSITING\CompositingTasks.xml'

	## create/overwrite previous compositing xml && write the first two lines of it
	xmlFile = open(xmlPath, 'w')
	xmlFile.write('<?xml version="1.0" encoding="utf-8"?>\n')
	xmlFile.write('<compositingTasks>\n')

	## define array to store all variable information
	variablesList = []

	## for each task get the variables
	for i in range(0, len(taskList)):
		
		## run getVariables to get all variables needed for script && add them to the variablesList array
		variables = getVariables(sg, logging, taskList[i]['id'], taskList[i]['sg_status_list'])
		variablesList.append(variables)

		## update all 'Comp' tasks to sent to render
		sg.update('Task', taskList[i]['id'], {'sg_status_list' : 's2rend'})
		
		## create array of all xml items && run setupXML
		xmlList = [projectList['projectNameXML'], variables['episode'], variables['sequenceName'], variables['shotName'], str(variables['shotDuration']), variables['renderType'], variables['masterComp']]
		buildXML(xmlFile, xmlList)

	## add the last line of the compositing xml after ALL tasks have been added
	xmlFile.write('</compositingTasks>\n')

	return variablesList

##############################################
########## updateShotgun Function ############
#### ARGUMENTS: (5) ##########################
#### RETURNS: (0) ############################
#### INFO: update all affected shotgun info ##
##############################################

def updateShotgun(sg, logging, variablesList, projectID, pathToProject):
	
	pathToEpisodes = pathToProject + r'\05_PROD\EPISODES'
	
	for i in range(0, len(variablesList)):

		## set shot folder name for shot
		shotFolder = variablesList[i]['sequenceName'] + '_' + variablesList[i]['shotName']

		## update compositing version && set the version folder name
		if variablesList[i]['compositingVersion'] == None:
			variablesList[i]['compositingVersion'] = 1
		else:
			variablesList[i]['compositingVersion'] = variablesList[i]['compositingVersion'] + 1
		
		versionFolder = 'v' + str(variablesList[i]['compositingVersion']).zfill(2)

		## set episode name
		episodeName = variablesList[i]['episode'].split('_')
		episodeName = episodeName[1]

		## set versionName
		if variablesList[i]['renderType'] == 'preview':
			versionName = episodeName.lower() + '_' + shotFolder + '_' + variablesList[i]['renderType'] + '_' + versionFolder
		else:
			versionName = episodeName.lower() + '_' + shotFolder + '_fullres_' + versionFolder

		## set pathToMov
		pathToMov = pathToEpisodes + "\\" + variablesList[i]['episode'] + "\\05_COMPOSITING\\FINAL_IMAGES\\" + shotFolder + "\\" + versionFolder + "\\" + versionName + ".mov"

		if os.path.isfile(pathToMov) == False:
			logging.info("PathToMov does not exist: " + pathToMov)
			return

		## create the version for the shot && upload the desired MOV to the created version
		versionData = { 'project': {'type': 'Project', 'id' : projectID},
				 'code': versionName,
				 'description': variablesList[i]['description'],
				 'sg_status_list': 'rev',
				 'entity': {'type': 'Shot', 'id': variablesList[i]['shotID']},
				 'sg_task': {'type': 'Task', 'id': variablesList[i]['taskID']},
				 'frame_count': variablesList[i]['shotDuration'],
				 'sg_path_to_movie': pathToMov
		}

		version = sg.create('Version', versionData)
		version = sg.upload('Version', version['id'], pathToMov, 'sg_uploaded_movie')

		## increment the compositing version && update task status to pending review
		sg.update('Shot', variablesList[i]['shotID'], {'sg_compositing_version' : variablesList[i]['compositingVersion']})
		sg.update('Task', variablesList[i]['taskID'], {'sg_status_list' : 'rev'})

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
	project = sg.find_one('Project', filters, fields=['sg_client_name', 'sg_share_drive_path'])
	
	projectList['projectID'] = projectID

	## check if clientName was given && if clientName is blank set both to only projectName
	if project['sg_client_name'] != None:
		projectList['projectNameXML'] = project['sg_client_name'] + "\\\\" + projectName
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + project['sg_client_name'] + "\\" + projectName
	else:
		projectList['projectNameXML'] = projectName
		projectList['pathToProject'] = project['sg_share_drive_path'] + "\\" + projectName

	return projectList

##############################################
########### getVariables Function ############
#### ARGUMENTS: (4) ##########################
#### RETURNS: (1) variables ##################
#### INFO: gets all variables ################
##############################################

def getVariables(sg, logging, taskID, taskStatus):

	variables = {}

	shotList = getShotList(sg, logging, taskID)

	## set our renderType variable based on the tasks status
	if taskStatus == 'finren':
		variables['renderType'] = 'final'
		sg.update('Shot', shotList['id'], {'sg_render_type': 'Final'})
		variables['description'] = 'Autocomposited :: FINAL'
	else: 
		variables['renderType'] = 'preview'
		sg.update('Shot', shotList['id'], {'sg_render_type': 'Preview'})
		variables['description'] = 'Autocomposited :: PREVIEW'


	## run getSequenceList && return sequenceList
	sequenceList = getSequenceList(sg, logging, shotList['id'])
	
	## run getEpisodeList && return episodeList
	episodeList = getEpisodeList(sg, logging, shotList['id'])

	## set all the variables in a dictionary
	variables['taskID'] = taskID
	variables['shotID'] = shotList['id']
	variables['shotName'] = shotList['code'].lower()
	variables['shotDuration'] = shotList['sg_cut_duration']
	variables['compositingVersion'] = shotList['sg_compositing_version']
	variables['sequenceName'] = sequenceList['code'].lower()
	variables['episode'] = episodeList['code']

	if '.' not in sequenceList['sg_master_comp']:
		variables['masterComp'] = sequenceList['sg_master_comp'] + '.aep'
	else:
		variables['masterComp'] = sequenceList['sg_master_comp']

	return variables

##############################################
########## getSequenceList Function ##########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) sequenceList ###############
#### INFO: get sequence data based on shotID #
##############################################

def getSequenceList(sg, logging, shotID):

	## set a filter that will limit results by shotID
	shotfilter = [
		{
			"filter_operator": "any",
			"filters": [
			[ "shots", "is", { "type": "Shot", "id": shotID } ]
			]
		}
	]

	## find the sequence with the shotID
	sequenceList = sg.find_one('Sequence', shotfilter, fields=['code', 'sg_master_comp'])

	## if sequenceDetails is 'None' then the shot is not linked to a sequence
	## log the error && quit function
	if sequenceList == None:
		logging.info("There is no SEQUENCE associated with this SHOT")
		return

	## if the sequence master comp is 'None' then
	## log the error && quit function
	if (sequenceList['sg_master_comp'] == None):
		logging.info("There is no MASTER COMP defined for this SEQUENCE")
		return

	return sequenceList

##############################################
########## getEpisodeList Function ###########
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) episodeList ################
#### INFO: get episode data based on shotID ##
##############################################

def getEpisodeList(sg, logging, shotID):

	## set a filter that will limit results by shotID
	shotfilter = [
		{
			"filter_operator": "any",
			"filters": [
			[ "shots", "is", { "type": "Shot", "id": shotID } ]
			]
		}
	]

	## find the episode with the shotID
	## -- NOTE THAT EPISODE IS LABELED SCENE IN SHOTGUN -- ##
	episodeList = sg.find_one('Scene', shotfilter, fields=['code'])

	## if episodeDetails is 'None' then the episode is not linked to a shot
	## log the error && quit function
	if episodeList == None:
		logging.info("There is no EPISODE associated with this SHOT")
		return

	return episodeList

##############################################
############ getShotList Function ############
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) shotList ###################
#### INFO: get shot data based on taskID #####
##############################################

def getShotList(sg, logging, taskID):

	## set a filter that will limit results by taskID
	idfilter = [
		{
			"filter_operator": "any",
			"filters": [
			[ "tasks", "is", { "type": "Task", "id": taskID } ]
			]
		}
	]

	## find the shot with the taskID
	shotList = sg.find_one('Shot', idfilter, fields=['code', 'sg_cut_duration', 'sg_compositing_version'])

	## if shotList is 'None' then the task is not linked to a shot
	## log the error && quit function
	if shotList == None:
		logging.info("There is no SHOT associated with this TASK")
		return

	return shotList

##############################################
############ getTaskList Function ############
#### ARGUMENTS: (3) ##########################
#### RETURNS: (1) taskList ###################
#### INFO: get task data based on projectID ##
##############################################

def getTaskList(sg, logging, projectID):
	
	## set the conditions we are looking for 
	## (status is preren, name is content, project is projectID, status is finren)
	condition1 = {'path' : "sg_status_list" , 'relation' : "is" , 'values' : ["preren"]}
	condition2 = {'path' : "content" , 'relation' : "is" , 'values' : ["Comp"]}
	condition3 = {'path' : "project" , 'relation' : "is" , 'values' : [{'type': 'Project', 'id': projectID}]}
	condition4 = {'path' : "sg_status_list" , 'relation' : "is" , 'values' : ["finren"]}
	
	## set the group of conditions && 'and' means all must be true
	conditionGroup1 = { 'logical_operator' : 'and' , 'conditions' : [condition1, condition2, condition3] }
	conditionGroup2 = { 'logical_operator' : 'and' , 'conditions' : [condition4, condition2, condition3] }

	## set the filter to look for one group of the other
	filters = { 'logical_operator' : 'or' , 'conditions' : [ conditionGroup1, conditionGroup2 ] }

	## find the task based on the filters
	taskList = sg.find('Task', filters, fields=['content', 'project', 'sg_status_list'])

	## if taskList is 'None' then there are no tasks ready for compositing
	## log the error && quit function
	if taskList == None:
		logging.info("There are no TASKS ready for COMP in this project")
		return

	return taskList

##############################################
############## buildXML Function #############
#### ARGUMENTS: (2) ##########################
#### RETURNS: (0)  ###########################
#### INFO: write a comp task in the xml ######
##############################################

def buildXML(xmlFile, xmlList):

	xmlFile.write('     <compositingTask>\n')
	xmlFile.write('          <project value="'+xmlList[0]+'" />\n')
	xmlFile.write('          <episode value="'+xmlList[1]+'" />\n')
	xmlFile.write('          <sequence value="'+xmlList[2]+'" />\n')
	xmlFile.write('          <shot value="'+xmlList[3]+'" />\n')
	xmlFile.write('          <frames value="'+xmlList[4]+'" />\n')
	xmlFile.write('          <renderType value="'+xmlList[5]+'" />\n')
	xmlFile.write('          <masterComp value="'+xmlList[6]+'" />\n')
	xmlFile.write('     </compositingTask>\n')


if __name__ == '__main__':
		try:
			logging.info(str(datetime.now()) + " Compositing Started")
			main(*sys.argv)
			logging.info(str(datetime.now()) + " Compositing Completed")
		except Exception, e:
			logging.exception(str(datetime.now()) + " There was an error running the script")