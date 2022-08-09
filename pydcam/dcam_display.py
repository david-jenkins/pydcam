#!/usr/bin/env python3

import sys
import zmq
import numpy
import time
from pydcam.dcam_reader import unpack_numpy, strip_timestamp
import PyQt5
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
import pyqtgraph as pg
import threading

from collections import deque

# class viewer(pg.Qt.QtGui.QtWidget):
#     def __init__(self):
#         super().__init__(self)
#         # rpyc to the camera reader
#         # buttons to control stuff
#         # boxes to input parameters
#         # connect boxes to rpyc to change reader setup
#         # button to open window to take data...
#         # use timestamp from zmq to show camera framerate
#         # calculate display fr
#         # put normal colourbar to show limits and saturation


# class saver(pg.Qt.QtGui.QtWidget):
#     def __init__(self):
#         super().__init__(self)
#         # open another zmq subscriber
#         # have buttons and boxes to configure data acquisition
#         # e.g. take n frames every m second for N total time
#         # save as they arrive? append to file? hdf5? fits?
        

class zmq_reader(threading.Thread):
    def __init__(self, ip="127.0.0.1", port=5556, topic='orca'):
        super().__init__()

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)

        self.topicfilter = topic.encode()
        self.socket.setsockopt(zmq.SUBSCRIBE, self.topicfilter)
        self.socket.setsockopt(zmq.CONFLATE, 1)
        self.socket.connect(f"tcp://{ip}:{port}")
        self.socket.RCVTIMEO = 10000

        self.callbacks = deque()
        self.ratelimit = 0

        self.go = 1
        self.this_time = 0

    def register(self, func, value=True):
        if value:
            if callable(func):
                if func not in self.callbacks:
                    self.callbacks.append(func)
        else:
            if func in self.callbacks:
                self.callbacks.remove(func)
    
    # def init(self):
    #     while 1:
    #         try:
    #             message = self.socket.recv()
    #             break
    #         except zmq.error.Again as e:
    #             print(e)
    #             print("timeout")
    #         except KeyboardInterrupt as e:
    #             print("Killed by ctrl-c")
    #             sys.exit(0)

    #     buffer = message[len(self.topicfilter):]
    #     buffer, this_time = strip_timestamp(buffer)
    #     self.data = numpy.squeeze(unpack_numpy(buffer))

    #     self.call_callbacks()
    #     self.go = 1
    #     self.this_time = 0

    def call_callbacks(self):
        for func in list(self.callbacks):
            func(self.data)
    
    def stop(self):
        self.go = 0
        
    def run(self):
        timeouts = 0
        self.now = 0
        while self.go:
            try:
                message = self.socket.recv()
            except KeyboardInterrupt as e:
                print("quit with ctrl-c")
            except zmq.error.Again as e:
                print("timeout")
                timeouts+=1
                if timeouts > 10:
                    return
                continue
            buffer = message[len(self.topicfilter):]
            buffer, this_time = strip_timestamp(buffer)
            self.this_time = this_time
            self.data = unpack_numpy(buffer)
            if self.ratelimit:
                if time.time()-self.now > self.ratelimit:
                    self.now = time.time()
                else:
                    continue
            self.call_callbacks()

    def oneshot(self):
        ready = threading.Event()
        def func(data):
            self.oneshot_data = data
            ready.set()
        self.oneshot_callback(func)
        ready.wait()
        return self.oneshot_data

    def oneshot_callback(self,func):
        def wrapper(data):
            self.register(wrapper,False)
            func(data)
        self.register(wrapper,True)

    def multishot(self,n):
        ready = threading.Event()
        self.multishot_return = []
        def func(data,done):
            self.multishot_return.append(data)
            if done:
                ready.set()
        self.multishot_callback(func,n)
        ready.wait()
        return numpy.array(self.multishot_return)

    def multishot_callback(self,func,n):
        cnt = [0]
        def wrapper(data):
            test = cnt[0] >= n - 1
            func(data,test)
            if test:
                self.register(wrapper,False)
            cnt[0]+=1
        self.register(wrapper,True)

