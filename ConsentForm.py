import vizdlg
import viz
import pandas as pd
import win32com.client
import os


class MyForm(vizdlg.Dialog):

    def __init__(self,**kw):

        #Initialize base class
        vizdlg.Dialog.__init__(self,**kw)

        space = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=10)
        space.addItem(viz.addText(' '))        

        titlespace = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=15)
        titlespace.addItem(viz.addText(' '))        
        
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Study Title: Human Behaviour during Automated and Manual Driving '))        

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

        def ethicsStatement(msg):
            txt = viz.addText(msg)
            txt.fontSize(10)
            row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=3)
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
        row.addItem(viz.addText('Participant ID: '))
        self.pp_id = row.addItem(viz.addTextbox())
        self.content.addItem(row)

        #ParticipantName           
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Participant Name: '))
        self.pp_name = row.addItem(viz.addTextbox())
        self.content.addItem(row)     
        self.content.addItem(space)      

        #Ethics statement 
        txt = ethicsText('Thank you for agreeing to take part in this study')
        self.content.addItem(txt)
        txt = ethicsText('The purpose of this form is to make sure that you are happy to take part in the research')
        self.content.addItem(txt)
        txt = ethicsText('Please read the following statements. If any of these statements do not apply to you then you should not take part in the study.')
        self.content.addItem(txt)
        self.content.addItem(space)             

        txt = ethicsStatement('1) I am not prone to extreme motion sickness.')
        self.content.addItem(txt)

        txt = ethicsStatement('2) I do not currently, or at any point in the past, suffer from a form of epilepsy.')
        self.content.addItem(txt)
        
        txt = ethicsStatement('3) I have had the opportunity to ask questions and discuss the study to my satisfaction')
        self.content.addItem(txt)

        txt = ethicsStatement('4) I understand that I am free to end the study at any time')
        self.content.addItem(txt)

        txt = ethicsStatement('5) I agree to take part in this study')
        self.content.addItem(txt)

        txt = ethicsStatement('6) I grant permission for my data to be used in reports of the research in the understanding that my anonymity will be maintained at all times')
        self.content.addItem(txt)
        self.content.addItem(titlespace)
        
        txt = ethicsText('By clicking "I agree", you give your informed consent to participate in this study')
        self.content.addItem(txt)
        self.content.addItem(titlespace)

        #Date
        row = vizdlg.Panel(layout=vizdlg.LAYOUT_HORZ_BOTTOM,border=False,background=False,margin=1)
        row.addItem(viz.addText('Date (DD/MM/YYY): '))
        self.date = row.addItem(viz.addTextbox())
        self.content.addItem(row)

        self.cancel.visible(0)

        #Rename accept button to 'submit'
        self.accept.message('I agree')    
    

import viztask
import vizinfo

def FormTask():    

    #Create input form
    form = MyForm(title='Consent Form')

    #Link form to center of screen
    viz.link(viz.MainWindow.CenterCenter,form)    

    viz.window.setFullscreen(viz.ON)

    while True:

        #TODO: Pause simulation

        #Display form
        yield form.show()

        if form.accepted:
            #User pressed 'I agree', process data
            consent = 'Yes'

            ID = form.pp_id.get()

            name = form.pp_name.get()

            date = form.date.get()
            
            output = [ID, name, date, consent]


            #Dealing with password protected excel files is convoluted, but the code below works.
            #open password protected. Code from: https://stackoverflow.com/questions/19450837/how-to-open-a-password-protected-excel-file-using-python; http://pythonexcels.com/python-excel-mini-cookbook/

            #retrieve path
            currdir = os.path.dirname(os.path.abspath(__file__))

            #open with password
            xlApp = win32com.client.Dispatch("Excel.Application")
            print "Excel library version:", xlApp.Version
            filename,password = currdir + "\\InformedConsent_rerun.xlsx", 'Vis1on'            
            xlwb = xlApp.Workbooks.Open(filename, False, False, None, password)

            #get last row and append
            ws = xlwb.Worksheets("Sheet1")
            lastRow = ws.UsedRange.Rows.Count
            print ws.Rows(lastRow)
            ws.Range(ws.Cells(lastRow+1,1), ws.Cells(lastRow+1,4)).Value = output
            print ws.Rows(lastRow+1)

            #save and close
            xlwb.Save()
            xlApp.Quit()

            break
                
    #Remove form when completely finished with it
    form.remove()
        
    #quit after form entry, if you are not calling this script from elsewhere
    if __name__ == '__main__':
        viz.quit()


if __name__ == '__main__':
    
    viz.go()
    viztask.schedule( FormTask() )    
    
    