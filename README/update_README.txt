
---------------- UPDATE SHOTGUN ---------------------
----------- Moondog Animation Studio ----------------
------------ Created by: Erin Terre -----------------
--------- Last Update: 06 - 17 - 2016 ---------------

This script automatically updates a Projects Episode XML based on data in Shotgun. This includes the Episode, Sequences and Shots.

SETUP:
	> In Shotgun
		>> Set Client Name if there is one (Located in project info) 
			**THIS VARIABLE WILL MAKE THE SCRIPTS LOOK FOR THE PROJECT FOLDER INSIDE THE CLIENTS FOLDER ON THE SHARE DRIVE**
		>> Set Share Drive Path (Located in project info)
		>> Mark Episodes to update with status 'Update'

TYPICAL USAGE: 
	> Mark Episodes you want to update with the status 'Update'
	> Click 'Update Episode XML's' button (Located under 'More' on the Episodes page)

Required Files: 
	> updatelog.log - logs the scripts process and any errors encountered. Look here if the script does not run correctly
	> UpdateAMIScript.py - script triggered in shotgun that reads an XML, generates a simplified version and then creates/updates information in Shotgun

Requirements: 
	> Windows Operating System
	> All project paths set correctly

TROUBLESHOOTING:
	> Check the updatelog.log file for any errors in UpdateAMIScript.py
	> Confirm EPISODENAME/99_PIPELINE has been created
	> Confirm Windows Registry has been set correctly
	> Confirm Shotgun Script Name, Server and Key is accurate in UpdateAMIScript.py

REPORTED BUGS: