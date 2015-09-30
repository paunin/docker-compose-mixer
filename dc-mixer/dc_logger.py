class IDcMixerLogger(object):
    def log(self, message, level='info'):
        """
        :param message: string
        :param level: string[emergency|alert|critical|error|warning|notice|info|debug]
        :return: None
        """


class DcMixerLogger(IDcMixerLogger):
    verbose_mode = False
    """:type : bool"""

    def __init__(self, verbose_mode):
        self.verbose_mode = verbose_mode

    def log(self, message, level='info'):
        if self.verbose_mode:
            print(level + ': ' + message)

