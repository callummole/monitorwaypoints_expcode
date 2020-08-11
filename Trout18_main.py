import sys 
import vizshape

#add rootpath for shared_modules
rootpath = 'C:\VENLAB data\shared_modules\Logitech_force_feedback'
sys.path.append(rootpath)
rootpath = 'C:\VENLAB data\shared_modules'
sys.path.append(rootpath)
rootpath = 'C:/VENLAB data/shared_modules/pupil/capture_settings/plugins/drivinglab_pupil/'
sys.path.append(rootpath)

#rootpath = 'C:\Program Files\WorldViz\Vizard5\python'
#sys.path.append(rootpath)

"""
Wheel fix attempts:
Downloaded window cleaner from - https://community.logitech.com/s/feed/0D531000050zd9DCAQ
Tried logitech gaming software 5.10.127 and also the last 9.x.x versions.
"""

AUTOWHEEL = True
EYETRACKING = True
PRACTICE = False #flag for whether in practice mode or not.

if PRACTICE: #HACK
	EYETRACKING = False

if AUTOWHEEL: 
	import logitech_wheel_threaded
import viz # vizard library
import numpy as np # numpy library - such as matrix calculation
import random # python library
import vizdriver #vizard library
import viztask # vizard library
import math as mt # python library
#import eyetrike
import pandas as pd
import vizTrialManager
import time
import myCave
import PPinput
import os
import gzip

if EYETRACKING:
	from eyetrike_calibration_standard import Markers, run_calibration
	from eyetrike_accuracy_standard import run_accuracy
	from UDP_comms import pupil_comms
	import pupil_logger

"""
Code generates an oval track (two straights, two constant curvature bends). 
This track can be splined into automated and manual sections.
the automated section should be a repeat of the steering wheel angle performance in the manual section
so I will need an interpolating step matching position at start of automation with start of manual.
"""
if EYETRACKING: 
	###Connect over network to eyetrike and check the connection
	comms = pupil_comms() #Initiate a communication with eyetrike	
	#Check the connection is live
	connected = comms.check_connection()

	if not connected:
		print("Cannot connect to Eyetrike. Check network")
		raise Exception("Could not connect to Eyetrike")
	else:
		pass	
	#markers = Markers() #this now gets added during run_calibration	
		
else:
	comms = []


global ExpID, out, autoflag
ExpID = "Trout18"
out = ""
autoflag = 0 #1 for automation, 0 for manual

# start empty world
###################  PERSPECTIVE CORRECT  ##################
cave = myCave.initCave()
caveview = cave.getCaveView()
viz.clip(1,100) #clips world at Xm #Not sure whether the cave or viz.clip is responsible now.


#global TrialStore
#TrialStore = {} #dictionary that contains all the trial info for playing back.

###Experiment parameters
global TotalTrials, mywheel, driver
if PRACTICE:
	TotalTrials = 1
else:
	# THE EXPERIMENT IS IN TWO BLOCKS. SO PUT HALF THE REQUIRED TRIALS.
	#poorly named variable. Amount of trials kept in each condition is TotalTrials/2.
	#For TotalTrials = 2 we should run in six blocks.
	TotalTrials = 2 #must be even, since the length of Playback and Stock is TotalTrials / 2. 


handle = viz.window.getHandle()

if AUTOWHEEL:
	#Create a steeringWheel instance
	mywheel = logitech_wheel_threaded.steeringWheelThreaded(handle)	
	mywheel.init() #Initialise the wheel
	mywheel.start() #Start the wheels thread

	#centre the wheel at start of experiment
	mywheel.set_position(0) #Set the pd control target
	mywheel.control_on()
else:
	mywheel = None

#need to initialise wheel, driver, and totalTrials to pass to trialmanager

