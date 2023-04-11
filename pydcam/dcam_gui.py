#!/usr/bin/env python3

import sys
import time
import PyQt5
from PyQt5 import QtCore as QtC 
from PyQt5 import QtGui as QtG
from PyQt5 import QtWidgets as QtW

from pyqtgraph.parametertree import Parameter, ParameterTree, ParameterItem, registerParameterType

# from pydcam.dcam_reader import DCamReader, DCamSim
from pydcam import DCamReader, CamSaver
from pydcam.dcam_display import ImageUpdater
from pydcam import open_config

class ConsoleLog(QtW.QMainWindow):
    writeSig = QtC.pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.text = QtW.QTextEdit()
        self.text.setReadOnly(True)
        self.text.document().setMaximumBlockCount(1000)

        self.setCentralWidget(self.text)

        self.stdout = None
        self.stderr = None

        self.writeSig.connect(self.update)

    def write(self, buf:str):
        self.writeSig.emit(buf)

    def update(self, buf:str):
        self.text.moveCursor(QtG.QTextCursor.End)
        self.text.insertPlainText(buf)
        self.text.moveCursor(QtG.QTextCursor.End)

    def flush(self):
        pass

    def set_as_stdout(self):
        self.stdout = sys.stdout
        sys.stdout = self

    def set_as_stderr(self):
        self.stderr = sys.stderr
        sys.stderr = self

    def closeEvent(self, a0: QtG.QCloseEvent) -> None:
        if self.stderr:
            sys.stderr = self.stderr
        if self.stdout:
            sys.stdout = self.stdout
        return super().closeEvent(a0)

