import os
import sys
import math
import copy
import RLPy
import PySide2
from PySide2.QtCore import *
from PySide2.QtCore import QResource
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget
from PySide2.QtQuickWidgets import QQuickWidget
from PySide2.QtQuick import QQuickView
from PySide2.shiboken2 import wrapInstance

import BoneData
import KeyData
from enum import IntEnum
class HandRiggerState(IntEnum):
    Disable = 0
    Ready   = 1
    Running = 2

sys.dont_write_bytecode = True


# register QML resource
exe_parent_path = os.path.abspath(os.path.join(sys.executable, os.pardir))
resoruce_path = exe_parent_path + "\\OpenPlugin\\HandRigger\\resource"
sys.path.insert(0, resoruce_path)
QResource.registerResource(resoruce_path + "\\handrigger.rcc")

# global data
app_start_up = True
avatar = None
hand_rigger_state = HandRiggerState.Disable
hand_device = None
keys = []
device_data = None

# dialog
main_dlg = None
main_pyside_dlg = None
main_dlg_view = None
main_dlg_root = None

# hotkey action
space_action = None

# RL API data member
ui_kit = RLPy.RUi
mocap_manager = RLPy.RGlobal.GetMocapManager()

# Callback
main_dlg_callback = None
hand_rigger_callback = None
hand_rigger_callback_list = []

class HandRigger(object):
    def __init__(self, _main_dlg):
        global main_dlg
        global main_pyside_dlg
        global main_dlg_view
        global main_dlg_root
        global space_action
        global ui_kit

        main_dlg = _main_dlg

        # create an URL to the QML file
        main_dlg_url = QUrl("qrc:/handrigger/qml/handrigger.qml")
        main_dlg_view = PySide2.QtQuickWidgets.QQuickWidget()
        main_dlg_view.setSource(main_dlg_url)
        main_dlg_view.setResizeMode(PySide2.QtQuickWidgets.QQuickWidget.SizeRootObjectToView)

        # Python get handrig.qml object
        main_dlg_root = main_dlg_view.rootObject()

        # set dialog layout with titlebar
        main_pyside_dlg = wrapInstance(int(main_dlg.GetWindow()), PySide2.QtWidgets.QDialog)
        main_pyside_dlg.setObjectName('HandRigger')

        # HotKey
        space_action = wrapInstance(int(ui_kit.AddHotKey('Space')), PySide2.QtWidgets.QAction)
        space_action.triggered.connect(self.run)
        space_action.setEnabled(False)

        # Generate custom dialog
        self.main_layout = main_pyside_dlg.layout()
        self.main_layout.addWidget(main_dlg_view)
        main_pyside_dlg.adjustSize()

    def show(self):
        global app_start_up
        global main_dlg
        global main_pyside_dlg
        global space_action
        global hand_device
        global keys
        
        if main_pyside_dlg.isVisible():
            space_action.setEnabled(False)
            main_pyside_dlg.hide()
        else:
            if app_start_up:
                register_dialog_callback()
                register_hand_rigger_callback()
                
                keys.append(KeyData.get_key_0())
                keys.append(KeyData.get_key_1())
                keys.append(KeyData.get_key_2())
                keys.append(KeyData.get_key_3())
                keys.append(KeyData.get_key_4())
                keys.append(KeyData.get_key_5())
                keys.append(KeyData.get_key_6())

                hand_device = mocap_manager.AddHandDevice('hand_rigger')
                app_start_up = False
            update_hand_rigger_state()
            main_dlg.Show()

    def hide(self):
        global main_pyside_dlg
        global space_action

        if main_pyside_dlg.isVisible():
            space_action.setEnabled(False)
            main_pyside_dlg.hide()
            
    def get_main_dlg(self):
        global main_dlg_view
        return main_dlg_view

    def run(self):
        global hand_rigger_state
        global mocap_manager
        global avatar
        global hand_device

        if hand_rigger_state == HandRiggerState.Ready:
            set_hand_rigger_state(HandRiggerState.Running)
            if mocap_manager != None:
                hand_device.SetEnable(avatar, True)
                self.rigger_init()
                mocap_manager.Start(RLPy.EMocapState_Preview)

        elif hand_rigger_state == HandRiggerState.Running:
            set_hand_rigger_state(HandRiggerState.Ready)
            if mocap_manager != None:
                mocap_manager.Stop()

    def rigger_init(self):
        global hand_device
        global avatar
        
        if hand_device != None:
            # device setting
            device_setting = hand_device.GetDeviceSetting()
            device_setting.SetMocapCoordinate(RLPy.ECoordinateAxis_Y, RLPy.ECoordinateAxis_Z, RLPy.ECoordinateSystem_RightHand)
            pos_setting = device_setting.GetPositionSetting()
            pos_setting.SetCoordinateSpace(RLPy.ECoordinateSpace_Local)
            pos_setting.SetUnit(RLPy.EPositionUnit_Centimeters)
            rot_setting = device_setting.GetRotationSetting()
            rot_setting.SetCoordinateSpace(RLPy.ECoordinateSpace_Local)
            rot_setting.SetType(RLPy.ERotationType_Euler)
            rot_setting.SetUnit(RLPy.ERotationUnit_Degrees)
            rot_setting.SetEulerOrder(RLPy.EEulerOrder_ZXY)

        if avatar:
            # hand setting
            hand_setting = hand_device.GetHandSetting(avatar)
            hand_setting.SetRightHandJoin(RLPy.EHandJoin_Wrist)
            hand_setting.SetLeftHandJoin(RLPy.EHandJoin_Wrist)
            hand_setting.SetHandJoinType(RLPy.EHandJoinType_UseParentBone)
            hand_setting.SetRightHandDataSource(RLPy.EHandDataSource_RightHand)
            hand_setting.SetLeftHandDataSource(RLPy.EHandDataSource_RightHand)
            hand_setting.SetActivePart(RLPy.EBodyActivePart_Hand_R | RLPy.EBodyActivePart_Finger_R |
                                       RLPy.EBodyActivePart_Hand_L | RLPy.EBodyActivePart_Finger_L)

        bone_list = BoneData.get_bone_list()
        hand_device.Initialize(bone_list)

    def process_data(self, square_dist):
        global keys
        global hand_device
        global mocap_manager
        global device_data

        if hand_device.IsTPoseReady() == False:
            t_pose = BoneData.get_t_pose()
            device_data = copy.deepcopy(t_pose)
            hand_device.SetTPoseData(t_pose)

        else:
            self.nearest_two_keys(square_dist)          # method 2
            #self.inverse_square_distance(square_dist)  # method 1

            hand_device.ProcessData(0, device_data, -1)

    def inverse_square_distance(self, square_dist):
        global keys
        global device_data
        
        offset = 6*16
        num_of_hand_bone = 6*20
        for i in range(7):
            if square_dist[i] < 0.4:
                for j in range(num_of_hand_bone):
                    device_data[offset+j] = device_data[offset+j] + keys[i][j]
                return
        for i in range(7):
            square_dist[i] = 1/square_dist[i]
        sum = 0
        for i in range(7):
            sum = sum + square_dist[i]
        for i in range(7):
            square_dist[i] = square_dist[i]/sum
        for i in range(num_of_hand_bone):
            device_data[offset+i] = 0
            for j in range(7):
                device_data[offset+i] = device_data[offset+i] + square_dist[j] * keys[j][i]

    def nearest_two_keys(self, square_dist):
        global keys
        global device_data

        offset = 6*16
        num_of_hand_bone = 6*20
        weights = []

        for i in range(7):
            weights.append([i, square_dist[i]])
        sorted_weights = sorted(weights, key = lambda w: w[1])

        key_1_index = sorted_weights[0][0]
        key_2_index = sorted_weights[1][0]
        key_1_dist = math.sqrt(square_dist[key_1_index])
        key_2_dist = math.sqrt(square_dist[key_2_index])
        dist_sum = key_1_dist + key_2_dist
        for i in range(num_of_hand_bone):
            device_data[offset+i] = (key_2_dist/dist_sum) * keys[key_1_index][i] + (key_1_dist/dist_sum) * keys[key_2_index][i]