#function to make track
def TrackMaker(sectionsize, colour = viz.WHITE):
	
	"""adds oval track with double straight. Returns 4 variables: midline, origin, section breaks, track details"""
	#at the moment each straight or bend is a separate section. So we can alter the colour if needed. But more efficient to just create one line per edge.

	"""
       ________
	 /   _B__   \ 
	/	/    \   \ 
	| A |    | C |
   _|   |    |   |_
   _| H |    | D |_
	|	|	 |   |
	| G	|	 | E |
	\	\___ /   /
     \ ____F___ /


	A = Empty Straight 
	B = Constant curvature Bend
	C = Straight with Targets.
	D = Interp period (Length = StraightLength / 2.0)
	E = Empty Straight
	F = Constant curvature bend
	G = Straight with Targets
	H = Interp period (Length = StraightLength / 2.0)

	TrackOrigin, centre of track = 0,0. Will be half-way into the interp period.

	"""


	#Start at beginning of 1st straight.
	StraightLength = 40.0 #in metres. 
	InterpProportion = 1.0 #Length of interpolation section relative to the straight sections
	InterpLength = StraightLength * InterpProportion
	InterpHalf = InterpLength / 2.0
	BendRadius = 25.0 #in metres, constant curvature bend.
	SectionSize = sectionsize
	roadwidth = 3.0/2.0
	right_array = np.linspace(np.pi, 0.0, SectionSize) 
	left_array= np.linspace(0.0, np.pi,SectionSize)
	
	TotalStraightLength = (StraightLength*2) + InterpLength
	
	#trackorigin = [BendRadius, StraightLength/2.0] #origin of track for bias calculation
	trackorigin = [0.0, 0.0]
	trackparams = [BendRadius, StraightLength, InterpLength, SectionSize, InterpProportion]

	#For readability set key course markers. Use diagram for reference
	LeftStraight_x = -BendRadius
	RightStraight_x = BendRadius
	Top_Interp_z = InterpHalf
	Top_Straight_z = InterpHalf+StraightLength
	Bottom_Interp_z = -InterpHalf
	Bottom_Straight_z = -InterpHalf-StraightLength
		
	def StraightMaker(x, start_z, end_z, colour = viz.WHITE, primitive= viz.QUAD_STRIP, width=None):
		"""returns a straight, given some starting coords and length"""
		viz.startlayer(primitive)
		if width is None:
			if primitive == viz.QUAD_STRIP:
				width = .05
			elif primitive == viz.LINE_STRIP:
				width = 2
				viz.linewidth(width)
				width = 0
		
		viz.vertex(x-width,.1,start_z)
		viz.vertexcolor(colour)
		viz.vertex(x+width,.1,start_z)
		viz.vertexcolor(colour)
		viz.vertex(x-width,.1,end_z)
		viz.vertexcolor(colour)
		viz.vertex(x+width,.1,end_z)		

		straightedge = viz.endlayer()

		return straightedge
	
	
	def BendMaker(startpos, size, rads, array, sign = 1, colour = viz.WHITE, primitive = viz.QUAD_STRIP, width=None):
		"""Returns a  bend"""
		#make sign -1 if you want a left bend.
		#improve to have a flag if it's a quad, and the quad width.

		#put default widths if not given
				
		i = 0
		viz.startlayer(primitive) 	

		if width is None:
			if primitive == viz.QUAD_STRIP:
				width = .05
			elif primitive == viz.LINE_STRIP:
				width = 2
				viz.linewidth(width)
				width = 0
		
		viz.vertex(startpos[0], .1, startpos[2]) #start at end of straight
		while i < SectionSize:			
			x1 = ((rads-width)*np.cos(array[i])) #+ BendRadius
			z1 = sign*((rads-width)*np.sin(array[i])) + startpos[2]
			
			#print (z1[i])			
			viz.vertex(x1, .1, z1)				
			viz.vertexcolor(colour)

			if primitive == viz.QUAD_STRIP:
				x2 = ((rads+width)*np.cos(array[i])) #+ BendRadius
				z2 = sign*((rads+width)*np.sin(array[i])) + startpos[2]
				viz.vertex(x2, .1, z2)				
				viz.vertexcolor(colour)

			i += 1
			
		Bend = viz.endlayer()

		return Bend

	def getLastPosition(road, primitive = viz.QUAD_STRIP):
		"""returns last vertex x,y,z of road"""

		if primitive == viz.LINE_STRIP:
			endpos = road.getVertex(-1)
		elif primitive == viz.QUAD_STRIP:
			ep1 = road.getVertex(-1)
			ep2 = road.getVertex(-2)
			endpos = [((ep1[0]+ep2[0])/2.0),((ep1[1]+ep2[1])/2.0),((ep1[2]+ep2[2])/2.0)]

		return (endpos)

	#first straight, A.
	#outside edge
	StraightA_Outside = StraightMaker(LeftStraight_x-roadwidth, Top_Interp_z, Top_Straight_z, colour = colour)

	#inside edge
	StraightA_Inside = StraightMaker(LeftStraight_x+roadwidth, Top_Interp_z, Top_Straight_z, colour = colour)
		
	#first corner, B. #might be neater to do this as a child of the straight.
	#outside 
	startpos = getLastPosition(StraightA_Outside)
	BendB_Outside = BendMaker(startpos, SectionSize, BendRadius+roadwidth, right_array, colour = colour)
		
	#inside
	startpos = getLastPosition(StraightA_Inside)
	BendB_Inside = BendMaker(startpos, SectionSize, BendRadius-roadwidth, right_array, colour = colour)
	
	#Second straight, C
	#outsiide
	startpos = getLastPosition(BendB_Outside)
	StraightC_Outside  = StraightMaker(startpos[0], startpos[2], startpos[2]-StraightLength, colour = colour)
	
	#inside
	startpos = getLastPosition(BendB_Inside)
	StraightC_Inside  = StraightMaker(startpos[0], startpos[2], startpos[2]-StraightLength, colour = colour)

	#First Interp Period, D
	#outsiide
	startpos = getLastPosition(StraightC_Outside)
	InterpD_Outside = StraightMaker(startpos[0], startpos[2], startpos[2]-InterpLength, colour = colour)
	
	
	#inside
	startpos = getLastPosition(StraightC_Inside)
	InterpD_Inside = StraightMaker(startpos[0], startpos[2], startpos[2]-InterpLength, colour = colour)
	
	#Third Straight, E.
	startpos = getLastPosition(InterpD_Outside)
	StraightE_Outside = StraightMaker(startpos[0], startpos[2], startpos[2]-StraightLength, colour = colour)
	
	#inside
	startpos = getLastPosition(InterpD_Inside)
	StraightE_Inside = StraightMaker(startpos[0], startpos[2], startpos[2]-StraightLength, colour = colour)


	#Second Bend, F.
	#outside
	startpos = getLastPosition(StraightE_Outside)
	BendF_Outside = BendMaker(startpos, SectionSize, BendRadius+roadwidth, left_array, -1, colour = colour)
	
	#inside
	startpos = getLastPosition(StraightE_Inside)
	BendF_Inside =  BendMaker(startpos, SectionSize, BendRadius-roadwidth, left_array, -1, colour = colour)

	#Fourth Straight, G.
	#outside
	startpos = getLastPosition(BendF_Outside)
	StraightG_Outside = StraightMaker(startpos[0], startpos[2], startpos[2]+StraightLength, colour = colour)
	
	#inside
	startpos = getLastPosition(BendF_Inside)
	StraightG_Inside = StraightMaker(startpos[0], startpos[2], startpos[2]+StraightLength, colour = colour)

	#Second Interp Period, H.
	#outside
	startpos = getLastPosition(StraightG_Outside)
	InterpH_Outside = StraightMaker(startpos[0], startpos[2], startpos[2]+InterpLength)
	
	#inside
	startpos = getLastPosition(StraightG_Inside)
	InterpH_Inside = StraightMaker(startpos[0], startpos[2], startpos[2]+InterpLength)
	
	###create unbroken midline. 1000 points in each section.	
	#at the moment this is a line so I can see the effects. But this should eventually be an invisible array.
	#straight	
	#The interp periods have index numbers of sectionsize / 4. So midline size = SectionSize * 7 (6 sections + two interps)
	midlineSize = SectionSize* (6 + 2 * InterpProportion)
	midline = np.zeros((int(midlineSize),2))

	SectionBreaks = []
	SectionBreaks.append(0)
	SectionBreaks.append(int(SectionSize)) #end of StraightA #1
	SectionBreaks.append(int(SectionSize*2)) #end of BendB #2
	SectionBreaks.append(int(SectionSize*3)) #end of StraightC #3
	SectionBreaks.append(int(SectionSize* (3 + InterpProportion))) #end of InterpD #4
	SectionBreaks.append(int(SectionSize*(4 + InterpProportion))) #end of StraightE #5
	SectionBreaks.append(int(SectionSize*(5 + InterpProportion))) #end of BendF #6
	SectionBreaks.append(int(SectionSize*(6 + InterpProportion))) #end of StraightG #7
	SectionBreaks.append(int(SectionSize*(6 + 2*InterpProportion))) #end of InterpH #8

	#Straight A
	StraightA_z = np.linspace(Top_Interp_z, Top_Straight_z, SectionSize)
	midline[SectionBreaks[0]:SectionBreaks[1],0] = LeftStraight_x
	midline[SectionBreaks[0]:SectionBreaks[1],1] = StraightA_z

	#print (SectionBreaks)
	#print (midline[SectionBreaks[0]:SectionBreaks[1],:])
		
	#Bend B
	i=0
	while i < SectionSize:
		x = (BendRadius*np.cos(right_array[i])) #+ BendRadius 
		z = (BendRadius*np.sin(right_array[i])) + (Top_Straight_z)
		midline[i+SectionBreaks[1],0] = x
		midline[i+SectionBreaks[1],1] = z
		#viz.vertex(x,.1,z)
		#viz.vertexcolor(viz.WHITE)
		xend = x
		i += 1
	
	#StraightC
	rev_straight = StraightA_z[::-1] #reverse
	midline[SectionBreaks[2]:SectionBreaks[3],0] = xend
	midline[SectionBreaks[2]:SectionBreaks[3],1] = rev_straight
	
