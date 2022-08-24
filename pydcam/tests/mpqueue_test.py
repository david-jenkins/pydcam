
"""

Doesn't really work...

"""

from pydcam.utils.mpqueue import mpqueue_publisher, mpqueue_reader
import sys
import numpy

if __name__ == "__main__":

    if len(sys.argv) > 1:
        opt = sys.argv[1]
    else:
        print("Need to specificy an option, either 1 or 0")
        sys.exit()

    if opt == '0':
        pub = mpqueue_publisher()
        array = numpy.arange(25).reshape((5,5))
        pub.publish(array)
        wait = input("Waiting...")
        array = numpy.arange(10)
        pub.publish(array)
        wait = input("Waiting...")
        array = numpy.arange(10)
        pub.publish(array)
        wait = input("Waiting...")
        array = numpy.arange(10)
        pub.publish(array)
        wait = input("Waiting...")
        pub.close()

    else:
        sub = mpqueue_reader()
        sub.register(print)
        sub.start()

        wait = input("Waiting...")

        sub.stop()