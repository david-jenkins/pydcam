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


def print_features(gc,name,indent=0):
	node = gc.get_node(name)
	istr = ["\t"]*indent
	print("".join(istr), node)
	print("".join(istr), name)
	if isinstance(node, Aravis.GcCategory):
		features = node.get_features()
		# print("".join(istr), features)
		for f in features:
			print_features(gc,f,indent=indent+1)
	elif isinstance(node, (Aravis.GcStringRegNode,Aravis.GcIntegerNode,Aravis.GcBoolean,Aravis.GcEnumeration)):
		print(node.get_value())

def get_gc_features(genicam, name):
	node = genicam.get_node(name)
	if isinstance(node, Aravis.GcCategory):
		retval = {}
		features = node.get_features()
		for f in features:
			retval[f] = get_gc_features(genicam, f)
		return retval
	elif isinstance(node, (Aravis.GcStringRegNode,Aravis.GcIntegerNode,Aravis.GcBoolean,Aravis.GcEnumeration)):
		return node.get_value()
	
def get_features(camera, name):
	device = camera.get_device ()
	genicam = device.get_genicam ()
	return get_gc_features(genicam,name)

def set_feature_from_string(camera, name, value):
	device = camera.get_device ()
	genicam = device.get_genicam ()
	node = genicam.get_node(name)
	node.set_value_from_string(value)

features = get_features(camera,"DeviceInformation")

for key,value in features.items():
	tabs = ["\t"]*(2)
	tabs = ["\t"]*(2-len(key)//15)
	print(key,"".join(tabs),": ",value)

if False:
    device = camera.get_device ()
    genicam = device.get_genicam ()
    root = genicam.get_node("Root")
    features = root.get_features()
    print (root)
    print(root.get_node_type())
    print(isinstance(root, Aravis.GcCategory))
    # print (features)
    for feat in features:
        node = genicam.get_node(feat)
        nfeats = node.get_features()
        print("\t",node)
        print("\t",node.get_node_type())
        # print("\t",nfeats)
        for f in nfeats:
            node2 = genicam.get_node(f)
            nfeats2 = node.get_features()
            print("\t\t",node2)
            print("\t\t",node2.get_node_type())
            # print("\t\t",nfeats2)


