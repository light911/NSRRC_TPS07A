#!/usr/bin/env python
"""
eigerStream.py listens to EIGER ZMQ messages and decodes the frames.
The data can be either saved as raw bytes, json format, tif, cbf or h5.
Please see the corresponding file writer modules for further information
on the decoding process.

DISCLAIMER:
This code is build for demonstration pupose only. It is not meant
to be productive, efficient, nor complete.

If you have any questions regarding the implementation of
the EIGER stream interface, please contact support@dectris.com.

usage: eigerStream.py [-h] -i IP [-p PORT] [-v] [-f FILENAME]

Listen to stream interface and save data

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        EIGER host ip
  -p PORT, --port PORT  EIGER host port
  -v, --verbose         print some more messages
  -f FILENAME, --filename FILENAME
                        /path/to/file.ext with extension
                        [.bytes|.raw|.tiff|.tiff16|.cbf|.h5|.log|none] stream
                        data to ALBULA viewer window if filename is "albula"

#########
TODO: implement software roi mode
TODO: implement software binning mode
#########
"""

__author__ = "SasG"
__date__ = "17/05/17"
__version__ = "0.0.10"
__reviewer__ = ""

import zmq
import argparse
import os
import sys
import datetime
import tempfile

class ZMQStream():
    def __init__(self, host, port=9999, verbose=False):
        """
        create stream listener object
        """
        self.__host__ = host # EIGER ip
        self.__port__ = port # tcp stream port
        self.__verbose__ = verbose # verbosity

        self.connect() # start stream

    def connect(self):
        """
        open ZMQ pull socket
        return receiver object
        """
        print("[INFO] MAKE SURE STREAM INTERFACE IS ACTIVATED")

        context = zmq.Context()
        receiver = context.socket(zmq.PULL)
        receiver.connect("tcp://{0}:{1}".format(self.__host__,self.__port__))

        self.__receiver__ = receiver
        print("[OK] initialized stream receiver for host tcp://{0}:{1}".format(self.__host__,self.__port__))
        return self.__receiver__

    def receive(self):
        """
        receive and return zmq frames if available
        """
        if self.__receiver__.poll(100): # check if message available
            frames = self.__receiver__.recv_multipart(copy = False)
            if self.__verbose__:
                t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                print("[%s] received zmq frames with length %d" %(t,len(frames)))
            return frames

    def close(self):
        """
        close and disable stream
        """
        if self.__verbose__:
            print("close connection")
        return self.__receiver__.close()

def parseArgs():
    """
    parse user input and return arguments
    """
    parser = argparse.ArgumentParser(description = "Listen to stream interface and save data")

    parser.add_argument("-i", "--ip", help="EIGER host ip", type=str, required=True)
    parser.add_argument("-p", "--port", help="EIGER host port", type=int, default=9999)
    parser.add_argument("-v", "--verbose", help="print some more messages", action="store_true", default = False)
    parser.add_argument("-f", "--filename", help="""/path/to/file.ext with extension
                                                    [.bytes|.raw|.tiff|.tiff16|.cbf|.h5|.log|none]
                                                    stream data to ALBULA viewer window if filename is \"albula\"""", default = None)
    #parser.add_argument("-roi", "--roi", type=int, nargs=4, help="roi mode", default=False)

    args = parser.parse_args()

    return args

def getFileWriter(filename, verbosity):
    """
    return file writer class corresponding to the file extension
    """

    if filename:
        output = os.path.dirname(filename) # get save directory if given
        if not output:
            output = os.getcwd()
        basename, ftype = os.path.splitext(os.path.basename(filename)) # get filename and extension

        if basename.startswith("."): # if only extension is given (AndF)
            ftype = basename
            basename = "eigerStream"
    else:
        from fileWriter import fileWriter
        return fileWriter.FileWriter("noname", ".", "dummy", verbosity)

    if filename in ["albula","ALBULA"]:
        from fileWriter import stream2albula
        fw = stream2albula.Stream2Albula(basename, output, verbosity)
        return fw

    if ftype == "":
        from fileWriter import fileWriter
        fw = fileWriter.FileWriter(basename, output, "dummy", verbosity)
    elif ftype == ".raw":
        from fileWriter import stream2raw
        fw = stream2raw.Stream2Raw(basename, output, verbosity)
    elif ftype == ".bytes":
        from fileWriter import stream2bytes
        fw = stream2bytes.Stream2Bytes(basename, output, verbosity)
    elif "tif" in ftype:
        if "16" in ftype:
            dtype = "int16"
        else:
            dtype = None # native
        from fileWriter import stream2tif
        fw = stream2tif.Stream2Tif(basename, output, verbosity, dtype)
    elif ftype == ".cbf":
        from fileWriter import stream2cbf
        fw = stream2cbf.Stream2Cbf(basename, output, verbosity)
    elif ftype == ".h5" or ftype == ".hdf":
        from fileWriter import stream2hdf
        fw = stream2hdf.Stream2Hdf(basename, output, verbosity)

    elif ftype == ".log":
        from fileWriter import stream2log
        fw = stream2log.Stream2Log(basename, output, verbose=verbosity)

    else:
        raise RuntimeError("Unkwon file type %s in %s" %(ftype,filename))
    return fw

def versionControl(required=(2,7)):
    """
    check python version
    """
    if sys.version_info < required:
        raise RuntimeError("minimum Python 2.7.0 is required!")


if __name__ == "__main__":
    os.system("clear") # clear terminal
    versionControl() # check if Python versions is > 2.7.0
    args = parseArgs() # get cmd line args
    fw = getFileWriter(args.filename, args.verbose) # create filewriter according to file type
    stream = ZMQStream(args.ip, args.port, args.verbose) # initialize stream pull socket
    if not args.filename: stream.__verbose__ = True
    try:
        print("[OK] stream listener ready")
        # listen to stream
        while True:
            frames = stream.receive() # get ZMQ frames
            if frames: # decode frames using the filewriter
                fw.decodeFrames(frames)

    except KeyboardInterrupt:
        stream.close()
