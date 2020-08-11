import vizdlg
import viz
import viztask
import vizinfo

class MyForm(vizdlg.Dialog):

    def __init__(self,**kw):

        #Initialize base class
        vizdlg.Dialog.__init__(self,**kw)

        space = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=5)
        space.addItem(viz.addText(' '))    

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
        self.content.addItem(space)

        
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('EXPERIMENTAL BLOCK (1, 2, 3, or 4):'))
        self.block = row.addItem(viz.addTextbox())

        #Add row to dialog content section
        self.content.addItem(row)
        self.content.addItem(space)



        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Participant ID (as int): '))
        self.pp_id = row.addItem(viz.addTextbox())

        #Add row to dialog content section
        self.content.addItem(row)
        self.content.addItem(space)

        #Add age textbox
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Age (as int): '))
        self.pp_age = row.addItem(viz.addTextbox())
        self.content.addItem(row)
        self.content.addItem(space)
                        

        #add gender checkbox.
        #Add row for textbox to subgroup
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Gender: '))
        
        self.Fem = row.addItem(viz.addCheckbox())
        row.addItem(viz.addText('Fem   '))
        
        self.Mal = row.addItem(viz.addCheckbox())
        row.addItem(viz.addText('Male    '))

        self.Oth = row.addItem(viz.addCheckbox())        
        row.addItem(viz.addText('Other    '))

        
        self.Pref = row.addItem(viz.addCheckbox())
        row.addItem(viz.addText('Prefer not to say  '))

        self.content.addItem(row)
        self.content.addItem(space)

        #Add Vision
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Wearing contacts or glasses for testing:    '))
        row.addItem(viz.addText('Yes'))
        self.VisYes = row.addItem(viz.addCheckbox())
        row.addItem(viz.addText('No'))
        self.VisNo = row.addItem(viz.addCheckbox())
        self.content.addItem(row)
        self.content.addItem(space)

        #Add Vision
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Number of years holding driving license:    '))
        self.DLyrs = row.addItem(viz.addTextbox())        
        self.content.addItem(row)
        self.content.addItem(space)                        
        
        self.cancel.visible(0)

        #Rename accept button to 'submit'
        self.accept.message('Submit')

def FormTask():

    info = vizinfo.InfoPanel("Press the 's' key to show the form")

    #Create input form
    form = MyForm(title='Demographics')

    #Link form to center of screen
    viz.link(viz.MainWindow.CenterCenter,form)

    while True:

        #Wait for 's' key to be pressed
        yield viztask.waitKeyDown('s')

        #TODO: Pause simulation

        #Display form
        yield form.show()

        if form.accepted:
            #User pressed 'Submit', process data
            ID = form.pp_id.get()
            print ('ID:', ID)

            Age = form.pp_age.get()
            print ('Age:', Age)

            block = form.block.get()
            print ('Block:', block)

            Gender = 0
            if form.Fem.get():
                Gender = 1
            elif form.Mal.get():
                Gender = 2
            elif form.Oth.get():
                Gender = 3
            elif form.Pref.get():
                Gender = 4

            Vision = 99
            if form.VisYes.get():
                Vision = 1
            elif form.VisNo.get():
                Vision = 0

            DLyrs = form.DLyrs.get()

            DLmnths = int(round(float(DLyrs) * 12)) #convert to months.

            print ('Gender:', Gender)

            demographics = [int(ID), int(Age), Gender, int(Vision), int(DLmnths)]	

            print (demographics)
            
            break

    #Remove form when completely finished with it
    form.remove()
    
    #quit after form entry, if you are not calling this script from elsewhere
    if __name__ == '__main__':
        viz.quit()

if __name__ == '__main__':
    
    viz.go()
    viztask.schedule( FormTask() )