class ControlWindow(QtW.QWidget):
    camfps_signal = QtC.pyqtSignal(float)
    disfps_signal = QtC.pyqtSignal(float)
    def __init__(self, reader:DCamReader, parent = None):
        super().__init__(parent=parent)
        self.setWindowFlags(QtC.Qt.Window)
        self.parameters = [
            {'name':'Camera Information', 'type':'group', 'expanded':False, 'children':[
                {'name':'Camera Model', 'type':'str', 'value':'NA', 'readonly': True},
                {'name':'Serial Number', 'type':'str', 'value':'NA', 'readonly': True},
            ]},
            {'name':'Camera Setup', 'type':'group', 'children':[
                {'name':'Width', 'type':'int', 'value':0, 'limits':[0,2560]},
                {'name':'Height', 'type':'int', 'value':0, 'limits':[0,2560]},
                {'name':'Position', 'type':'group', 'children':[
                    {'name':'Horizontal', 'type':'int', 'value':0, 'limits':[0,2560]},
                    {'name':'Vertical', 'type':'int', 'value':0, 'limits':[0,2560]}
                ]},
                {'name':'Set Dimensions', 'type':'action', 'tip':'Use to set Window Parameters'},
                {'name':'Set Fullframe', 'type':'action', 'tip':'Use to set Window Parameters'},
                {'name':'Exposure Time (s)', 'type':'float', 'value':0, 'limits':[0.0001,10]},
                {'name':'Exposure Time (ms)', 'type':'float', 'value':0, 'limits':[1,10000]}
            ]},
            {'name':'Frame Rates','type':'group','children':[
                {'name':'Camera Frame Rate', 'type':'float', 'value':0, 'readonly':True},
                {'name':'Display Frame Rate', 'type':'float', 'value':0, 'readonly':True}
            ]}
        ]
        self.mainlayout = QtW.QHBoxLayout()
        
        self.paramgroup = Parameter.create(name='params', type='group', children=self.parameters)
        
        self.parameterTree = ParameterTree()
        self.parameterTree.setParameters(self.paramgroup)
        self.mainlayout.addWidget(self.parameterTree)

        self.buttonlayout = QtW.QVBoxLayout()
        self.startcamerabutton = QtW.QPushButton("Start Camera")
        self.startcamerabutton.clicked.connect(self.start_camera)
        self.buttonlayout.addWidget(self.startcamerabutton)
        self.stopcamerabutton = QtW.QPushButton("Stop Camera")
        self.stopcamerabutton.clicked.connect(self.stop_camera)
        self.buttonlayout.addWidget(self.stopcamerabutton)
        self.opendisplaybutton = QtW.QPushButton("Open Display")
        self.opendisplaybutton.clicked.connect(self.show_display)
        self.buttonlayout.addWidget(self.opendisplaybutton)
        self.loadconfigbutton = QtW.QPushButton("Load Config")
        self.loadconfigbutton.clicked.connect(self.load_config)
        self.buttonlayout.addWidget(self.loadconfigbutton)
        self.opensaverbutton = QtW.QPushButton("Open Image Saver")
        self.opensaverbutton.clicked.connect(self.show_saver)
        self.buttonlayout.addWidget(self.opensaverbutton)

        self.mainlayout.addLayout(self.buttonlayout)
        self.setLayout(self.mainlayout)

        self.camdisplays = []
        self.roi_info = None
        self.camdisplay_info = None


        self.camreader = reader
        self.camsaver = CamSaver(self.camreader.get_image,self.camreader.get_images,self.camreader.get_exposure)
        self.camsaver.set_can_save(self.camreader.get_running)

        self.camreader.camera.set_fps_cb(self.camfps_signal.emit)
        self.camfps = 0
        self.camfps_cnt = 0
        self.disfps = 0
        self.disfps_cnt = 0

        self.camfps_signal.connect(self.camerafps_callback)
        self.disfps_signal.connect(self.displayfps_callback)
        self.fps_update_rate = 1
        self.camfps_lastupdate = time.time()
        self.disfps_lastupdate = time.time()

        self.paramgroup.param('Camera Setup').param('Set Dimensions').sigActivated.connect(self.setWindowDimensions)
        self.paramgroup.param('Camera Setup').param('Set Fullframe').sigActivated.connect(self.setFullFrame)
        self.paramgroup.param('Camera Setup').param('Exposure Time (s)').sigValueChanged.connect(self.setExposureTime)
        self.paramgroup.param('Camera Setup').param('Exposure Time (ms)').sigValueChanged.connect(self.setExposureTime)

        self.installEventFilter(self)

        self.closefuncs = []

        # self.timer = QtC.QTimer()
        # self.timer.timeout.connect(QtW.QApplication.processEvents)
        # self.timer.start(100)

    def camerafps_callback(self, fps):
        self.camfps_cnt += 1
        self.camfps = (self.camfps*(self.camfps_cnt-1) + fps)/self.camfps_cnt
        if time.time() - self.camfps_lastupdate > 1/self.fps_update_rate:
            self.camerafps_reset(self.camfps)

    def camerafps_reset(self,fps=0):
        self.camfps_lastupdate = time.time()
        self.paramgroup.param('Frame Rates').param('Camera Frame Rate').setValue(fps)
        self.camfps = 0
        self.camfps_cnt = 0

    def displayfps_callback(self,fps):
        self.disfps_cnt += 1
        self.disfps = (self.disfps*(self.disfps_cnt-1) + fps)/self.disfps_cnt
        if time.time()-self.disfps_lastupdate > 1/self.fps_update_rate:
            self.displayfps_reset(self.disfps)

    def displayfps_reset(self,fps=0):
        self.disfps_lastupdate = time.time()
        self.paramgroup.param('Frame Rates').param('Display Frame Rate').setValue(fps)
        self.disfps = 0
        self.disfps_cnt = 0

    def setWindowDimensions(self):
        print('Setting')
        w = self.paramgroup.param('Camera Setup').param('Width').value()
        h = self.paramgroup.param('Camera Setup').param('Height').value()
        pw = self.paramgroup.param('Camera Setup').param('Position').param('Horizontal').value()
        ph = self.paramgroup.param('Camera Setup').param('Position').param('Vertical').value()
        print(w,h,pw,ph)
        self.camreader.set_subarray(w,h,pw,ph)
        time.sleep(0.5)
        self.set_window_info()

    def setFullFrame(self):
        window_info = self.camreader.get_window_info_dict()
        w = window_info["SUBARRAYHSIZE"][2]
        h = window_info["SUBARRAYVSIZE"][2]
        pw = 0
        ph = 0
        print(f"Setting full frame to {w},{h} at {pw},{ph}")
        self.camreader.set_subarray(w,h,pw,ph)
        time.sleep(0.5)
        self.set_window_info()

    def setExposureTime(self,event):
        if event.name() == "Exposure Time (s)":
            ts = self.paramgroup.param('Camera Setup').param('Exposure Time (s)').value()
            self.paramgroup.param('Camera Setup').param('Exposure Time (ms)').setValue(ts*1000., blockSignal=self.setExposureTime)
        else:
            tms = self.paramgroup.param('Camera Setup').param('Exposure Time (ms)').value()
            self.paramgroup.param('Camera Setup').param('Exposure Time (s)').setValue(tms/1000., blockSignal=self.setExposureTime)

        ts = self.paramgroup.param('Camera Setup').param('Exposure Time (s)').value()
        tms = self.paramgroup.param('Camera Setup').param('Exposure Time (ms)').value()
        print(ts,tms)
        self.camreader.set_exposure(ts)

    def start_camera(self):
        if self.camreader.get_running():
            return
        self.camreader.open_camera()
        camera_params = self.camreader.get_info()
        self.paramgroup.param('Camera Information').param('Camera Model').setValue(camera_params["MODEL"])
        self.paramgroup.param('Camera Information').param('Serial Number').setValue(camera_params["CAMERAID"])
        self.set_window_info()

    def set_window_info(self):
        window_info = self.camreader.get_window_info()
        self.paramgroup.param('Camera Setup').param('Width').setValue(window_info[0][0])
        self.paramgroup.param('Camera Setup').param('Width').setLimits(window_info[0][1:])
        self.paramgroup.param('Camera Setup').param('Position').param('Horizontal').setValue(window_info[1][0])
        self.paramgroup.param('Camera Setup').param('Position').param('Horizontal').setLimits(window_info[1][1:])

        self.paramgroup.param('Camera Setup').param('Height').setValue(window_info[2][0])
        self.paramgroup.param('Camera Setup').param('Height').setLimits(window_info[2][1:])
        self.paramgroup.param('Camera Setup').param('Position').param('Vertical').setValue(window_info[3][0])
        self.paramgroup.param('Camera Setup').param('Position').param('Vertical').setLimits(window_info[3][1:])

        self.paramgroup.param('Camera Setup').param('Exposure Time (ms)').setValue(window_info[4][0]*1000., blockSignal=self.setExposureTime)
        self.paramgroup.param('Camera Setup').param('Exposure Time (s)').setValue(window_info[4][0], blockSignal=self.setExposureTime)

    def stop_camera(self):
        if self.camreader.get_running():
            print("CLICKED Stop Camera")
            self.camreader.close_camera()
            self.camerafps_reset()

    def quit_camera(self):
        self.camreader.quit()

    def show_display(self):
        this_display = ImageUpdater(self)
        self.camdisplays.append(this_display)
        this_display.setWindowFlags(QtC.Qt.Window)
        this_display.installEventFilter(self)
        this_display.set_fps_cb(self.disfps_signal.emit)
        if self.camdisplay_info is not None:
            this_display.set_roi_info(self.camdisplay_info[0])
            this_display.setGeometry(self.camdisplay_info[1])
        this_display.show()
        this_display.fid = self.camreader.register_callback(this_display.update_trigger)

    def show_saver(self):
        self.camsaver.show()
        self.camsaver.setFixedSize(self.camsaver.size())

    def load_config(self):
        cf_dict = open_config()
        if cf_dict is not None:
            wasrunning = self.camreader.get_running()
            if wasrunning:
                self.stop_camera()
            self.camreader.dcam.prop_setfromdict(cf_dict)
            if wasrunning:
                self.start_camera()

    def eventFilter(self, obj, event):
        if event.type() == QtC.QEvent.Close and obj in self.camdisplays:
            print("Closing cam display")
            self.camdisplay_info = obj.get_roi_info(),obj.geometry()
            self.displayfps_reset()
            self.camreader.deregister_callback(obj.fid)
            self.camdisplays.remove(obj)
        if event.type() == QtC.QEvent.Close and obj is self:
            self.camreader.quit()
            for obj in self.camdisplays:
                obj.close()
            self.camsaver.close()
            for func in self.closefuncs:
                func()
        return super().eventFilter(obj, event)

    def register_atclose(self, func):
        self.closefuncs.append(func)

if __name__ == "__main__":

    from pydcam.api import OpenCamera
    from pathlib import Path

    fname = None
    if len(sys.argv) > 1:
        fname = Path(sys.argv[1]).resolve()

    with OpenCamera(0) as dcam:

        dcam.prop_setdefaults()
        if fname is not None:
            init_dict = open_config(fname)
            if init_dict: dcam.prop_setfromdict(init_dict)

        app = QtW.QApplication(sys.argv)
        reader = DCamReader(dcam)
        controlWin = ControlWindow(reader)
        controlWin.show()
        sys.exit(app.exec())
