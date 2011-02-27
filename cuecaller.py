#!/usr/bin/python

####################################################################################
####################################################################################
####                                                                            ####
####    cuecaller.py   (version 1.0)                                            ####
####    Copyright 2011 Berkeley Churchill                                       ####
####                                                                            ####
####    This program is free software: you can redistribute it and/or modify    ####
####    it under the terms of the GNU General Public License as published by    ####
####    the Free Software Foundation, either version 3 of the License, or       ####
####    (at your option) any later version.                                     ####
####                                                                            ####
####    This program is distributed in the hope that it will be useful,         ####
####    but WITHOUT ANY WARRANTY; without even the implied warranty of          ####
####    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           ####
####    GNU General Public License for more details.                            ####
####                                                                            ####
####    You should have received a copy of the GNU General Public License       ####
####    along with this program.  If not, see <http://www.gnu.org/licenses/>.   ####
####                                                                            ####
####################################################################################
####################################################################################

import threading
import time
import subprocess
import sys
import signal

# open configuration file
#  read label file
#  read shells, read cues

class configuration:
    def __init__(self,filename, v):

        self.verbose = v

        file = open(filename,'r')
        line = file.readline()
        options={}
        lineNumber = 0
        while(line != ""):
            lineNumber = lineNumber + 1         
            commentAt = line.find("#")   #remove comments
            if(commentAt != -1):
                line = line[:commentAt]

            line = line.split("=")  #process lines of the form:: [^=]*=[^=]*
            if(len(line) == 2):
                key = line[0]
                value = line[1]
                key = key.strip()
                value = value.strip()
                options[key] = value
            elif(len(line) > 2):
                raise RuntimeError("Invalid configuration file syntax, line " + str(lineNumber))

            line = file.readline()
        file.close()

        self.currentCue = 0 

        #for key in options.keys():
        #   print key, options[key]
        if('INTERPRETER' in options.keys()):
            self.interpreter = options['INTERPRETER'].split(" ")   #split is necessary since we need to pass a list...
        else:
            self.interpreter = '/bin/bash'
        
        if('LABELFILE' in options.keys()):
            self.labelfilename = options['LABELFILE']
        else:
            self.labelfilename = 'label.txt'

        if('SOUNDFILE' in options.keys()):
            self.soundfile = options['SOUNDFILE']
        else:
            self.soundfile = 'sound.mp3'    
        
        if('SOUNDPLAYER' in options.keys()):
            self.soundplayer = options['SOUNDPLAYER']
        else:
            self.soundplayer="mplayer"

            #the default command string supports the following escapes
            # %l - the label
            # %s - the start time
            # %S - the start time in milliseconds
            # %e - the end time
            # %E - the end time in milliseconds
            # %t - the fade time
            # %T - the fade time in milliseconds
            # %n - the number
            # %% - the percent symbol
        if('DEFAULTCOMMAND' in options.keys()):
            self.defaultcommand = options['DEFAULTCOMMAND']
        else:
            self.defaultcommand = "%l"

        if('STARTUPCOMMAND' in options.keys()):
            self.startupcommand = options['STARTUPCOMMAND']
        else:
            self.startupcommand = ""
    
        if(self.verbose):
            print "Using", self.labelfilename, "for cues."
            print "Using", self.interpreter, "for an interpreter."
            print "Using", self.soundfile, "for the sound file."
            print "Using", self.soundplayer, "for the sound player."

        self.pipefilename = "/tmp/lap.cuecaller." + str(time.time())
        mkfifo = subprocess.Popen(["mkfifo", self.pipefilename])
        mkfifo.communicate() #wait for it to finish

        self.cues = {}      #the keys will be times, and the values will be (label, fadetime, command, number)
        labelfile = open(self.labelfilename,'r')
        count = 1
        
        subs = {}
        subs['%'] = '%'
        while(True):
            line = labelfile.readline();
            if(line == ""):
                break;
            line = line.split(None,3)
            if((len(line) == 1) or (len(line) > 3)):
                print sys.stderr.write("WARNING: line " + str(count) + " of the label file appears to be misformatted.");
                continue
            if((len(line) == 2) or (len(line) == 3)):
                key = line[0]
                fadetime = float(line[1])-float(line[0])
                label = "";
                command = self.defaultcommand

            if(len(line) == 3):
                key = line[0]
                fadetime = float(line[1])-float(line[0])
                label = line[2].strip()
                command = self.defaultcommand

                subs['l'] = label
                subs['s'] = line[0]
                subs['e'] = line[1]
                subs['t'] = str(fadetime)
                subs['n'] = count

                subs['S'] = str(int(round(1000*float(line[0]))))  #can you say inefficient?
                subs['E'] = str(int(round(1000*float(line[1]))))    #I might look at this later.
                subs['T'] = str(int(round(1000*fadetime)))

                try:
                    for i in range(0,len(command)):
                        if i < len(command) and command[i]=="%":
                            #print "Found subsitution:",command[i+1],"  value=",subs[command[i+1]]
                            command = command.replace(command[i:i+2],subs[command[i+1]])
                            
                except:
                    if(i >= len(command) - 1):
                        raise RuntimeError("The switch used on the end of DEFAULTCOMMAND line of the configuration file is invalid.")
                    else:
                        raise RuntimeError("The switch used (" + command[i+1] + ") on the DEFAULTCOMMAND line of the configuration file is invalid.")
            self.cues[count] = (key,label,fadetime,command, count)
            count = count+1
            if count > 3 and key < self.cues[count-2][0]:
                print sys.stderr.write("WARNING: line " + str(count-1) + " of the label file is out of order.  A cue might not be called properly.");
        self.count = count;

    def docue(self,cue_number):
        ctime = float(self.cues[cue_number][0]);
        if cue_number+3 < self.count:
            ntime = float(self.cues[cue_number+3][0]);
            dtime = ntime-ctime;
            timer = threading.Timer(dtime,self.docue,[cue_number+3])
            timer.start();
            self.timer_list.append(timer)
        else:
            self.timers_running = self.timers_running-1;
        self.currentCue = self.currentCue + 1
        command = self.cues[cue_number][3]
        self.pipefile.write(command + '\n')
        self.pipefile.flush()
        if self.verbose:
            print "Calling cue...",self.currentCue
            print "    executing command:",command
        

    def go(self):

        #adjust sigterm to exit as cleanly as possible.
        signal.signal(signal.SIGTERM,self.signal_handler);
        signal.signal(signal.SIGINT,self.signal_handler);
        
        #start the interpreter and open the pipe
        nullfile = open('/dev/null')
        self.pipefile = open(self.pipefilename,'r+')
        self.interp = subprocess.Popen(self.interpreter, stdin=self.pipefile, stdout=None)
        
        if(self.startupcommand != ""):
            self.pipefile.write(self.startupcommand + "\n")

        #play the music
        

        if(self.verbose):
            print "Running",self.soundplayer,self.soundfile
            self.musicp = subprocess.Popen([self.soundplayer, self.soundfile], stdin=nullfile, stdout=nullfile)
        else:
            self.musicp = subprocess.Popen([self.soundplayer, self.soundfile], stdin=nullfile, stdout=nullfile, stderr=subprocess.PIPE)

        #start the timers

        print "Calling cues:"


        self.timers_running = 0;
        self.timer_list = [];
        for i in [1,2,3]:
            key = self.cues[i][0];
            timer = threading.Timer(float(key),self.docue,[i])
        #   print "Cue",self.cues[key][0],"At",key,"For",self.cues[key][1],"Does",self.cues[key][2]
            timer.start()
            self.timer_list.append(timer);
            self.timers_running = self.timers_running+1;
        


        #wait for the music to end.
        self.musicp.wait()

        #wait for all the timers to finish
        while self.timers_running > 0:
            time.sleep(1);

        #close the pipelines...
        nullfile.close()
        self.pipefile.close()
    
    def signal_handler(self,signum, frame):
        print "SIGNAL " + str(signum) + " received.";
        for T in self.timer_list:
            if T.isAlive():
                T.cancel();
        running = threading.enumerate();
        self.timers_running = 0;
        self.musicp.terminate();
        self.interp.terminate();
        
        
#this is where execution starts
def main(): 
    if(len(sys.argv) != 2):
        print("Usage:")
        print("     cuecaller.py <config file>")
        print("")
        print("     A configuration file consists of key-value pairs written in the form A=B, one per line.  Some important keys to set are INTERPRETER, LABELFILE, SOUNDFILE, and SOUNDPLAYER.")
    else:
        c = configuration(sys.argv[1],True)
        c.go()

main()

