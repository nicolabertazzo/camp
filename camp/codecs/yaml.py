#
# CAMP
#
# Copyright (C) 2017, 2018 SINTEF Digital
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.
#



from __future__ import absolute_import

from camp.codecs.commons import Codec
from camp.entities.model import Model, Component, Service, Goals, Variable, \
    Feature, DockerFile, DockerImage, Substitution, Instance, Configuration

from yaml import safe_load as load_yaml, dump as yaml_dump



class InvalidYAMLModel(Exception):


    def __init__(self, warnings):
        self._warnings = warnings


    @property
    def warnings(self):
        return self._warnings



class YAML(Codec):


    def __init__(self):
        self._warnings = []


    def save_configuration(self, configuration, stream):
        dictionary = self._as_dictionary(configuration)
        yaml_dump(dictionary, stream, default_flow_style=False)


    @staticmethod
    def _as_dictionary(configuration):
        dictionary = {}
        dictionary[Keys.INSTANCES] = {}
        for each_instance in configuration.instances:
            instance = {}
            instance[Keys.DEFINITION] = each_instance.definition.name

            if each_instance.feature_provider:
                instance[Keys.FEATURE_PROVIDER] = each_instance.feature_provider.name
            instance[Keys.SERVICE_PROVIDERS] = [ each.name \
                                                 for each in each_instance.service_providers]
            instance[Keys.CONFIGURATION] = {}
            for variable, value in each_instance.configuration:
                instance[Keys.CONFIGURATION][variable.name] = value

            dictionary[Keys.INSTANCES][each_instance.name] = instance
        return dictionary


    @staticmethod
    def load_configuration_from(model, stream):
        data = load_yaml(stream)

        instances = [ YAML._create_instance(model, key, item) \
                      for key, item in data[Keys.INSTANCES].items() ]

        result = Configuration(model, instances)

        for each in instances:
            YAML._connect_instance(result, each, data[Keys.INSTANCES][each.name])

        return result


    @staticmethod
    def _create_instance(model, name, data):
        definition = model.resolve(data[Keys.DEFINITION])
        configuration = []
        if Keys.CONFIGURATION in data:
            for variable_name, value in data[Keys.CONFIGURATION].items():
                for any_variable in definition.variables:
                    if any_variable.name == variable_name:
                        configuration.append((any_variable, value))
                        break
                else:
                    raise RuntimeError("Variable '%s' has no match in the model" % variable_name)
        return Instance(name, definition, configuration)


    @staticmethod
    def _connect_instance(configuration, instance, data):
        if Keys.FEATURE_PROVIDER in data \
           and data[Keys.FEATURE_PROVIDER]:
            provider = configuration.resolve(data[Keys.FEATURE_PROVIDER])
            instance.feature_provider = provider
        if Keys.SERVICE_PROVIDERS in data:
            providers = [configuration.resolve(each_provider) \
                         for each_provider in data[Keys.SERVICE_PROVIDERS]]
            instance.service_providers = providers


    def load_model_from(self, stream):
        data = load_yaml(stream)
        components = []
        goals = Goals()
        constraints = []
        for key, item in data.items():
            if key == Keys.COMPONENTS:
                if not isinstance(item, dict):
                    self._wrong_type(dict, type(item), key)
                    continue
                components = self._parse_components(item)
            elif key == Keys.GOALS:
                if not isinstance(item, dict):
                    self._wrong_type(dict, type(item), key)
                    continue
                goals = self._parse_goals(item)
            elif key == Keys.CONSTRAINTS:
                if not isinstance(item, list):
                    self._wrong_type(list, type(item), key)
                    continue
                constraints.extend(item)

            else:
                self._ignore(key)

        if self._warnings:
            raise InvalidYAMLModel(self._warnings)

        return Model(components, goals, constraints)


    def _parse_components(self, data):
        components = []
        for key, item in data.items():
            components.append(self._parse_component(key, item))
        return components


    def _parse_component(self, name, data):
        provided_services = []
        required_services = []
        provided_features = []
        required_features = []
        variables = []
        implementation = None

        for key, item in data.items():

            if key == Keys.PROVIDES_SERVICES:
                if not isinstance(item, list):
                    self._wrong_type(list, type(item), Keys.COMPONENTS, name, key)
                    continue
                for each_name in item:
                    provided_services.append(Service(self._escape(each_name)))

            elif key == Keys.REQUIRES_SERVICES:
                if not isinstance(item, list):
                    self._wrong_type(list, type(item), Keys.COMPONENTS, name, key)
                    continue
                for each_name in item:
                    required_services.append(Service(self._escape(each_name)))

            elif key == Keys.PROVIDES_FEATURES:
                if not isinstance(item, list):
                    self._wrong_type(list, type(item), Keys.COMPONENTS, name, key)
                    continue
                for each_name in item:
                    provided_features.append(Feature(self._escape(each_name)))

            elif key == Keys.REQUIRES_FEATURES:
                if not isinstance(item, list):
                    self._wrong_type(list, type(item), Keys.COMPONENTS, name, key)
                    continue
                for each_name in item:
                    required_features.append(Feature(self._escape(each_name)))

            elif key == Keys.VARIABLES:
                if not isinstance(item, dict):
                    self._wrong_type(dict, type(item), Keys.COMPONENTS, name, key)
                    continue
                variables = self._parse_variables(name, item)

            elif key == Keys.IMPLEMENTATION:
                if not isinstance(item, dict):
                    self._wrong_type(dict, type(item), Keys.COMPONENTS, name, key)
                    continue
                implementation = self._parse_implementation(name, item)

            else:
                self._ignore(Keys.COMPONENTS, name, key)


        return Component(name,
                         provided_services=provided_services,
                         required_services=required_services,
                         provided_features=provided_features,
                         required_features=required_features,
                         variables=variables,
                         implementation=implementation)

    @staticmethod
    def _escape(name):
        if not isinstance(name, str):
            return "_" + str(name)
        return name

    def _parse_variables(self, component, data):
        variables = []
        for key, item in data.items():
            variables.append(self._parse_variable(component, key, item))
        return variables


    def _parse_variable(self, component, name, data):
        path = [Keys.COMPONENTS, component, Keys.VARIABLES, name]
        value_type = None
        values = []
        realization = []
        for key, item in data.items():
            if key == Keys.VALUES:
                if not isinstance(item, list) and not isinstance(item, dict):
                    self.wrong_type(list, type(item), *(path + [key]))
                    continue
                values = self._parse_values(item, path + [key])
            elif key == Keys.TYPE:
                if not isinstance(item, str):
                    self.wrong_type(str, type(item), *(path + [key]))
                    continue
                value_type = item
            elif key == Keys.REALIZATION:
                for index, each in enumerate(item, 1):
                    substitution = self._parse_substitution(component, name, index, each)
                    realization.append(substitution)
            else:
                self._ignore(*(path + [key]))

        return Variable(name, value_type, values, realization)


    def _parse_values(self, data, path):
        values = []
        if isinstance(data, list):
            values = [each for each in data]

        elif isinstance(data, dict):
            minimum = None
            maximum = None
            coverage = None
            for key, item in data.items():
                if key == Keys.RANGE:
                    minimum = min(item)
                    maximum = max(item)
                elif key == Keys.COVERAGE:
                    if not isinstance(item, int):
                        self._wrong_type(int, type(item), *(path + [key]))
                        continue
                    coverage = item
                else:
                    self._ignore(*path + [key])

            if minimum is None or maximum is None:
                self._missing([Keys.RANGE], *path)

            elif not coverage:
                self._missing([Keys.COVERAGE], *path)

            else:
                values = Variable.cover(minimum, maximum, coverage)

        else:
            self._wrong_type(dict, type(item), *path)

        return values

    def _parse_substitution(self, component, variable, index, data):
        path = [Keys.COMPONENTS,
                component,
                Keys.VARIABLES,
                variable,
                Keys.REALIZATION,
                "#%d" % index]

        targets = []
        pattern = self.UNDEFINED_PATTERN
        replacements = []
        for key, item in data.items():

            if key == Keys.TARGETS:
                if not isinstance(data[key], list):
                    self._wrong_type(list, type(data[key]), *(path + [key]))
                    continue
                targets = [each for each in data[key]]

            elif key == Keys.PATTERN:
                pattern = data[key]

            elif key == Keys.REPLACEMENTS:
                if not isinstance(data[key], list):
                    self._wrong_type(list, type(data[key]), *(path + [key]))
                    continue
                replacements = [each for each in data[key]]

            else:
                self._ignore(*(path + [key]))

        if not targets:
            self._missing([Keys.TARGETS], *path)

        if pattern == self.UNDEFINED_PATTERN:
            self._missing([Keys.PATTERN], *path)

        if not replacements:
            self._missing([Keys.REPLACEMENTS], *path)

        return Substitution(targets, pattern, replacements)

    UNDEFINED_PATTERN = "missing pattern!"


    def _parse_implementation(self, name, data):
        implementation = None
        for key, item in data.items():
            if key == Keys.DOCKER:
                implementation = self._parse_docker(name, item)
            else:
                self._ignore(Keys.COMPONENTS, name, Keys.IMPLEMENTATION, key)
        return implementation


    def _parse_docker(self, name, data):
        docker = None
        for key, item in data.items():
            if key == Keys.FILE:
                docker = DockerFile(self._escape(item))
            elif key == Keys.IMAGE:
                docker = DockerImage(self._escape(item))
            else:
                self._ignore(Keys.COMPONENTS, name, Keys.IMPLEMENTATION, Keys.DOCKER, key)

        if not docker:
            self._missing(
                [Keys.FILE, Keys.IMAGE],
                Keys.COMPONENTS, name, Keys.IMPLEMENTATION, Keys.DOCKER)

        return docker


    def _parse_goals(self, data):
        running_services = []
        for key, item in data.items():
            if key == Keys.RUNNING:
                if not isinstance(item, list):
                    self._wrong_type(list, type(item), Keys.GOALS, key)
                    continue
                for index, each_name in enumerate(item, 1):
                    running_services.append(Service(str(each_name)))
            else:
                self._ignore(Keys.GOALS, key)

        return Goals(running_services)


    def _ignore(self, *path):
        self._warnings.append(IgnoredEntry(*path))


    def _wrong_type(self, expected, found, *path):
        self._warnings.append(WrongType(expected, found, *path))


    def _missing(self, candidates, *path):
        self._warnings.append(MissingEntry(candidates, *path))


    @property
    def warnings(self):
        return self._warnings