#		
# 	#InterpD
	InterpD_z = np.linspace(Top_Interp_z, Bottom_Interp_z, int(SectionSize*InterpProportion))
	midline[SectionBreaks[3]:SectionBreaks[4],0] = xend
	midline[SectionBreaks[3]:SectionBreaks[4],1] = InterpD_z

	#StraightE
	StraightE_z = np.linspace(Bottom_Interp_z, Bottom_Straight_z, SectionSize)
	midline[SectionBreaks[4]:SectionBreaks[5],0] = xend
	midline[SectionBreaks[4]:SectionBreaks[5],1] = StraightE_z

	#BendF
	i=0
	while i < SectionSize:
		x = (BendRadius*np.cos(left_array[i]))
		z = -(BendRadius*np.sin(left_array[i])) + (Bottom_Straight_z)
		midline[i+(SectionBreaks[5]),0] = x
		midline[i+(SectionBreaks[5]),1] = z
	#	viz.vertex(x,.1,z)
	#	viz.vertexcolor(viz.WHITE)
		xend = x
		i += 1
	
	#StraightG
	StraightG_z = np.linspace(Bottom_Straight_z, Bottom_Interp_z, SectionSize)
	midline[SectionBreaks[6]:SectionBreaks[7],0] = xend
	midline[SectionBreaks[6]:SectionBreaks[7],1] = StraightG_z

	#InterpG
	InterpG_z = np.linspace(Bottom_Interp_z, Top_Interp_z, int(SectionSize*InterpProportion))
	midline[SectionBreaks[7]:SectionBreaks[8],0] = xend
	midline[SectionBreaks[7]:SectionBreaks[8],1] = InterpG_z

	TrackData = []
	TrackData.append(midline)
	TrackData.append(trackorigin)
	TrackData.append(SectionBreaks)
	TrackData.append(trackparams)

	#save track data.
	track_df = pd.DataFrame(columns = ['midline_x', 'midline_z', 'leftedge_x', 'left_edge_z', 'rightedge_x','right_edge_z','origin_x','origin_z','bendradius','straightlength'])

	track_df['midline_x'] = midline[:,0]
	track_df['midline_z'] = midline[:,1]
	track_df['origin_x'] = trackorigin[0]
	track_df['origin_z'] = trackorigin[1]
	track_df['bendradius'] = BendRadius
	track_df['straightlength'] = TotalStraightLength

	track_df.to_csv('TrackData//TrackData.csv')

	return TrackData

	#midline = viz.endlayer()	
