#cave as spec for trout.

import vizcave
import viz
import viztracker
import numpy as np

EH = 1.2
Proj_Dist = 1.0 #front projection distance to Eye
				
Proj_V_F = 1.115#vertical extent of projection (m)
Proj_H_F = 1.985#1.96#horizontal extent of projection (m)		
		
Proj_HfG = .665 #Front projection height from ground.
	
FB = Proj_HfG #FrontBottom
FT = Proj_HfG + Proj_V_F #FrontTop

FL = -Proj_H_F/2 #Front Left
FR = Proj_H_F/2 #Front Right

FC0 = FL,FB,Proj_Dist      # Front  Wall: FC0,FC1,FC2,FC3
FC1 = FR,FB,Proj_Dist
FC2 = FL,FT,Proj_Dist
FC3 = FR,FT,Proj_Dist

FrontWall = vizcave.Wall(   upperLeft=FC2,upperRight=FC3,lowerLeft=FC0,lowerRight=FC1,name='Front Wall' ) #Create front wall	

cave = vizcave.Cave(stereo=0)		
cave.addWall(FrontWall)#,window=frontWindow)

cave.setNearPlane(1.0)
cave.setFarPlane(100.0)

view = viz.MainView

track = viztracker.Keyboard6DOF() #tracker object
track.setPosition(0,EH,0)
viz.link(track,view) #linked to mainview
cave.setTracker(pos=track)
##Create CaveView object for manipulating the entire cave environment
##The caveorigin is a node that can be adjusted to move the entire cave around the virtual environment, it needs a tracker object to initialise it.
caveview = vizcave.CaveView(track)

#help(FrontWall)

headpos = [0, 1.2, 0]
frustum = FrontWall.computeFrustum(headpos)

print(frustum)

centre_screen = Proj_HfG + (Proj_V_F / 2.0)
print(centre_screen)

EH = 1.2
width = 1920
height = 1080
z = 1
x = 1.985
y = 1.115

centre_cave_screen = .665 + (y/2.0)
cave_eh_rotation = np.arctan((EH - centre_cave_screen / z))
#print(np.degrees(cave_eh_rotation))