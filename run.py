""" This is the main file of the project. It is used to run the project. """

import getopt
import sys
import FabOMatic
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
    FabOMatic.start(getArgLoglevel())
except (KeyboardInterrupt, SystemExit):
    logging.info("Exiting...")
    sys.exit()
