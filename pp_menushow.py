import os
from Tkinter import *
import Tkinter as tk
import PIL.Image
import PIL.ImageTk
import PIL.ImageEnhance


from pp_imageplayer import ImagePlayer
from pp_medialist import MediaList
from pp_videoplayer import VideoPlayer
from pp_messageplayer import MessagePlayer
from pp_utils import Monitor


class MenuShow:
    """ Displays a menu with optional hint below it. User can traverse the menu and
              select a track using key or button presses.
        Interface:
         * play - displays the menu and selects the first entry
         * key_pressed, button_pressed - receives user events passes them to a Player if a track is playing,
                otherwise actions them with _next, _previous, _play_selected_track, _end
         Optional display of eggtimer by means of Players ready_callback
         Supports imageplayer, videoplayer,messagplayer,menushow,mediashow
         Destroys itself on exit
    """

# *********************
# external interface
# ********************

    def __init__(self,
                            show,
                            canvas,
                            showlist,
                            pp_home,
                            pp_profile):
        """ canvas - the canvas that the menu is to be written on
            show - the name of the configuration dictionary section for the menu
            cf  - the configuration object
            pp_home - Pi presents data_home directory
            pp_profile - Pi presents profile directory"""
        
        self.mon=Monitor()
        self.mon.on()
        
        #instantiate arguments
        self.show=show
        self.showlist=showlist
        self.canvas=canvas
        self.pp_home=pp_home
        self.pp_profile=pp_profile

        
        # init variables
        self.drawn  = None
        self.player=None
        self.shower=None
        self.menu_timeout_running=None



    def play(self,end_callback,ready_callback=None,top=False):
        """ displays the menu 
              end_callback - function to be called when the menu exits
              ready_callback - callback when menu is ready to display (not used)
              top is True when the show is top level (run from [start])
        """
        
        #instantiate arguments
        self.end_callback=end_callback
        self.ready_callback=ready_callback
        self.top=top

        
        # check  data files are available.
        self.menu_file = self.pp_profile + "/" + self.show['medialist']
        if not os.path.exists(self.menu_file):
            self.mon.err(self,"Medialist file not found: "+ self.menu_file)
            self._end("Medialist file not found")
        
        #create a medialist for the menu and read it.
        self.medialist=MediaList()
        if self.medialist.open_list(self.menu_file,self.showlist.sissue()) == False:
            self.mon.err(self,"Version of medialist different to Pi Presents")
            self._end("fatal error")
           
        if self.show['has-background']=="yes":
            background_index=self.medialist.index_of_track ('pp-menu-background')
            if background_index>=0:
                self.menu_img_file = self.complete_path(self.medialist.track(background_index))
                if not os.path.exists(self.menu_img_file):
                    self.mon.err(self,"Menu background file not found: "+ self.menu_img_file)
                    self._end("Menu background file not found")
            else:
                self.mon.err(self,"Menu background not found in medialist")
                self._end("Menu background not found")

        #start timeout alarm if required
        if int(self.show['timeout'])<>0:
            self.menu_timeout_running=self.canvas.after(int(self.show['timeout'])*1000,self._timeout_menu)
        
        if self.ready_callback<>None:
            self.ready_callback()
        
        self.canvas.delete(ALL)
        
        # display background image
        if self.show['has-background']=="yes":
            self._display_background()
 
       #display the list of video titles
        self._display_video_titles()

        # display instructions (hint)
        self.canvas.create_text(int(self.canvas['width'])/2,
                                int(self.canvas['height']) - int(self.show['hint-y']),
                                text=self.show['hint-text'],
                                fill=self.show['hint-colour'],
                                font=self.show['hint-font'])
        self.canvas.update( )



   # respond to key presses.
    def key_pressed(self,key_name):
        self.mon.log(self,"received key: " + key_name)
        
        if key_name=='':
            pass
        
        elif key_name=='escape':
            # if next lower show eor player is running pass down to stop bottom level
            # ELSE stop this show if not at top
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            elif self.player<>None:
                self.player.key_pressed(key_name)
            else:
                # not at top so stop the show
                if  self.top == False:
                    self._end("exit from stop command")
                else:
                    pass
      
        elif key_name in ('up','down'):
        # if child or sub-show running and is a show pass down
        # if  child not running - move
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            else:
                if self.player==None:
                    if key_name=='up':
                        self._previous()
                    else:
                        self._next()
                
        elif key_name=='return':
            # if child running and is show - pass down
            # if no track already running  - play
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            else:
                if self.player==None:
                    self._play_selected_track(self.medialist.selected_track())

        elif key_name in ('p',' '):
            # pass down if show or track running.
            if self.shower<>None:
                self.shower.key_pressed(key_name)
            elif self.player<>None:
                self.player.key_pressed(key_name)
 
 
    def button_pressed(self,button,edge):
        if button=='play': self.key_pressed("return")
        elif  button =='up': self.key_pressed("up")
        elif button=='down': self.key_pressed("down")
        elif button=='stop': self.key_pressed("escape")
        elif button=='pause': self.key_pressed('p')

    def kill(self):
        if self.shower<>None:
            self.mon.log(self,"sent kill to shower")
            self.shower.kill()
        elif self.player<>None:
            self.mon.log(self,"sent kill to player")
            self.player.kill()
        else:
            self._end("killed")



# *********************
# INTERNAL FUNCTIONS
# ********************

# *********************
# Sequencing
# *********************

    def _timeout_menu(self):
        self.canvas.delete(ALL)
        self.canvas.update_idletasks( )
        self.end_callback("exit menu from timeout")
        self=None
        return
        
    
    #stop menu from user command or error
    def _end(self,message):
        self.canvas.delete(ALL)
        self.canvas.update_idletasks( )
        self.mon.log(self,"Ending menushow: "+ self.show['show-ref'])  
        if self.menu_timeout_running<>None:
            self.canvas.after_cancel(self.menu_timeout_running)
            self.menu_timeout_running=None
        self.end_callback(message)
        self=None
        return


    def _next(self):     
        self._highlight_menu_entry(self.menu_index,False)
        self.medialist.next()
        if self.menu_index==self.menu_length-1:
            self.menu_index=0
        else:
            self.menu_index+=1
        self._highlight_menu_entry(self.menu_index,True)     


    def _previous(self):   
        self._highlight_menu_entry(self.menu_index,False)
        if self.menu_index==0:
            self.menu_index=self.menu_length-1
        else:
            self.menu_index-=1
        self.medialist.previous()
        self._highlight_menu_entry(self.menu_index,True)    


# *********************
# Dispatching to Players
# *********************

    def complete_path(self,selected_track):
        #  complete path of the filename of the selected entry
        track_file = selected_track['location']
        if track_file[0]=="+":
                track_file=self.pp_home+track_file[1:]
        self.mon.log(self,"Track to play is: "+ track_file)
        return track_file     
         
        if os.path.exists(track_file)==False:
            self.mon.err(self,"Track not found: "+ track_file)
            self._end("track file not found")
            return False

    def _play_selected_track(self,selected_track):
        """ selects the appropriate player from type field of the medialist and computes
              the parameters for that type
              selected track is a dictionary for the track/show
        """
         #remove menu and show working.....        
        self.canvas.delete(ALL)
        if self.menu_timeout_running<>None:
            self.canvas.after_cancel(self.menu_timeout_running)
            self.menu_timeout_running=None
        self._display_eggtimer('Loading........')
    
        # dispatch track by type
        self.player=None
        self.shower=None
        track_type = selected_track['type']
        self.mon.log(self,"Track type is: "+ track_type)
        
        if track_type=="video":
            # create a videoplayer
            track_file=self.complete_path(selected_track)
            self.player=VideoPlayer(self.canvas,self.show,selected_track)
            self.player.play(track_file,
                                        self._end_player,
                                        self._delete_eggtimer,
                                        enable_menu=False)
                                        
        elif track_type=="image":
            # images played from menus don't have children
            enable_child=False
            track_file=self.complete_path(selected_track)
            self.player=ImagePlayer(self.canvas,self.show,selected_track)
            self.player.play(track_file,
                                    self._end_player,
                                    self._delete_eggtimer,
                                    enable_menu=enable_child,
                                    )
                                    
        elif track_type=="message":
            # bit odd because MessagePlayer is used internally to display text. 
            text=selected_track['text']
            self.player=MessagePlayer(self.canvas,self.show,selected_track)
            self.player.play(text,
                                    self._end_player,
                                    self._delete_eggtimer,
                                    enable_menu=False
                                    )
 
        elif track_type=="show":
            # get the show from the showlist
            index = self.showlist.index_of_show(selected_track['sub-show'])
            if index >=0:
                self.showlist.select(index)
                selected_show=self.showlist.selected_show()
            else:
                self.mon.err(self,"Show not found in showlist: "+ selected_track['sub-show'])
                self._end("Unknown show")
            
            if selected_show['type']=="mediashow":    
                self.shower= MediaShow(selected_show,
                                                                self.canvas,
                                                                self.showlist,
                                                                self.pp_home,
                                                                self.pp_profile)
                self.shower.play(self._end_shower,top=False)

            elif selected_show['type']=="menu": 
                self.shower= MenuShow(selected_show,
                                                        self.canvas,
                                                        self.showlist,
                                                        self.pp_home,
                                                        self.pp_profile)
                self.shower.play(self._end_shower,top=False)                                    
            else:
                self.mon.err(self,"Unknown Show Type: "+ selected_show['type'])
                self._end("Unknown show type")  
                
        else:
            self.mon.err(self,"Unknown Track Type: "+ track_type)
            self._end("Unknown track type")
            
    def _end_player(self,message):
        self.mon.log(self,"Returned from player with message: "+ message)
        self.player=None
        if message in("killed","fatal error"):
            self._end(message)
        self._display_eggtimer("Stopping..")
        self._what_next(message)

    def _end_shower(self,message):
        self.mon.log(self,"Returned from shower with message: "+ message)
        self.shower=None
        if message in ("killed","fatal error"):
            self._end(message)
        self._display_eggtimer("Stopping..")
        self._what_next(message)  
   

     # at the end of a track just re-display the menu with the original callback from the menu       
    def _what_next(self,message):
        self.mon.log(self,"Re-displaying menu")
        self.play(self.end_callback,top=self.top)



