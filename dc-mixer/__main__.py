import os
import sys
import getopt
from dc_mixer import DcMixer
from dc_mixer import ScopesContainer
from dc_logger import DcMixerLogger


def main(argv):
    def usage():
        print(
            'Compile docker-compose from several docker-compose.yml files\n\n'

            'Usage:\n'
            '  dc-mixer [options]\n\n'

            'Options:\n'
            '  -h, --help                Print help information\n'
            '  -v, --verbose             Enable verbose mode\n\n'

            'For more information read documentation: https://github.com/paunin/docker-compose-mixer'
        )

    verbose = False
    """:type : bool"""

    try:
        opts, args = getopt.getopt(argv, "hv", ["help", "verbose"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        if opt in ("-v", "--verbose"):
            verbose = True

    mixer = DcMixer(os.getcwd(), os.getcwd() + '/docker-compose.yml', ScopesContainer(), DcMixerLogger(verbose))
    mixer.process()


# ----------------------------------- #
# ------------ main call ------------ #
# ----------------------------------- #
if __name__ == '__main__':
    main(sys.argv[1:])