#	
	# import matplotlib.pyplot as plt	
	
	# plt.figure()
	# plt.plot(midline[:,0], midline[:,1], 'b.')
	# #plt.plot(midline[3000,0],midline[3000,1],'r.')
	# plt.axis('equal')	
	# plt.show()
#	
def AddObstacles(trackdetails):

	"""draws and returns a set of chicane targets. Needs to be called after TrackMaker()"""

	#add circular targets
	"""
	Adds obstacles to Straights C and G. See Trackmaker() for reference.

	"""
	
	radius = trackdetails[0]
	straightL = trackdetails[1]
	interpL = trackdetails[2]
	StraightG_bottom = -(interpL/2.0) - straightL
	StraightC_top = (interpL/2.0) + straightL
	
	fifth = straightL/5.0

	#offset = .75

	targetpositions = []
	targetpositions.append([-radius,0.1,StraightG_bottom+(fifth*1)])
	targetpositions.append([-radius,0.1,StraightG_bottom+(fifth*2)])
	targetpositions.append([-radius,0.1,StraightG_bottom+(fifth*3)])
	targetpositions.append([radius,0.1,StraightC_top-(fifth*3)])
	targetpositions.append([radius,0.1,StraightC_top-(fifth*2)])
	targetpositions.append([radius,0.1,StraightC_top-(fifth*1)])

	targetdeflections = [1, -1, 1, -1, 1, -1] # determines offset deflections.
	
	def MakeDisc(height, rads, position, colour):
		"""returns disc"""

		disc = vizshape.addCylinder(height=height, radius=rads,topRadius=None,bottomRadius=None,axis=vizshape.AXIS_Y,slices=30,bottom=True,top=True,lighting=False) 
		disc.color(colour)
		disc.setPosition(position)

		return disc
	
	#StraightG
	target1 = MakeDisc(.005, .5, targetpositions[0], viz.BLUE)
	target2 = MakeDisc(.005, .5, targetpositions[1], viz.BLUE)
	target3 = MakeDisc(.005, .5, targetpositions[2], viz.BLUE)

	targetA = MakeDisc(.0051, .2, targetpositions[0], viz.GRAY)
	targetB = MakeDisc(.0051, .2, targetpositions[1], viz.GRAY)
	targetC = MakeDisc(.0051, .2, targetpositions[2], viz.GRAY)

	#StraightC
	target4 = MakeDisc(.005, .5, targetpositions[3], viz.BLUE)
	target5 = MakeDisc(.005, .5, targetpositions[4], viz.BLUE)
	target6 = MakeDisc(.005, .5, targetpositions[5], viz.BLUE)

	targetD = MakeDisc(.0051, .2, targetpositions[3], viz.GRAY)
	targetE = MakeDisc(.0051, .2, targetpositions[4], viz.GRAY)
	targetF = MakeDisc(.0051, .2, targetpositions[5], viz.GRAY)	
	
	targets = []
	#Main Obstacles
	targets.append(target1)
	targets.append(target2)
	targets.append(target3)
	targets.append(target4)
	targets.append(target5)
	targets.append(target6)

	#Obstacle Centre.
	targetcentres = []
	targetcentres.append(targetA)
	targetcentres.append(targetB)
	targetcentres.append(targetC)
	targetcentres.append(targetD)
	targetcentres.append(targetE)
	targetcentres.append(targetF)

	TargetData = []
	TargetData.append(targets)
	TargetData.append(targetcentres)
	TargetData.append(targetpositions)
	TargetData.append(targetdeflections)

	return TargetData
	
