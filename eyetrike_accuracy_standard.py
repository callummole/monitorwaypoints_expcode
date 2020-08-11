import numpy as np
import viztask
import viz
import vizinput
import sys 
import time 
import pdb


rootpath = 'C:/VENLAB data/shared_modules/pupil/capture_settings/plugins/drivinglab_pupil/'
sys.path.append(rootpath)

from UDP_comms import pupil_comms

"""
TODO: Save calibration data.
TODO: Pixel level calibration.

"""

class Markers:
	def __init__(self):
		

		#function to add headmarkers
		self.file_hm1 = 'C:/VENLAB data/shared_modules/textures/marker1_white.png'
		self.file_hm2 = 'C:/VENLAB data/shared_modules/textures/marker2_white.png'
		self.file_hm3 = 'C:/VENLAB data/shared_modules/textures/marker3_white.png'
		self.file_hm4 = 'C:/VENLAB data/shared_modules/textures/marker4_white.png'
		self.file_hm5 = 'C:/VENLAB data/shared_modules/textures/marker5_white.png'
		self.file_hm6 = 'C:/VENLAB data/shared_modules/textures/marker6_white.png'
		self.file_hm7 = 'C:/VENLAB data/shared_modules/textures/marker7_white.png'
	
		self.boxsize = [.8,.5] #xy box size
		self.lowerleft = [.1,.1] #starting corner
		#counter-scale it to adjust for the aspect ratio.
		defaultscale = 800.0/600.0
		aspect = 1920.0 / 1080.0
		
		scale = aspect/defaultscale
		
		#TODO: Relabel sc_v and sc_h so that they are correct.
		#TODO: Specify pixels in orthographic layer.
		sc = .8
		sc_v = .8
		sc_h = sc_v*scale
	
		#two ways of doing it
		#bottom left
		self.hm1 = viz.addTexQuad(parent=viz.SCREEN, scene=viz.MainWindow)
		self.hm1.texture(viz.add(self.file_hm1))
		self.hm1.setPosition([self.lowerleft[0],self.lowerleft[1],0])
		#self.hm1.setPosition([0,0,0])
		self.hm1.scale(sc_v,sc_h,sc)
		
		pixelh = 128*sc_v
		pixelv = 128*sc_h
		print("SizeH: ", 128*sc_v, "SizeV: ", 128*sc_h)
		print("BoxPixelSize: ", self.boxsize[0]*1920, self.boxsize[1]*1080)
		print("SurfacePixels: ", pixelh+(self.boxsize[0]*1920), pixelv+(self.boxsize[1]*1080))
		
		#top left
		self.hm2 = viz.add(viz.TEXQUAD,viz.SCREEN)
		self.hm2.texture(viz.add(self.file_hm2))	
		self.hm2.setPosition([self.lowerleft[0],self.lowerleft[1]+self.boxsize[1],0])
		self.hm2.scale(sc_v,sc_h,sc)
		
		#bottom right
		self.hm3 = viz.add(viz.TEXQUAD,viz.SCREEN)
		self.hm3.texture(viz.add(self.file_hm3))
		self.hm3.setPosition([self.lowerleft[0]+self.boxsize[0],self.lowerleft[1],0])
		self.hm3.scale(sc_v,sc_h,sc)
		
		#top right
		self.hm4 = viz.add(viz.TEXQUAD,viz.SCREEN)
		self.hm4.texture(viz.add(self.file_hm4))
		self.hm4.setPosition([self.lowerleft[0]+self.boxsize[0],self.lowerleft[1]+self.boxsize[1],0])
		self.hm4.scale(sc_v,sc_h,sc)
	
		#add middle markers
