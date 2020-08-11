import numpy as np
import matplotlib.pyplot as plt
import pdb

def angle_between_vectors(a, b):
    """Get the angle between vectors a and b"""
    
    return np.arccos(np.dot(a, b) / (np.sqrt(np.dot(a, a)) * np.sqrt(np.dot(b, b))) )


def TrackMaker():
	
    """adds oval track"""
    #at the moment each straight or bend is a separate section. So we can alter the colour if needed. But more efficient to just create one line per edge.

    #Start at beginning of 1st straight.
    #Start at beginning of 1st straight.
    SectionSize = 10000
    StraightLength = 40.0 #in metres. 
    InterpLength = StraightLength / 4.0
    InterpHalf = InterpLength / 2.0
    BendRadius = 30.0 #in metres, constant curvature bend.
    roadwidth = 3.0/2.0
    right_array = np.linspace(np.pi, 0.0, SectionSize) 
    left_array= np.linspace(0.0, np.pi,SectionSize)
    trackorigin = [0.0, 0.0] #origin of track
    TotalStraightLength = InterpLength + (StraightLength*2)
    print ("StraightLength:", TotalStraightLength)

    	#For readability set key course markers. Use diagram for reference
    LeftStraight_x = -BendRadius
    RightStraight_x = BendRadius
    Top_Interp_z = InterpHalf
    Top_Straight_z = InterpHalf+StraightLength
    Bottom_Interp_z = -InterpHalf
    Bottom_Straight_z = -InterpHalf-StraightLength
        
    global midline
    #The interp periods have index numbers of sectionsize / 4. So midline size = SectionSize * 6.5 (6 sections + two interps)
    midlineSize = SectionSize*6.5
    midline = np.zeros((int(midlineSize),2), dtype = np.float)

    SectionBreaks = []
    SectionBreaks.append(0)
    SectionBreaks.append(SectionSize) #end of StraightA
    SectionBreaks.append(SectionSize*2) #end of BendB
    SectionBreaks.append(SectionSize*3) #end of StraightC
    SectionBreaks.append(int(SectionSize*3.25)) #end of InterpD
    SectionBreaks.append(int(SectionSize*4.25)) #end of StraightE
    SectionBreaks.append(int(SectionSize*5.25)) #end of BendF
    SectionBreaks.append(int(SectionSize*6.25)) #end of StraightG
    SectionBreaks.append(int(SectionSize*6.5)) #end of InterpH

    #Straight A
    StraightA_z = np.linspace(Top_Interp_z, Top_Straight_z, SectionSize)
    midline[SectionBreaks[0]:SectionBreaks[1],0] = LeftStraight_x
    midline[SectionBreaks[0]:SectionBreaks[1],1] = StraightA_z

    print (SectionBreaks)
    print (midline[SectionBreaks[0]:SectionBreaks[1],:])

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
    InterpD_z = np.linspace(Top_Interp_z, Bottom_Interp_z, int(SectionSize/4.0))
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
    InterpG_z = np.linspace(Bottom_Interp_z, Top_Interp_z, int(SectionSize / 4.0))
    midline[SectionBreaks[7]:SectionBreaks[8],0] = xend
    midline[SectionBreaks[7]:SectionBreaks[8],1] = InterpG_z


    return midline, trackorigin

