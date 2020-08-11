import sys
#add rootpath for shared_modules
rootpath = 'C:\VENLAB data\shared_modules'
sys.path.append(rootpath)

import viz
import numpy as np
import vizmat
import vizact
import viztask
import pandas as pd
import time
import matplotlib.pyplot as plt
import os

class TrialManager(viz.EventClass):
	def __init__(self, demographics, mydriver, mywheel, TrackData, TotalTrials, comms, eyetrackingflag, cave, TargetData, Practice):
		viz.EventClass.__init__(self)

		"""
		Class that organises trial execution, data recording, and playback

		"""

		#TODO: code should handle travelling opposite way around the oval
		#TODO: adjust code so that it handles on-the-fly track reorganisation.		

		"""
		EXPERIMENT DESIGN

		Before completing the experiment proper the participant will complete a practice experiment, consisting of one trial per condition, then two manual-to-AUTOMATION handovers of attract vs. avoid, where the playback is the stock trials.
		
		The pre-experiment practice will reduce the likelihood of large errors, and mean that we can use the entire Bank period in experiment proper for Playback.
		
		In the Experiment Proper participants will initially experiences a continous period of manual driving. The 'Bank' period will consist of two manual trials per condition, which are recorded for playback.
		
		After the Bank period the driver then experiences transitions to AUTOMATION and manual control. They experience X trials per condition, where a 'trial' consists of matched active control and passive playback periods.
		
		In addition, they will view X playback 'Stock' trials for each condition, these are the same trials each time to give a controlled indication of how gaze behaviour changes across the experiment.

		If a manual trial contains a large error that is deemed obvious and uncontrolled, the playback version will be replaced by a backup playback trial (different to the Stock playback trial). The experiment continues until we have a sufficient number of matched trials.

		"""

		self.DEBUG = False #flag for switching debugging text on / off

		self.EXP_BLOCK = demographics[2]
		self.eyetrike_filename = "Trout_" + str(demographics[0]) + "_" + str(self.EXP_BLOCK)
		

		#variables for controlling position and wheel
		self.view = cave
		#self.view = viz.MainView #will need mainview for position and orientation
		self.driver = mydriver #will need driver for wheelpos.		
		self.wheel = mywheel #class for wheel AUTOMATION

		self.PRACTICEMODE = Practice #Bool assessing whether in practice mode or not

		#useful track constants for monitoring vehicle position and organising sections.
		self.midline = TrackData[0]
		self.tracksize = len(self.midline)
		self.trackorigin = TrackData[1]
		self.SectionBreaks = TrackData[2]
		trackparams = TrackData[3]
		self.radius = trackparams[0]
		self.straightlength = trackparams[1] 
		self.interplength = trackparams[2]
		self.sectionsize = trackparams[3]	
		self.interp_proportion = trackparams[4]	
		
		self.Integral_On = False

		#move view to start.
		start = self.midline[0,:]
		self.view.setPosition(start[0],0.0,start[1])
		
		#trial info
		self.trialn = 0
		self.triallength = trackparams[3] * 3 # Straight, Bend, Straight #length of trial in midline pts. 

		#bank variables
		self.BankTrials = 1 
		self.BANKMODE = True
		
		#parameters to organise obstacle trialtype
		self.targets = TargetData[0]
		self.targetcentres = TargetData[1]
		self.targetpositions = TargetData[2]
		self.targetdeflections = TargetData[3]
		self.obstaclecolour = 0 #0=blue, attract. 1=red, avoid.
		self.obstacleoffset = 0 #metres from the centre.
		self.FACTOR_obstaclecolour = [0,1] #attract, avoid
		self.FACTOR_obstacleoffset = [.25, .75] #narrow, wide		

		#trial order.
		self.TrialsPerCondition = TotalTrials #per condition. A Trial consists of matched Manual and Playback periods.								
		self.NCndts = len(self.FACTOR_obstaclecolour) * len(self.FACTOR_obstacleoffset)	
		self.ConditionList = range(self.NCndts) 

		#automatically generate factor lists so you can adjust levels using the FACTOR variables
		self.ConditionList_obstaclecolour = np.repeat(self.FACTOR_obstaclecolour, len(self.FACTOR_obstacleoffset)	)
		self.ConditionList_obstacleoffset = np.tile(self.FACTOR_obstacleoffset, len(self.FACTOR_obstaclecolour)	)

		print (self.ConditionList_obstaclecolour)
		print (self.ConditionList_obstacleoffset)

		####SAVE CSV of TargetData for Analysis####
		self.SaveTargetData()

		# ##0 = Attract_Narrow, 1=Attract_Wide, 2=Avoid_Narrow, 3=Avoid_Wide
		# self.attract = [0,1]
		# self.avoid = [2,3]
		# self.narrow = [0,2]		
		# self.wide = [1,3]

		#NOTE on Conditions. The amount of additional (unplanned) manual trials needed equate to len(BankTrialOrder) + len(self.StockTrial) - 2 (for the last one and the first playback after Bank).


		self.TotalMatchedTrials = self.NCndts * (self.TrialsPerCondition/2) #matched trials is half of the manual trials.
		self.TotalManualTrials = self.NCndts * self.TrialsPerCondition  #total active manual trials that are in the experiment design
		self.BankTrialOrder = [] #have two trials of each condition.	
		self.ManualTrialOrder = [] #randomised order of manual trials
		self.PlaybackTrialOrder = [] #randomised order of playback trials
		self.StockTrial = [] #randomised order of Stock playback conditions
		self.PlaybackStock_SequenceIndex = [] #sequence order of how Stock and Real playback trials are interleaved.
		self.ManualRecord = np.zeros(self.NCndts) #The record arrays are incremented everytime a valid trial of the corresponding condition is finished
		self.PlaybackRecord = np.zeros(self.NCndts) #This also serves as a record for complete 'Matched' trials, since playback is only recorded for a participant active trial.
		self.StockRecord = np.zeros(self.NCndts)
		self.BackupCount = 0 #number of backup trials played.		
		self.ErrorCount =0
		self.OrderTrials()
	
		#new variables for saving individual sections and dynamically playing them back.
		self.sectionorder = 0 #order of section (regardless of manual/auto/interp) in overall sequence
		self.playback_i = 0 #number of playback periods played
		self.man_i = 0 #number of manual periods played
		#self.throwaway_i = 0 #index for throwaway trials.
		self.playbacksequence_i = 0
		self.stock_i = 0 #number of stock periods played				
		self.interpcount = 0 #order of interp period in overall sequence	
		self.currenttrialtype= 0 #index showing which manual period the sections are yoked to.		
		self.currentmanualfilename = ""		
		self.currentplaybackfilename = ""
		self.currentmanualconditioncount = 0 
		
		#############
		#track variables for monitoring.
		#indexes that keep track of trial
		self.sectionindex = 0 #index of each playback/manual/interpolation period.
		self.trialendindex = 0 #midline index that signals end of manual period. gets recalculated for each manual period.			
		self.lastmidlineindex = 0 #needed to capture when there are large changes in track index (which signals a new lap)		
		
		#to keep track of crossover of mid-point indexes.
		self.startlap = 1 #lap that manual period starts on
		self.currentlap = 1 #current lap of the vehicle position
		self.endlap = 1	#lap that manual period should end on
		#############				
		# 					
		#data saving
		
		self.datacolumns = ['ID', 'Age', 'Block', 'Gender','Vision','LicenseMonths', 'frameidx','trackindex','trialn','currtime','midlinepts','SWA','posx','posz','yaw','yaw_d','yawrate','steeringbias','autoflag', 'sectiontype', 'sectionorder','sectioncount','trialtype','obstaclecolour','obstacleoffset'] #variables
		self.demographics = demographics #constants
		#print "Demographics"
		print(self.demographics)
		self.trialdata = None	
		
		#Flags for controlling modes: Manual/Automation, and Interpolation.
		self.UPDATELOOP = False	#flag for whether the Update Position runs, since sometimes the timer iterates before other functions are finished.
		self.AUTOMATION = False #flag for AUTOMATION/manual
		self.INTERP_PERIOD = False #flag for interpolation period.
		self.QUITFLAG = False #tells main vizard script whether to quit.
				
		#playback variables
		self.FLIP_PLAYBACK = False #flag whether to flip playback (mirror yaw and position around the track origin).
		self.playbackindex = 0 #could use section index for this? 		
		self.playbacklength = 0 
		self.playbackdata = "" #filename.

		#PD controller variables
		self.speed = self.driver.getSpeed()
		self.error_i = 0
		self.max_error = 0
		self.min_error = 0
		self.error_T_minus_1 = 0
		self.yaw_T_minus_1 = 0
		self.YR_T_minus_1 = 0
		self.yawrate_inseconds = 0 #turnrate in driver
		self.yawrate_inframes = 0 #turnrate in driver
		self.Timeelapsed = 0
		self.startinterp_yawrate = 0	
		
		#interpolating variables.				
		self.x_interp = []  #arrays for interpolation
		self.z_interp = []
		self.yaw_interp = []
		self.wheel_interp = []
		self.interp_idx = 0 
		self.pid_idx = 0
		self.controller_period_size = self.sectionsize * self.interp_proportion #size of the combined PID + linear interp periods.
		self.linear_interp_proportion = .1 #changed when straight length increased.
		self.linear_interp_size = self.controller_period_size * self.linear_interp_proportion #fixed size in terms of midline pts. Only relevant for the interp_period that comes in after the playback.

		#calculate the number of frames taken to travel the linear_interp_length at 8m/s
		linear_interp_length = self.interplength * self.linear_interp_proportion #real-world distance of linear interp section
		framerate = 1.0/60.0
		estimateddistance = self.speed * framerate
		self.interp_steps = int(np.round(linear_interp_length / estimateddistance)) #there will be some rounding error, but it's close.				
	
		self.interp_begin = 0 #idx at which interpolation period begins.
		self.PID_CONTROL = False
		self.pid_desired_position = 0
		self.currentsteeringbias = 0
		###		
		self.Swa_readout = [] #SWA store for playback
		self.Ori_readout = []
		self.PosX_readout = []
		self.PosZ_readout = []

		self.txtMode = viz.addText("Mode",parent=viz.SCREEN)
		self.txtMode.setBackdrop(viz.BACKDROP_OUTLINE)
		self.txtMode.setBackdropColor(viz.BLACK)
		#set above skyline so I can easily filter glances to the letter out of the data
		self.txtMode.setPosition(.05,.52)
		self.txtMode.fontSize(36)
		self.txtMode.color(viz.WHITE)
		self.txtMode.visible(viz.ON)
			# self.txtMode.visible(viz.OFF)
		
		#text for beta versions
		if self.DEBUG:

			self.txtPlaybackTrial = viz.addText("PlaybackTrial",parent=viz.SCREEN)
			self.txtPlaybackTrial.setPosition(.7,.3)
			self.txtPlaybackTrial.fontSize(50)
			self.txtPlaybackTrial.color(viz.WHITE)
			# self.txtPlaybackTrial.visible(viz.ON)
			self.txtPlaybackTrial.visible(viz.ON)

			self.txtManualTrial = viz.addText("ManualTrial",parent=viz.SCREEN)
			self.txtManualTrial.setPosition(.7,.1)
			self.txtManualTrial.fontSize(50)
			self.txtManualTrial.color(viz.WHITE)
			# self.txtManualTrial.visible(viz.ON)
			self.txtManualTrial.visible(viz.ON)

		###Update Text so experiment knows experiment status
		self.txtStatus = viz.addText("Status", parent = viz.SCREEN)
		self.txtStatus.setPosition(.86,.98)
		self.txtStatus.fontSize(10)		
		#Skyblue is (.5, .5, 1)
		col = (.4,.4,.9)
		self.txtStatus.color(col)
		self.txtStatus.visible(viz.ON)

		#starts update loop, called every frame
		self.callback(viz.TIMER_EVENT,self.UpdatePosition)
		self.starttimer(0,1.0/60.0,viz.FOREVER)								

		self.trial_begin = 0
		self.trial_begin_yaw = 0

		self.comms = comms #EYETRACKING comms class. 
		self.EYETRACKING = eyetrackingflag

		#add audio files
		self.manual_audio = viz.addAudio('C:/VENLAB data/shared_modules/textures/490.wav') #high beep to signal change
		self.manual_audio.stoptime(.4) #cut it short for minimum interference.
		self.manual_audio.volume(.5)

		
		self.auto_audio = viz.addAudio('C:/VENLAB data/shared_modules/textures/590.wav') #high beep to signal change
		self.auto_audio.stoptime(.1) #cut it short for minimum interference.		
		self.auto_audio.volume(.5)		

		#test wheel.
		#self.test_wheel()

		#initialise the beginning trial. Ultimately this will be a manual period.
		self.NewTrial()		

	########################
	#### CORE FUNCTIONS ####
	########################
			
	def UpdatePosition(self, num):	
				
		"""monitors position and takes action depending on experiment state"""
		
		"""	
		STEPS:
		1) Monitors position and calculates bias
		2) If interpolation or PID_CONTROL is on then calculates a step and moves viewer.
		3) If AUTOMATION is on then moves viewer the next playback step.
		4) If manual is on then leaves the driver to move viewer.

		"""

		#If an interpolation period is in progress, currently don't save anything
		#TODO: Save data during interp period.		

		#Monitor the position for every section.
		if self.UPDATELOOP:
				
			#For both manual/AUTOMATION periods record all steering/position data.

			dt = viz.elapsed() #get time since last function call
			
			#update xy position, yaw, and wheel position				
			pos = self.view.getPosition() # get mainview position(x, y, z). #actually get cave position.
			# print ("Pos : ", pos)
			ori = self.getNormalisedEuler() # get yaw

			self.yawrate_inframes = vizmat.AngleDiff(ori[0], self.yaw_T_minus_1) #in frame units
			self.yaw_T_minus_1 = ori[0]
			
			self.yawrate_inseconds = self.yawrate_inframes / dt #or viz.elapsed(), but this is subject to very small values (meaning very large yaw rates)

			#print ("Read Ori : ", ori[0])
			steeringWheel = self.driver.getPos() #on a scale of -1,1. Can also get position through self.wheel.get_state(True) but the difference is minimal																						
																
			###########
			#calculate steering bias. Use the minimum pythagorean distance to find the closest midline point.  
			steeringbias = 0.0 # deviation variable between the vehicle and target path, plus: oversteering, minus: understeering
			
			#TODO: cut down on processing but only selecting a window of points based on lastmidindex.
			midlinedist = np.sqrt(((pos[0]-self.midline[:,0])**2)+((pos[2]-self.midline[:,1])**2)) #get a 4000 array of distances from the midline
			idx = np.argmin(abs(midlinedist)) #find smallest difference. This is the closest index on the midline.				
			closestpt = self.midline[idx,:] #xy of closest point
			dist = midlinedist[idx] #distance from closest point				
			
			#Sign bias from assessing if the closest point on midline is closer to the track origin than the driver position. Since the track is an oval, closer = understeering, farther = oversteering.
			middist_from_origin = np.sqrt(((closestpt[0]-self.trackorigin[0])**2)+((closestpt[1]-self.trackorigin[1])**2))  #distance of midline to origin
			pos_from_trackorigin = np.sqrt(((pos[0]-self.trackorigin[0])**2)+((pos[2]-self.trackorigin[1])**2)) #distance of driver pos to origin
			distdiff = middist_from_origin - pos_from_trackorigin #if driver distance is greater than closest point distance, steering position should be understeering
			steeringbias = dist * np.sign(distdiff) 
			self.currentsteeringbias = steeringbias
			############

			##############
			### Store all relevant variables ####
			#self.datacolumns = ['pp_id', 'trackindex','trialn','currtime','midlinepts','SWA','posx','posz','yaw','yawrate','steeringbias','autoflag','sectionorder','sectioncount','trialtype']						
			#TODO: Add eyedata				
			#SECTIONTYPES: 0 = Manual, 1= Playback, 2= Stock, 3=Backup, 4=PID, 5=Interp.
			if self.INTERP_PERIOD: 
				count = self.interpcount
				sectiontype = 5
				outputindex = self.interp_idx
				conditioncount=0
			elif self.PID_CONTROL:
				count = self.interpcount
				sectiontype = 4
				outputindex = self.pid_idx
				conditioncount=0
			elif self.AUTOMATION: 
				if self.currentplaybackfilename[:6] == "backup":
					count = self.BackupCount
					sectiontype = 3					
					conditioncount = self.BackupCount
					self.currenttrialtype = 99 	
				else:
					if self.PlaybackStock_SequenceIndex[self.playbacksequence_i] == 1:
						count = self.playback_i
						sectiontype = 1
						conditioncount = self.PlaybackRecord[self.currenttrialtype]
					elif self.PlaybackStock_SequenceIndex[self.playbacksequence_i] == 2:
						count = self.stock_i
						sectiontype = 2			
						if not self.PRACTICEMODE:			
							conditioncount = self.StockRecord[self.currenttrialtype]		

				outputindex = self.sectionindex
			else:
				count = self.man_i
				sectiontype = 0
				outputindex = self.sectionindex
				
			#TODO: self.trialn is probably not needed.
			#output = [self.sectionindex, idx, self.trialn, viz.tick(), self.trialendindex, steeringWheel, pos[0], pos[2], ori[0], self.yawrate_inframes, steeringbias, self.AUTOMATION, sectiontype, self.sectionorder, count, self.currenttrialtype, self.obstaclecolour, self.obstacleoffset]
			output = [outputindex, idx, self.trialn, viz.tick(), self.trialendindex, steeringWheel, pos[0], pos[2], ori[0], self.yawrate_inframes, self.yawrate_inseconds, steeringbias, self.AUTOMATION, sectiontype, self.sectionorder, count, self.currenttrialtype, self.obstaclecolour, self.obstacleoffset]
			output = np.concatenate((self.demographics,output))
			#self.trialdata.loc[self.sectionindex,:] = output 			
			self.trialdata.loc[outputindex,:] = output 			
			###############

			##############
			#increment lap for all sections.
			indexdiff = self.lastmidlineindex - idx #difference between current and last.
			self.lastmidlineindex = idx #update last midline index 
			if indexdiff > (self.tracksize - (self.sectionsize)) :# & (self.trialindex > 0): #the only place where there is a large drop in indexes should be when the driver starts a new lap.
				self.currentlap += 1
				#print ("incrementing lap: ", self.currentlap)
			##############

			if self.INTERP_PERIOD:
				
				
				if self.interp_idx == 0:
					#send annotation. 