class Keys:
    """
    The labels that are fixed in the YAML
    """

    COMPONENTS = "components"
    CONFIGURATION = "configuration"
    CONSTRAINTS = "constraints"
    COVERAGE = "coverage"
    DEFINITION = "definition"
    DOCKER = "docker"
    FEATURE_PROVIDER = "feature_provider"
    FILE = "file"
    GOALS = "goals"
    IMAGE = "image"
    IMPLEMENTATION = "implementation"
    INSTANCES = "instances"
    NAME = "name"
    PATTERN = "pattern"
    PROVIDES_FEATURES = "provides_features"
    PROVIDES_SERVICES = "provides_services"
    RANGE = "range"
    REALIZATION = "realization"
    REPLACEMENTS = "replacements"
    REQUIRES_FEATURES = "requires_features"
    REQUIRES_SERVICES = "requires_services"
    RUNNING = "running"
    SERVICE_PROVIDERS = "service_providers"
    TARGETS = "targets"
    TYPE = "type"
    VARIABLES = "variables"
    VALUES= "values"



class YAMLWarning(object):

    def __init__(self, *path):
        self._path = "/".join(path)


    @property
    def path(self):
        return self._path



class IgnoredEntry(YAMLWarning):

    def __init__(self, *path):
        super(IgnoredEntry, self).__init__(*path)

    def __str__(self):
        return "Entry '%s' ignored!" % self._path



class WrongType(YAMLWarning):

    def __init__(self, expected, found, *path):
        super(WrongType, self).__init__(*path)
        self._expected = expected.__name__
        self._found = found.__name__

    @property
    def found(self):
        return self._found


    @property
    def expected(self):
        return self._expected


    def __str__(self):
        return "Wrong type at '%s'! Expected '%s' but found '%s'." % (self._path,
                                                                  self._expected,
                                                                  self._found)

class MissingEntry(YAMLWarning):


    def __init__(self, candidates, *path):
        super(MissingEntry, self).__init__(*path)
        self._candidates = candidates


    def __str__(self):
        return "Incomplete entry '%s'! Possibly missing entries %s" \
            % (self._path,
               ", ".join("'%s'" % each for each in self._candidates))

    @property
    def candidates(self):
        return [each for each in self._candidates]