class vehicle:
    
    def __init__(self, pos, heading, speed, dt, desired_trajectory, trackorigin, k_i, k_n, k_f):
            
        #self.pos = np.array([pos[0], pos[1]])
        self.pos = np.array([pos[0], pos[1]])
        self.heading = heading #heading angle
        self.speed = speed 
        self.dt = dt       
        self.trackorigin = trackorigin                        
        
        
        self.k_i = k_i
        self.k_n = k_n
        self.k_f = k_f

        self.heading_dot = 0
        
        self.pos_history = []
        self.heading_history = []
        self.heading_dot_history = []                
        self.error_history = []   
        self.closestpt_history = []  

        self.sight_point_angles_history = []           
  
       
        self.desired_trajectory = desired_trajectory

        
        
        self.currenterror, self.closestpt = self.calculatebias()

        self.error_T_minus_1 = None #should this be set to self.current error? 
        self.error_i = 0

        self.YR_T_minus_1 = 0

        self.sight_point_angles_minus_1 = None

        self.Integral_On = False

        # self.save_history()

    

       
        

    def calculatebias(self):

        #TODO: cut down on processing but only selecting a window of points based on lastmidindex.
        midlinedist = np.sqrt(((self.pos[0]-self.desired_trajectory[:,0])**2)+((self.pos[1]-self.desired_trajectory[:,1])**2)) #get a 4000 array of distances from the midline
        idx = np.argmin(abs(midlinedist)) #find smallest difference. This is the closest index on the midline.	

        closestpt = self.desired_trajectory[idx,:] #xy of closest point
        dist = midlinedist[idx] #distance from closest point				

        #Sign bias from assessing if the closest point on midline is closer to the track origin than the driver position. Since the track is an oval, closer = understeering, farther = oversteering.
        middist_from_origin = np.sqrt(((closestpt[0]-self.trackorigin[0])**2)+((closestpt[1]-self.trackorigin[1])**2))  #distance of midline to origin
        pos_from_trackorigin = np.sqrt(((self.pos[0]-self.trackorigin[0])**2)+((self.pos[1]-self.trackorigin[1])**2)) #distance of driver pos to origin
        distdiff = middist_from_origin - pos_from_trackorigin #if driver distance is greater than closest point distance, steering position should be understeering
        steeringbias = dist * np.sign(distdiff)     

        return steeringbias, closestpt



    def pid_step(self, currentbias, desired_position):
        """PID controller step using lateral error as input and yawrate as output"""		

        #dt = 1/60.0
        #dt = viz.elapsed()

        #print ("Elapsed: ", viz.elapsed())
        #print ("dt: ", 1/60.0)

       # print ("Pos: ", self.pos)
       # print ("Euler: ", self.heading)

        #Error between desired and actual position
        error = (desired_position - currentbias)
        
        if error < .1:
            self.Integral_On = True
        else:
            self.Integral_On = False

        #introduce some satisficing behaviour to avoid oscillations around midline.
        threshold = .01
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
                                                                
        #Set yaw rate output		
        YR_p = self.tau_p * error
        YR_d =  self.tau_d * d_error
        YR_i = self.tau_i * self.error_i
        
        YR = YR_p + YR_d + YR_i #does not need converted back, because taus will be adjusted.

        #based on vizdriver, max yawrate given by wheel=1.0
        maxwheelval = (1.0 * (1/60.0) * 35.0) * np.pi/180 #in rads per frame
     #   print ("maxwheelval: ", maxwheelval)

        clip_YR = np.clip(YR, -maxwheelval, maxwheelval)	#clamp max jerk.

        if abs(clip_YR) == maxwheelval:
            self.Integral_On = False
        else:
            self.Integral_On = True
        #print ("Yaw OUT: ", YR)
        #print(currentbias, error, YR, YR_p, YR_d)
        #self.yawrate = self.startinterp_yawrate+YR

        YR_output = clip_YR

        #From a single manual file it seems a reasonable limit for yawrate_dot, in radians, is .0005

        d_clip = .0005
        d_YR = YR_output - self.YR_T_minus_1
        d_YR_clamped = np.clip(d_YR, -d_clip, d_clip)

        # #avoid integral windup by turning the integral off when actuator limits are reached
        if abs(d_YR_clamped) == d_clip:
            self.Integral_On = False
        else:
            self.Integral_On = True
        
        YR_output = self.YR_T_minus_1 + d_YR_clamped

        self.YR_T_minus_1 = YR_output

        return YR_output

    def calculate_sight_point_angles(self, target_trajectory):

        sight_point_times = np.array([0.5, 2])
      
        sight_point_distances = sight_point_times * self.speed
        n_sight_points= len(sight_point_distances)
        
        #Get vectors from vehicle to road points
        vectors_to_road_points = np.array([target_trajectory[:,0] - self.pos[0], 
                                           target_trajectory[:,1] - self.pos[1]]).T
        
        #Get distances to road points
        road_point_distances = np.sqrt(np.sum(np.square(vectors_to_road_points), axis = 1))
        
        #Get the forward vector
        self.forward_vector = np.array([np.sin(self.heading), np.cos(self.heading)])        
        
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
                                 
            self.vector_to_sight_point = sight_point - self.pos      

            
            # plt.plot(sight_point[0], sight_point[1], 'o', color = colors[i])
         
            # plt.plot([self.pos[0], self.pos[0] +  self.vector_to_sight_point[0]], [self.pos[1], self.pos[1] + self.vector_to_sight_point[1]], 'k-')
        
            #Gustavs method of calculating sight point angle
            longitudinal_dist_2_sp = np.dot(self.vector_to_sight_point, self.forward_vector)
            lateral_dist_2_sp = np.dot(self.vector_to_sight_point, np.array([np.sin(self.heading + np.pi / 2), np.cos(self.heading + np.pi / 2)]))
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

        self.currenterror = self.calculatebias()[0]

        target_trajectory = self.desired_trajectory + np.array([offset, 0.0]) 

        sight_point_angles = self.calculate_sight_point_angles(target_trajectory)

        self.sight_point_angles = sight_point_angles        
        
        if self.sight_point_angles_minus_1 is None:
            sight_point_angles_d = np.zeros(2) #Change in sight point angles between timesteps
        else:
       
            sight_point_angles_d  = (sight_point_angles - self.sight_point_angles_minus_1) 

        self.sight_point_angles_minus_1 = sight_point_angles.copy()

        k_i, k_n, k_f = self.k_i, self.k_n, self.k_f

        heading_dot = (k_i * sight_point_angles[0] * self.dt +
                            k_n * sight_point_angles_d[0] + 
                            k_f * sight_point_angles_d[1] ) 

        return heading_dot

    def move_vehicle(self):           
        """update the position of the vehicle over timestep dt"""                        
                                 
        self.heading_dot = self.pid_step_sng(-1.0)

        # self.heading_dot = np.deg2rad(0.5) # np.random.normal(0, 0.001)

        maxheadingval = np.deg2rad(35.0) #in rads per second
        
        self.heading_dot = np.clip(self.heading_dot, -maxheadingval, maxheadingval)
        # print(self.heading_dot)
        # self.heading_dot = 0.0

        self.heading = self.heading + self.heading_dot * self.dt  #+ np.random.normal(0, 0.005)
        
        #zrnew = znew*cos(omegaH) + xnew*sin(omegaH);
        #xrnew = xnew*cos(omegaH) - znew*sin(omegaH)

        x_change = self.speed * self.dt * np.sin(self.heading)
        y_change = self.speed * self.dt * np.cos(self.heading)
        
        self.pos = self.pos + np.array([x_change, y_change]) 
        
        self.save_history()
    
    def save_history(self):

        self.pos_history.append(self.pos)        
        self.heading_history.append(self.heading)
        self.heading_dot_history.append(self.heading_dot)
        self.error_history.append(self.currenterror)
        self.closestpt_history.append(self.closestpt)
        self.sight_point_angles_history.append(self.sight_point_angles)

    