#					self.sectionorder += 1
					if self.DEBUG:
						self.txtMode.message("I") #update display text

					if self.EYETRACKING:					
						label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
						label = "IntStart " + label
						self.comms.annotate(label)

					
				if self.BANKMODE: #if in bak mode then do not interpolate, just monitor position and switch to manual mode once interp period is over.
					
					#if index matches trial start. switch off interperiod.
					#print ("idx : ", idx, self.trial_begin, self.trial_begin+5)	
					if (idx >= self.trial_begin) & (idx <= self.trial_begin+(self.sectionsize*.005)): #if the position matches where they currently are then start the manual period again.
						print ("finished interpolation bank mode")

						#send annotation
						label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
						data = self.trialdata.copy()
						self.SendAnnotationAndSaveData("IntFinish", label, data)
					
						#empty dataframe for next section						
						self.trialdata = pd.DataFrame(columns=self.datacolumns)

						# Save Data				
						self.INTERP_PERIOD = False		
										
						self.sectionorder += 1

					
				else: #do interpolation. Change this to a PD controller.							
					# if self.sectionindex == 0:
					# 	self.WheelandVisuals(True)
					# if self.interp_idx == self.interp_steps: #if reached the end of the interp period set flag to false and continue with subsequent manual/AUTOMATION period
					# 	print "reached interp end"
					# 	self.interpcount +=1
					# 	self.INTERP_PERIOD = False
					 
					#if using PD control need to monitor idx	
					#print ("idx : ", idx, self.trial_begin, self.trial_begin+5)		
					if self.interp_idx == self.interp_steps:#(idx >= self.trial_begin-1) & (idx <= self.trial_begin+(self.sectionsize*.005)): #if the position matches where they currently are then start the manual period again.
						print ("finished interpolation controller mode")

						#send annotation
						label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
						data = self.trialdata.copy()
						self.SendAnnotationAndSaveData("IntFinish", label, data)
					
						#empty dataframe for next section						
						self.trialdata = pd.DataFrame(columns=self.datacolumns)
					
											
						#Reset parameters for AUTOMATION.
						self.INTERP_PERIOD = False
						self.sectionindex = 0

						# #plot steering bias during this period
						# sb_array = self.trialdata.get("steeringbias")
						# yaw = self.trialdata.get("yaw")
						# yawrate = self.trialdata.get("yawrate")
						
						#viz.director(self.plotController, sb_array, yaw, yawrate)		
						if not self.AUTOMATION:
							viz.director(SingleBeep, self.manual_audio)					
							self.WheelandVisuals(self.AUTOMATION) #Only turn Off when followed by a manual trial.		
						#reconnect visuals with wheel, depending on whether in AUTOMATION mode or not
						#self.WheelandVisuals(self.AUTOMATION)		

						#increment sectionorder when finished
						self.sectionorder += 1
					else:
						#do interpolation						
						#read position and orientation from interp arrays.
						newpos = [self.x_interp[self.interp_idx], 0.0, self.z_interp[self.interp_idx]]
						#newpos = [self.x_interp[self.interp_idx], 1.2, self.z_interp[self.interp_idx]]
						newori = [self.yaw_interp[self.interp_idx], 0.0, 0.0]
																		
						newSWApos = self.wheel_interp[self.interp_idx]		
						if self.wheel is not None:							
							self.wheel.set_position(newSWApos) #set wheel																							
						#set variables
				
						#set view. 
						#print ("Interp Set Ori: ", newori[0])
						self.view.setPosition(newpos)
						self.view.setEuler(newori)#, viz.REL_LOCAL)
				self.interp_idx += 1																		
				
			elif self.PID_CONTROL:
				#controller in charge
				#check whether interp should start
			
				if self.DEBUG:
					if self.pid_idx == 0:
						self.txtMode.message("PID") #update display text

				if self.BANKMODE:
					
					#increment section position in entire sequence
					#if self.pid_idx == 0:
						#self.sectionorder += 1

					#continue manual control
					if (idx >= self.interp_begin): #if the position matches where they currently are then start the manual period again.
						
						self.PID_CONTROL = False

						#send annotation
						label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
						data = self.trialdata.copy()
						self.SendAnnotationAndSaveData("PIDFinish", label, data)
					
						#empty dataframe for next section						
						self.trialdata = pd.DataFrame(columns=self.datacolumns)

						# print("PID")
						# print(self.trialdata["sectiontype"])

						#ensure interp period follows.
						self.INTERP_PERIOD = True
						self.interp_idx = 0

						#increment section order
						self.sectionorder += 1 
					else:
						self.pid_idx += 1	

					

				else:
					if self.pid_idx == 0:	
						#self.sectionorder += 1					
						self.WheelandVisuals(True)
						if self.EYETRACKING:
							label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
							self.comms.annotate("PIDStart " + str(label))													

					if self.DEBUG:
						print ("idx: ", idx)
						print ("self.interp_begin: ", self.interp_begin)
					if (idx >= self.interp_begin): #if the position matches where they currently are then start the manual period again.
						if self.DEBUG:
							print ("finished PID control mode")

						# 

						# print("PID")
						# print(self.trialdata)

						self.PID_CONTROL = False

						#send annotation
						label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
						data = self.trialdata.copy()
						self.SendAnnotationAndSaveData("PIDFinish", label, data)
					
						#empty dataframe for next section						
						self.trialdata = pd.DataFrame(columns=self.datacolumns)

						if self.AUTOMATION:
							self.InterpForPlayback()
						else:
							self.InterpForManual()

						#reconnect visuals with wheel, depending on whether in AUTOMATION mode or not						
						# self.WheelandVisuals(self.AUTOMATION)		#Do not reconnect since going into interp period			

						#increment section order
						self.sectionorder += 1
					else:
						
						###PD CONTROL###
						#print self.sectionindex
						# self.pid_step(steeringbias, self.pid_desired_position)	
						self.pid_step_sng(self.pid_desired_position)	
						#self.sectionindex += 1
						self.pid_idx += 1

			elif self.AUTOMATION:										
						
				if self.DEBUG: 
					self.txtMode.message('A')
				#playback
				if self.sectionindex == 0:					
					#self.sectionorder += 1
					if self.EYETRACKING:	
						#print "Sending annotation"																		
																	
					 	# self.comms.start_trial(self.eyetrike_filename, viz.elapsed)
						if not self.PRACTICEMODE:
							label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
							label = "AutStart " + label
							self.comms.annotate(label)
				
				if self.playbackindex == self.playbacklength: #end of trial reached


					#increment section order
					self.sectionorder += 1
														
					self.UPDATELOOP = False #stop loop. 												

					data = self.trialdata.copy()
														
					if sectiontype ==3: #backup file						
						self.currenttrialtype = 99 #TODO: change backup file trialtype to a reasonable value
						conditioncount = self.BackupCount
						self.BackupCount += 1
						
					else:
						self.playbacksequence_i += 1

						#save section
					
						if sectiontype == 1: #playback
							#increment count in playback record and index
							#print("End of Trial " + str(self.playbacksequence_i-1) + "; TrialType: " + str(self.currenttrialtype))
							conditioncount = self.PlaybackRecord[self.currenttrialtype]
							self.PlaybackRecord[self.currenttrialtype] = conditioncount + 1
							self.playback_i += 1
							#print ("Incremented Playback i to " + str(self.playback_i))

						elif sectiontype == 2: #stock
							#increment count in stock record and index
							#print("End of STOCK trial " + str(self.playbacksequence_i-1) + "; TrialType "+str(self.currenttrialtype))
							if not self.PRACTICEMODE:
								conditioncount = self.StockRecord[self.currenttrialtype]
								self.StockRecord[self.currenttrialtype] = conditioncount + 1
							self.stock_i += 1
							#print ("Incrementing Stock Count", self.stock_i)
					
					if not self.PRACTICEMODE:
						label = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_" + str(sectiontype) + "_" + str(self.currenttrialtype) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount
						self.SendAnnotationAndSaveData("AutFinish", label, data)				
					


					if self.PRACTICEMODE:
						if (self.stock_i == len(self.StockTrialOrder)): #reached the end of the practice experiment. 
							print ("Finished Practice")					
							self.Quit()
						
						else:
							#start manual period
							self.NewTrial()

					else:
						
						if (self.playback_i == self.TotalMatchedTrials) and (self.stock_i == len(self.StockTrialOrder)): #reached the end of the experiment. 
							print ("Finished Experiment")											
							#quit
							self.Quit()
						else:
																	
							self.NewTrial()
					
				else:
					#retrieve variables from store
					SWApos = self.Swa_readout[self.playbackindex]
					posx = self.PosX_readout[self.playbackindex]
					posz = self.PosZ_readout[self.playbackindex]
					yaw = self.Ori_readout[self.playbackindex]
					yaw = vizmat.NormAngle(yaw)
					
					#set variables
					if self.wheel is not None:							
						self.wheel.set_position(SWApos) #set wheel
						
					pos = [posx,0.0, posz] #since the tracker is already placed at EH within in the cave, the cave doesn't need to move in the y direction
					#pos = [posx,1.2, posz]
					ori = [yaw,0.0,0.0]						
					if self.FLIP_PLAYBACK:						
						[pos, ori] = self.MirrorRoundTrackOrigin(pos,ori)
						
					#set view and ori
					self.view.setPosition(pos)

					#print ("Automation set Euler: ", ori[0])
					self.view.setEuler(ori)#, viz.REL_LOCAL)
					
					#increment index.
					self.playbackindex +=1								
					self.sectionindex += 1 #indexes each subsection
					
			elif not self.AUTOMATION:
					
				self.txtMode.message("M")				
				
				#if it is the first frame of a manual period record starting positions for playback.
				#TODO: REMOVE THESE. DO NOT NEED
				if self.sectionindex == 0:
#					self.sectionorder += 1

					self.currentmanualfilename = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_0_" + str(self.currenttrialtype) + "_" + str(self.currentmanualconditioncount) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount

					#print ("CurrentManualFile: ",self.currentmanualfilename)
					if self.DEBUG:			
						self.txtManualTrial.message(self.currentmanualfilename)		
					
					#print("Trial Data size Manual: " + str(len(self.trialdata)))

					#print(self.trialdata["sectiontype"])

					#print ("Setting Start Lap")
					self.startlap = self.currentlap #needed to decide whether to flip playback+

					#Annotate start Man here, on first frame of new period. Not at the initialisation of a new trial (which incorporates PID and interp).
					if self.EYETRACKING:	
						# self.comms.start_trial(self.eyetrike_filename, viz.elapsed)

						self.comms.annotate("ManStart " + self.currentmanualfilename)

					if self.BANKMODE: #if this is the last bank mode trial, then switch it off and load next trial
						if self.man_i >= (len(self.BankTrialOrder)-1): 
							self.BANKMODE = False												
												
					if not self.BANKMODE: #if it is the last trial of the bank period. #Should also work as if not self.bankmode.
					
						# chosentrial = str(0) + "_" + str(self.autocount+1) + "_" + str(self.demographics[0]) + ".csv"#instead of randomly selecting trials we can just start from the beginning. Use either (self.mancount - self.totalbanktrials) or self.autocount
						
						chosentrial = self.PickTrial()
						#chosentrial =  "stock_4_3.csv"#instead of randomly selecting trials we can just start from the beginning. Use either (self.mancount - self.totalbanktrials) or self.autocount
						if self.DEBUG:
							self.txtPlaybackTrial.message(chosentrial)
						self.currentplaybackfilename = chosentrial
						viz.director(self.OpenTrial, chosentrial)																				
					

					# if self.EYETRACKING:	
					# 	#print ("Sending annotation")
					# 	label = chosentrial
					# 	self.comms.annotate(label)			

				if (self.endlap == self.currentlap) & (idx >= self.trialendindex): #if the laps are the same and the current midline idx passess the trial end index then finish the trial
					#print "Manual Trial Finished"
					self.sectionorder += 1											
					data = self.trialdata.copy()															
					viz.director(self.CheckAndSave, data, self.currentmanualfilename, self.currenttrialtype) #prepend ERRORDUMP if trial does not satisfy error requirements.
					#viz.director(self.SaveTrial, data, filename)																
					self.man_i += 1																	
					if self.BANKMODE: #check if we are waiting for more trials to bank
						
						self.NewTrial()

					else:						
						#if we aren't initialise playback (at the moment it just plays the most recent trial back
						
						viz.director(DoubleBeep, self.auto_audio)
						self.txtMode.message("A") #update display text										
						self.InitialisePlayback() #sets parameters for playback										
				else:
									
					self.sectionindex += 1 #indexes each subsection				
					
	def InitialisePlayback(self):
		
		"""Sets conditions for playback after an interpolation period"""

		#print ("Initialising Playback")
		self.UPDATELOOP = False #stop loop updating whilst function is called.				
		
		#playbackdata = pd.read_csv(chosentrial) #read chosen playback
		playbackdata = self.playbackdata #read chosen playback
		
		self.Swa_readout = playbackdata.get("SWA") #pick up wheel pos executed so far in trial
		self.Ori_readout = playbackdata.get("yaw")
		self.PosX_readout = playbackdata.get("posx")
		self.PosZ_readout = playbackdata.get("posz")

		#change obstacle colour depending on obstacle type
		self.obstaclecolour = playbackdata.get("obstaclecolour")[0]
		self.ChangeObstacleColour()
		self.obstacleoffset = playbackdata.get("obstacleoffset")[0]
		self.ChangeObstacleOffset()
		
		#set trialtype
		self.currenttrialtype = int(playbackdata.get("trialtype")[0])

		print("727 - Set Current Trial Type to: ", self.currenttrialtype)

		#self.currenttrialtype = 0

		#reset parameters for AUTOMATION playback
		self.playbacklength = len(self.Swa_readout) #the current trial index will be the manual period length
		self.playbackindex = 1 #why 1? #TODO: use section index.		

		#######
		playbackstart_index = playbackdata.loc[0,"trackindex"] #pick trackindex
		#playbackend_index = playbackdata.loc[self.playbacklength-1,"trackindex"] #pick trackindex		
		
