import yaml
import os
from dc_exceptions import DcException


class DcMixer(object):
    __MIXER_FILE = 'docker-compose-mixer.yml'
    """:type : string"""

    __EXIT_STATUS_INPUT_FILE_NOT_EXISTS = 2
    """:type : string"""

    __work_path = '/'
    """:type : string"""

    __output_file = '/docker-compose.yml'
    """:type : string"""

    __logger = None
    """:type : IDcMixerLogger"""

    __scopes_container = None
    """:type : ScopesContainer"""

    def __init__(self, work_path, output_file, scope_container, logger):
        """
        :param work_path: string
        :param output_file: string
        :param scope_container: ScopesContainer
        :param logger: IDcMixerLogger
        """
        self.__work_path = work_path
        self.__output_file = output_file
        self.__scopes_container = scope_container
        self.__logger = logger

    def get_input_file(self):
        """
        :return: string
        """
        return self.__work_path + '/' + self.__MIXER_FILE

    def process(self):
        self.__logger.log('Start compiling docker-compose file in directory:' + self.__work_path)
        input_file = self.get_input_file()

        if not os.path.isfile(self.get_input_file()):
            raise DcException('File ' + input_file + ' does not exist, can\'t continue!')

        mixer_config = yaml.load(open(self.get_input_file(), 'r'))

        self.__logger.log('Mixer config is below:\n\t' + str(mixer_config), 'debug')

        if 'includes' not in mixer_config:
            self.__logger.log('No includes found in' + self.__MIXER_FILE, 'warning')
        else:
            self.flush()
            self.build_scopes(mixer_config)
            self.save_result_scope()

    def save_result_scope(self):
        """
        Save result scope in output file as yaml
        :return: bool
        """
        scope = self.__scopes_container.get_result_scope()
        self.__logger.log('Result scope is:\n\t' + str(scope), 'debug')
        with open(self.__output_file, 'w') as outfile:
            self.__logger.log('Save result scope in the file "' + self.__output_file + '"', 'debug')
            outfile.write(yaml.dump(scope, default_flow_style=False, indent=2))

    def flush(self):
        """
        Flush ScopesContainer
        """
        self.__scopes_container.flush()

    def build_scopes(self, mixer_config):
        """
        Build scopes in scopes container

        :param mixer_config: dict
        """
        for (prefix, include_file) in mixer_config['includes'].iteritems():
            self.__logger.log('Creating scope for file: ' + include_file + ' and prefix: ' + prefix, 'debug')
            scope = ServicesScope(prefix)
            scope.extract_services(include_file)
            self.__scopes_container.add_scope(prefix, scope)


class ServiceExtractor(object):
    __file = None

    def __init__(self, file_name):
        self.__file = file_name


class ScopesContainer(object):
    __scopes = {}
    """:type : dict[ServicesScope]"""

    def add_scope(self, scope_name, scope):
        """
        Add scope to container

        :param scope_name:
        :param scope: ServicesScope
        """
        self.__scopes[scope_name] = scope

    def flush(self):
        """
        Remove all scopes from container
        """
        self.__scopes = {}

    def get_result_scope(self):
        """
        Get result array of services

        :return: dict
        """
        services_definitions = {}
        for (scope_name, scope) in self.__scopes.iteritems():
            services_definitions.update(scope.get_services_definitions())

        return services_definitions


class ServicesScope(object):
    __scope_name = None
    """:type : string"""

    __services = {}
    """:type : dict[Service]"""

    __services_path = None
    """:type : string"""

    def __init__(self, scope_name):
        self.__scope_name = scope_name

    def extract_services(self, file_name):
        """
        Get  scope of services from one file

        :param file_name: list[Service]
        """

        services_file = os.path.abspath(file_name)
        self.__services_path = os.path.dirname(services_file)

        services_array = yaml.load(open(services_file, 'r'))

        for (service_name, service) in services_array.iteritems():
            self.__services[service_name] = Service(service)

    def get_services_definitions(self):
        """
        Get services as dictionary

        :return: dict
        """
        definitions = {}
        for (service_name, service) in self.__services.iteritems():
            definitions[service_name] = service.get_definition()

        return definitions


class Service(object):
    __definition = None

    def __init__(self, definition):
        """
        :param definition: list
        """
        self.__definition = definition

    def get_definition(self):
        """
        Get definition of service

        :return: list
        """
        return self.__definition