class DialogCallback(RLPy.RDialogEventCallback):
    def __init__(self):
        RLPy.RDialogEventCallback.__init__(self)
        self.show_fptr = None

    def OnDialogShow(self):
        if self.show_fptr is not None:
            self.show_fptr()

    def register_show_callback(self, show_function):
        self.show_fptr = show_function

class HandRiggerCallback(RLPy.REventListenerCallback):
    def __init__(self):
        RLPy.REventListenerCallback.__init__(self)

    def OnObjectSelectionChanged(self):
        update_hand_rigger_state()

def register_dialog_callback():
    global main_dlg
    global main_dlg_callback
    main_dlg_callback = DialogCallback()
    main_dlg_callback.register_show_callback(on_show)
    main_dlg.RegisterEventCallback(main_dlg_callback)

def register_hand_rigger_callback():
    global hand_rigger_callback
    global hand_rigger_callback_list
    
    hand_rigger_callback = HandRiggerCallback()
    callback_id = RLPy.REventHandler.RegisterEventListenerCallback(hand_rigger_callback)
    hand_rigger_callback_list.append(callback_id)
    
def on_show():
    update_hand_rigger_state()
    
def update_hand_rigger_state():
    global main_dlg_root
    global avatar
    global hand_rigger_state
    global hand_device

    if main_dlg_root != None:
        if avatar:
            hand_device.RemoveAvatar(avatar)
            avatar = None

        selection_list = RLPy.RGlobal.GetSelectedObjects()
        if len(selection_list) > 0:
            for object in selection_list:  # find first avatar
                object_type = object.GetType()
                if object_type == RLPy.EObjectType_Avatar:
                    avatar = object
                    hand_device.AddAvatar(avatar)
                    hand_device.SetProcessDataIndex(avatar, 0)
                    set_hand_rigger_state(HandRiggerState.Ready)
                    return

        set_hand_rigger_state(HandRiggerState.Disable)

def set_hand_rigger_state(state):
    global hand_rigger_state
    global main_dlg_root
    global space_action

    hand_rigger_state = state
    main_dlg_root.setHandRiggerState(state)
    if state == HandRiggerState.Disable:
        space_action.setEnabled(False)
    else:
        space_action.setEnabled(True)