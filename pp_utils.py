import time
import tkMessageBox

class StopWatch:
    
    global_enable=False

    def __init__(self):
        self.enable=False

    def on(self):
        self.enable=True

    def off(self):
        self.enable=False
    
    def start(self):
        if StopWatch.global_enable and self.enable: self.sstart=time.clock()

    def split(self,text):
        if StopWatch.global_enable and self.enable:
            self.end=time.clock()
            print text + " " + str(self.end-self.sstart) + " secs"
            self.sstart=time.clock()
        
    def stop(self,text):
        if StopWatch.global_enable and self.enable:
            self.end=time.clock()
            print text + " " + str(self.end-self.sstart) + " secs"


class Monitor:
    global_enable=False 
    log_path=""
    ofile=None
    start_time= time.time()

    def __init__(self):
        if Monitor.ofile==None:
            Monitor.ofile=open(Monitor.log_path+"/pp_log.log","w")          
        self.enable=False

    def on(self):
        self.enable=True
        
    def off(self):
        self.enable=False

    def err(self,caller,text):
        print "%.2f" % (time.time()-Monitor.start_time), " ERROR: ",caller.__class__.__name__," ", text
        Monitor.ofile.write (" ERROR: " + caller.__class__.__name__ + ":  " + text + "\n")
        tkMessageBox.showwarning(
                                caller.__class__.__name__ ,
                                text
                                        )

    def log(self,caller,text):
        if Monitor.global_enable and self.enable:
             print "%.2f" % (time.time()-Monitor.start_time), " ",caller.__class__.__name__," ", text
             Monitor.ofile.write (caller.__class__.__name__ +": " + text+"\n")
             
    def finish(self):
        Monitor.ofile.close()
        pass
