#!/usr/bin/env python3

import sys
import threading
import numpy
import time
import PyQt5
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtCore as QtC
from PyQt5 import QtGui as QtG
import pyqtgraph as pg

from pysinewave import BeatWave, SineWave

from superqt import QRangeSlider, QLabeledRangeSlider, QLabeledSlider

PLAYTIME = 2

class AudioFeedback(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.pixeltone = BeatWave(decibels_per_second=100)
        self.pixeltone.set_beat_frequency(0)
        self.rangetimer = None
        self.rangego = True

        self.valuelabel = QtW.QLabel("Pixel Value")

        self.valuebar = QLabeledRangeSlider(QtC.Qt.Orientation.Vertical)
        self.valuebar.valueChanged.connect(self.valuecallback)
        self.valuebar.setRange(0,2**16)
        self.valuebar.setValue((0, 2**16))
        self.valuebar.setTickPosition(QtW.QSlider.TicksLeft)

        self.pitchlabel = QtW.QLabel("Pitch")
        
        self.pitchbar = QLabeledRangeSlider(QtC.Qt.Orientation.Vertical)
        self.pitchbar.setRange(-10,40)
        self.pitchbar.setValue((-5, 18))
        self.pitchbar.setTickPosition(QtW.QSlider.TicksLeft)

        self.volumelabel = QtW.QLabel("Volume")
        self.volumebar = QLabeledSlider(QtC.Qt.Orientation.Vertical)
        self.volumebar.setRange(0,100)
        self.volumebar.setValue(100)
        self.volumebar.valueChanged.connect(self.setvolume)

        self.playbutton = QtW.QPushButton("Play Tone")
        self.playbutton.setCheckable(True)
        self.playbutton.clicked.connect(self.playcallback)

        self.playrangebutton = QtW.QRadioButton("Range")
        self.playrangebutton.toggled.connect(self.changetone)
        self.playminbutton = QtW.QRadioButton("Min")
        self.playminbutton.toggled.connect(self.changetone)
        self.playmaxbutton = QtW.QRadioButton("Max")
        self.playmaxbutton.toggled.connect(self.changetone)
        self.playpxlmaxbutton = QtW.QRadioButton("Pixel Max")
        self.playpxlmaxbutton.toggled.connect(self.changetone)
        self.playpxlavgbutton = QtW.QRadioButton("Pixel Average")
        self.playpxlavgbutton.toggled.connect(self.changetone)
        self.playpxlmedbutton = QtW.QRadioButton("Pixel Median")
        self.playpxlmedbutton.toggled.connect(self.changetone)

        self.pxlrangemaxlabel = QtW.QLabel("Pixel Max")
        self.pxlrangemax = QtW.QSpinBox()
        self.pxlrangemax.setRange(0,2**16)
        self.pxlrangeminlabel = QtW.QLabel("Pixel Min")
        self.pxlrangemin = QtW.QSpinBox()
        self.pxlrangemin.setRange(0,2**16)
        self.pxlrangebutton = QtW.QPushButton("Set Pixel Range")
        self.pxlrangebutton.clicked.connect(self.updatepxlrange)
        self.resetrangebutton = QtW.QPushButton("Reset")
        self.resetrangebutton.clicked.connect(self.resetpxlrange)

        self.pulsefreqlabel = QtW.QLabel("Pulse Freq")
        self.pulsefreqspin = QtW.QSpinBox()
        self.pulsefreqspin.setRange(0,20)

        self.pulsefreqspin.valueChanged.connect(self.pixeltone.set_beat_frequency)

        self.pulsefreqspin.setValue(0)

        self.playpxlmaxbutton.setChecked(True)

        self.pitchbar.valueChanged.connect(self.pitchcallback)

        self.lay = QtW.QGridLayout()
        self.lay.addWidget(self.valuelabel,0,0,1,1)
        self.lay.addWidget(self.pitchlabel,0,1,1,1)
        self.lay.addWidget(self.valuebar,1,0,20,1)
        self.lay.addWidget(self.pitchbar,1,1,20,1)
        self.lay.addWidget(self.playbutton,1,2,1,2)
        self.lay.addWidget(self.playpxlmaxbutton,2,2,1,2)
        self.lay.addWidget(self.playpxlavgbutton,3,2,1,2)
        self.lay.addWidget(self.playpxlmedbutton,4,2,1,2)
        self.lay.addWidget(self.playrangebutton,5,2,1,2)
        self.lay.addWidget(self.playmaxbutton,6,2,1,2)
        self.lay.addWidget(self.playminbutton,7,2,1,2)

        self.lay.addWidget(self.pxlrangemaxlabel,9,2,1,1)
        self.lay.addWidget(self.pxlrangemax,9,3,1,1)
        self.lay.addWidget(self.pxlrangeminlabel,10,2,1,1)
        self.lay.addWidget(self.pxlrangemin,10,3,1,1)
        self.lay.addWidget(self.pxlrangebutton,11,2,1,1)
        self.lay.addWidget(self.resetrangebutton,11,3,1,1)

        self.lay.addWidget(self.pulsefreqlabel,13,2,1,1)
        self.lay.addWidget(self.pulsefreqspin,13,3,1,1)

        self.lay.addWidget(self.volumebar,15,2,5,1)
        self.lay.addWidget(self.volumelabel,17,3,1,1)

        self.setLayout(self.lay)
        self.resize(400,800)

    def setvolume(self, vol):
        self.pixeltone.set_volume((vol-100)/2)

    def valuecallback(self, value):
        pass

    def is_running(self):
        return self.playbutton.isChecked()

    def pitchcallback(self, value):
        if self.playmaxbutton.isChecked():
            self.pixeltone.set_pitch(value[1])
        elif self.playminbutton.isChecked():
            self.pixeltone.set_pitch(value[0])

    def updatetone(self, maxpxl, avgpxl, medpxl):
        truth = self.playpxlmaxbutton.isChecked(), self.playpxlavgbutton.isChecked(), self.playpxlmedbutton.isChecked()
        if any(truth):
            self.pixeltone.set_pitch_per_second(50)
            if truth[0]:
                value = maxpxl
            elif truth[1]:
                value = avgpxl
            else:
                value = medpxl
            vmin, vmax = self.valuebar.value()
            pmin, pmax = self.pitchbar.value()
            norm = max(0,min(1,(value-vmin)/(vmax-vmin)))
            pitch = round(norm*(pmax-pmin)+pmin,2)
            self.pixeltone.set_pitch(pitch)

    def playcallback(self, value):
        if value:
            self.changetone()
            self.pixeltone.play()
        else:
            self.pixeltone.stop()
    
    def changetone(self):
        self.playrange(self.playrangebutton.isChecked())
        pmin,pmax = self.pitchbar.value()
        if self.playmaxbutton.isChecked():
            self.pixeltone.set_pitch_per_second(50)
            self.pixeltone.set_pitch(pmax)
        elif self.playminbutton.isChecked():
            self.pixeltone.set_pitch_per_second(50)
            self.pixeltone.set_pitch(pmin)

    def _playrange(self):
        pmin,pmax = self.pitchbar.value()
        self.pixeltone.set_pitch_per_second((pmax-pmin)/PLAYTIME)
        self.pixeltone.set_pitch(pmin)
        time.sleep(1)
        while self.rangego:
            self.pixeltone.set_pitch(pmax)
            time.sleep(PLAYTIME+0.2)
            if not self.rangego: return
            pmin,pmax = self.pitchbar.value()
            self.pixeltone.set_pitch_per_second((pmax-pmin)/PLAYTIME)
            self.pixeltone.set_pitch(pmin)
            time.sleep(PLAYTIME+0.2)

    def playrange(self, event):
        self.rangego = event
        if (self.rangetimer is None or not self.rangetimer.is_alive()) and self.rangego:
            self.rangetimer = threading.Thread(target=self._playrange)
            self.rangetimer.start()

    def updatepxlrange(self):
        pmin = self.pxlrangemin.value()
        pmax = self.pxlrangemax.value()
        if pmax >= 80 + pmin:
            self.valuebar.setRange(pmin,pmax)
            self.valuebar.setValue((pmin,pmax))
        else:
            print("Range must be greater than 80")

    def resetpxlrange(self):
        self.valuebar.setRange(0,2**16)
        self.valuebar.setValue((0,2**16))

    def closeEvent(self, a0: QtG.QCloseEvent) -> None:
        self.pixeltone.stop()
        return super().closeEvent(a0)

class ImageSigCapture():
    def __init__(self, im1, im2):
        self.im1 = im1
        self.im2 = im2

    def __getattr__(self, name):
        attr1 = getattr(self.im1, name)
        attr2 = getattr(self.im2, name)
        if isinstance(attr1,(QtC.pyqtSignal,QtC.pyqtBoundSignal)):
            return attr1
        elif callable(attr1):
            def wrap(*args,**kwargs):
                attr2(*args,**kwargs)
                return attr1(*args,**kwargs)
            return wrap
        else:
            return attr1

class ImageDisplay_base(QtW.QWidget):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.mainlayout = QtW.QGridLayout()

        self.image = pg.ImageView()
        self.roi_gview = pg.GraphicsView()
        self.roi_view = pg.ViewBox(lockAspect=True)
        self.roi_gview.setCentralItem(self.roi_view)
        self.sat_image = pg.ImageItem()
        self.roi_image = pg.ImageItem()
        self.roi_sat_image = pg.ImageItem()
        # self.roi = pg.PolygonROI(((0,0),(0,20),(20,20),(20,0)),pen=(0,9))
        self.roi = pg.RectROI((100,100),(100,100),pen=(0,9))
        self.roi.addRotateHandle([1,0], [0.5, 0.5])
        self.image.getView().addItem(self.sat_image)
        self.roi_view.addItem(self.roi_image)
        self.roi_view.addItem(self.roi_sat_image)
        self.image.getView().addItem(self.roi)
        self.roi.hide()
        self.imsigcap = ImageSigCapture(self.image.imageItem,self.roi_image)
        hist = self.image.getHistogramWidget()
        hist.setImageItem(self.imsigcap)
        hist.setHistogramRange(0,1000)
        hist.vb.invertX()
        self.mainlayout.addWidget(self.roi_gview,0,0,1,1)
        self.mainlayout.addWidget(self.image,0,1,1,1)
        self.mainlayout.setColumnStretch(0,2)
        self.mainlayout.setColumnStretch(1,3)

        self.isocurve = pg.IsocurveItem(level=200, pen='g')
        self.isocurve.setParentItem(self.image.getImageItem())
        self.isocurve.setZValue(100)

        self.isotext = pg.TextItem("ISO")
        self.isoLine = pg.InfiniteLine(angle=0, movable=True, pen='g')
        hist.vb.addItem(self.isoLine)
        hist.vb.addItem(self.isotext)
        self.isotext.setPos(0,65000)
        self.isoLine.setValue(65000)
        self.isoLine.setZValue(1000) # bring iso line above contrast controls

        self.sattext = pg.TextItem("SAT")
        self.satLine = pg.InfiniteLine(angle=0, movable=True, pen='orange')
        hist.vb.addItem(self.satLine)
        hist.vb.addItem(self.sattext)
        self.sattext.setPos(0,65217)
        self.satLine.setValue(65217)
        self.satLine.setZValue(1000) # bring iso line above contrast controls

        self.updatebutton = QtW.QPushButton("Update Image Limits")
        self.resetviewbutton = QtW.QPushButton("Reset View")

        self.roibutton = QtW.QPushButton("Update ROI")
        self.roibutton.setCheckable(True)

        self.showisobutton = QtW.QPushButton("Isocurve")
        self.showisobutton.setCheckable(True)

        self.isospin = QtW.QSpinBox()
        self.isospin.setRange(0,65536)
        self.isospin.setSingleStep(10)
        self.resetisospin = QtW.QPushButton("Reset")

        self.satspin = QtW.QSpinBox()
        self.satspin.setRange(0,65536)
        self.satspin.setSingleStep(10)
        self.resetsatspin = QtW.QPushButton("Reset")

        self.showsatbutton = QtW.QPushButton("Saturation")
        self.showsatbutton.setCheckable(True)

        self.audiofeedback_button = QtW.QPushButton("Audio Feedback")

        self.buttonlayout = QtW.QGridLayout()
        self.buttonlayout.addWidget(self.updatebutton,0,0,1,2)
        self.buttonlayout.addWidget(self.resetviewbutton,0,2,1,2)
        self.buttonlayout.addWidget(self.showisobutton,0,4,1,2)
        self.buttonlayout.addWidget(self.showsatbutton,0,6,1,2)
        self.buttonlayout.addWidget(self.audiofeedback_button,0,8,1,2)

        self.buttonlayout.addWidget(self.roibutton,1,0,1,2)
        self.buttonlayout.addWidget(self.isospin,1,4,1,1)
        self.buttonlayout.addWidget(self.satspin,1,6,1,1)

        self.buttonlayout.addWidget(self.resetisospin,1,5,1,1)
        self.buttonlayout.addWidget(self.resetsatspin,1,7,1,1)

        self.mainlayout.addLayout(self.buttonlayout,1,0,1,2)
        self.setLayout(self.mainlayout)

class ImageDisplay(ImageDisplay_base):
    updateSig = QtC.pyqtSignal()
    updateIsoSat = QtC.pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent=parent)

        self.im_size = 100,100

        self.isoLine.sigDragged.connect(self.updateIsocurve)
        
        self.satLine.sigDragged.connect(self.updateSatcurve)

        
        self.updatebutton.clicked.connect(self.relimitimage)
        self.resetviewbutton.clicked.connect(self.autoRange)

        self.roibutton.clicked.connect(self.roibutton_callback)

        self.showisobutton.toggled.connect(self.toggleisocurve)
        self.toggleisocurve(False)

        self.isospin.editingFinished.connect(self.isospinupdate)
        self.resetisospin.clicked.connect(self.resetisospincallback)

        self.satspin.editingFinished.connect(self.satspinupdate)
        self.resetsatspin.clicked.connect(self.resetsatspincallback)

        self.showsatbutton.toggled.connect(self.togglesat)
        self.togglesat(False)

        
        self.audiowidget = AudioFeedback()
        self.audiofeedback_button.clicked.connect(self.audiowidget.show)

        self.resetisospincallback()
        self.resetsatspincallback()

        self.image.roi.setSize(200)

        self.sat_data = None
        self.iso_data = None
        self.roi_data = None
        self.im_data = None
        self.data = None

        self.updateSig.connect(self.update_image)

        self.update_lock = threading.Lock()
        self.wait_event = threading.Event()
        self.worker_go = False
        self.worker_thread = None
        
        self.relimit = True

        self.update_once(numpy.zeros((2,2)))

    def start_worker_thread(self):
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._process_thread)
            self.worker_go = True
            self.worker_thread.start()

    def stop_worker_thread(self):
        if self.worker_thread:
            self.worker_go = False
            self.wait_event.set()
            self.worker_thread.join()
            self.worker_thread = None

    def toggleisocurve(self, event):
        if event:
            self.isoLine.setPen("g")
            self.update_overlay()
        else:
            self.isoLine.setPen("orange")
            self.isocurve.setData(None)

    def togglesat(self, event):
        if event:
            self.satLine.setPen("g")
            self.update_overlay()
        else:
            self.satLine.setPen("orange")
            self.sat_image.setImage(numpy.zeros((2,2,4)))

    def satspinupdate(self):
        value = self.satspin.value()
        self.satLine.setValue(value)
        self.updateSatcurve()

    def isospinupdate(self):
        value = self.isospin.value()
        self.isoLine.setValue(value)
        self.updateIsocurve()

    def resetisospincallback(self):
        self.isospin.setValue(65000)
        self.isospin.editingFinished.emit()

    def resetsatspincallback(self):
        self.satspin.setValue(65217)
        self.satspin.editingFinished.emit()

    def updateIsocurve(self):
        val = self.isoLine.value()
        self.isotext.setPos(0,val)
        self.isocurve.setLevel(val)
        self.isospin.setValue(int(val))
        self.updateIsoSat.emit()

    def updateSatcurve(self):
        val = self.satLine.value()
        self.sattext.setPos(0,val)
        self.satspin.setValue(int(val))
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
        self.relimit = True

    def autoRange(self):
        if self.image.image is not None:
            self.image.autoRange()

    def update_trigger(self, data):
        if not self.wait_event.is_set():
            self.data = data
            self.wait_event.set()

    def update_once(self, data):
        self.data = data
        self.process_data()

    def _process_thread(self):
        while self.worker_go:
            self.wait_event.clear()
            self.wait_event.wait()
            if not self.worker_go:
                return
            self.process_data()

    def process_data(self):
        data = self.data
        if len(self.data.shape)==3:
            data = data[0]
        self.im_data = self.data
        if self.roibutton.isChecked():
            self.roi_data = numpy.fliplr(self.roi.getArrayRegion(data, self.image.imageItem))
            data = self.roi_data
        if self.audiowidget.is_running():
            self.audiowidget.updatetone(numpy.amax(data),numpy.mean(data),numpy.median(data))
        if self.showisobutton.isChecked():
            self.iso_data = pg.gaussianFilter(data, (2, 2))
        if self.showsatbutton.isChecked():
            if self.sat_data is None or self.sat_data.shape[:2]!=data.shape:
                self.sat_data = numpy.zeros((*data.shape,4),dtype=numpy.uint8)
            self.sat_data.fill(0)
            self.sat_data[numpy.where(data>=self.satLine.value())] = (1,0,0,1)

    def update_image(self):
        self.image.setImage(self.im_data, autoHistogramRange=False, autoRange=False, autoLevels=False)
        if self.roibutton.isChecked():
            self.roi_image.setImage(self.roi_data, autoLevels=False)
        if self.relimit:
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
            self.relimit = False
        if self.showisobutton.isChecked():
            self.isocurve.setData(self.iso_data)
        if self.showsatbutton.isChecked():
            self.sat_image.setImage(self.sat_data)

    def old_update(self, data):
        self.data = data
        self.process_data()
        self.update_image()

    def update_overlay(self):
        im = self.image.getProcessedImage()
        if len(im.shape)==3:
            index = self.image.currentIndex
            im = im[index]
        if self.roibutton.isChecked():
            im = self.roi_data = numpy.fliplr(self.roi.getArrayRegion(im, self.image.imageItem))
        if self.audiowidget.is_running():
            self.audiowidget.updatetone(numpy.amax(im),numpy.mean(im),numpy.median(im))
        self.update_isocurve(im)
        self.update_satimage(im)
        self.update_roi(im)

    def update_roi(self, data):
        if self.roibutton.isChecked():
            self.roi_image.setImage(data, autoLevels=False)

    def update_isocurve(self, data):
        if self.showisobutton.isChecked():
            self.iso_data = pg.gaussianFilter(data, (2, 2))
            self.isocurve.setData(self.iso_data)
            # self.isocurve.setData(self.data)

    def update_satimage(self, data):
        if self.showsatbutton.isChecked():
            if self.sat_data is None or self.sat_data.shape[:2]!=data.shape:
                self.sat_data = numpy.zeros((*data.shape,4),dtype=numpy.uint8)
            self.sat_data.fill(0)
            self.sat_data[numpy.where(data>self.satLine.value())] = (1,0,0,1)
            self.sat_image.setImage(self.sat_data)

    def setUpdateOnChange(self):
        self.updateIsoSat.connect(self.update_overlay)
        self.image.sigTimeChanged.connect(self.update_overlay)
        self.roi.sigRegionChanged.connect(self.update_overlay)

    def roibutton_callback(self, event):
        if event:
            self.roi.show()
            self.image.getView().removeItem(self.sat_image)
            self.roi_view.addItem(self.sat_image)
            self.isocurve.setParentItem(self.roi_image)
        else:
            self.roi.hide()
            self.roi_view.removeItem(self.sat_image)
            self.image.getView().addItem(self.sat_image)
            self.isocurve.setParentItem(self.image.getImageItem())
        self.update_overlay()

    def closeEvent(self, a0: QtG.QCloseEvent) -> None:
        print("Closing ImageDisplay")
        self.stop_worker_thread()
        print("Worker thread ended")
        self.audiowidget.close()
        return super().closeEvent(a0)

