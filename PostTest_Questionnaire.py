
import vizdlg
import viz
import pandas as pd

class MyForm(vizdlg.Dialog):

    def __init__(self,**kw):

        #Initialize base class
        vizdlg.Dialog.__init__(self,**kw)

        space = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=10)
        space.addItem(viz.addText(' '))        

        titlespace = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=15)
        titlespace.addItem(viz.addText(' '))                
 
        
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Thank you for completing the experiment. Can you please answer the following questions: '))        

        #Add two rows.         
        self.content.addItem(row)
        self.content.addItem(titlespace)
        
        #ADD ETHICS TEXT
        def ethicsText(msg):
            txt = viz.addText(msg)
            txt.fontSize(10)
            row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
            row.addItem(txt)
            return row
            
        eth1 = ethicsText('Ethics approval has been granted by the School of Psychology Research Ethics Committee')        
        self.content.addItem(eth1)
        eth2 = ethicsText('Ethics Reference Number: PSC-435')
        self.content.addItem(eth2)
        eth3 = ethicsText('Approval Date: 25/09/2018')
        self.content.addItem(eth3)

        self.content.addItem(space)                                                          

        #ParticipantCode
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Participant ID (as int): '))
        self.pp_id = row.addItem(viz.addTextbox())
        self.content.addItem(row)
        self.content.addItem(space)                        

        #Add human-like qu 1
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('1) How human-like did you find the automated steering control?'))
        
        self.content.addItem(row)
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)

        row.addItem(viz.addText('Not at all human-like   '))
        self.q1 = self.likertrow(row)
        row.addItem(viz.addText('   Human-like'))
    
        self.content.addItem(row)
        self.content.addItem(space)                        

        #add Readiness Qu 2
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('2) During automation, how ready did you feel to immediately take over the vehicle?'))
        
        self.content.addItem(row)
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)

        row.addItem(viz.addText('Not at all ready   '))
        self.q2 = self.likertrow(row)
        row.addItem(viz.addText('   Ready'))
    
        self.content.addItem(row)
        self.content.addItem(space)         
        
        #add eye-movements Qu 3
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('3) During automation, to what extent were you looking in the same place as when you were driving? '))        
        self.content.addItem(row)
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)

        row.addItem(viz.addText('Not at all in the same place   '))
        self.q3 = self.likertrow(row)
        row.addItem(viz.addText('   In the same place'))
    
        self.content.addItem(row)
        self.content.addItem(space)   

        #add eye-movements Qu 4
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('4) How similar to your own steering behaviour did you feel the automated vehicle was? '))        
        self.content.addItem(row)
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)

        row.addItem(viz.addText('Not at all similar   '))
        self.q4 = self.likertrow(row)
        row.addItem(viz.addText('  Very similar'))
    
        self.content.addItem(row)
        self.content.addItem(space)   

        
        self.cancel.visible(0)

        #Rename accept button to 'submit'
        self.accept.message('Submit')
    

    def likertrow(self,row):
        likert = []

        for i in range(8):
            row.addItem(viz.addText('  ' + str(i) + ' '))
            likert.append(row.addItem(viz.addCheckbox()))

        return likert
    

import viztask
import vizinfo

def FormTask():    

    #Create input form
    form = MyForm(title='Post-Test Questionnaire')

    #Link form to center of screen
    viz.link(viz.MainWindow.CenterCenter,form)

    viz.window.setFullscreen(viz.ON)

    def ProcessLikert(likert):
        
        ans = 0
        for i, item in enumerate(likert):
           if item.get():
               ans = i
               break
        return ans

    while True:

        #TODO: Pause simulation

        #Display form
        yield form.show()

        if form.accepted:
            #User pressed 'Submit', process data
            ID = form.pp_id.get()
            print ('ID:', ID)

            q1 = ProcessLikert(form.q1)
            print ('Q1:', q1)

            q2 = ProcessLikert(form.q2)
            print ('Q2:', q2)

            q3 = ProcessLikert(form.q3)
            print ('Q3:', q3)

            q4 = ProcessLikert(form.q4)
            print ('Q4:', q4)

            df = pd.read_csv("PostTest_rerun.csv", index_col=0)                                    
            df.loc[len(df)] = [ID, q1, q2, q3, q4] 
            df.to_csv("PostTest_rerun.csv")
            break
                
    #Remove form when completely finished with it
    form.remove()
    
    #quit after form entry, if you are not calling this script from elsewhere
    if __name__ == '__main__':
        viz.quit()

if __name__ == '__main__':
    
    viz.go()
    viztask.schedule( FormTask() )    