#		print("start lap: ", self.startlap)
		#print("current lap: ", self.currentlap)

		#print ("playbackstart_index: ", playbackstart_index)
		#print ("self.lastmidlineindex: ", self.lastmidlineindex)

		def DistanceFromStart(idx):
			"""returns distance in midline indexes from the start of the track"""
			if idx > (self.tracksize/2):
				distance = idx - self.tracksize
			else:
				distance = idx
			
			return abs(distance)

		#determine whether to flip playback. If the symmetrical index (e.g. 50 vs 2050) is closer to the last index than the start index, choose that.		
		startindex = DistanceFromStart(playbackstart_index) #+ (self.tracksize*self.startlap) #add amount of indexes passed in trial to put indexes on same scale

		#print ("StartIndex: ", startindex)

		sym_index = DistanceFromStart(playbackstart_index + (self.tracksize/2)) #+ (self.tracksize*self.startlap)

		#print ("SymIndex: ", sym_index)
		#endindex = playbackend_index + (self.tracksize*self.currentlap)
		endindex = DistanceFromStart(self.lastmidlineindex)  #+ (self.tracksize*self.currentlap)

		#print ("EndIndex: ", endindex)
				
		sym_indexdiff = endindex - sym_index
		#print ("Sym_indexdiff: ", sym_indexdiff)
		startindexdiff = endindex - startindex
		#print ("start_indexdiff: ", startindexdiff)
					
		if abs(sym_indexdiff) < abs(startindexdiff): #if closer to symmetrical index, flip playback.
			self.FLIP_PLAYBACK = True
			self.trial_begin = playbackstart_index + (self.tracksize/2)
		else:
			self.FLIP_PLAYBACK = False
			self.trial_begin = playbackstart_index
		
		#correct for >4000
		if self.trial_begin >= self.tracksize: 
			self.trial_begin = int(self.trial_begin) - self.tracksize
		
		#reset dataframe
		self.trialdata = pd.DataFrame(columns=self.datacolumns)
		
		#reset flags and indexes
		self.sectionindex = 0					
		self.UPDATELOOP = True		
		
		#disconnect wheel and visuals
		self.AUTOMATION = True
		#self.WheelandVisuals(self.AUTOMATION)		

		#set controller flag
		initialsteeringbias = playbackdata.get("steeringbias")[0] #set PID desired position to initial steering bias so there is minimal linear translation in the interpolation.
		print ("initial steering bias: ", initialsteeringbias)
		self.InitialiseController(initialsteeringbias)
	
	def NewTrial(self):
		
		"""Sets conditions for a manual trial after interpolation period"""

		#TODO: if the manual trial list has been exhausted, select conditions at random, and put Count as 100+n
		
		#print ("Begin new manual trial: ", self.man_i)
		self.UPDATELOOP = False #pause update loop.										

		####### 
		#determine the start and end indexes of next manual period, taking account for the interpolation period and any potential lap increments
		self.endlap = self.currentlap #make sure that lap counters are synced before new endpoint is set.
		if self.man_i > 0: #if it's the first trial there is no interpolation period, so no risk of starting a new lap
			#print ("last midline: ", self.lastmidlineindex)
			trialstart = self.lastmidlineindex + self.controller_period_size #add the interpolation period.
			#trialstart = self.SectionBreaks[0]			
			
			#print ("trialstart", trialstart)
			#print ("tracksize", self.tracksize)
			#TODO: remove endlap 
			if trialstart >= self.tracksize: #check if the interp period size nudges the starting position into the next lap.
				#I don't think you need currentlap to be incremented since thecurrent lap gets incremented whichever mode you're in.
				# self.currentlap += 1 #if so, increment both current and end laps
				self.endlap += 1
				trialstart = trialstart - self.tracksize #and reset the trialstart by 4000
				#self.lastmidlineindex = trialstart #also need to update last midline index to the start of the trial, otherwise the update loop will think a new lap has started.
				trialstart= self.SectionBreaks[0]
			#	print ("newtrialstart: ", trialstart)

			#####Initilise Interpolation Period#####
			#the interpolation period BEFORE a manual drive should reset the driver to the centre of the road & correct yaw, regardless of where the driver is on the track.
			#TODO: also could automate wheel so wheelpos is lined up with curvature. Currently the wheel AUTOMATION at start of manual period centres
				
			#determining yaw rate will require splitting into straights and bends.
			#TODO: pass section breaks to vizTrialManager so they do not need to be hardcoded.
			if ((trialstart >= self.SectionBreaks[0]) and (trialstart <= self.SectionBreaks[1])) or ((trialstart >= self.SectionBreaks[6]) and (trialstart <= self.tracksize)) : #first straight
				yaw = 0.0
			elif (trialstart > self.SectionBreaks[1] and trialstart <= self.SectionBreaks[2]): #first bend	
				#use law of cosines to retrieve yaw angle.
				#use the centre of bend circle as your point of reference.
				rads = self.trackorigin[0]
				
				#use of start of bend and trial start to get hypotheneuse distance. 
				bendstart = self.midline[self.SectionBreaks[1],:]
				xstart = self.midline[trialstart,:]
				hypdist = np.sqrt(((bendstart[0]-xstart[0])**2) + ((bendstart[1]-xstart[1])**2))
				
				#cos(C) = (a**2 + b**2 - c**2) / 2ab
				#cos(orient) = (rads^2 + rads^2 - hypdist^2) / (2*rads*rads)
				#using law of cosines
				val = ( 2*(rads**2) - hypdist**2) / (2*(rads**2))				
				yaw = np.arccos(val)				
				yaw = yaw*180.0/np.pi				
				
			elif (trialstart > self.SectionBreaks[2] and trialstart <=  self.SectionBreaks[5]): #back straight
				yaw = 180.0
			elif (trialstart >  self.SectionBreaks[5] and trialstart <= self.SectionBreaks[6]): #second bend
				#use law of cosines to retrieve yaw angle.
				#use the centre of bend circle as your point of reference.
				rads = self.trackorigin[0]
				
				#use of start of bend and trial start to get hypotheneuse distance. 
				bendstart = self.midline[self.SectionBreaks[5],:]
				xstart = self.midline[trialstart,:]
				hypdist = np.sqrt(((bendstart[0]-xstart[0])**2) + ((bendstart[1]-xstart[1])**2))
				
				#cos(C) = (a**2 + b**2 - c**2) / 2ab
				#cos(orient) = (rads^2 + rads^2 - hypdist^2) / (2*rads*rads)				
				#using law of cosines
				val = ( 2*(rads**2) - hypdist**2) / (2*(rads**2))				
				yaw = np.arccos(val)				
				yaw = yaw*180.0/np.pi
				
				#since it's second bend, minus 180
				yaw = yaw - 180 #vizard yaw becomes negative after 180.
				
			#now I have the end yaw I can linearly interpolate
			currentori = self.getNormalisedEuler()				

			#print ("playback startyaw: ", currentori[0])
			#print ("playback endyaw: ", yaw)
			#change obstacle colour


		else:
			trialstart = self.lastmidlineindex
			self.UPDATELOOP = True
			yaw = 0
			self.wheel.control_off()
				
		self.trialendindex = trialstart + self.triallength #new trial index.
						
		if self.trialendindex >= self.tracksize: #if the entire trial has passed 4000, then reset the trialendindex. Allows for long manual periods.
			self.endlap = self.currentlap + 1
			self.trialendindex = self.trialendindex - self.tracksize				
		
		###End of setting trial start and stop indexes#####
		
		#reset dataframe
		self.trialdata = pd.DataFrame(columns=self.datacolumns)
		
		print("man_i: " + str(self.man_i))
		print("backup count: " + str(self.BackupCount))
		print("error count " + str(self.ErrorCount))
		print("Valid Trials: " + str(self.man_i - self.ErrorCount))
		print("ManualTrialOrder: " + str(self.ManualTrialOrder))

		validmanualtrials = self.man_i - self.ErrorCount
		remainingtrials_index = validmanualtrials - len(self.BankTrialOrder)
		remainingmanualtrials = self.TotalManualTrials - validmanualtrials

		print ("remainingtrials_index: " + str(remainingtrials_index))

		msgstatus = "V: {}, R: {}, E: {}, P: {}, S: {}, B: {}".format(validmanualtrials, remainingmanualtrials, self.ErrorCount, self.playback_i, self.stock_i, self.BackupCount)
		self.txtStatus.message(msgstatus)

		#Set Condition Parameters.
		if self.BANKMODE: 			
			self.currenttrialtype = self.BankTrialOrder[self.man_i]
			print("914 - Set Current Trial Type to: ", self.currenttrialtype)
			self.currentmanualconditioncount = int(self.ManualRecord[self.currenttrialtype])			
			
		else:
			#TODO: here force a random condition selection if list is exhausted
			if validmanualtrials >= self.TotalManualTrials: #list has been exhausted with valid trials, now we are into superfluous active trials whilst the passive trials plays out.
				
				randomcondition = pickrandom(self.ConditionList)
				self.currenttrialtype = randomcondition
				self.currentmanualconditioncount = int(self.ManualRecord[self.currenttrialtype])							
				self.currentmanualconditioncount = 100+(self.currentmanualconditioncount								)
			
			else:
				self.currenttrialtype = self.ManualTrialOrder[remainingtrials_index] #picks trial.
				print("928 - Set Current Trial Type to: ", self.currenttrialtype)
				self.currentmanualconditioncount = int(self.ManualRecord[self.currenttrialtype])
				
		self.setObstacles(self.currenttrialtype) #function that determines obstacle colour and offset depending on trial type												
				
		self.sectionindex = 0		
		#self.currenttrialtype = self.mancount + 1 #mancount starts at zero and only increments at the end of the manual period.
				
		self.UPDATELOOP = True				

		self.trial_begin = trialstart
		#print ("trial_begin_in newtrial: ", trialstart)
		self.trial_begin_yaw = yaw
		
		if self.man_i > 0:
		#set controller flag if not first trial.
			self.InitialiseController()

		self.AUTOMATION = False

	##########################################
	## FUNCTIONS THAT ORGANISE INTERPOLATION ##
	###########################################

	def InterpForPlayback(self):
		"""set parameters for interpolation to AUTOMATION"""
		#Setting the position is the same for both interp to AUTOMATION and interp to manual
		posx = self.PosX_readout[0]
		posz = self.PosZ_readout[0]
		yaw = self.Ori_readout[0]
		# print ("prenorm: ", yaw)
		yaw = vizmat.NormAngle(yaw)
		# print ("postnorm: ", yaw)
		
		playbackstart_pos = [posx,1.2, posz]		
		playbackstart_ori = [yaw,0.0,0.0]
		

		# print ("Flipped Playback: ", self.FLIP_PLAYBACK)
		if self.FLIP_PLAYBACK:			
			

			# print "preflipped yaw: " + str(playbackstart_ori)
			# print "preflipped position: " + str(playbackstart_pos)
			
			[playbackstart_pos, playbackstart_ori] = self.MirrorRoundTrackOrigin(playbackstart_pos, playbackstart_ori)			

			# print "postflipped yaw: " + str(playbackstart_ori)
			# print "postflipped position: " + str(playbackstart_pos)

		######## Correct yaw for interpolation
		currentori = self.getNormalisedEuler()		
		startyaw = currentori[0]
		endyaw = playbackstart_ori[0]		
		
		# if abs(np.sign(endyaw) + np.sign(startyaw)) != 2: #the absolute of added signs should == 2 if they are both the same
		# 	if endyaw < 0: #yaw ends negative
		# 		endyaw = 360 + (endyaw) #put endyaw on a 0-360 scale. Vizard should accept this.
		# 	elif startyaw < 0: #yaw starts negative
		# 		startyaw = 360 + (startyaw) #but start yaw on a 0-360 scale.

		self.InitialiseInterpolation(playbackstart_pos[0], playbackstart_pos[2], [startyaw, endyaw])
	
	def InterpForManual(self):
		"""set parameters for interpolation to manual"""

		currentori = self.getNormalisedEuler()		
		self.InitialiseInterpolation(self.midline[int(self.trial_begin),0], self.midline[int(self.trial_begin),1], [currentori[0], self.trial_begin_yaw] )			

	def InitialiseInterpolation(self, endx, endz, yaws = []):

		"""Sets conditions for interpolation period"""
		
		#print "Initialising Interpolation"
		self.interp_idx = 0
		
		currentpos = self.view.getPosition()

		# print ("Current Position: ", currentpos)
		currentori = self.getNormalisedEuler()	
		currentwheel = self.wheel.get_state(True)

		#print ("SELF READOUT", self.Swa_readout)
		playbackstart_wheel = self.Swa_readout[0]

				#a simple linear interpolation between currennt position and playback start position.
		self.x_interp = np.linspace(currentpos[0], endx, self.interp_steps)
		self.z_interp = np.linspace(currentpos[2], endz, self.interp_steps)
		if self.wheel is not None:		
			# print "currentwheel: " + str(currentwheel)
			# print "futurewheel: " + str(playbackstart_wheel)
			self.wheel_interp = np.linspace(currentwheel, playbackstart_wheel, self.interp_steps)

		#correct for potential flipping.				
		startyaw = yaws[0]
		endyaw = yaws[1]
		# print ("startyaw: ", startyaw)
		# print ("endyaw: ", endyaw)

		#correct for potential flipping from 360 to 0.
		diff = vizmat.AngleDiff(startyaw, endyaw) 
		newstartyaw = endyaw - diff
		# print ("new start yaw", newstartyaw)

		self.yaw_interp = np.linspace(newstartyaw, endyaw, self.interp_steps)

		#print (self.yaw_interp)

		self.startinterp_yawrate = self.yawrate_inframes #in frame units
		#self.sectionindex = 0 
		self.INTERP_PERIOD = True #puts AUTOMATION on hold until interpolation period is finished.



	##############################################
	# FUNCTIONS INVOLVING WHEEL AUTOMATION ######
	##############################################

	def InitialiseController(self, desired_position = 0):
		"""Sets flag for PID control"""
	
		#send annotation, controller: sectiontype 2.
		self.sight_point_angles_minus_1 = None
		print ("Controller Initialised")
		# if self.EYETRACKING:	
		# 	#TODO: CHANGE TO UPDATE LOOP
		# 	label = "2" + "_" + str(self.currenttrialtype) + "_" + str(self.demographics[0])
		# 	self.comms.annotate(label)		

		#set PID_CONTROL flag
		self.PID_CONTROL = True
		self.pid_desired_position = desired_position

		#reset parameters
		###OSCAR HERE###
		self.error_T_minus_1 = None #Oscar - do we want to do this?
		self.YR_T_minus_1 = self.yawrate_inframes * (np.pi/180.0) 

		if self.DEBUG:
			print ("Initial YR: ", self.YR_T_minus_1)
		self.error_i = 0

		self.pid_idx = 0

		if self.DEBUG:
			print ("self.trial_begin: ", self.trial_begin)
			print ("self.linear_interp_size:	", self.linear_interp_size	)

		self.interp_begin = self.trial_begin - self.linear_interp_size	
		

		if self.interp_begin < 0:
			if self.DEBUG:
				print ("Reset interp_begin from: ", self.interp_begin)
				print ("Add track size:", self.tracksize)
			self.interp_begin += self.tracksize

	def calculate_sight_point_angles(self, target_trajectory):

		sight_point_times = np.array([0.5, 2])

		sight_point_distances = sight_point_times * self.speed
		n_sight_points= len(sight_point_distances)


		pos = self.view.getPosition()
		pos = np.array([pos[0], pos[2]])
		heading = self.getNormalisedEuler()
		heading = np.deg2rad(heading[0])
		#Get vectors from vehicle to road points
		vectors_to_road_points = np.array([target_trajectory[:,0] - pos[0], 
										target_trajectory[:,1] - pos[1]]).T

		#Get distances to road points
		road_point_distances = np.sqrt(np.sum(np.square(vectors_to_road_points), axis = 1))

		#Get the forward vector
		self.forward_vector = np.array([np.sin(heading), np.cos(heading)])        

		straight_ahead_distance_to_road_points = np.dot(vectors_to_road_points, self.forward_vector)

		road_point_distances[straight_ahead_distance_to_road_points < 0 ] = np.Infinity

		sight_point_angles = np.empty(n_sight_points)
		sight_points = np.empty((n_sight_points, 2))
		i = 0

		colors = ['b', 'g']
			
		for sight_point_d in sight_point_distances:

			#Get the absolute error between the distance to the road points and the sight pont distance
			v_abs_error = np.abs(road_point_distances - sight_point_d)         

			nearest_points_idx = np.argsort(v_abs_error)[:2]

			#Find sight points on road and calculate distance error (how close are they compared the look ahead)
			sight_road_points = target_trajectory[nearest_points_idx] # the two closest road points 
			sight_road_error = v_abs_error[nearest_points_idx]
			total_abs_error = np.sum(sight_road_error)

			# Get the average position between to points weighted by their error
			sight_point = (sight_road_points[0] * sight_road_error[0] + sight_road_points[1] * sight_road_error[1]) / total_abs_error


			sight_points[i] = sight_point                    
							
			self.vector_to_sight_point = sight_point - pos      


			# plt.plot(sight_point[0], sight_point[1], 'o', color = colors[i])

			# plt.plot([self.pos[0], self.pos[0] +  self.vector_to_sight_point[0]], [self.pos[1], self.pos[1] + self.vector_to_sight_point[1]], 'k-')

			#Gustavs method of calculating sight point angle
			longitudinal_dist_2_sp = np.dot(self.vector_to_sight_point, self.forward_vector)
			lateral_dist_2_sp = np.dot(self.vector_to_sight_point, np.array([np.sin(heading + np.pi / 2), np.cos(heading + np.pi / 2)]))
			sp_angle = np.arctan(lateral_dist_2_sp / longitudinal_dist_2_sp)

			# Calculate the angle between vectors
			# sp_angle = angle_between_vectors(self.forward_vector, self.vector_to_sight_point)

			# print(sp_angle, sp_angle2)
								
			# pdb.set_trace()qq
			sight_point_angles[i] = sp_angle     
			i += 1
		# plt.plot(self.pos[0], self.pos[1], 'ro', ms = 5)
		# plt.plot([self.pos[0], self.pos[0] + self.forward_vector[0] * 10], [self.pos[1], self.pos[1] + self.forward_vector[1] * 10], 'b-o', ms = 3 )
			
		# plt.ylim([-40, 0])        
		# plt.text(0.5, 0.75, " ".join([str(i) for i in sight_point_angles.tolist()]), horizontalalignment='center', verticalalignment='center', 
		#     transform=plt.gca().transAxes)
		# plt.show()

		# plt.plot(v_abs_error)
		# pdb.set_trace()
		return sight_point_angles    

	def pid_step_sng(self, offset):

		"""offset: offsets the desired trajectories x value by offset.

		This solution will only work on straight roads"""

		# self.currenterror = self.calculatebias()[0]

		#dt = viz.elapsed()
		dt = 1.0/60.0

		target_trajectory = self.midline + np.array([offset, 0.0]) 

		sight_point_angles = self.calculate_sight_point_angles(target_trajectory)

		self.sight_point_angles = sight_point_angles        

		if self.sight_point_angles_minus_1 is None:
			sight_point_angles_d = np.zeros(2) #Change in sight point angles between timesteps
		else:

			sight_point_angles_d  = (sight_point_angles - self.sight_point_angles_minus_1) 

		self.sight_point_angles_minus_1 = sight_point_angles.copy()

		k_i, k_n, k_f = 100.0, 20., 20.

		heading_dot = (k_i * sight_point_angles[0] * dt +
						k_n * sight_point_angles_d[0] + 
						k_f * sight_point_angles_d[1] ) 
		

		#Let vizard do it.
		YR_output = heading_dot
		d_clip = .005 #.01 #change in rads per second #.00025
		d_YR = YR_output - self.YR_T_minus_1
		d_YR_clamped = np.clip(d_YR, -d_clip, d_clip)
		YR_output = self.YR_T_minus_1 + d_YR_clamped

		self.YR_T_minus_1 = YR_output

		YR_degrees = YR_output * (180/np.pi)

		self.view.setEuler((YR_degrees * dt, 0, 0), viz.REL_LOCAL) #surely this should be global rather than local? 
		self.view.setPosition((0,0,self.speed * dt), viz.REL_LOCAL)

		#automate wheel. 
		#turnrate = self.__dir * (data[0])  * elapsedTime * 35
		#change yaw_rate into wheel position change
		wheelpos = YR_degrees / 35.0
		self.wheel.set_position(wheelpos)	

	def pid_step(self, currentbias, desired_position, tau_p = 0.01, tau_d = .4, tau_i =0.000):
		"""PID controller step using lateral error as input and yawrate as output"""		

		#0.01, 0.4, 0.0001
		#dt = 1/60.0
		#dt = viz.elapsed()	
		#print ("Elapsed: ", viz.elapsed())
		#print ("dt: ", 1/60.0)
		#p = [0.01684333709520866, 0.26611946572961437, -3.0569927185666086e-05]
	#	p =[0.005065372161779556, 0.07463897274205897, -2.5908482849261276e-05]
	#0.014317907237840646, 0.4264284237624855, 0.0
		# [0.004, 0.2, 0.0] 		
		
		# pos = self.view.getPosition()
		# #print ("pos: ", pos)

		# Euler = self.view.getEuler()
		# #print ("Euler: ", Euler)