# *********************
# Displaying things
# *********************

    def _display_background(self):
        pil_menu_img=PIL.Image.open(self.menu_img_file)
        # adjust brightness and rotate (experimental)
        # enh=PIL.ImageEnhance.Brightness(pil_menu_img)
        # pil_menu_img=enh.enhance(0.1)
        # pil_menu_img=pil_menu_img.rotate(45)
        self.menu_background = PIL.ImageTk.PhotoImage(pil_menu_img)
        self.drawn = self.canvas.create_image(int(self.canvas['width'])/2,
                                      int(self.canvas['height'])/2,
                                      image=self.menu_background,
                                      anchor=CENTER)


    def _display_video_titles(self):
        self.menu_length=1
        self.menu_entry_id=[]
        x=int(self.show['menu-x'])
        y=int(self.show['menu-y'])
        self.medialist.start()
        while True:
            id=self.canvas.create_text(x,y,anchor=NW,
                                       text="* "+self.medialist.selected_track()['title'],
                                       fill=self.show['entry-colour'],
                                       font=self.show['entry-font'])
            self.menu_entry_id.append(id)
            y+=int(self.show['menu-spacing'])
            if self.medialist.at_end():
                break
            self.menu_length+=1
            self.medialist.next()
            
        # select and highlight the first entry
        self.medialist.start()
        self.menu_index=0
        self._highlight_menu_entry(self.menu_index,True)
        # self.medialist.print_list()

    def _highlight_menu_entry(self,index,state):
        if state==True:
            self.canvas.itemconfig(self.menu_entry_id[index],fill=self.show['entry-select-colour'])
        else:
            self.canvas.itemconfig(self.menu_entry_id[index],fill=self.show['entry-colour'])
    
    
    # make this cd controlled!!!!!!!!!!

    def _display_eggtimer(self,text):
        self.canvas.create_text(int(self.canvas['width'])/2,
                                              int(self.canvas['height'])/2,
                                                  text= text,
                                                  fill='white',
                                                  font="Helvetica 20 bold")
        self.canvas.update_idletasks( )


    def _delete_eggtimer(self):
            self.canvas.delete(ALL)

from pp_mediashow import MediaShow
