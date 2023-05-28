""" This is the main file of the project. It is used to run the project. """
import getopt
import sys
import rfid_backend_FABLAB_BG
import logging


def getArgLoglevel():
    try:
        options, args = getopt.getopt(sys.argv[1:], "l:", ["loglevel ="])
    except:
        print("Error Message ")

    for name, value in options:
        if name in ["-l", "--loglevel"]:
            return int(value)
    return logging.INFO


try:
    rfid_backend_FABLAB_BG.start(getArgLoglevel())
except (KeyboardInterrupt, SystemExit):
    logging.info("Exiting...")
    sys.exit()