#		print ("desired position: ", desired_position)

		#Error between desired and actual position
		error = desired_position - currentbias

		        
		if error < .1:
			self.Integral_On = True
		else:
			self.Integral_On = False

		#introduce some satisficing behaviour to avoid oscillations around midline.
		#error =np.clip(error, -.15, +.15) #clip so the error isn't huge.
		threshold = .05 #.01 #clip so does not respond to tiny errors
		if abs(error) < threshold:
			error = 0

		#print("SteeringBias: ", currentbias)		
		#print ("PID ERROR: ", error)
				
		#Derivative of error
		if self.error_T_minus_1 is None:
			d_error = 0
		else:
			d_error = (error - self.error_T_minus_1) #/ dt #change in bias (s)

		self.error_T_minus_1 = error

		#integral of error
		if self.Integral_On:
			self.error_i = self.error_i + error

		self.max_error = max([self.error_T_minus_1, error, self.max_error])
		self.min_error = min([self.error_T_minus_1, error, self.min_error])

		#print ("MaxErr: ", self.max_error)
		#print ("MinErr: ", self.min_error)
																
		#Set yaw rate output		
		YR_p = tau_p * error
		YR_d =  tau_d * d_error
		YR_i = tau_i * self.error_i
		
		YR = YR_p + YR_d + YR_i #does not need converted back, because taus will be adjusted.
		#clip_YR = int(np.clip(YR, -.5, .5))	#clamp max jerk.
	
		#print(currentbias, error, YR, YR_p, YR_d)
		#self.yawrate = self.startinterp_yawrate+YR

		# print ("start yawrate: ", self.startinterp_yawrate)
		# print ("current yawrate: ", self.yawrate_inframes)
		# print ("added yawrate: ", YR)


		#print ("Yaw OUT: ", YR)		
		#YR_output = self.startinterp_yawrate+YR 
		# max yawrate specified in vizdriver by (1 * (1/60.0) * 35.0) * np.pi/180.0 	
		maxwheelval = (1.0 * (1/60.0) * 35.0) * np.pi/180	  
		clip_YR =np.clip(YR, -maxwheelval, maxwheelval)

		#put threshold to stop very minor oscillations around midline.
		YR_output = clip_YR

		if self.DEBUG:
			print ("Attempted YR_output: ", YR_output)

		#limit the amount yawrate can change 
		d_clip = .0005#.00025
		d_YR = YR_output - self.YR_T_minus_1
		d_YR_clamped = np.clip(d_YR, -d_clip, d_clip)
		YR_output = self.YR_T_minus_1 + d_YR_clamped

		self.YR_T_minus_1 = YR_output

		###move Camera###

		#Let vizard do it.
		YR_degrees = YR_output* (180/np.pi)

		self.view.setEuler((YR_degrees, 0, 0), viz.REL_LOCAL) #surely this should be global rather than local? 
		self.view.setPosition((0,0,self.speed), viz.REL_LOCAL)

		#automate wheel. 
		#turnrate = self.__dir * (data[0])  * elapsedTime * 35
		#change yaw_rate into wheel position change
		wheelpos = YR_degrees / (1/60.0) / 35
		self.wheel.set_position(wheelpos)	

	def WheelandVisuals(self, flag = None):
		"""(dis)connects wheel with visuals, depending on AUTOMATION mode and whether wheel AUTOMATION is turned on"""		

		
		#print ("Changing Wheel and Visuals Relationship")		
		if flag is None:
			flag = self.AUTOMATION	

		self.driver.setAutomation(flag)

		if self.wheel is not None:			
			if flag:
				#self.wheel.control_on() #now we never need to turn the wheel on as it automatically happens when you set position.
				pass
			else:
				self.wheel.control_off()

	def test_wheel(self):

		"""move wheel to hard right or left"""
		
		#print ("TESTING WHEEL")
		pos = self.wheel.get_state(True)

		if pos > 0: #position is rightwards, move leftwards
			self.wheel.set_position(-.9) #set wheel																							
		else:
			self.wheel.set_position(.9) #set wheel

	def plotController(self, sb_array, yaw, yawrate):
		
		
		plt.subplot(3,1,1)

		plt.axhline(y=0, color = 'b')			
		plt.plot(range(len(sb_array)), sb_array, 'r.')						
		plt.xlabel("Frame")
		plt.ylabel("Interp_SB")						

		plt.subplot(3,1,2)
		plt.plot(range(len(yaw)), yaw, 'g.')						
		plt.xlabel("Frame")
		plt.ylabel("Yaw")						

		plt.subplot(3,1,3)
		plt.plot(range(len(yawrate)), yawrate, 'k.')						
		plt.xlabel("Frame")
		plt.ylabel("YawRate")						

		fig1 = plt.gcf()
		randi = np.random.randint(500,size=1)
		fig1.savefig('Controller/InterpControlPerformance_'+str(randi[0])+'.png')																								

	####################################################
	# FUNCTIONS FOR ORGANISING TRIAL SAVING AND LOADING 
	####################################################

	def CheckAndSave(self, data, filename, condition):

		"""checks that manual trial meets error requirements, and saves if so"""		

		#Increment relevant condition count.				
		self.ManualRecord[condition] += 1

		if self.currentmanualconditioncount < 100: #If the trial is going to be replayed, check error.

			Passed = False #guilty until proven innocent.

			Passed = self.ErrorCatch(data)

			#print ("Passed: ", Passed)

			if not Passed:
				#If not passed, add condition to the end of ManualTrialOrder
				self.ManualTrialOrder.append(condition)
				filename = "ERRORDUMP_" + filename
				self.ErrorCount += 1
				#Decrement relevant condition count. Otherwise there are gaps in the playback filenames that the programme struggles to find				
				self.ManualRecord[condition] -= 1

		
		if self.EYETRACKING:	
			self.comms.annotate("ManFinish " + filename)

			# self.comms.stop_trial()

		self.SaveTrial(data, filename)
		
	def SaveTrial(self, data, filename):
		
		"""saves data to csv"""

		if self.PRACTICEMODE:
			filename = "PRAC_" + filename
		
		print ("Called save trial: ", filename)
		
		#PRACTICE EXPERIMENT HACKS
		#pracfilename = "PRAC_" + filename
		data.to_csv("Data//" + filename)
		#self.trialdata.to_csv(str(self.demographics[0]) + "_" + str(self.trialn) +  ".csv")

	def OpenTrial(self,filename):
		"""opens csv file"""

		print ("Loading next playback file: " + filename)
		self.playbackdata = pd.read_csv("Data//"+filename)

	def PickTrial(self):
		"""Picks the next playback Trial based on experiment status and error of chosen trial"""

		#TODO: if the condition list is exhausted, force through the remainder recordings.

		#print ("Playback Sequence i: " + str(self.playbacksequence_i))
		playback_or_stock = self.PlaybackStock_SequenceIndex[self.playbacksequence_i] #if 1==Playback a real trial. If 2==Playback a stock trial		
		#print ("Playback or Stock: " + str(playback_or_stock))
		if playback_or_stock == 1: #Real playback
		#	print("Playback i: " + str(self.playback_i))			
			condition = self.PlaybackTrialOrder[self.playback_i] #select condition.
		#	print ("Playback Trial Order: ", self.PlaybackTrialOrder)
		#	print ("Playback Condition: " + str(condition))
			conditioncount = int(self.PlaybackRecord[condition])	
			print("Playback Record ", self.PlaybackRecord)	
	#		print ("Playback Count: " + str(conditioncount))
			filename = str(self.EXP_BLOCK) + "_" + str(self.demographics[0]) + "_0_" + str(condition) + "_" + str(int(conditioncount)) + ".csv" #"_" + str(int(self.sectionorder)) + ".csv" #PP_sectiontype_condition_conditioncount

			#Here look up filename. If not produced, load the backup trial.
			mypath = os.curdir + os.sep + 'Data' + os.sep + filename 
			print ("Looking for: " + mypath)
			print (os.path.exists(mypath))
			if os.path.exists(mypath):
				# print ("Found")
				pass
			else:
				filename = "backup_attract.csv" #TODO: randomly select condition with backup? 				


		elif playback_or_stock == 2: #Stock recording
			condition = self.StockTrialOrder[self.stock_i]
			print ("Stock Record: ", self.StockRecord)
			print ("Stock Condition: ", condition)			
			filename = "stock_" + str(condition) + ".csv" #stock_condition		

			#filename = "stock_attract.csv"	
		else:
			raise Exception ("Invalid trialtype")

		print(filename)

		# choose = self.pickrandom([0,1]) #random choice between 0 & 1
		# if choose == 1:
		# 	filename = "stock_avoid.csv"
		# elif choose == 0:
		# 	filename = "stock_attract.csv"
		# filename = "stock_attract.csv"


		return filename

	def OrderTrials(self):
		"""Determine pseudorandom sequence of manual, playback, and stock trials. Manual Trials = playback + stock trials"""

		
		backupcount = 1

		while backupcount > 0:

			##BANK MODE###	
			BANKSEQ = range(0,self.NCndts)* self.BankTrials #two trials of each condition
			#print ("Bankseq: ", BANKSEQ)
			np.random.shuffle(BANKSEQ)
			self.BankTrialOrder = list(BANKSEQ)
			print ("BankTrialOrder ", self.BankTrialOrder)

			#Active Trials - BANKMODE
			MANSEQ = range(0,self.NCndts)*(self.TrialsPerCondition-self.BankTrials)
			np.random.shuffle(MANSEQ) 
			self.ManualTrialOrder = list(MANSEQ) #randomised order of manual trials
			print ("Manual Trial Order: ", self.ManualTrialOrder)

			if self.PRACTICEMODE:

				#jump straight to automation
				# self.BankTrialOrder = [1]
				# self.ManualTrialOrder = [1,2]

				self.StockTrialOrder = [10,11]
				self.PlaybackStock_SequenceIndex = [2,2]
				backupcount = 0
				break

			else:

				TRIALSEQ = range(0,self.NCndts)*(self.TrialsPerCondition/2)
				np.random.shuffle(TRIALSEQ) 
				self.PlaybackTrialOrder = list(TRIALSEQ) #randomised order of playback trials
				print ("Playback Trial Order: ", self.PlaybackTrialOrder)		
				np.random.shuffle(TRIALSEQ) 
				self.StockTrialOrder = list(TRIALSEQ) #randomised order of stock trials [at the moment there is 6 stock trials per condition]
				print ("Stock Trial Order: ", self.StockTrialOrder)
				
				#Randomly interleave real and false trials. There is the same amount of stock trials as matched triaals
				sequence = range(1,3)*self.TotalMatchedTrials #sequence of 1,2.
				np.random.shuffle(sequence)		
				self.PlaybackStock_SequenceIndex = list(sequence)
				print ("PlaybackStock_Sequence: ", self.PlaybackStock_SequenceIndex)	

				backupcount = self.EstimateCompletionTime()

		#PRACTICE EXPERIMENT HACKS - LENGTH MUST BE SAME AS self.StockTrialOrder
		# self.PlaybackStock_SequenceIndex = [2,2]
		
	def txtmode_visibility(self, vis):
		
		self.txtMode.visible(vis)

	def EstimateCompletionTime(self):
		"""Estimates completion time based on current randomisation"""

		trialtime = 25 #length of each trial
		trials = 0 #trials that are part of main sequence
		backupcount = 0 #plug trials due to not finding correct trial
		excesscount = 0 #unneeded manual trials

		unplayedrecord = range(0,self.NCndts)

		#first, loop through bank trials.
		for i in self.BankTrialOrder:
			unplayedrecord[i] += 1
			trials += 1
		
		#then simulate the experiment design
		play_i = 0
		man_i = 0
		sequence_i = 0
		
		while sequence_i < len(self.PlaybackStock_SequenceIndex):
			i = self.PlaybackStock_SequenceIndex[sequence_i]
			#immediately after bank trials there is an automated trial.
			if i == 1:
				#playback
				replay_trialtype = self.PlaybackTrialOrder[play_i] #get playback type
				bankcount = unplayedrecord[replay_trialtype] #retrieve any unplayed conditions
				if bankcount > 0: #if there exists unplayed trials
					trials += 1
					unplayedrecord[replay_trialtype] -= 1 #remove the unplayed trial
					play_i += 1 #increment playback index
					sequence_i += 1 #increment sequence index										
				else:
					backupcount += 1 #play a backup trial
			elif i == 2:
				#stock
				trials += 1 #add a trial
				sequence_i += 1
			
			#then play the manual trial
			if man_i < len(self.ManualTrialOrder):
				manual_trialtype = self.ManualTrialOrder[man_i]
				unplayedrecord[manual_trialtype] += 1
				man_i += 1
				trials += 1
			else:
				excesscount += 1

		print("estimated valid trials:", trials)
		print("estimated backup count:", backupcount)
		print("estimated excess count:", excesscount)
		totaltrials = trials + backupcount + excesscount

		totaltime = totaltrials * trialtime	
			
		msg = "estimated experiment time at {}s per trial".format(trialtime)
		print(msg, totaltime/60.0)
		
		return(backupcount)

	####################################################
	# FUNCTIONS THAT DEAL WITH CATCHING ERRONEOUS TRIALS
	####################################################

	
	def ErrorCatch(self, data):

		"""returns True if trials meets error requirements"""

		"""
		Three step error catch process. 

		1) High Steering Bias (leaving the road)
		2) Missing or going through the obstacles counter to instructions
		3) High frequency steering wheel actions.
		"""

		Passed = False

		#ERROR FILTER 1#
		#If steering bias is greater than roadwidth, they have left the road
		steeringbias = data.get("steeringbias")
		maxerror = max(abs(steeringbias))
		#print ("MAX ERROR: ", maxerror) 
		if maxerror > 1.5:			
			Passed = False
		else:
			Passed = True
		#print ("Passed Steering Bias: ", Passed)

		#ERROR FILTER 2#
		#Determine whether the driver pass through, or correctly avoided, the targets.
		
		if Passed:
			Passed = self.TargetSuccess(data)
		#	print ("Passed Obstacle Success: ", Passed)
		
		return Passed
	
	def TargetSuccess(self, data):
		"""Returns True if driver correctly dealt with the targets"""

		Passed = False
		obstaclecolour = data.get("obstaclecolour")[0]
		obstacleoffset = data.get("obstacleoffset")[0]

		posz = data.get("posz")
		

		BoundaryBox = .5 #Box with the same size as the radius of targets. #TODO: do not hardcode.
		
		success = 0

		#TODO: alter depending on offset.
		
		for i, tp in enumerate(self.targetpositions):
			
			#here, match the z values up to the obstacles.
			#print ("Target Postion: ")
			#print (tp)

			tp_z = tp[2]
			min_z = tp_z-BoundaryBox
			max_z = tp_z +BoundaryBox			

			lowerbound = posz > min_z
			upperbound = posz < max_z
			data_targetregion = data.loc[lowerbound & upperbound, :] #picks all the x values within upper and lower z bounds. Will also contain positions on the other side of the track (before bend), but this isn't a problem

