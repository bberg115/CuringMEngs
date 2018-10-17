# Ralph's edit. 10/16/18
# take control.py and th_2.c 
# need to add a runningRH/runningTemp to make sure that it stays on/off for min time


# Imports
from subprocess import Popen, PIPE
from os.path import expanduser
from ouimeaux.environment import Environment
from datetime import datetime, timedelta
import xml.etree.cElementTree as ET
import os #for parsing
import csv #export to CSV



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

# Set time format
timeFormat = "%Y-%m-%d %H:%M:%S.%f"

# Get current date and time as datetime object
currentDateTime = datetime.now()





	
	

# Read settings from XML file
xmlPath = "/home/pi/raspi-rht/" #will pre-define characteristics / limits
tree = ET.parse(os.path.join(xmlPath, 'ralph_control.xml'))
root = tree.getroot()
settingsXML = root.find("settings")
statusXML = root.find("status")

# Check if script is enabled. Quit if not.
enabled = settingsXML.find("enabled").text
if enabled != "True":
    raise SystemExit(1)

#make sure that run/stop doesn't happen too often
#if none, assume now eventhough this isn't 100% correct on startup
lastCommandRH = statusXML.find("lastCommandRH").text

if lastCommandRH is None:
	lastCommandRH = str(currentDateTime)
	
lastCommandRH = datetime.strptime(lastCommandRH, timeFormat)

lastCommandTemp = statusXML.find("lastCommandTemp").text
if lastCommandTemp is None:
	lastCommandTemp = str(currentDateTime)
lastCommandTemp = datetime.strptime(lastCommandTemp, timeFormat)		
# Check the last time we ran a WeMo discovery cycle
#lastDiscovery = statusXML.find("lastDiscovery").text

	
	
#Get values for humidifier from XML
targetRH = int(settingsXML.find("targetRH").text) # Get the target humidity level
toleranceRH = int(settingsXML.find("toleranceRH").text) # Get the tolerance for humidity level
runMinutesRH = int(settingsXML.find("runMinutesRH").text) # Get the min time for Humidifier to run
runMinutesTemp = int(settingsXML.find("runMinutesTemp").text) # Get the min time for Humidifier to run
# may need to convert minutes to seconds.. like original script
switchNameRH = settingsXML.find("switchNameRH").text # Get "friendly" name of WeMo Switch for humidifier

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
p = Popen([os.path.join(xmlPath,"./th_2")], stdout=PIPE, stderr=PIPE)
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

#causes error - cannot find wemo if waiting
#if lastDiscovery is not None:
#    # Convert to datetime object
#    lastDiscovery = datetime.strptime(lastDiscovery, timeFormat)
	
# Check if lastDiscovery is None or was more than 24 hours ago
#if lastDiscovery is None or (lastDiscovery + timedelta(hours=24)) < currentDateTime:
#    # Clear WeMo cache
#    p = Popen(["sudo", "wemo", "clear"], stdout=PIPE, stderr=PIPE)
#    p.communicate()
#    # Check if an error was returned
#    if err != '': print "WARNING: wemo clear returned error "+str(err)
#    # Rediscover devices
#    discoverWeMoDevices(env)
#    lastDiscovery = currentDateTime	
discoverWeMoDevices(env)	
	
# Connect to WeMo Switch - RH First
#change the following to loop between RH and Temp
switchRH = connectToWeMo(env, switchNameRH)
switchTemp = connectToWeMo(env, switchNameTemp)
# Status remains at 4 if no conditions are matched
statusRH = 4
statusTemp = 4

# Check if humidifier is running
if isSwitchRunning(switchRH): #if switch is on
    # Check if humidifier is out of water
    if isSwitchDrawingPower(switchRH):
        statusRH = 2
        friendlyStatusRH = "Out of Water"
    else:
        statusRH = 1
        friendlyStatusRH = "Running"
        #print "Thinks humidifier is on"
