#!/usr/bin/python
#From https://gist.github.com/svdgraaf/198e2c0cf4cf0a031c84
import pygraphviz as pgv
import threading

from janitoo.options import JNTOptions
from janitoo.dhcp import JNTNetwork
from janitoo.node import JNTNodeMan

network = JNTNetwork(threading.Event(), JNTOptions({}))
network.fsm_network = network.create_fsm()
network.fsm_network .show_graph(fname='rst/images/fsm_network.png', prog='dot')
nodeman = JNTNodeMan(JNTOptions({}), None, None)
nodeman.fsm_state = nodeman.create_fsm()
nodeman.fsm_state .show_graph(fname='rst/images/fsm_nodeman.png', prog='dot')