#			print("\n Data_TargetRegion: ")
			#print(data_targetregion)

			if len(data_targetregion) > 0: #only investigate further if obstacle is in trial.
				posx_targetregion = data_targetregion.get("posx") #could I get this directly? AS in [lowerbound & upperbound, "posx"]?

				#print ("ObstacleColour: ", int(obstaclecolour))				
				offset = obstacleoffset * self.targetdeflections[i]
				tp_x = tp[0] + offset
				min_x = tp_x - BoundaryBox
				max_x = tp_x + BoundaryBox

				#print ("Boundaries: ", min_x, max_x)

				#print ("\n Posx_Target:")
				#print (posx_targetregion)
				
				lower = posx_targetregion > min_x
				upper = posx_targetregion < max_x
				#posx_inZone = posx_targetregion[lowerbound & upperbound] #picks all the x values within upper and lower z bounds. Will also contain positions on the other side of the track (before bend), but this isn't a problem
				mask = (posx_targetregion > min_x) & (posx_targetregion < max_x)	
				posx_inZone = posx_targetregion[mask]

				#print ("\n Posx_InZone:")
				#print (posx_inZone)

				#Depending on obstacle colour, if posx_inZone contains (or does not contain) anything set success flag.
				if len(posx_inZone) > 0:
					if obstaclecolour == 0:
						#if trial is 'attract', then len() > 0 is a good thing.
						#print ("SUCCESS")
						success += 1
					else:
						#print ("FAILURE")
						pass
				else:
					if obstaclecolour == 1:
						#if trial is 'aviod', then len() == 0 is a good thing.
						#print ("SUCCESS")
						success += 1
					else:
						#print ("FAILURE")
						pass

		print ("Targets Responded Successfully: " + str(success))
		if success >= 2: #If at least two targets out of the three were responding to correctly. Should this be three? 
			Passed = True
		
		return Passed

	#################################################
	# FUNCTIONS THAT DEAL WITH ORGANISING THE SCENE #
	################################################
				
	def MirrorRoundTrackOrigin(self, pos, ori):
		"""mirrors pos & yaw round any given track origin"""
		
		pos[0] = self.trackorigin[0]+(self.trackorigin[0]-pos[0]) #mirror x 
		pos[2] = self.trackorigin[1]+(self.trackorigin[1]-pos[2]) #mirror z
		
		ori[0] = ori[0]+180.0
		ori[0] = vizmat.NormAngle(ori[0])
		
		return [pos,ori]

	def getNormalisedEuler(self):
		"""returns three dimensional euler on 0-360 scale"""
		
		euler = self.view.getEuler()
		
		euler[0] = vizmat.NormAngle(euler[0])
		euler[1] = vizmat.NormAngle(euler[1])
		euler[2] = vizmat.NormAngle(euler[2])

		return euler	

	def ChangeObstacleColour(self):
		"""changes target colour depending on self.obstaclecolour"""	

		#print ("Changing obstacle colour: " + str(self.obstaclecolour))
		if self.obstaclecolour == 0:
			for t in self.targets:
				t.color(viz.BLUE)
		elif  self.obstaclecolour == 1:
			for t in self.targets:
				t.color(viz.RED)

	def ChangeObstacleOffset(self):
		"""changes obstacle offset depending on self.obstaclecolour"""

		#print ("Changing obstacle Offset: " + str(self.obstacleoffset))
		
		
		for i, tpos in enumerate(self.targetpositions):			
			offsetpos = list(tpos)
			# print(type(offsetpos), type(tpos))
			#print(id(offsetpos), id(tpos))			
			offsetpos[0] = offsetpos[0] + (self.obstacleoffset * self.targetdeflections[i]) #calculate offset			
			target = self.targets[i] #retrieve target			 
			target.setPosition(offsetpos) #set to new offset position
			tcentre = self.targetcentres[i] #do the same for centre.
			tcentre.setPosition(offsetpos)
			

	def setObstacles(self, trialtype):
		""" sets obstacles depending on trialtype"""
		
		print("TRIAL TYPE: " + str(trialtype))

		# #set obstacle colour
		self.obstaclecolour = self.ConditionList_obstaclecolour[trialtype]


		# if trialtype in self.attract:
		# 	self.obstaclecolour = 0
		# elif trialtype in self.avoid:
		# 	self.obstaclecolour = 1
		# else:
		# 	raise Exception("Colour Trial Type not recognised")



		# #set offset 
		self.obstacleoffset = self.ConditionList_obstacleoffset[trialtype]

		# if trialtype in self.narrow:
		# 	self.obstacleoffset = self.FACTOR_obstacleoffset[0]
		# elif trialtype in self.wide:
		# 	self.obstacleoffset = self.FACTOR_obstacleoffset[1]
		# else:
		# 	raise Exception("Offset Trial type not recognised")
		
		self.ChangeObstacleColour()
		self.ChangeObstacleOffset()
	
	##################################
	# QUIT FUNCTIONS ################
	##################################

	def Quit(self):
		
		"""sets quit flag"""
		##cannot call viz.quit from this class. Need to call it in the core viz.go() script.
		#print("calling quit")
		self.QUITFLAG = True
		
		
	def GetQuitFlag(self):
		
		return self.QUITFLAG

	def SendAnnotationAndSaveData(self, prefix, filename, data):
		"""finishes section by sending annotation to comms and saving trialdata"""

		#send annotation
		if self.EYETRACKING:						
			msg = prefix + " " + filename
			self.comms.annotate(msg)
								
		viz.director(self.SaveTrial, data, filename)

	
	def SaveTargetData(self):
		"""Saves CSV of necessary target info for post-processing metric derivation"""
		
		savetargetdata = pd.DataFrame(columns=['targetindex','condition','xcentre','zcentre','centre_radius','target_radius'])
		centre_radius = .2
		target_radius = .5
		df_i = 0

		#list through targets and calculate all the position deviations for each condition
		for i, tpos in enumerate(self.targetpositions):
			offsetpos = list(tpos)					
			xpos = offsetpos[0]
			zpos = offsetpos[2]
			for condition in self.ConditionList:			
				
				obstacleoffset = self.ConditionList_obstacleoffset[condition]					
				new_xpos = xpos + (obstacleoffset * self.targetdeflections[i]) #calculate offset			

				output = [i,condition, new_xpos, zpos, centre_radius, target_radius] 
				
				savetargetdata.loc[df_i,:] = output				

				df_i += 1
		
		t = time.time() #add t so do not overwrite. 

		#savetargetdata.to_csv("TrackData//TargetPositions_" + str(t) + ".csv")
		savetargetdata.to_csv("TrackData//TargetPositions.csv")

#####################################
##	OTHER FUNCTIONS	 ###############
#####################################

def pickrandom(arr):
	"""returns a single integer from an array"""
	n = len(arr)
	i = np.random.randint(0,n)
	a = arr[i]
	return a	

def SingleBeep(audio):
	"""Plays a single beep"""

	#print "BEEP"
	audio.play() 

def DoubleBeep(audio):
	"""Plays a double beep"""

#	print "BEEP"
	audio.play()

	viz.waitTime(.5)

	audio.play()
	


