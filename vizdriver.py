import viz
import vizact
import vizmat
import vizjoy
import viztask
import math as mt # python library
JOY_FIRE_BUTTONS = [100, 101, 102]
JOY_DIR_SWITCH_BUTTON = [5, 6]
KEY_FIRE_BUTTONS = [' ']
KEY_DIR_SWITCH_BUTTON = viz.KEY_DELETE

class Driver(viz.EventClass):
	def __init__(self, Cave):
		viz.EventClass.__init__(self)
				
		#self.__speed = 0.223 #metres per frame. equates to 13.4 m/s therefore 30mph.
		#8ms = 8/60 = .1333
		self.__speed = 8.0 #m/s
		#self.__speed = .1333
		self.__heading = 0.0
		self.__pause = 0#-50 #pauses for 50 frames at the start of each trial
		
		#self.__view = viz.MainView.setPosition(0,1.20,0) #Grabs the main graphics window
		self.__view = Cave
		#self.__view = viz.MainView
		#self.__view.moverelative(viz.BODY_ORI)
		
		self.__automation = False

		self.__keyboardturnrate = 0
		
		self.__dir = 1.0 # direction of the vehicle (+: )
			
		self.callback(viz.TIMER_EVENT,self.__ontimer)
		self.callback(viz.KEYDOWN_EVENT,self.keyDown) #enables control with the keyboard
		self.callback(vizjoy.BUTTONDOWN_EVENT,self.joyDown) 
		self.callback(vizjoy.MOVE_EVENT,self.joymove)
		
		self.starttimer(0,0,viz.FOREVER)

		global joy
		joy = vizjoy.add()

		
	def toggleDir(self):
		if self.__dir > 0:
			self.__dir = -1.0
		else:
			self.__dir = 1.0
		
	def reset(self):
		
		self.__heading = 0.0
		self.__dir = 1.0
		turnrate = 0.0
		self.__view.reset(viz.BODY_ORI) 
				
		#self.__view = viz.MainView
		
		self.__view.reset(viz.HEAD_POS|viz.BODY_ORI)
		self.__pause = -50
		
		#self.__view = viz.MainView.setPosition(0,1.20,0) ##CHANGE EYE-HEIGHT FROM HERE
		#self.__view = viz.MainView.setPosition(0,1.20,0) ##CHANGE EYE-HEIGHT FROM HERE
		#self.__view = viz.MainView
		#self.__view.moverelative(viz.BODY_ORI)
		data = joy.getPosition()
		data[0] = 0
		
		gas = data[1]

	def __ontimer(self,num):
		elapsedTime = viz.elapsed()

		#dt = elapsedTime
		dt = 1.0/60.0 #since these will be played-back, and you cannot be sure of the timestamp at playback, keep at 1/60.0.
	
		#Get steering wheel and gas position
		data = joy.getPosition()
		gas = data[1]
		if self.__automation:
			#keep heading up to date.
			ori = self.__view.getEuler()
			self.__heading = ori[0]

		elif not self.__automation:
			if viz.key.isDown(viz.KEY_UP):
				gas = -5
			elif viz.key.isDown(viz.KEY_DOWN):
				gas = 5
			if viz.key.isDown(viz.KEY_LEFT): #rudimentary control with the left/right arrows. Made into 2nd order controller
				#data[0] = -1
				self.__keyboardturnrate = self.__keyboardturnrate - .025
				turnrate = self.__dir * self.__keyboardturnrate  * dt * 35
			elif viz.key.isDown(viz.KEY_RIGHT):
				#data[0] = 1
				self.__keyboardturnrate = self.__keyboardturnrate + .025
				turnrate = self.__dir * self.__keyboardturnrate  * dt * 35
			else:
		#		#Compute drag
		#		drag = self.__speed / 300.0
				self.__dir = 1				
				turnrate = self.__dir * (data[0]+self.__keyboardturnrate)  * dt * 35 
							
			self.__heading += turnrate 
		
			self.__pause = self.__pause+1
			#Update the viewpoint
			if self.__pause > 0:				
				
				distance = self.__speed * dt
				#posnew = (0,0,self.__speed)
				posnew = (0,0,distance)
				eulernew = (self.__heading,0,0)			
					
		#		print ("Pos: ", self.__view.getPosition())
	#			print ("Euler: ", self.__view.getEuler())

				#print ("Driver set Euler: ", eulernew[0])	
				self.__view.setPosition(posnew, viz.REL_LOCAL)
				self.__view.setEuler(eulernew, viz.ABS_GLOBAL) #surely this should be global rather than local? 
				
			#	print ("NewPos: ", self.__view.getPosition())
		#		print ("NewEuler: ", self.__view.getEuler())
					
			else:
				self.__heading = 0.0
				self.__dir = 1.0
				turnrate = 0.0

	def keyDown(self,button):
		if button == KEY_DIR_SWITCH_BUTTON:
			self.toggleDir()		
		
	def joyDown(self,e):
		if e.button == JOY_DIR_SWITCH_BUTTON:
			return e.button			
		if e.button in JOY_FIRE_BUTTONS:
			button = e.button # do nothing

	def resetHeading(self):
		self.__heading = 0.0

	def getSpeed(self):
		return self.__speed
		
	def setAutomation(self,Auto):

		"""flag to disconnect wheel and visuals"""
		self.__automation = Auto		
		
	def getPos(self):
		xPos = joy.getPosition()
		return xPos[0]#*90.0 ##degrees of steering wheel rotation 
		
	def getPause(self): ###added for flow manipulations
		return self.__pause
		
		
	def joymove(self,e):
	
		#translate position to SWA.		
	
		x = e.pos[0]*10				
			
