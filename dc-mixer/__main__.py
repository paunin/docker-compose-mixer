import os
import sys
import getopt
import logging
from dc_mixer import DcMixer
from dc_mixer import ScopesContainer


def main(argv):
    def usage():
        print(
            'Compile docker-compose from several docker-compose.yml files\n\n'

            'Usage:\n'
            '  dc-mixer [options]\n\n'

            'Options:\n'
            '  -h, --help                Print help information\n'
            '  -i, --input-file          Input file (default `docker-compose-mixer.yml` in current directory)\n'
            '  -o, --output-file         Output file (default `docker-compose.yml` in current directory)\n'
            '  -h, --help                Print help information\n'
            '  -v, --verbose             Enable verbose mode\n\n'

            'For more information read documentation: https://github.com/paunin/docker-compose-mixer'
        )

    input_file = None
    output_file = None

    try:
        opts, args = getopt.getopt(argv, "hvo:i:", ["help", "verbose", "output-file=", "input-file="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit(0)
        if opt in ("-v", "--verbose"):
            logging.basicConfig(level=logging.DEBUG)
        if opt in ("-i", "--input-file"):
            input_file = arg
        if opt in ("-o", "--output-file"):
            output_file = arg

    if not input_file:
        input_file = os.getcwd() + '/docker-compose-mixer.yml'

    if not output_file:
        output_file = os.getcwd() + '/docker-compose.yml'

    mixer = DcMixer(input_file, output_file, ScopesContainer())
    mixer.process()


# ----------------------------------- #
# ------------ main call ------------ #
# ----------------------------------- #
if __name__ == '__main__':
    main(sys.argv[1:])
