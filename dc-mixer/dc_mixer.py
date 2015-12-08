import yaml
import os
import logging
from os.path import relpath
from dc_exceptions import DcException
from copy import deepcopy


class DcMixer(object):
    """
    Main class for dc-mixer
    """
    __MIXER_FILE = 'docker-compose-mixer.yml'
    """:type : string"""

    __EXIT_STATUS_INPUT_FILE_NOT_EXISTS = 2
    """:type : string"""

    __input_file = '/docker-compose-mixer.yml'
    """:type : string"""

    __output_file = '/docker-compose.yml'
    """:type : string"""

    __scopes_container = None
    """:type : ScopesContainer"""

    def __init__(self, input_file, output_file, scope_container):
        """
        :param input_file: string
        :param scope_container: ScopesContainer
        """

        self.__input_file = input_file
        self.__output_file = output_file
        self.__scopes_container = scope_container

    def get_input_file(self):
        """
        :return: string
        """
        return self.__input_file

    def process(self):
        logging.log(logging.DEBUG, 'Start compiling compose file...')
        logging.log(logging.DEBUG, 'Input file: ' + self.__input_file + '; output file: ' + self.__output_file)
        input_file = self.get_input_file()

        if not os.path.isfile(self.get_input_file()):
            raise DcException('File ' + input_file + ' does not exist, can\'t continue!')

        mixer_config = yaml.load(open(self.get_input_file(), 'r'))

        logging.log(logging.DEBUG, 'Mixer config is below:\n\t' + str(mixer_config))

        if 'includes' not in mixer_config:
            logging.log(logging.WARNING, 'No includes found in' + self.__MIXER_FILE)
        else:
            self.flush()
            self.build_scopes(mixer_config)
            self.resolve_services_names()
            self.resolve_paths()
            self.resolve_ports()
            self.add_master_scope(mixer_config)
            self.apply_overrides(mixer_config)
            self.save_result_scope()

    def flush(self):
        """
        Flush ScopesContainer
        """
        self.__scopes_container.flush()

    @staticmethod
    def is_path_relative(path):
        """
        Check if we can update path with prefix

        :param path: string
        :return: Bool
        """
        if os.path.isabs(path) or str(path).startswith('~'):
            return False
        else:
            return True

    def build_scopes(self, mixer_config):
        """
        Build scopes in scopes container

        :param mixer_config: dict
        """
        if 'ignores' not in mixer_config:
            mixer_config['ignores'] = []
        self.__scopes_container.set_ignored_services(mixer_config['ignores'])

        for (prefix, include_file) in mixer_config['includes'].iteritems():
            if self.is_path_relative(include_file):
                include_file = os.path.normpath(os.path.join(os.path.dirname(self.__input_file), include_file))

            logging.log(logging.DEBUG, 'Creating scope for file: ' + include_file + ' and prefix: ' + prefix)
            scope = ServicesScope(prefix)
            scope.extract_services_from_file(include_file)
            self.__scopes_container.add_scope(prefix, scope)

    def resolve_services_names(self):
        """
        Resolve services names in all scopes
        """
        logging.log(logging.DEBUG, 'Resolving services names')
        self.__scopes_container.resolve_names()

    def resolve_paths(self):
        """
        Resolve paths to files and dirs
        """
        logging.log(logging.DEBUG, 'Resolving services paths with')
        self.__scopes_container.resolve_paths(os.path.dirname(self.__output_file))

    def resolve_ports(self):
        """
        Resolve ports which we will bind to host machine
        """
        logging.log(logging.DEBUG, 'Resolving services ports')
        redefined_ports = self.__scopes_container.resolve_ports()
        logging.log(logging.DEBUG, 'Redefined ports:\n\t' + str(redefined_ports))

    def add_master_scope(self, mixer_config):
        """
        Add master services from `master_services` section
        """
        if 'master_services' not in mixer_config:
            return
        scope = ServicesScope('')
        scope.extract_services(mixer_config['master_services'])
        self.__scopes_container.add_scope('', scope)

    def apply_overrides(self, mixer_config):
        """
        Apply overrides from `overrides` section

        :param mixer_config: dict
        """
        if 'overrides' not in mixer_config:
            return

        self.__scopes_container.apply_overrides(mixer_config['overrides'])

    def save_result_scope(self):
        """
        Save result scope in output file as yaml

        :return: bool
        """
        scope = self.__scopes_container.get_result_scope()
        logging.log(logging.DEBUG, 'Result scope is:\n\t' + str(scope))
        with open(self.__output_file, 'w') as outfile:
            logging.log(logging.DEBUG, 'Save result scope in the file "' + self.__output_file + '"')
            outfile.write(yaml.dump(scope, default_flow_style=False, indent=2))