def setStage():
		
	"""adds groundplane and texture"""
	
	global groundplane, groundtexture
	
	###should set this hope so it builds new tiles if you are reaching the boundary.
	fName = 'C:/VENLAB data/shared_modules/textures/strong_edge.bmp'
	
	# add groundplane (wrap mode)
	groundtexture = viz.addTexture(fName)
	groundtexture.wrap(viz.WRAP_T, viz.REPEAT)	
	groundtexture.wrap(viz.WRAP_S, viz.REPEAT)	
	
	groundplane = viz.addTexQuad() ##ground for right bends (tight)
	tilesize = 500
	planesize = tilesize/5
	groundplane.setScale(tilesize, tilesize, tilesize)
	groundplane.setEuler((0, 90, 0),viz.REL_LOCAL)
	#groundplane.setPosition((0,0,1000),viz.REL_LOCAL) #move forward 1km so don't need to render as much.
	matrix = vizmat.Transform()
	matrix.setScale( planesize, planesize, planesize )
	groundplane.texmat( matrix )
	groundplane.texture(groundtexture)
	groundplane.visible(1)	
	
	viz.clearcolor(viz.SKYBLUE)

exit_callbacks = []
def runtrials():
	
	#global autoflag, midline, trackorigin, TotalTrials, mywheel, midline, driver
	#initalise recording & reset time
	
	
	if PRACTICE:
		demographics = [0, 0, 0, 0, 0, 0]
		viz.mouse.setVisible(viz.OFF)		
		
	else:
		viz.pause()
		form = PPinput.MyForm(title = "Demographics")		
		viz.mouse.setVisible(viz.ON)

		viz.link(viz.MainWindow.CenterCenter,form)

		#wait for input
		yield form.show()
		
		viz.link(viz.MainWindow.CenterCenter,form)	

		while True:

			if form.accepted:
				
				ID = form.pp_id.get()
				print ('ID:', ID)
				if ID == '':
					ID = 99

				Age = form.pp_age.get()
				print ('Age:', Age)
				if Age == '':
					Age = 99
				
				Block = form.block.get()
				print ('Block:', Block)
				if Block == '':
					Block = 99

				Gender = 99
				if form.Fem.get():
					Gender = 1
				elif form.Mal.get():
					Gender = 2
				elif form.Oth.get():
					Gender = 3
				elif form.Pref.get():
					Gender = 4

				print ('Gender:', Gender)

				Vision = 99
				if form.VisYes.get():
					Vision = 1
				elif form.VisNo.get():
					Vision = 0

				DLyrs = form.DLyrs.get()
				if DLyrs == '':
					DLmnths = 99
				else:
					DLmnths = int(round(float(DLyrs) * 12)) #convert to months.				

				print ('Gender:', Gender)

				demographics = [int(ID), int(Age), int(Block), Gender, int(Vision), int(DLmnths)]	
				viz.mouse.setVisible(viz.OFF)				
				viz.play()
				break

		if EYETRACKING:
			filename = "Trout_" + str(demographics[0]) + "_" + str(demographics[2]) #add experimental block to filename
			print (filename)

			# Start logging the pupil data
			pupilfile = gzip.open(
				os.path.join("Data", filename + ".pupil.jsons.gz"),
				'a')
			closer = pupil_logger.start_logging(pupilfile, timestamper=viz.tick)
			def stop_pupil_logging():
				closer()
				pupilfile.close()
			exit_callbacks.insert(0, stop_pupil_logging)
				
			
			#start recording before calibration
				#initalise recording & reset time
			currtime = viz.tick()
			print ("Current Time to reset: ", currtime)
			comms.start_trial(filename, currtime)

			yield run_calibration(comms, filename)
			#yield run_accuracy(comms, filename)		

			#add markers after calibration.
			markers = Markers()

		#pass
