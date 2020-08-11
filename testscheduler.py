import viztask
import viz
import vizact

viz.go()

def printtiger():
    
    print("tiger")
    
def printnumber(i):
    
    yield viztask.waitTime(.5)
    print("num:", i)
    
def mainloop():
    
    #vizact.ontimer((1.0/30.0),waittwo_quit)   #if the experiment goes over 5 seconds then quit
    
    for i in range(5):
        
        yield printnumber(i)
    
    yield viztask.waitTrue(waittwo_return)
    yield printtiger()
    quit_viz()
    
def waittwo_return():
    
    waited = False
    if viz.tick > 2:
        waited = True
    
    return(waited)
    
def waittwo_quit():
    
    waited = False
    if viz.tick() > 2:
        waited = True
    
    if waited:
       # yield printtiger() #if this is included then the function isn't called.
        #printtiger()
        quit_viz()
        
def quit_viz():
    print ("quitting")
    viz.quit()
    
viztask.schedule(mainloop())