class ScopesContainer(object):
    """
    High level container for scopes
    """
    __scopes = {}
    """:type : dict[ServicesScope]"""

    __ignored_services = []
    """:type : list"""

    def __init__(self):
        self.__scopes = {}
        self.__ignored_services = []

    def set_ignored_services(self, ignored_services):
        self.__ignored_services = ignored_services

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
        self.__ignored_services = []

    def get_result_scope(self):
        """
        Get result array of services

        :return: dict
        """
        services_definitions = {}
        for (scope_name, scope) in self.__scopes.iteritems():
            services_definitions.update(scope.get_services_definitions())

        return services_definitions

    def resolve_names(self):
        """
        Resolve names in services and add prefixes using scopes' name
        """
        for (scope_name, scope) in self.__scopes.iteritems():
            scope.update_names(self.__ignored_services)

    def resolve_paths(self, work_path='/'):
        """
        Resolve paths in services
        """
        for (scope_name, scope) in self.__scopes.iteritems():
            scope.update_paths(work_path)

    def resolve_ports(self):
        """
        Resolve ports and return redefined in each container
        {
            projaphp: {
                80:81 // redefine port 80 to 81 for service projaphp
            }
        }

        :return: dict
        """
        busy_ports = []
        redefined_ports = {}
        for (scope_name, scope) in self.__scopes.iteritems():
            busy_ports, new_redefined_ports = scope.update_ports(busy_ports)
            redefined_ports.update(new_redefined_ports)

        return redefined_ports

    def apply_overrides(self, overrides):
        """
        Apply overrides

        :param overrides: dict
        """
        for (scope_name, scope) in self.__scopes.iteritems():
            self.__scopes[scope_name].apply_overrides(overrides)