class ImageUpdater(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.imageview = ImageDisplay()
        self.setLayout(QtW.QGridLayout())
        self.layout().addWidget(self.imageview)

        self.resize(1200, 600)

        self.fps_cb = None
        self.lastupdate = time.time()

        self.firstgo = True

        self.indata = None
        self.data = None

        self.timer = QtC.QTimer()
        self.timer.timeout.connect(self.update)

        self.installEventFilter(self)

        # self.imageview.start_worker_thread()

    def set_fps_cb(self,func):
        if callable(func):
            self.fps_cb = func

    def update_trigger(self, data:numpy.ndarray):
        self.indata = data

    def update(self):
        if self.indata is not None:
            self.data = self.indata
            self.indata = None
            # self.imageview.update_trigger(self.data)
            # self.imageview.update_image()
            self.imageview.old_update(self.data)
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

    def closeEvent(self, a0: QtG.QCloseEvent) -> None:
        self.imageview.close()
        return super().closeEvent(a0)

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

    from pydcam.utils.zmq_pubsub import zmq_reader
    from pydcam.utils.shmem import shmem_reader, shmem_reader_async

    # this_zmq = zmq_reader(ratelimit=0.05)
    this_zmq = shmem_reader_async(ratelimit=0.05)

    app = QtW.QApplication(sys.argv)
    
    this = ImageUpdater()
    this.show()

    this_zmq.register(this.update_trigger)

    with this_zmq:
        sys.exit(app.exec())




###### NOTES #######


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