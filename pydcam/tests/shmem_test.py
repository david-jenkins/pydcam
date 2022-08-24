


from pydcam.utils.shmem import shmem_publisher, shmem_reader
import sys
import numpy

if __name__ == "__main__":

    if len(sys.argv) > 1:
        opt = sys.argv[1]
    else:
        print("Need to specificy an option, either 1 or 0")
        sys.exit()

    if opt == '0':
        pub = shmem_publisher(10000)
        array = numpy.arange(25).reshape((5,5))
        pub.publish(array)
        wait = input("Waiting...")
        array = numpy.arange(10)
        pub.publish(array)
        wait = input("Waiting...")
        pub.close()

    else:
        sub = shmem_reader()
        sub.register(print)
        sub.start()

        wait = input("Waiting...")

        sub.stop()