#		#middle top
#		self.hm5 = viz.add(viz.TEXQUAD,viz.SCREEN)
#		self.hm5.texture(viz.add(self.file_hm5))
#		self.hm5.setPosition([lowerleft[0]+boxsize[0]/2,lowerleft[1]+boxsize[1],0])
#		self.hm5.scale(sc,sc,sc)
		
		#middle top right
		self.hm6 = viz.add(viz.TEXQUAD,viz.SCREEN)
		self.hm6.texture(viz.add(self.file_hm6))
		self.hm6.setPosition([self.lowerleft[0]+(self.boxsize[0]*2)/3,self.lowerleft[1]+self.boxsize[1],0])
		self.hm6.scale(sc_v,sc_h,sc)
		
		#middle top left
		self.hm7 = viz.add(viz.TEXQUAD,viz.SCREEN)
		self.hm7.texture(viz.add(self.file_hm7))
		self.hm7.setPosition([self.lowerleft[0]+(self.boxsize[0]*1)/3,self.lowerleft[1]+self.boxsize[1],0])
		self.hm7.scale(sc_v,sc_h,sc)


def initialise_display():
	
	# viz.message('Calibration on Pupil Capture must be set to Manual Marker')
	
	#load scene for luminance.
	# start empty world
	EH = 1.2 #metres from ground.
	Eye_ScreenDist = 1 #distance from screen of ocular point
	Proj_V = 1.12 #measured on 18/01/18 #vertical extent of projection (m)
	Proj_H = 1.965 #horizontal extent of projection (m)

	# setting Field-of-View fov(vertical degree, horizontal ratio(vertical*ratio[deg]))
	vfov = ((np.arctan((Proj_V/2)/Eye_ScreenDist))*2) * (180/np.pi)
	h2v = Proj_H/Proj_V

	#viz.setDisplayMode(1920,1080)
	viz.go()
	viz.window.setSize(1920,1080)
	#viz.fov(vfov,h2v) #sets window aspect ratio.
	viz.fov(vfov,h2v) #sets window aspect ratio.
	#viz.window.setSize([1920,1080]) 
	#viz.window.setBorder(viz.BORDER_NONE)	
	#viz.window.setFullscreen(1)
	#viz.window.setFullscreenMonitor(2)
	#viz.window.setFullscreenRectangle( [0,0,1920,1080] )

	viz.eyeheight(1.2)#viz.MainView.setPosition(0,EH,0) 
	viz.clip(1,60) #clips world at 60m
	# background color
	viz.clearcolor(viz.SKYBLUE)	
	
	# ExpID = viz.input('Enter your unique Experiment ID:')
	# filename = viz.input('Participant code: ')

	# filename = str(ExpID) + '_' + str(filename)

	
	##here could talk to pupil-labs and set up calibration automatically. 
			
	#def onExit(): #add an onExit function to stop open ports.
	#	print 'onExit event...closing comms'
	#	comms.close_all()

def MakeGrid(Nrows, Ncolumns, BoxSize = [.6, .3], lowerleft = [.2, .2]):
	"""Returns a list of grid points of Nrows and NColumns"""

	xstart = lowerleft[0]
	ystart = lowerleft[1]
	
	xsize = BoxSize[0]
	ysize = BoxSize[1]

	xshift = xsize / (Ncolumns - 1)
	yshift = ysize / (Nrows - 1)
	
	Nmarkers = Nrows * Ncolumns

	Grid = []

	#Populate markers, starting from the bottom left and working upwards.
	for row in range(Nrows):
		#for each row, loop through columns
		for col in range(Ncolumns):
			xpt = xstart + (xshift * col)
			ypt = ystart + (yshift * row)
			point = [xpt, ypt]
			Grid.append(point)	

	# Grid = [[xstart,lowerleft[1]+boxsize[1]], #TL
	# [xstart+(boxsize[0]*1)/3,lowerleft[1]+boxsize[1]], #TCL
	# [xstart+(boxsize[0]*2)/3,lowerleft[1]+boxsize[1]], #TCR
	# [xstart+boxsize[0],lowerleft[1]+boxsize[1]], #TR
	# [xstart,lowerleft[1]+(boxsize[1]/2)], #ML
	# [xstart+(boxsize[0]*1)/3,lowerleft[1]+(boxsize[1]/2)], #MCL
	# [xstart+(boxsize[0]*2)/3,lowerleft[1]+(boxsize[1]/2)], #MCR
	# [xstart+boxsize[0],lowerleft[1]+(boxsize[1]/2)], #MR
	# [xstart,lowerleft[1]],	#BL	
	# [xstart+(boxsize[0]*1)/3,lowerleft[1]],	#BCL
	# [xstart+(boxsize[0]*2)/3,lowerleft[1]],	#BCR	
	# [xstart+boxsize[0],lowerleft[1]]]	#BR	

	return Grid

