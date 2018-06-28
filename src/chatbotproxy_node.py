#!/usr/bin/env python

import rospy, json
from threading import Thread

from std_msgs.msg import *
from rtspeech.msg import RealtimeTranscript
from rtspeech.srv import setMicrophoneMuteState, getMicrophoneMuteState
from assistant.msg import ChatbotAnswer
from commandproc.msg import CommandString

loglevel = rospy.get_param('/debug/loglevel', rospy.INFO)
minimumconfidence = 0.4

rospy.init_node('chatbotproxy', anonymous=False, log_level=loglevel)

controllerpub = rospy.Publisher(rospy.get_namespace() + 'chatbotcontroller_out', std_msgs.msg.String, queue_size=10)

def sendToWebpage(jsonobj):
    controllerpub.publish(json.dumps(jsonobj))

rospy.loginfo("Waiting for microphone mute services...")
rospy.wait_for_service(rospy.get_namespace() + 'setmicrophonemutestate', timeout=None)
rospy.wait_for_service(rospy.get_namespace() + 'getmicrophonemutestate', timeout=None)
rospy.loginfo("Done.")

getmicstate = rospy.ServiceProxy(rospy.get_namespace() + 'getmicrophonemutestate', getMicrophoneMuteState)
setmicstate = rospy.ServiceProxy(rospy.get_namespace() + 'setmicrophonemutestate', setMicrophoneMuteState)

micstate = getmicstate()
rospy.loginfo("Microphone is {}".format(micstate))

commandpub = rospy.Publisher(rospy.get_namespace() + 'commandstring', CommandString, queue_size=10)

def assicb(cbans):
    sendToWebpage({
        'type' : 'answers',
        'answers': [
            {'confidence' : cbans.confidence,
            'text' : cbans.text}    
        ]})

assistantsub = rospy.Subscriber(rospy.get_namespace() + 'chatbotanswer', ChatbotAnswer, assicb)

def rtscb(rts):
    sendToWebpage({
        'type' : 'stt',
        'confidence' : rts.confidence,
        'text' : rts.text
        })

rttranscriptsub = rospy.Subscriber(rospy.get_namespace() + 'realtimetranscript', RealtimeTranscript, rtscb)

def togglecb(msg):
    global micstate
    if msg['what'] == 'microphone':
        micstate = not micstate
        setmicstate(micstate)
        msg['text'] = "Disabled" if micstate else "Enabled"
        sendToWebpage(msg)

def answercb(msg):
    com = CommandString()
    com.command = msg['text']
    commandpub.publish(com)

def navicb(msg):
    pass

controlleractions = {
    'toggle' : togglecb,
    'click_answer' : answercb,
    'click_navigation': navicb
    }

def cbcntrcb(msg):
    msg = json.loads(msg.data)
    controlleractions[msg['type']](msg)

controllersub = rospy.Subscriber(rospy.get_namespace() + 'chatbotcontroller_in', std_msgs.msg.String, cbcntrcb)

while not rospy.is_shutdown():
    try:
        rospy.spin()
    except:
        pass
rospy.loginfo("chatbotproxy node shutdown")