#	viz.play()	
	
	setStage() #draw groundplane
	sectionsize = 10000
	TrackData = TrackMaker(sectionsize, colour = [.9,.9,.9]) #draw track and calculate midline.
	TargetData = AddObstacles(TrackData[3]) #trackmaker should get called, passing track parameters

	viz.message('\t\tEXPERIMENT INSTRUCTIONS \n\n1) Steer within the road-edges\n2) Steer over the centre of Blue Targets\n3) Steer between Red Targets\n4) A Single beep means you are now in manual control. \n5) A Double beep means that the automated system is now in control.\n6) During automation, keep hands loosely on the wheel as if steering, ready to take-over\n\t  	You will begin in manual control at full speed\n\n\t\t\tGet Ready...')	

	driver = vizdriver.Driver(caveview) #initialise driver
		
	#first off, try one trial.
	global trialendindex
	trialendindex = 2000 #keep it symmetrical. Length in midline pts.
	#datacolumns = ['pp_id','trialn','currtime','midlinepts','rawWheel','SWA','posx','posz','yaw','yawrate','steeringbias','autoflag']
	#trialstore = pd.Dataframe(columns=datacolumns)	
	#demographics = [pp_id]
	viz.MainScene.visible(viz.ON,viz.WORLD)		
	#eventually track position will be a class, similar to driver.

	# viz.play()

	##Will need to pass EYETRACKING comms to trial manager for annotations. The plan is to have on continous recording with annotations
	#trial manager takes care of everything else
	
	TrialManager = vizTrialManager.TrialManager(demographics, driver, mywheel, TrackData, TotalTrials, comms, EYETRACKING, caveview, TargetData, PRACTICE)
	
	yield viztask.waitTrue(TrialManager.GetQuitFlag) #wait until trialmanager is ready to quit.
	
	#then quit
	if EYETRACKING:
		markers.remove_markers() #remove markers
		yield run_accuracy(comms, filename)
	
	viz.MainScene.visible(viz.OFF,viz.WORLD)	
	TrialManager.txtmode_visibility(viz.OFF)
	
	CloseConnections()
			
	def QuitViz():
		quit = TrialManager.GetQuitFlag()

		#remove markers.
		
		#run accuracy test
#		yield run_accuracy(comms, filename)		

		if quit:
			CloseConnections()
			#markers.remove_markers()#
			#viztask.schedule(CloseConnections())
	#nested function that monitors all the necessary parameters.	
							
	#change to birdseye view so I can view the track.
	#viz.MainView.setPosition(30,150,25)
	#viz.MainView.setEuler(0,90,0)
	#vizact.ontimer((1.0/30.0),QuitViz)

def CloseConnections():
	
	"""Shuts down EYETRACKING and wheel threads then quits viz"""		
	
	print ("Closing connections")
	
	
	if EYETRACKING: 
#		yield run_accuracy(comms, filename)		
		comms.stop_trial() #closes recording			
	
	#kill automation
	if AUTOWHEEL:
		mywheel.thread_kill() #This one is mission critical - else the thread will keep going 
		mywheel.shutdown()	
	viz.quit()
exit_callbacks.append(CloseConnections)
def do_exit_callback():
	for cb in exit_callbacks:
		cb()
viz.callback(viz.EXIT_EVENT, do_exit_callback)
viztask.schedule(runtrials())