class ServicesScope(object):
    """
    Class which defines services from one scope (file docker-compose.yml)
    """
    __scope_name = None
    """:type : string"""

    __services = {}
    """:type : dict[Service]"""

    __services_path = None
    """:type : string"""

    def __init__(self, scope_name):
        self.__scope_name = scope_name
        self.__services = {}
        self.__services_path = None

    def extract_services_from_file(self, file_name):
        """
        Get  scope of services from one file

        :param file_name: list[Service]
        """

        services_file = os.path.abspath(file_name)
        self.__services_path = os.path.dirname(services_file)

        services_config = yaml.load(open(services_file, 'r'))

        self.extract_services(services_config)

    def extract_services(self, services_config):
        """
        Extract services from config array

        :param services_config: dict
        """
        for (service_name, service) in services_config.iteritems():
            self.__services[service_name] = Service(service)

    def get_services_definitions(self):
        """
        Get services as dictionary

        :return: dict
        """
        definitions = {}
        for (service_name, service) in self.__services.iteritems():
            if not service.is_ignored():
                definitions[service_name] = service.get_definition()

        return definitions

    def update_names(self, ignored_services=[], prefix=None):
        """
        Update services names with prefix
        :param prefix: string
        """
        if not prefix:
            prefix = self.__scope_name

        services = {}
        name_map = {}
        for (service_name, service) in self.__services.iteritems():
            # rename
            new_name = str(prefix + service_name)
            name_map[service_name] = new_name
            service = deepcopy(self.__services[service_name])  # deepcopy and remove old dictionary
            services[new_name] = service
            if new_name in ignored_services:
                service.ignore()

        self.__services = services

        for (service_name, service) in self.__services.iteritems():
            # update usages of service name
            service.update_container_name(service_name)
            service.update_volumes_from(name_map, ignored_services)
            service.update_links(name_map, ignored_services)
            service.update_extends(name_map, ignored_services)

    def update_paths(self, work_path):
        """
        Resolve paths in scope
        """
        rel_path = relpath(self.__services_path, work_path)

        for (service_name, service) in self.__services.iteritems():
            # update usages of service name
            service.update_build_path(rel_path)
            service.update_volumes_path(rel_path)
            service.update_env_file_path(rel_path)
            service.update_extends_path(rel_path)

    def update_ports(self, busy_ports=[]):
        """
        Update ports and add busy ports to input array

        :param busy_ports: dict
        :return: list, dict
        """
        redefined_ports = {}
        for (service_name, service) in self.__services.iteritems():
            if service.is_ignored():  # dont need to deal with ignored service
                continue

            busy_ports, service_redefined_ports = service.update_ports()
            if len(service_redefined_ports):
                redefined_ports[service_name] = service_redefined_ports
        return busy_ports, redefined_ports

    def apply_overrides(self, overrides):
        """
        Override

        :param overrides: dict
        """
        for (service_name, service) in self.__services.iteritems():
            if service_name in overrides:
                service.apply_overrides(overrides[service_name])


