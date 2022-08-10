from pydcam.dcam_reader import DCamSim
from pydcam.utils.zmq_pubsub import zmq_publisher

if __name__ == "__main__":

    camreader = DCamSim()
    this_zmq = zmq_publisher()
    camreader.register_callback(this_zmq.publish)
    camreader.open_camera()

    while 1:
        try:
            x = input("Type: exp X\nwhere X is the exposure time:\n")
            if x[:3] == "exp":
                try:
                    et = float(x[4:])
                except Exception as e:
                    print("wrong type for exposure time")
                    continue
                camreader.set_exposure(et)
        except KeyboardInterrupt as e:
            print("Finished with ctrl-C")
            break

    print("closing")
    camreader.quit()
    this_zmq.close()