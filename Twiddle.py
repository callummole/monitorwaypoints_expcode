import numpy as np
import matplotlib.pyplot as plt
from PIDcontrol import *


def Simulation_RMSWrapper(course, trackorigin, p, offset):
    """Return RMS from Simulation"""

    Car = runSimulation(course, trackorigin, p, offset)
    steeringbias = np.array(Car.error_history)
    YR_history = np.array(Car.heading_dot_history)


    jerk = np.diff(YR_history)
    RMS_bias = np.sqrt(np.mean(steeringbias**2))
    RMS_YR = np.sqrt(np.mean(YR_history**2))
    RMS_jerk = np.sqrt(np.mean(jerk**2))

    error = RMS_bias + (RMS_YR * 10)
    #error = RMS_bias + (RMS_YR * 25)+ (RMS_jerk * 200) #fit to some combination of position and smoothness that gives desired performance.

    return error 

def Wrapper_for_Wrapper(course, trackorigin, p, offsets):
    """returns combined error from a list of offsets"""

    best_error = 0
    for offset in offsets:
        error = Simulation_RMSWrapper(course, trackorigin, p, offset)
        best_error += error

    return best_error

if __name__ == '__main__':

    [course, trackorigin] = TrackMaker()
    
    #Twiddle algorithm adapted from: https://martin-thoma.com/twiddle/
    # Choose an initialization parameter vector
    p = [15.0, 5., 5.]
   # p = [.0047030553378439735, 0.09276356650659244, 6.325806151080248e-05]
    # Define potential changes
    dp = [0.1, 0.1, 0.1]
    # Calculate the error
    offsets = [-1.5, -1, -.5, 0, .5, 1, 1.5]

    best_err = Wrapper_for_Wrapper(course, trackorigin, p, offsets)
    #best_err = Simulation_RMSWrapper(course, trackorigin, p)

    threshold = 0.001

    while sum(dp) > threshold:
        print("dp: ", sum(dp))
        print("best_err: ", best_err)
        print("best_Params: ", p)
        for i in range(len(p)):
            p[i] += dp[i]
            err = Wrapper_for_Wrapper(course, trackorigin, p, offsets)
            #err = Simulation_RMSWrapper(course, trackorigin, p)

            if err < best_err:  # There was some improvement
                best_err = err
                dp[i] *= 1.1
            else:  # There was no improvement
                p[i] -= 2*dp[i]  # Go into the other direction
                err = Wrapper_for_Wrapper(course, trackorigin, p, offsets)
                #err = Simulation_RMSWrapper(course, trackorigin, p)

                if err < best_err:  # There was an improvement
                    best_err = err
                    dp[i] *= 1.05
                else:  # There was no improvement
                    p[i] += dp[i]
                    # As there was no improvement, the step size in either
                    # direction, the step size might simply be too big.
                    dp[i] *= 0.95

    print (p, best_err, dp)

    #save best parameters
    output = "Best Parameters: " + str(p) + "\n" + "Best error: " + str(best_err) 
    txtfile = open("TwiddleResults.txt", "w")
    txtfile.write(output)
    txtfile.close()

    #runSimulation(course, trackorigin)
    
    
    
    