def runSimulation(course, trackorigin, params, offset = -.5):

    """run simulation and return RMS"""

    #Sim params
    fps = 60.0
    speed = 8.0
 

   # print ("speed; ", speed)

    dt = 1.0 / fps
    run_time = 20 #seconds
    time = 0

    startposition = course[0,:]

    Car = vehicle([startposition[0]+offset,startposition[1]-40],0.0, speed, dt, course, trackorigin, params[0], params[1], params[2])

    close_sp_all = []
    far_sp_all = []
    i = 0
    while time < run_time:
        
       # print i
        time += dt        
       
        i += 1
        Car.move_vehicle()           

    return Car
    
    #RMS = np.sqrt(np.mean(steeringbias**2))

    #print ("RMS: ", RMS)

     

def plotResults(course, trackorigin, positions, midlinepositions, heading, heading_dot, wheelpositions, steeringbias, spa):
    """Plot results of simulations"""


    plt.figure(3)
    plt.plot(course[:,0], course[:,1], '--b')
    trackwidth = trackorigin[0]*2
        
    plt.xlim([0-5, trackwidth+5])
    plt.ylim([-trackorigin[0]-5, trackorigin[1]*2 + trackorigin[0]+5])
    plt.plot(positions[:,0], positions[:,1],'-r')
    plt.plot(positions[:,0], positions[:,1],'.g')
    #plt.plot(midlinepositions[:,0], midlinepositions[:,1],'.k')
    plt.axis('equal')
   # plt.show()


    plt.figure(4)  		
    ax1 = plt.subplot(6,1,1)
    plt.axhline(y=0, color = 'b')			
    plt.plot(range(len(steeringbias)), steeringbias, 'r.')						
    plt.ylim([-1.5,1.5])
    plt.xlabel("Frame")
    plt.ylabel("SB")			



    plt.subplot(6,1,2, sharex = ax1)
    plt.plot(range(len(heading)), heading, 'g.')						
    plt.ylim([-.1,.1])
    plt.xlabel("Frame")
    plt.ylabel("Yaw")		

    plt.subplot(6,1,3, sharex = ax1)
    plt.plot(range(len(heading)), spa[:,0], 'g-')						
    # plt.ylim([-.1,.1])
    plt.xlabel("Frame")
    plt.ylabel("spa_0")

    plt.subplot(6,1,4, sharex = ax1)
    plt.plot(range(len(heading)), spa[:,1], 'g-')						
 
    plt.xlabel("Frame")
    plt.ylabel("spa_1")

    plt.subplot(6,1,5, sharex = ax1)
    plt.plot(range(len(heading_dot)), heading_dot, 'k.')
    plt.ylim([np.deg2rad(-45), np.deg2rad(45)])						
    plt.xlabel("Frame")
    plt.ylabel("YawRate")	

    plt.subplot(6,1,6, sharex = ax1)
    plt.plot(range(len(wheelpositions)), wheelpositions, 'y.')						
    # plt.ylim([-1,1])						
    plt.xlabel("Frame")
    plt.ylabel("WheelPositions")	

    plt.show()

