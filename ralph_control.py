# Ralph's edit. 2050 10/15/18
#need to make it do RH first, then temp. Need to change functions to be more 'general' for both RH and Temp
# take control.py and th_2.c 
# output a the temp & rh to log
# modify weemo based on being above or below targets
# assumes that this require py2.7


# Imports
from subprocess import Popen, PIPE
from os.path import expanduser
from ouimeaux.environment import Environment
from datetime import datetime, timedelta
import xml.etree.cElementTree as ET
import logging #added this based on python.org

# attempt at testing a log...
logging.basicConfig(filename='example.log',level=logging.DEBUG)
logging.debug('This message should go to the log file')
logging.info('So should this')
logging.warning('And this, too')




# Functions
def startWeMoEnvironment():
    "Starts the WeMo environment"
    env = Environment()
    env.start()
    return env

def discoverWeMoDevices(env): 
    "Discover WeMo devices"
    env.discover(seconds=3)
    return

def connectToWeMo(env, switchName):
    "Connects to the WeMo switch"
    return env.get_switch(switchName)

def isSwitchRunning(switch):
    "Checks if WeMo switch is on"
    state = switch.basicevent.GetBinaryState()['BinaryState']
    if state == '1' or state == '8':
        return True
    else:
        return False

def isSwitchStopped(switch):
    "Checks if WeMo switch is off"
    if switch.basicevent.GetBinaryState()['BinaryState'] == '0':
        return True
    else:
        return False

def isSwitchDrawingPower(switch): # still not sure if the switch we have will measure mWatts
    "Checks if WeMo energy usage is low"
    # Extract current energy usage in mW
    usage = switch.insight.GetInsightParams()['InsightParams'].split("|")[7]
    # Convert to watts
    usage = int(usage) / 1000
    # If watts is less than 10, it's out of water, unplugged, or turned off
    if usage < 10:
        return True
    else:
        return False

def sendOutNoPowerAlert(): #see line 45
    "Send an alert about humidifier being out of water"
    # TODO
    return

def startSwitch(switch):
    "Turns the WeMo switch on"
    switch.basicevent.SetBinaryState(BinaryState=1)
    return

def stopSwitch(switch):
    "Turns the WeMo switch off"
    switch.basicevent.SetBinaryState(BinaryState=0)
    return

env = startWeMoEnvironment()
discoverWeMoDevices(env) #need to run once a day?

# Read settings from XML file
xmlPath = "ralph_control.xml" #will pre-define characteristics / limits
tree = ET.parse(xmlPath)
root = tree.getroot()
settingsXML = root.find("settings")
statusXML = root.find("status")

# Check if script is enabled. Quit if not.
enabled = settingsXML.find("enabled").text
if enabled != "True":
    raise SystemExit(1)

	
#Get values for humidifier from XML
targetRH = int(settingsXML.find("targetRH").text) # Get the target humidity level
toleranceRH = int(settingsXML.find("toleranceRH").text) # Get the tolerance for humidity level
runMinutesRH = int(settingsXML.find("runMinutesRH").text) # Get the min time for Humidifier to run
# may need to convert minutes to seconds.. like original script
switchName = settingsXML.find("switchNameRH").text # Get "friendly" name of WeMo Switch for humidifier

# Calculate maximum humidity
maxRH = targetRH + toleranceRH
# Calculate minimum humidity
minRH = targetRH - toleranceRH


#temperature's turn, incomplete (need to add functions above)...
#Get values for temperature from XML
targetTemp = int(settingsXML.find("targetTemp").text) # Get the target temperature
toleranceTemp = int(settingsXML.find("toleranceTemp").text) # Get the tolerance for temperature
runMinutesTemp = int(settingsXML.find("runMinutesTemp").text) # Get the min time for fridge to run
# may need to convert minutes to seconds.. like original script
switchNameTemp = settingsXML.find("switchNameTemp").text # Get "friendly" name of WeMo Switch for temperature

# Calculate maximum temperature
maxTemp = targetTemp + toleranceTemp
# Calculate minimum temperature
minTemp = targetTemp - toleranceTemp



















# Run program to get temp and humidity from sensor
p = Popen(["./th_2"], stdout=PIPE, stderr=PIPE)
output, err = p.communicate()

# Check if an error was returned
if err != '':
    print "ERROR: th_2 returned error "+str(err)
    # Exit with error status
    raise SystemExit(1)

# Split the output into separate variables
temp, rh = output.split()

# Make them floats
temp = float(temp)
rh = float(rh)

# Connect to WeMo Switch - RH First
#change the following to loop between RH and Temp
switch = connectToWeMo(env, switchName)

# Status remains at 4 if no conditions are matched
status = 4

# Check if humidifier is running
if isSwitchRunning(switch): #if switch is on
    # Check if humidifier is out of water
    if isSwitchDrawingPower(switch):
        status = 2
        friendlyStatus = "Out of Water"
    else:
        status = 1
        friendlyStatus = "Running"
# Check if humidifier is stopped
elif isSwitchStopped(switch):
    status = 0
    friendlyStatus = "Not Running"

print "Status = "+str(status)

# If status is still 4, there's an issue reading the status
if status == 4:
    print "ERROR: Unable to read WeMo status"
    # Exit with error status
    raise SystemExit(1)


# Start or stop humidifier based on time and relative humidity
if status == 0 and rh <= minRH:
    startSwitch(switch)
    friendlyStatus = "Running"

elif status > 0 and (rh >= maxRH):
    stopSwitch(switch)
    friendlyStatus = "Not Running"
#    statusXML.find("stoppedDateTime").text = str(currentDateTime)
    
elif status == 2:
    sendOutNoPowerAlert()
    friendlyStatus = "No Power Draw"
	
	
	
# Update status in XML file
#statusXML.find("nextScheduledStart").text = str(nextStart)
#statusXML.find("nextScheduledStop").text = str(nextStop)
statusXML.find("lastRH").text = str(rh)
statusXML.find("lastTemp").text = str(temp)
#statusXML.find("lastUpdate").text = str(currentDateTime)
statusXML.find("lastStatus").text = str(friendlyStatus)
#statusXML.find("lastDiscovery").text = str(lastDiscovery)
tree.write(xmlPath)
