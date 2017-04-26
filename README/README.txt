
------------------ AMI SCTIPTS ----------------------
----------- Moondog Animation Studio ----------------
------------ Created by: Erin Terre -----------------
--------- Last Update: 06 - 17 - 2016 ---------------

These python scripts are used with shotgun to run specfic program scripts. 

** IMPORTANT: CHECK THE LIB FOLDER FOR ALREADY CREATED WINDOWS REGISTRY FILES. EDIT THEM SO THE SCRIPT PATH MATCHES THE CURRENT SCRIPT LOCATIONS THEN DOUBLE CLICK THEM TO INSTALL THEM ON YOUR COMPUTER

** See the AMI_Setup.pdf file for a run down of each requirment needed to run the AMI Scripts.

Requirements:
	> Shotgun API installed
	> Python 2.7 installed
	> Python Environment Variable setup
	> Windows Registry for each script

Scripts: (* More information about each script can be found in the README file for the program script it runs)
	> CompositingAMIScript.py
		>> INFO: Runs the Autocompositor, generates the CompositingTasks.xml used by the Autocompositor, updates Shotgun data
		>> README location - AFXSCRIPTS\AUTOCOMPOSITING\README.txt
		>> Windows Registry Key Name: autocompositor
		>> Windows Registry Script Path: W:\\DEV\\PIPELINE\\SHOTGUN\\AMI_Scripts\\CompositingAMIScript.py\
		
		>> USAGE:
			>>> Mark Shots Comp task to 'Final - Ready to Render' or 'Preview - Ready to Render'
			>>> Click 'Run the Compositor' button (Located under 'More' in the Shots page)

	> SetupAMIScript.py
		>> INFO: Creates/Updates an Episodes shot and sequence information for a project
		>> README location - SHOTGUN\README\setup_README.txt
		>> Windows Registry Key Name: shotgunsetup
		>> Windows Registry Script Path: W:\\DEV\\PIPELINE\\SHOTGUN\\AMI_Scripts\\SetupAMIScript.py\

		>> USAGE:
			>>> Define 'Setup XML' in Project Info
			>>> Click 'Project Setup' button (Located under 'Project Actions' inside the project)

	> AnimaticAMIScript.py
		>> INFO: Runs the AnimaticSplitter, generates epName_cutdata.xml used by the AnimaticSplitter, uploads versions of each cut to Shotgun
		>> README location - AFXSCRIPTS\ANIMATICSPLITTER\README.txt
		>> Windows Registry Key Name: animatic
		>> Windows Registry Script Path: W:\\DEV\\PIPELINE\\SHOTGUN\\AMI_Scripts\\AnimaticAMIScript.py\

		>> USAGE:
			>>> Define Episode Duration, Animatic Name and Cut in, Cut out and Cut duration for each Shot
			>>> Mark Episodes Status to 'Animatic'
			>>> Click 'Run the Animatic Splitter' button (Located under 'More' in the Episodes page)

	> UpdateAMIScript.py
		>> INFO: Updates an Episodes XML based on data in Shotgun
		>> README location - SHOTGUN\README\update_README.txt
		>> Windows Registry Key Name: shotgunupdate
		>> Windows Registry Script Path: W:\\DEV\\PIPELINE\\SHOTGUN\\AMI_Scripts\\UpdateAMIScript.py\

		>> USAGE:
			>>> Mark Episodes you want to update with the status 'Update'
			>>> Click 'Update Episode XML's' button (Located under 'More' on the Episodes page)
