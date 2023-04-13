#!/usr/bin/env python

#  If you have installed aravis in a non standard location, you may need
#   to make GI_TYPELIB_PATH point to the correct location. For example:
#
#   export GI_TYPELIB_PATH=$GI_TYPELIB_PATH:/opt/bin/lib/girepositry-1.0/
#
#  You may also have to give the path to libaravis.so, using LD_PRELOAD or
#  LD_LIBRARY_PATH.

import sys
import gi
import numpy

from matplotlib import pyplot

gi.require_version ('Aravis', '0.8')

from gi.repository import Aravis

Aravis.enable_interface ("Fake")

try:
    if len(sys.argv) > 1:
        camera = Aravis.Camera.new (sys.argv[1])
    else:
        camera = Aravis.Camera.new (None)
except TypeError:
	print ("No camera found")
	exit ()

# device = camera.get_device ()
camera.set_region (0,664,400,400)
camera.set_integer ("FrameRate", 2)
camera.set_integer ("Exposure", 5000)
camera.set_pixel_format (Aravis.PIXEL_FORMAT_MONO_8)

payload = camera.get_payload ()

[x,y,width,height] = camera.get_region ()

print ("Camera vendor : %s" %(camera.get_vendor_name ()))
print ("Camera model  : %s" %(camera.get_model_name ()))
print ("ROI           : %dx%d at %d,%d" %(width, height, x, y))
print ("Payload       : %d" %(payload))
print ("Pixel format  : %s" %(camera.get_pixel_format_as_string ()))


stream = camera.create_stream (None, None)

print(stream)

for i in range(0,10):
	stream.push_buffer (Aravis.Buffer.new_allocate (payload))

print ("Start acquisition")

camera.start_acquisition ()

print ("Acquisition")

images = []

for i in range(0,5):
	print("got image ", i)
	image = stream.pop_buffer ()
	if image:
		buf = image.get_image_data()
		im = numpy.frombuffer(buf[:width*height],dtype="u1")
		im.shape = width,height
		images.append(im)
		stream.push_buffer (image)

camera.set_integer ("FrameRate", 20)
camera.set_integer ("Exposure", 10000)

for i in range(5,10):
	print("got image ", i)
	image = stream.pop_buffer ()
	if image:
		buf = image.get_image_data()
		im = numpy.frombuffer(buf[:width*height],dtype="u1")
		im.shape = width,height
		images.append(im)
		stream.push_buffer (image)



camera.stop_acquisition()
stream.stop_thread(True) # this deletes the buffers -> stop_thread(self, delete_buffers:bool)

camera.set_region(176, 716, 176, 272)
payload = camera.get_payload()

for i in range(10):
	stream.push_buffer(Aravis.Buffer.new(payload))

camera.set_integer ("FrameRate", 6)

[x,y,width,height] = camera.get_region ()

stream.start_thread()
camera.start_acquisition()

for i in range(0,5):
	image = stream.pop_buffer ()
	if image:
		buf = image.get_image_data()
		im = numpy.frombuffer(buf[:width*height],dtype="u1")
		im.shape = height,width
		images.append(im)
		stream.push_buffer (image)

print ("Stop acquisition")

camera.stop_acquisition ()

indxs = [0,5,10]

for indx in indxs:
	pyplot.figure()
	pyplot.imshow(images[indx])

pyplot.show()