def save_calibration(calib_data, fname, write_args = 'a'):
	"""save calibration data

	args:
		calib data: a list where [0] is the calibration accuracy, [1] calibration precision, [2] timestamp , [3] success
		success: a boolean saying whether calibration accepted
		fname: the file name to append to
		write_args: arguments to pass to the file object
	"""

	f = open('CalibrationData//{}.csv'.format(fname), write_args)

	line = "{},{},{},{}\n".format(calib_data[0], calib_data[1], calib_data[2], calib_data[3])

	f.write(line)
	f.close()


def run_accuracy(comms, fname):

	fname = fname + '_accuracy_test'

	print(fname)
	##MAKE WHITE BACKGROUND COLOUR FOR BETTER CALIBRATION
	viz.MainWindow.clearcolor(viz.WHITE)
	#draw roadedges
	
	#fName = 'textures\strong_edge.bmp'
#	fName = imagepath + 'strong_edge.bmp'	
#		
#	# add groundplane (wrap mode)
#	groundtexture = viz.addTexture(fName)
#	groundtexture.wrap(viz.WRAP_T, viz.REPEAT)
#	groundtexture.wrap(viz.WRAP_S, viz.REPEAT)
#
#	groundplane = viz.addTexQuad() ##ground for right bends (tight)
#	tilesize = 300
#	planesize = tilesize/5
#	groundplane.setScale(tilesize, tilesize, tilesize)
#	groundplane.setEuler((0, 90, 0),viz.REL_LOCAL)
#	matrix = vizmat.Transform()
#	matrix.setScale( planesize, planesize, planesize )
#	groundplane.texmat( matrix )
#	groundplane.texture(groundtexture)
#	groundplane.visible(1)

	#markers = Markers() #add markers. 

	#run through calibration programme
	#throw two 9 point fleixble grid. Can simple keep going until satisfied.
	#Needs a separate save function than the original to be completely self-sufficient.
	boxsize = [.9,.8] #xy box size
	lowerleft = [.05,.1] #starting corner
	#start from top right
	nrow = 5
	ncol = 7
	Grid = MakeGrid(nrow, ncol, boxsize, lowerleft)	
	nmarkers = nrow * ncol
	
	imagepath = 'C:/VENLAB data/shared_modules/textures/'
	#fn = imagepath + 'calibmarker.png'
	#fn = imagepath + 'calibmarker_black.png' #pupil-labs has issues. Stops due to not collecting enough data. Might be to tell it to stop? 
	fn = imagepath + 'calibmarker_white.png' #seems to work best with this one. 
	#fn = imagepath + 'calibmarker_white_old.png'
	def loadimage(fn):
		"""Loads a and scales a texture from a given image path""" 
		defaultscale = 800.0/600.0
		aspect = 1920.0 / 1080.0		
		scale = aspect/defaultscale
		ttsize = 1
		pt = viz.add(viz.TEXQUAD, viz.SCREEN)
		pt.scale(ttsize, ttsize*scale, ttsize)
		pt.texture(viz.add(fn))
		pt.translate(Grid[0][0],Grid[0][1]) # Now you can specify screen coordinates, so the visual angle is OK (i.e. no depth)
		pt.visible(0)
		return (pt)

	pt = loadimage(fn)
	pt_buffer = loadimage(imagepath + 'calibmarker_buffer.png')
	pt_buffer.visible(0)
		
	#### CALIB GRID #####
	#need to make sure they are the same visual angle (account for the depth of the virtual world). 
	#test the calibration by plotting the calibration sequence taken from the eyetracker (onto the dots)
		
		
	#(0.37, 0.6) #Point1
	#	(0.485, 0.6) #Point 2
	#	(0.6, 0.6) #Point 3
	#	(0.37, 0.495) #Point 4
	#	(0.485, 0.495) #Point 5
	#	(0.6, 0.495) #Point 6
	#	(0.37, 0.39) #Point 7
	#	(0.485, 0.39) #Point 8
	#	(0.6, 0.39) #Point 9
			
	viz.message('\t\t\tACCURACY TEST \n\nPlease look at the white dot in the very centre of the accuracy target. Try and move your head as little as possible')
		
	calib_flag = 0 
	record_flag = 0
	satisfied = False
	i = 0 #index for point.
	
	#normalise markers on surface
	print (Grid)
	#calibpositions_normed = normaliseToSurface(Grid, markers.boxsize, markers.lowerleft)
	
	#print (calibpositions_normed)
	#comms.send_marker_positions(calibpositions_normed)

	comms.send_msg('P') #start accuracy test

	#add buffer point
	pt_buffer.visible(1) 
	pt.visible(0)
	yield viztask.waitTime(.75) #wait for half a second
	pt_buffer.visible(0) #remove buffer point
	pt.visible(1)
	
	while not satisfied:	
				
					
		msg_rcv = comms.poll_msg()
		
		if 'calibration.marker_sample_completed' in msg_rcv:
			
			pt_buffer.visible(1)  #add buffer point
			pt.visible(0)
			yield viztask.waitTime(.5) #wait for half a second

			i = i+1
		
			if i > nmarkers-1: #clamp i
				comms.send_msg('p')
								
				while True:
					msg_rcv = comms.poll_msg()		
					
					if True in ['calibration' in j for j in msg_rcv]:			
						
						out = [j for j in msg_rcv if 'calibration' in j][0]
						calib_accuracy = out.split('//')[0]
						calib_precision = out.split('//')[1]
						# calib_accuracy = out.split('calibration.Accuracy')[1].split('.Precision')[0]
						# calib_precision = out.split('calibration.Accuracy')[1].split('.Precision')[0]
						

						satisfied = True		
						save_calibration([calib_accuracy, calib_precision, time.time(), True], fname)				
						pt.visible(0)
						pt_buffer.visible(0)
						break
						# happy = vizinput.ask("Calibration Accuracy: " + calib_accuracy + "\nAre you satisfied?")
						
						# if happy:
						# 	print ("happy")
						# 	satisfied = True
						# 	pt.visible(0)
						# 	break
						# else:
						# 	print ("not happy")
						# 	satisfied = False
						# 	i = 0
						# 	pt.translate(Grid[i][0], Grid[i][1])
						# 	comms.send_msg('P')
						# 	break
						#yield viztask.returnValue(happy)
					
						#Now check if the calibration accuracy is good enough. Else run through again
			else:
				pt.translate(Grid[i][0], Grid[i][1])	
				pt_buffer.translate(Grid[i][0], Grid[i][1])	
				#pt.translate(0,0)

				yield viztask.waitTime(.75) #wait for half a second
				pt_buffer.visible(0) #remove buffer point
				pt.visible(1)

		yield viztask.waitTime(.5)

	#viz.quit()
def normaliseToSurface(Grid, boxsize, lowerleft):
	"""Converts screen coordinates to normalised coordinates on the surface"""
	
	calibpositions_normed = []
	for m in Grid:
		#normalise to surface.
		normx = (m[0]-lowerleft[0])/boxsize[0]
		normy = (m[1]-lowerleft[1])/boxsize[1]
		calibpositions_normed.append([normx, normy])

	return calibpositions_normed
	
	
if __name__ == '__main__':
	
	imagepath = 'C:/VENLAB data/shared_modules/textures/' #relative paths for images	
	
	comms = pupil_comms() #Initiate a communication with eyetrike	
	#Check the connection is live
	connected = comms.check_connection()

	if not connected:
		print("Cannot connect to Eyetrike. Check network")
	else:			
		initialise_display()
		
		fname = 'Testing'
		viztask.schedule(run_accuracy(comms, fname))
		
#	calib_satisfied = False
#		
#	while not calib_satisfied:
#		
#		output = run_accuracy()
#		
		
	
				
			