class ImageDisplay(QtW.QWidget):
    updateDisplay = QtC.pyqtSignal()
    updateIsoSat = QtC.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.mainlayout = QtW.QVBoxLayout()

        self.image = pg.ImageView()
        self.sat_image = pg.ImageItem()
        self.image.getView().addItem(self.sat_image)
        hist = self.image.getHistogramWidget()
        hist.setHistogramRange(0,1000)
        hist.vb.invertX()
        self.mainlayout.addWidget(self.image)

        self.isocurve = pg.IsocurveItem(level=200, pen='g')
        self.isocurve.setParentItem(self.image.getImageItem())
        self.isocurve.setZValue(100)

        self.isotext = pg.TextItem("ISO")
        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        hist.vb.addItem(self.isoLine)
        hist.vb.addItem(self.isotext)
        self.isotext.setPos(0,200)
        self.isoLine.setValue(200)
        self.isoLine.setZValue(1000) # bring iso line above contrast controls
        self.isoLine.sigDragged.connect(self.updateIsocurve)


        self.sattext = pg.TextItem("SAT")
        self.satLine = pg.InfiniteLine(angle=0, movable=True, pen='orange')
        hist.vb.addItem(self.satLine)
        hist.vb.addItem(self.sattext)
        self.sattext.setPos(0,180)
        self.satLine.setValue(180)
        self.satLine.setZValue(1000) # bring iso line above contrast controls
        self.satLine.sigDragged.connect(self.updateSatcurve)

        ###### A different plot, needs work
        # self.glay = pg.GraphicsLayoutWidget()
        # self.plot = self.glay.addPlot()

        # self.image = pg.ImageItem()

        # self.plot.addItem(self.image)
        # self.mainlayout.addWidget(self.glay)

        # roi = pg.ROI([-8, 14], [6, 5])
        # roi.addScaleHandle([0.5, 1], [0.5, 0.5])
        # roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        # self.plot.addItem(roi)
        # roi.setZValue(10)

        # iso = pg.IsocurveItem(level=0.8, pen='g')
        # iso.setParentItem(self.image)
        # iso.setZValue(5)

        # hist = pg.HistogramLUTItem()
        # hist.setImageItem(self.image)
        # self.glay.addItem(hist)

        # isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        # hist.vb.addItem(isoLine)
        # hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        # isoLine.setValue(0.8)
        # isoLine.setZValue(1000) # bring iso line above contrast controls

        # self.glay.nextRow()
        # p2 = self.glay.addPlot(colspan=2)
        # p2.setMaximumHeight(250)
        
        ###### end different plot

        self.updatebutton = QtW.QPushButton("Update Image Limits")
        self.updatebutton.clicked.connect(self.relimitimage)
        self.resetviewbutton = QtW.QPushButton("Reset View")
        self.resetviewbutton.clicked.connect(self.autoRange)

        self.showisobutton = QtW.QPushButton("Isocurve")
        self.showisobutton.setCheckable(True)
        self.showisobutton.toggled.connect(self.toggleisocurve)
        self.toggleisocurve(False)

        self.showsatbutton = QtW.QPushButton("Saturation")
        self.showsatbutton.setCheckable(True)
        self.showsatbutton.toggled.connect(self.togglesat)
        self.togglesat(False)

        self.buttonlayout = QtW.QHBoxLayout()
        self.buttonlayout.addWidget(self.updatebutton)
        self.buttonlayout.addWidget(self.resetviewbutton)
        self.buttonlayout.addWidget(self.showisobutton)
        self.buttonlayout.addWidget(self.showsatbutton)

        self.mainlayout.addLayout(self.buttonlayout)

        self.setLayout(self.mainlayout)

        self.image.roi.setSize(200)

        self.sat_data = None
        self.data = None

        self.update(numpy.zeros((2,2)))

    def toggleisocurve(self, event):
        if event:
            self.isoLine.setPen("g")
            self.updateOverlay()
        else:
            self.isoLine.setPen("orange")
            self.isocurve.setData(None)

    def togglesat(self, event):
        if event:
            self.satLine.setPen("g")
            self.updateOverlay()
        else:
            self.satLine.setPen("orange")
            self.sat_image.setImage(numpy.zeros((2,2,4)))

    def updateIsocurve(self):
        self.isotext.setPos(0,self.isoLine.value())
        self.isocurve.setLevel(self.isoLine.value())
        self.updateIsoSat.emit()

    def updateSatcurve(self):
        self.sattext.setPos(0,self.satLine.value())
        self.updateIsoSat.emit()

    def get_roi_info(self):
        size = self.image.roi.size()
        pos = self.image.roi.pos()
        visible = self.image.ui.roiBtn.isChecked()
        return (size, pos, visible)

    def set_roi_info(self,roi_info):
        self.image.roi.setSize(roi_info[0])
        self.image.roi.setPos(roi_info[1])
        self.image.ui.roiBtn.setChecked(roi_info[2])

    def relimitimage(self):
        if self.data is not None:
            im = self.image.getProcessedImage()
            if len(im.shape)==3:
                index = self.image.currentIndex
                im = im[index]
            amin = numpy.amin(im)
            amax = numpy.amax(im)
            print(f"min:{amin}, max:{amax}")
            self.image.setLevels(amin,amax)
            self.image.getHistogramWidget().setLevels(amin,amax)
            self.image.getHistogramWidget().setHistogramRange(amin,amax)

    def autoRange(self):
        if self.image.image is not None:
            self.image.autoRange()

    def update(self, data):
        self.data = data
        self.image.setImage(data, autoHistogramRange=False, autoRange=False, autoLevels=False)
        self.updateOverlay()

    def updateOverlay(self):
        im = self.image.getProcessedImage()
        if len(im.shape)==3:
            index = self.image.currentIndex
            im = im[index]
        self.update_isocurve(im)
        self.update_satimage(im)

    def update_isocurve(self, data):
        if self.showisobutton.isChecked():
            self.isocurve.setData(pg.gaussianFilter(data, (2, 2)))
            # self.isocurve.setData(self.data)

    def update_satimage(self, data):
        if self.showsatbutton.isChecked():
            if self.sat_data is None or self.sat_data.shape[:2]!=data.shape:
                self.sat_data = numpy.zeros((*data.shape,4),dtype=numpy.uint8)
            self.sat_data.fill(0)
            self.sat_data[numpy.where(data>self.satLine.value())] = (1,0,0,1)
            self.sat_image.setImage(self.sat_data)

    def setUpdateOnChange(self):
        self.updateIsoSat.connect(self.updateOverlay)
        self.image.sigTimeChanged.connect(self.updateOverlay)