# Check if humidifier is stopped
elif isSwitchStopped(switchRH):
    statusRH = 0
    #print "Thinks humidifier is off"
    friendlyStatusRH = "Not Running"


# If status is still 4, there's an issue reading the status
if statusRH == 4:
    print "ERROR: Unable to read WeMo status"
    # Exit with error status
    raise SystemExit(1)


# Start or stop humidifier based on time and relative humidity
if statusRH == 0 and rh <= minRH:
    if (lastCommandRH + timedelta(minutes=runMinutesRH)) < currentDateTime:
	startSwitch(switchRH)
	lastCommandRH = currentDateTime
	friendlyStatusRH = "Running"
    else:
	print "RH Off-Time Too Short"

elif statusRH > 0 and (rh >= maxRH):
    if (lastCommandRH + timedelta(minutes=runMinutesRH)) < currentDateTime:
        stopSwitch(switchRH)
        lastCommandRH = currentDateTime
        friendlyStatusRH = "Not Running"#    statusXML.find("stoppedDateTime").text = str(currentDateTime)
    else:
        print "RH On-Time Too Short"

elif statusRH == 2:
    sendOutNoPowerAlert()
    friendlyStatusRH = "No Water"
	
print "RH Status: "+str(friendlyStatusRH)
print ("RH Value: " + str(rh) + " (" + str(minRH) + ")")



# Check if temp is running
if isSwitchRunning(switchTemp): #if switch is on
    # Check if humidifier is out of water
    if isSwitchDrawingPower(switchTemp):
        statusTemp = 2
        friendlyStatusTemp = "Out of Water"
    else:
        statusTemp = 1
        friendlyStatusTemp = "Running"
# Check if humidifier is stopped
elif isSwitchStopped(switchTemp):
    statusTemp = 0
    friendlyStatusTemp = "Not Running"


# If status is still 4, there's an issue reading the status
if statusTemp == 4:
    print "ERROR: Unable to read Temp WeMo status"
    # Exit with error status
    raise SystemExit(1)


# Start or stop humidifier based on time and relative humidity
if statusTemp == 0 and temp >= maxTemp:
    if (lastCommandTemp + timedelta(minutes=runMinutesTemp)) < currentDateTime:
        startSwitch(switchTemp)
        lastCommandTemp = currentDateTime
        friendlyStatusTemp = "Running"
    else:
        print "Temp Off-Time Too Short"	

elif statusTemp > 0 and (temp <= minTemp):
    if (lastCommandTemp + timedelta(minutes=runMinutesTemp)) < currentDateTime:
        stopSwitch(switchTemp)
        lastCommandTemp = currentDateTime
        friendlyStatusTemp = "Not Running"
    else:
        print "RH On-Time Too Short"

    
elif statusTemp == 2:
    sendOutNoPowerAlert()
    friendlyStatusTemp = "No Temp Power Draw"
	
print "Temp Status: "+str(friendlyStatusTemp)
print("Temp Value: " + str(temp) + " (" + str(maxTemp) + ")")
	
	
	
# Update status in XML file
statusXML.find("lastRH").text = str(rh)
statusXML.find("lastTemp").text = str(temp)
#statusXML.find("lastDiscovery").text = str(lastDiscovery)
statusXML.find("friendlyStatusRH").text = str(friendlyStatusRH)
statusXML.find("lastCommandRH").text = str(lastCommandRH)
statusXML.find("friendlyStatusTemp").text = str(friendlyStatusTemp)
statusXML.find("lastCommandTemp").text = str(lastCommandTemp)

tree.write(os.path.join(xmlPath, 'ralph_control.xml'))

with open('/home/pi/raspi-rht/log_export.csv', mode='a') as log_file:
    log_writer = csv.writer(log_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    log_writer.writerow([' '+str(currentDateTime), ' ' +str(minRH),' '+str(rh), ' ' +str(friendlyStatusRH), ' '+str(maxTemp),' '+str(temp), ' ' +str(friendlyStatusTemp)])
