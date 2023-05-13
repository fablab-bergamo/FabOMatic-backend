""" This is the main file of the project. It is used to run the project. """
import getopt
import sys
from rfid_backend_FABLAB_BG.main import *


def getArgLoglevel() -> int:
    try:
        options, args = getopt.getopt(sys.argv[1:], "l:", ["loglevel ="])
    except:
        print("Error Message ")

    for name, value in options:
        if name in ["-l", "--loglevel"]:
            return int(value)
    return logging.INFO


main(getArgLoglevel())