class ImageUpdater(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.imageview = ImageDisplay()
        self.setLayout(QtW.QGridLayout())
        self.layout().addWidget(self.imageview)

        self.resize(800, 600)

        self.fps_cb = None
        self.lastupdate = time.time()

        self.firstgo = True

        self.indata = None
        self.data = None

        self.timer = QtC.QTimer()
        self.timer.timeout.connect(self.update)

        self.installEventFilter(self)

    def set_fps_cb(self,func):
        if callable(func):
            self.fps_cb = func

    def update_trigger(self, data:numpy.ndarray):
        self.indata = data

    def update(self):
        if self.indata is not None:
            self.data = self.indata
            self.indata = None
            self.imageview.update(self.data)
            now = time.time()
            self.fps = 1/(now-self.lastupdate)
            if self.fps_cb is not None:
                self.fps_cb(self.fps)
            self.lastupdate = now
            if self.firstgo:
                self.imageview.relimitimage()
                self.firstgo = False
        QtW.QApplication.processEvents()

    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtC.QEvent.Close:
            print("Stopping viewer")
            self.timer.stop()
        if obj is self and event.type() == QtC.QEvent.Show:
            print("Starting viewer")
            self.timer.start(20)
        return super().eventFilter(obj, event)

    def get_roi_info(self):
        return self.imageview.get_roi_info()

    def set_roi_info(self,roi_info):
        self.imageview.set_roi_info(roi_info)

class CamDisplay(QtW.QWidget):
    plotsignal = QtC.pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.resize(800, 600)

        self.mainlayout = QtW.QVBoxLayout()

        self.image = pg.ImageView()
        self.sat_image = pg.ImageItem()
        self.image.getView().addItem(self.sat_image)
        # self.rmview.setCentralItem(self.image)
        hist = self.image.getHistogramWidget()
        hist.setHistogramRange(0,1000)
        self.mainlayout.addWidget(self.image)


        self.isocurve = pg.IsocurveItem(level=200, pen='g')
        self.isocurve.setParentItem(self.image.getImageItem())
        self.isocurve.setZValue(100)

        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        hist.vb.addItem(self.isoLine)
        # hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        self.isoLine.setValue(200)
        self.isoLine.setZValue(1000) # bring iso line above contrast controls
        self.isoLine.sigDragged.connect(self.updateIsocurve)

        ###### A different plot, needs work
        # self.glay = pg.GraphicsLayoutWidget()
        # self.plot = self.glay.addPlot()

        # self.image = pg.ImageItem()

        # self.plot.addItem(self.image)
        # self.mainlayout.addWidget(self.glay)

        # roi = pg.ROI([-8, 14], [6, 5])
        # roi.addScaleHandle([0.5, 1], [0.5, 0.5])
        # roi.addScaleHandle([0, 0.5], [0.5, 0.5])
        # self.plot.addItem(roi)
        # roi.setZValue(10)

        # iso = pg.IsocurveItem(level=0.8, pen='g')
        # iso.setParentItem(self.image)
        # iso.setZValue(5)

        # hist = pg.HistogramLUTItem()
        # hist.setImageItem(self.image)
        # self.glay.addItem(hist)

        # isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        # hist.vb.addItem(isoLine)
        # hist.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        # isoLine.setValue(0.8)
        # isoLine.setZValue(1000) # bring iso line above contrast controls

        # self.glay.nextRow()
        # p2 = self.glay.addPlot(colspan=2)
        # p2.setMaximumHeight(250)
        
        ###### end different plot
    
        self.updatebutton = QtW.QPushButton("Update Image Limits")
        self.updatebutton.clicked.connect(self.relimitimage)
        self.resetviewbutton = QtW.QPushButton("Reset View")
        self.resetviewbutton.clicked.connect(self.autoRange)

        self.showisobutton = QtW.QPushButton("Isocurve")
        self.showisobutton.setCheckable(True)
        self.showisobutton.toggled.connect(self.toggleisocurve)

        self.showsatbutton = QtW.QPushButton("Saturation")
        self.showsatbutton.setCheckable(True)
        self.showsatbutton.setChecked(True)
        self.showsatbutton.toggled.connect(self.toggleisocurve)
        self.showsatbutton.toggle()

        self.buttonlayout = QtW.QHBoxLayout()
        self.buttonlayout.addWidget(self.updatebutton)
        self.buttonlayout.addWidget(self.resetviewbutton)
        self.buttonlayout.addWidget(self.showisobutton)
        self.buttonlayout.addWidget(self.showsatbutton)

        self.mainlayout.addLayout(self.buttonlayout)

        self.setLayout(self.mainlayout)

        self.plotsignal.connect(self.update)
        self.lastplot = time.time()
        self.plotrate = 20

        self.data = None
        self.indata = None

        self.lastupdate = time.time()
        self.fps_cb = None

        

        self.firstgo = True
        self.sat_data = None
        self.timer = QtC.QTimer()
        self.timer.timeout.connect(self.plotsignal.emit)
        self.timer.start(100)
        self.installEventFilter(self)

    def toggleisocurve(self, event):
        if self.showisobutton.isChecked() or self.showsatbutton.isChecked():
            self.isoLine.setPen("g")
        else:
            self.isoLine.setPen("orange")
        if not self.showisobutton.isChecked():
            self.isocurve.setData(None)
        if not self.showsatbutton.isChecked():
            self.sat_image.setImage(numpy.zeros((2,2)))

    def updateIsocurve(self):
        self.isocurve.setLevel(self.isoLine.value())

    def get_roi_info(self):
        size = self.roi.size()
        pos = self.roi.pos()
        visible = self.image.ui.roiBtn.isChecked()
        return (size, pos, visible)

    def set_roi_info(self,roi_info):
        self.roi.setSize(roi_info[0])
        self.roi.setPos(roi_info[1])
        self.image.ui.roiBtn.setChecked(roi_info[2])

    def update_trigger(self, data:numpy.ndarray):
        self.indata = data.copy()

    def set_fps_cb(self,func):
        if callable(func):
            self.fps_cb = func

    def update(self):
        if self.indata is not None:
            self.data = self.indata
            self.indata = None
            self.image.setImage(self.data,autoHistogramRange=False,autoRange=False,autoLevels=False)
            if self.showisobutton.isChecked():
                self.isocurve.setData(pg.gaussianFilter(self.data, (1, 1)))
                # self.isocurve.setData(self.data)
            if self.showsatbutton.isChecked():
                if self.sat_data is None or self.sat_data.shape[:2]!=self.data.shape:
                    self.sat_data = numpy.zeros((*self.data.shape,4),dtype=numpy.uint8)
                self.sat_data.fill(0)
                self.sat_data[numpy.where(self.data>self.isocurve.level)] = (1,0,0,1)
                self.sat_image.setImage(self.sat_data)
            now = time.time()
            self.fps = 1/(now-self.lastupdate)
            if self.fps_cb is not None:
                self.fps_cb(self.fps)
            self.lastupdate = now
            if self.firstgo:
                self.relimitimage()
                self.firstgo = False
        QtW.QApplication.processEvents()



if __name__ == "__main__":

    this_zmq = zmq_reader()
    this_zmq.ratelimit = 0.01

    app = QtW.QApplication(sys.argv)
    
    this = ImageUpdater()
    this.show()

    this_zmq.register(this.update_trigger)

    this_zmq.start()
    try:
        app.exec_()
    except KeyboardInterrupt as e:
        print("Cancelled")
    this_zmq.stop()