if __name__ == '__main__':

    
    [course, trackorigin] = TrackMaker()
    
    #Twiddle algorithm adapted from: https://martin-thoma.com/twiddle/
    # Choose an initialization parameter vector
    # p = [0.2704948415379533, 3.263599982753203, 2.5990540927551563e-06]
    #p = [0.05807755038186424, 1.1344020593230026, 2.385033857177837e-05]
    #p = [0.015979766373924648, 0.2047098892725661, -4.103711875162375e-05]
    #p = [0.027109797530714495, 0.20498508276582952, -0.0001523838889187754]
    #p = [0.021412944767697454, 0.17408459036422627, -0.00011982005139995604]
    #p = [0.00434494582694005, 0.07534588969519918, 0.0]
    # p = [0.005065372161779556, 0.07463897274205897, -2.5908482849261276e-05]
    # p = [0.001, 0.05, 0.0000] #twiddle
    # p = [0.01, 0.4, 0.0001]

    p = [200.0, 20., 20.]
    # p = [11.743827236853686, 8.56570999899826, 2.164280092218638]
    #p = [0.004619533018848891, 0.836591966320042, 0.0004771039459413638] #RMS_bias + RMS_YR
   # p = [0.004528798430091772, 0.5734633542518311, 0.00034394933029141295] #RMS_bias + (RMS_YR+2)
    # Define potential changes
    # Calculate the error


    Car = runSimulation(course, trackorigin, p, -.5)

        #plot
    positions = np.array(Car.pos_history)
    midlinepositions = np.array(Car.closestpt_history)
    heading = np.array(Car.heading_history)
    heading_dot = np.array(Car.heading_dot_history)
    wheelpositions = (heading_dot / np.pi) * 90.0
    
  
    steeringbias = np.array(Car.error_history)

    sight_point_angles = np.array(Car.sight_point_angles_history)



    RMS_bias = np.sqrt(np.mean(steeringbias**2))
    RMS_YR = np.sqrt(np.mean(heading_dot**2))
    jerk = np.diff(heading_dot)
    RMS_jerk = np.sqrt(np.mean(jerk**2))
    print ("RMS_bias: ", RMS_bias)
    print ("RMS_YR: ", RMS_YR)
    print ("RMS_jerk: ", RMS_jerk)

    plotResults(course, trackorigin, positions, midlinepositions, heading, heading_dot, wheelpositions, steeringbias, sight_point_angles)

    
    
    