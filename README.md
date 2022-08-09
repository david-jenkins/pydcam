# PyDCAM

Control software for Hamamatsu cameras in Python

The basic class is the DcamReader which control the and configures the camera.

The camera is read using a camera thread which waits for a new image and grabs it.

It then copies it into a numpy based circular buffer.

A publisher thread can then read the circular buffer, get a new frame and pass it on by using callbacks.

A Display is available which starts a DcamReader(+cam_thread+pub_thread) and registers a callback to the publish thread.

A zmq_publisher is also available, to use it, instantiate the class with the required parameters and register it's publish function as a callback in the publish thread.

A saver GUI is also here, which allows saving images. This registers a callback when images are requested and then unregisters it when data collection is done. It then saves the images.

You can use
[Github-flavored Markdown](https://guides.github.com/features/mastering-markdown/)
to write your content.