class Service(object):
    """
    Class which defines service from docker compose
    """
    __definition = None
    """:type : dict"""

    __ignored = False
    """:type : bool"""

    def __init__(self, definition):
        """
        :param definition: dict
        """
        self.__definition = definition
        self.__ignored = False

    def ignore(self):
        """
        Ignore service in scope
        """
        self.__ignored = True

    def is_ignored(self):
        """
        If service ignored

        :return: bool
        """
        return self.__ignored

    def get_definition(self):
        """
        Get definition of service

        :return: list
        """
        return self.__definition

    def update_container_name(self, name):
        """
        Update container name if only exists

        :param name: string
        """
        if 'container_name' in self.__definition:
            if self.__definition['container_name']:
                self.__definition['container_name'] = name
            else:
                del self.__definition['container_name']

    def update_volumes_from(self, name_map, ignored_services=[]):
        """
        Update volumes from

        :param name_map: dict
        :param ignored_services: list
        """
        new_volumes_from = []

        if 'volumes_from' in self.__definition:
            if self.__definition['volumes_from']:
                for (service_name) in self.__definition['volumes_from']:
                    new_volume_from = name_map[service_name]
                    if new_volume_from not in ignored_services:  # we don't need ignored services
                        new_volumes_from.append(new_volume_from)

                self.__definition['volumes_from'] = new_volumes_from
            else:
                del self.__definition['volumes_from']

    def update_links(self, name_map, ignored_services=[]):
        """
        Update links

        :param name_map: dict
        :param ignored_services: list
        """
        new_links = []
        if 'links' in self.__definition:
            if self.__definition['links']:
                for (link) in self.__definition['links']:
                    link_parts = str(link).split(':', 1)
                    old_link_service=link_parts[0]
                    new_link_service = name_map[old_link_service]

                    if new_link_service not in ignored_services:  # we don't need ignored services
                        link_parts[0] = new_link_service
                        if len(link_parts) == 1:
                            link_parts.append(old_link_service)
                        new_links.append(':'.join(link_parts))

                self.__definition['links'] = new_links
            else:
                del self.__definition['volumes_from']

    def update_extends(self, name_map, ignored_services):
        """

        :param name_map: dict
        :param ignored_services: list
        """
        if 'extends' in self.__definition and self.__definition['extends'] and \
                ('file' not in self.__definition['extends'] or not self.__definition['extends']['file']) and \
                        'service' in self.__definition['extends'] and self.__definition['extends']['service']:
            new_extends_service = name_map[self.__definition['extends']['service']]
            if new_extends_service in ignored_services:
                del self.__definition['extends']
                self.ignore()
            else:
                self.__definition['extends']['service'] = new_extends_service

    def update_build_path(self, rel_path):
        """
        :param rel_path: string
        """
        if 'build' in self.__definition:
            if self.__definition['build']:
                new_build = self.__definition['build']
                if DcMixer.is_path_relative(new_build):
                    new_build = os.path.normpath(os.path.join(rel_path, new_build))

                self.__definition['build'] = new_build
            else:
                del self.__definition['build']

    def update_volumes_path(self, rel_path):
        """
        :param rel_path: string
        """
        new_volumes = []
        if 'volumes' in self.__definition:
            if self.__definition['volumes']:
                for (volume) in self.__definition['volumes']:
                    volume_parts = str(volume).split(':', 1)

                    if DcMixer.is_path_relative(volume_parts[0]):
                        host_path = os.path.normpath(os.path.join(rel_path, volume_parts[0]))
                        if not str(volume_parts[0]).startswith('..'):
                            host_path = os.path.join('.', host_path)
                        volume_parts[0] = host_path

                    new_volumes.append(':'.join(volume_parts))

                self.__definition['volumes'] = new_volumes
            else:
                del self.__definition['volumes']

    def update_env_file_path(self, rel_path):
        """
        Update path[s] to file with ENV variables

        :param rel_path: string
        """
        if 'env_file' in self.__definition:
            if self.__definition['env_file']:
                if isinstance(self.__definition['env_file'], str):
                    self.__definition['env_file'] = [self.__definition['env_file']]

                new_env_files = []
                for (env_file) in self.__definition['env_file']:
                    new_env_file = env_file
                    if DcMixer.is_path_relative(new_env_file):
                        new_env_file = os.path.normpath(os.path.join(rel_path, new_env_file))

                    new_env_files.append(new_env_file)

                self.__definition['env_file'] = new_env_files
            else:
                del self.__definition['env_file']

    def update_extends_path(self, rel_path):
        """
        :param rel_path: string
        """
        if 'extends' in self.__definition and self.__definition['extends'] and \
                        'file' in self.__definition['extends'] and self.__definition['extends']['file']:
            new_file = self.__definition['extends']['file']
            if DcMixer.is_path_relative(new_file):
                self.__definition['extends']['file'] = os.path.normpath(os.path.join(rel_path, new_file))

    def update_ports(self, busy_ports=[]):
        """
        Update ports and return busy ports and redefined ports

        :param busy_ports: dict
        :returns: list, dict
        """
        redefined_ports = {}
        new_ports = []
        if 'ports' in self.__definition and self.__definition['ports']:
            for port in self.__definition['ports']:
                port_parts = str(port).split(':')

                if len(port_parts) > 2:  # 127.0.0.1:8001:8001
                    element_to_change = 1
                elif len(port_parts) > 1:  # 8001:8001
                    element_to_change = 0
                else:  # 8001
                    continue  # just the container port (a random host port will be chosen)

                origin_port = int(port_parts[element_to_change])
                redefined_port = origin_port
                while redefined_port in busy_ports:
                    redefined_port += 1
                if origin_port != redefined_port:
                    redefined_ports[origin_port] = redefined_port

                busy_ports.append(redefined_port)
                port_parts[element_to_change] = str(redefined_port)
                new_ports.append((':'.join(port_parts)))

            self.__definition['ports'] = new_ports

        return busy_ports, redefined_ports

    def apply_overrides(self, overrides):
        """
        Override parts in service

        :param overrides:
        """
        for (override_part, override_val) in overrides.iteritems():
            self.__definition[override_part] = override_val
