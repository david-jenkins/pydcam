
import sys
import numpy
import pyqtgraph as pg
import pydcam.dcam_display as display
from PyQt5 import QtCore as QtC
from PyQt5 import QtWidgets as QtW
from PyQt5 import QtGui as QtG

from pydcam.utils.zmq_pubsub import zmq_reader

from lark.utils import var_from_file

control = var_from_file("control", "/home/djenkins/git/canapy-rtc/larkconfig/darc/configNGSLO.py")

subapLocation = control["subapLocation"]
subapFlag = control["subapFlag"]
nsubx = int(control['nsubx'][0])

class SHWFS(display.ImageUpdater):
    def __init__(self, parent=None):
        self.roi_winx = None
        self.roi_winy = None
        super().__init__(parent)
    
    def draw_subaps(self):
        print(subapLocation)
        pen = QtG.QPen(QtC.Qt.red,1)
        self.subapItems = {}
        for i,subap in enumerate(subapLocation):
            if subapFlag[i]:
                rect = QtW.QGraphicsRectItem(subap[0],subap[3],subap[1]-subap[0],subap[4]-subap[3])
                rect.setPen(pen)
                self.imageview.image.getView().addItem(rect)
                self.subapItems[i] = rect
    
    # def plot_cross_sections(self):
    #     self.roi_winx = pg.GraphicsLayoutWidget()
    #     self.roi_winx.setWindowTitle("X")
    #     self.roi_winy = pg.GraphicsLayoutWidget()
    #     self.roi_winy.setWindowTitle("Y")
    #     self.subap_rois = {}
    #     self.subap_plots = {}
    #     self.subap_plot_curves = {}
    #     pen = QtG.QPen(QtC.Qt.yellow,0.05)
    #     for i,subap in enumerate(subapLocation):
    #         if subapFlag[i]:
    #             plotx = self.roi_winx.addPlot(i//nsubx, i%nsubx)
    #             ploty = self.roi_winy.addPlot(i//nsubx, i%nsubx)
    #             print(self.subapItems[i])
    #             roi = pg.ROI([subap[0],subap[3]],[subap[1]-subap[0],subap[4]-subap[3]],pen=pen,movable=False,maxBounds=self.subapItems[i].boundingRect())
    #             roi.addScaleHandle([0.5, 1], [0.5, 0.5])
    #             roi.addScaleHandle([0, 0.5], [0.5, 0.5])
    #             self.imageview.image.getView().addItem(roi)
    #             roi.setZValue(10)

    #             curvex = plotx.plot(numpy.zeros(5))
    #             curvey = ploty.plot(numpy.zeros(5))
    #             self.subap_plot_curves[i] = curvex,curvey
    #             self.subap_rois[i] = roi
    #             self.subap_plots[i] = plotx,ploty
    #     self.roi_winx.show()
    #     self.roi_winy.show()

    def plot_cross_sections(self):
        self.roi_winx = pg.GraphicsLayoutWidget()
        self.roi_winx.setWindowTitle("X")
        self.roi_winy = pg.GraphicsLayoutWidget()
        self.roi_winy.setWindowTitle("Y")
        self.subap_rois = []
        self.subap_plots = []
        pen = (255, 206, 53)
        for i in range(nsubx):
            subap1 = subapLocation[i]
            subap2 = subapLocation[i+nsubx*(nsubx-1)]
            rect = QtC.QRectF(subap1[0],subap1[3],subap2[1]-subap1[0],subap1[4]-subap1[3])
            roi = pg.ROI([subap1[0],subap1[3]],[subap2[1]-subap1[0],subap1[4]-subap1[3]],pen=pen,movable=False,maxBounds=rect)
            roi.setZValue(10)
            roi.addScaleHandle([0.5, 1], [0.5, 0.5])
            # roi.addScaleHandle([0, 0.5], [0.5, 0.5])
            self.imageview.image.getView().addItem(roi)
            plotx = self.roi_winx.addPlot(i, 0)
            curvex = plotx.plot(numpy.zeros(5))
            self.subap_rois.append((roi,curvex,1))
            self.subap_plots.append(plotx)

        for i in range(nsubx):
            subap1 = subapLocation[i*nsubx]
            subap2 = subapLocation[i*nsubx+(nsubx-1)]
            rect = QtC.QRectF(subap1[0],subap1[3],subap1[1]-subap1[0],subap2[4]-subap1[3])
            roi = pg.ROI([subap1[0],subap1[3]],[subap1[1]-subap1[0],subap2[4]-subap1[3]],pen=pen,movable=False,maxBounds=rect)
            roi.setZValue(10)
            # roi.addScaleHandle([0.5, 1], [0.5, 0.5])
            roi.addScaleHandle([0, 0.5], [0.5, 0.5])
            self.imageview.image.getView().addItem(roi)
            ploty = self.roi_winy.addPlot(0, i)
            curvey = ploty.plot(numpy.zeros(5))
            self.subap_rois.append((roi,curvey,0))
            self.subap_plots.append(ploty)
        self.roi_winx.show()
        self.roi_winy.show()
        
    def update(self):
        super().update()
        if self.roi_winx is not None:
            for roi,curve,axis in self.subap_rois:
                selected = roi.getArrayRegion(self.data, self.imageview.image.getImageItem())
                if axis == 0:
                    curve.setData(selected.mean(axis=axis),numpy.arange(selected.shape[1]))
                else:
                    curve.setData(selected.mean(axis=axis))
                # self.subap_plot_curves[i][1].setData(selected.mean(axis=1))
            QtW.QApplication.processEvents()

    def closeEvent(self, a0) -> None:
        self.roi_winx.close()
        self.roi_winy.close()
        return super().closeEvent(a0)


if __name__ == "__main__":

    this_zmq = zmq_reader(ratelimit=0.05)

    app = QtW.QApplication(sys.argv)

    this = SHWFS()
    this.draw_subaps()
    this.plot_cross_sections()
    this.imageview.image.getView().setBackgroundColor(0.3)
    this.setWindowFlags(QtC.Qt.Window)
    this.show()

    this_zmq.register(this.update_trigger)

    with this_zmq:
        sys.exit(app.exec())