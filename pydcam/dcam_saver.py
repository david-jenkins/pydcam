#!/usr/bin/env python3

import os
import sys
import numpy
import time
import h5py
import datetime
from datetime import timezone
from collections import deque
from astropy.io import fits

from PyQt5 import QtCore as QtC, QtGui
from PyQt5 import QtGui as QtG
from PyQt5 import QtWidgets as QtW
from pydcam.utils import LoopRunner, get_datetime_stamp, list_to_numpy
import pyqtgraph as pg

from functools import partial

from pathlib import Path

from pydcam.dcam_display import ImageDisplay, ImageViewer 
from pydcam.utils.zmq_pubsub import zmq_reader
from pydcam.utils.runnable import MyRunnable, run_in_background

# get_now = partial(datetime.datetime.now, timezone.utc)

def my_wait(secs,start_time=None):
    if start_time is None:
        start_time = time.time()
    waittime = secs-(time.time()-start_time)
    if waittime > 0:
        time.sleep(waittime)

class CamSaver(QtW.QWidget):
    def __init__(self, get_one_func, get_multi_func=None, get_exp_func=None):
        super().__init__()
        self.get_one_callback = get_one_func
        self.get_multiple_callback = get_multi_func
        self.get_exp_func = get_exp_func

        self.mainlayout = QtW.QVBoxLayout()
        self.setLayout(self.mainlayout)

        self.savebutton = QtW.QPushButton("Save Images")
        self.savebutton.clicked.connect(self.savebutton_callback)

        self.savefitslabel = QtW.QLabel("FITS:")
        self.savefitscheck = QtW.QCheckBox()
        self.savehdf5label = QtW.QLabel("HDF5:")
        self.savehdf5check = QtW.QCheckBox()

        self.savechecklayout = QtW.QHBoxLayout()
        self.savechecklayout.addWidget(self.savefitslabel)
        self.savechecklayout.addWidget(self.savefitscheck)
        self.savechecklayout.addWidget(self.savehdf5label)
        self.savechecklayout.addWidget(self.savehdf5check)
        self.savechecklayout.setContentsMargins(0,0,0,0)
        self.savebuttonlayout = QtW.QVBoxLayout()
        self.savebuttonlayout.addLayout(self.savechecklayout)
        self.savebuttonlayout.addWidget(self.savebutton)
        self.savebuttonlayout.setContentsMargins(0,0,0,0)

        self.filenameentry = QtW.QLineEdit()
        self.filenameentry.setPlaceholderText("Enter Filename")
        self.filenameentry.textChanged.connect(self.update_filenamepreview)

        self.filedialogbutton = QtW.QPushButton("Choose Directory")
        self.filedialogbutton.clicked.connect(self.filedialogbutton_callback)

        self.numberofimageslabel = QtW.QLabel("Number of Images:")
        self.numberofimages = QtW.QSpinBox()
        self.numberofimages.setValue(1)
        self.numberofimages.setRange(0,1000)
        self.continouslabel = QtW.QLabel("Save Continuously:")
        self.continouscheck = QtW.QCheckBox()

        self.timesteplabel = QtW.QLabel("Time Interval (s):")
        self.timestep = QtW.QDoubleSpinBox()
        self.timestep.setValue(1.0)
        self.filenamepreview = QtW.QLabel("Filename Preview:\n")

        self.continouscheck.toggled.connect(self.toggletimestep)
        self.continouscheck.toggle()

        self.exptimelabel = QtW.QLabel("Exposure Time for hdf5 files:")
        self.exptime = QtW.QDoubleSpinBox()
        self.exptime.setDecimals(10)
        self.exptime.setValue(0.5)
        self.getexptimebutton = QtW.QPushButton("Get Exposure Time")
        self.getexptimebutton.setCheckable(True)
        self.getexptimebutton.setChecked(True)
        # self.getexptimebutton.clicked.connect(self.get_exp_time)

        self.statuslabel = QtW.QLabel("Initialising...")


        self.savelayouttop = QtW.QHBoxLayout()
        self.savelayouttop.addLayout(self.savebuttonlayout)
        self.savelayouttop.addWidget(self.filenameentry)
        self.savelayouttop.addWidget(self.filedialogbutton)
        self.savelayoutmiddle = QtW.QHBoxLayout()
        self.savelayoutmiddle.addWidget(self.numberofimageslabel)
        self.savelayoutmiddle.addWidget(self.numberofimages)
        self.savelayoutmiddle.addWidget(self.continouslabel)
        self.savelayoutmiddle.addWidget(self.continouscheck)
        self.savelayoutmiddle.addWidget(self.timesteplabel)
        self.savelayoutmiddle.addWidget(self.timestep)
        self.savelayoutbottom = QtW.QHBoxLayout()
        self.savelayoutbottom.addWidget(self.exptimelabel)
        self.savelayoutbottom.addWidget(self.exptime)
        if self.get_exp_func is not None:
            self.savelayoutbottom.addWidget(self.getexptimebutton)

        self.mainlayout.addLayout(self.savelayouttop)
        self.mainlayout.addLayout(self.savelayoutmiddle)
        self.mainlayout.addLayout(self.savelayoutbottom)
        self.mainlayout.addWidget(self.filenamepreview)
        self.mainlayout.addWidget(self.statuslabel)

        self.opendisplaylayout = QtW.QHBoxLayout()
        self.openlastimagebutton = QtW.QPushButton("Open Previous Images")
        self.openlastimagebutton.clicked.connect(self.opendisplay)
        self.savelastimagebutton = QtW.QPushButton("Save Previous Images")
        self.savelastimagebutton.clicked.connect(self.save_current_images)
        self.openfilebutton = QtW.QPushButton("Open Saved Images")
        self.openfilebutton.clicked.connect(self.openfile)
        self.opendisplaylayout.addWidget(self.openlastimagebutton)
        self.opendisplaylayout.addWidget(self.savelastimagebutton)
        self.opendisplaylayout.addWidget(self.openfilebutton)

        self.mainlayout.addLayout(self.opendisplaylayout)

        self.imdisplay = ImageViewer()

        self.images = None

        self.can_save = lambda: True

        self.dir_path = Path.home()/"Hamamatsu_images"
        self.dir_path.mkdir(exist_ok=True)
        self.update_filenamepreview()
        self.statuslabel.setText("Ready")
        
        self.disp_timer = QtC.QTimer()
        self.disp_timer.timeout.connect(self.update_display)
        self.disp_timer.setInterval(1000)

    def get_exp_time(self):
        exp_time = self.get_exp_func()
        self.exptime.setValue(exp_time)

    def toggletimestep(self,value):
        self.timestep.setEnabled(not value)

    def savebutton_callback(self,event):
        self.statuslabel.setText("Working...")
        self.saveimages()

    def set_can_save(self,func):
        if callable(func):
            self.can_save = func
            
    async def get_images(self):
        N = self.N
        if N == 0:
            return
        elif N == 1:
            print("awaiting self get one")
            self.images = await self.get_one()
        elif self.continouscheck.isChecked():
            print("awaiting self get multiple")
            images = await self.get_multiple(N)
            self.images = list_to_numpy(images)
            print("Got images")
        else:
            s = self.timestep.value()
            images = deque()
            now = time.time()
            for n in range(N):
                my_wait(s,now)
                print("awaiting self get one")
                images.append(await self.get_one())
                now = time.time()
            self.images = list_to_numpy(images)
            print("Got images")

    def saveimages(self):
        print("Saving images")
        if not self.can_save():
            self.statuslabel.setText("Can't save yet...")
            return
        self.now = get_datetime_stamp()
        self.N = self.numberofimages.value()
        # run_in_background(self.get_images, callback=self.done_saveimages)
        fut = LoopRunner.run_coroutine(self.get_images())
        fut.add_done_callback(self.done_saveimages)
        
    def done_saveimages(self, event):
        self.statuslabel.setText(f"Got {self.N} images")
        self.save_current_images(now=self.now)

    def save_current_images(self, event=None, now=None):
        if now is None:
            now = get_datetime_stamp()
        # timestamp = f"{now.year:0>4}-{now.month:0>2}-{now.day:0>2}T{now.hour:0>2}{now.minute:0>2}{now.second:0>2}"
        timestamp = now#.isoformat(timespec='seconds')[:19].replace(":","-")
        if self.getexptimebutton.isChecked():
            self.get_exp_time()
        if self.savefitscheck.isChecked():
            self.save_many_fits(timestamp)
        if self.savehdf5check.isChecked():
            self.save_many_hdf5(timestamp)

    def filedialogbutton_callback(self,event):
        # fname = QtG.QFileDialog.getOpenFileName(self, 'Open file', 'darc_images',"Image files (*.FITS *.hdf5)")
        self.dir_path = QtW.QFileDialog.getExistingDirectory(self, 'Select Dave Directory',str(Path.home()))
        self.update_filenamepreview()

    def update_filenamepreview(self):
        now = get_datetime_stamp()
        text = self.filenamepreview.text().split("\n")[0] + "\n"
        fname = self.filenameentry.text()
        if fname != "":
            fname += "_"
        self.fname = os.path.join(self.dir_path, fname)
        fname = self.fname + now#.isoformat(timespec='seconds')[:19].replace(":","-") #f"{now.year:0>4}-{now.month:0>2}-{now.day:0>2}T{now.hour:0>2}{now.minute:0>2}{now.second:0>2}"
        text += fname
        self.filenamepreview.setText(text)

    def update_display(self):
        self.update_filenamepreview()
        if self.getexptimebutton.isChecked():
            self.get_exp_time()

    async def get_one(self):
        if self.get_one_callback is not None:
            print("awaiting get one cb")
            return await self.get_one_callback()

    async def get_multiple(self,n):
        if self.get_multiple_callback is not None:
            print("awaiting get mult cb")
            return await self.get_multiple_callback(n)
        else:
            data = deque()
            for i in range(n):
                print("awaiting self get one")
                data.append(await self.get_one())
            return data

    def save_many_hdf5(self, timestamp=""):
        if self.images is not None:
            labels = numpy.zeros(len(self.images))
            labels[:] = self.exptime.value()

            fname = self.fname + timestamp
            file = h5py.File(f"{fname}.hdf5", "w")

            # Create a dataset in the file
            dataset = file.create_dataset(
                "images", numpy.shape(self.images), dtype="uint16", data=self.images
            )
            meta_set = file.create_dataset(
                "meta", numpy.shape(labels), dtype="f", data=labels
            )
            file.close()

    def save_many_fits(self,timestamp=""):
        # for i,im in enumerate(images):
        #     hdu = fits.PrimaryHDU(im)
        #     hdu.writeto('{}-{:0>2}.fits'.format(fname,i))
        if self.images is not None:

            fname = self.fname + timestamp
            hdr = fits.Header()
            hdr["ExpTime"] = self.exptime.value()
            hdr["DATE-OBS"] = timestamp
            fits.writeto(f'{fname}.fits', self.images, header=hdr)

            # this old style was used before.....
            # hdul = fits.HDUList()
            # hdul.append(fits.PrimaryHDU())

            # for img in self.images:
            #     hdul.append(fits.ImageHDU(data=numpy.squeeze(img)))

            # hdul.writeto(f'{fname}.fits')

            #this is how to read these old style files....
            # data = []
            # with fits.open(fname) as hdul:
            #     for hd in hdul:
            #         data.append(hd.data)
            # data = data[1:]
            # data = numpy.array(data)

    def opendisplay(self):
        print(self.images.shape)
        print(self.images.dtype)
        if self.images is not None:
            self.imdisplay.update(self.images)
            self.imdisplay.show()

    def openfile(self):
        fname = QtW.QFileDialog.getOpenFileName(self, 'Open file', str(self.dir_path), "Image files (*.FITS *.hdf5)",options=QtW.QFileDialog.DontUseNativeDialog)
        if fname == ('',''):
            return
        fext = fname[0].split(".")[-1]
        if fext in ("FITS","fits"):
            data = fits.getdata(fname[0])
            images = data
        elif fext == "hdf5":
            file = h5py.File(fname[0], "r")
            images = file['images'][:]
            file.close()
        self.imdisplay.update(images)
        self.imdisplay.show()
        
    def showEvent(self, a0) -> None:
        self.disp_timer.start(1000)
        return super().showEvent(a0)
    
    def hideEvent(self, a0) ->None:
        self.disp_timer.stop()
        return super().hideEvent(a0)


def test():
    def get_one():
        image = numpy.arange(200)
        image = numpy.resize(image,(200,200))
        while 1:
            yield image

    g = get_one()
    f = partial(next,g)
    app = QtW.QApplication(sys.argv)
    this = CamSaver(f)

    this.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # test()

    read_zmq = zmq_reader()
    read_zmq.start()

    app = QtW.QApplication(sys.argv)
    this = CamSaver(read_zmq.oneshot,read_zmq.multishot)

    this.show()
    ret = app.exec()
    read_zmq.stop()
    sys.exit(ret)