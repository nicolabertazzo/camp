#
# CAMP
#
# Copyright (C) 2017, 2018 SINTEF Digital
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.
#



from camp.entities.model import Model, Component, Variable, Substitution, \
    DockerFile, Instance, Configuration, Service, Goals
from camp.realize import Builder

from os import makedirs
from os.path import isdir, join as join_paths

from shutil import rmtree

from unittest import TestCase



class VariablesAreRealized(TestCase):


    def setUp(self):
        self._builder = Builder()
        self.create_workspace()
        self.create_docker_file()
        self.create_config_file()
        self.create_docker_compose_file()

    def create_workspace(self):
        if isdir(self.WORKSPACE):
            rmtree(self.WORKSPACE)
        makedirs(self.WORKSPACE)

    WORKSPACE = "temp/realize/variables"


    def create_docker_file(self):
        directory = join_paths(self.WORKSPACE, "template", "server")
        makedirs(directory)
        path = join_paths(directory, "Dockerfile")
        with open(path, "w") as docker_file:
            docker_file.write("FROM debian:jessie\n"
                              "mem=XXX")


    def create_config_file(self):
        path = join_paths(self.WORKSPACE, "template", "server", "server.cfg")
        with open(path, "w") as docker_file:
            docker_file.write("mem=XXX")


    def create_docker_compose_file(self):
        path = join_paths(self.WORKSPACE, "template", "docker-compose.yml")
        with open(path, "w") as docker_file:
            docker_file.write("mem=XXX")


    def test_substitution_in_component_files(self):
        model = Model(
            components=[
                Component(name="server",
                          provided_services=[Service("Awesome")],
                          variables=[
                              Variable(
                                  name="memory",
                                  value_type=str,
                                  values=["1GB", "2GB"],
                                  realization=[
                                      Substitution(
                                          targets=["server/Dockerfile",
                                                   "server/server.cfg"],
                                          pattern="mem=XXX",
                                          replacements=["mem=1", "mem=2"])
                                  ])
                          ],
                          implementation=DockerFile("server/Dockerfile"))
            ],
            goals=Goals(services=[Service("Awesome")]))

        server = model.resolve("server")
        configuration = Configuration(
            model,
            instances = [
                Instance(name="server_0",
                         definition=server,
                         configuration=[(server.variables[0], "2GB")])
            ])

        self.realize(configuration)

        self.assert_file_contains("config_1/images/server_0/Dockerfile", "mem=2")
        self.assert_file_contains("config_1/images/server_0/server.cfg", "mem=2")


    def test_substitution_in_orchestration_file(self):
        model = Model(
            components=[
                Component(name="server",
                          provided_services=[Service("Awesome")],
                          variables=[
                              Variable(
                                  name="memory",
                                  value_type=str,
                                  values=["1GB", "2GB"],
                                  realization=[
                                      Substitution(
                                          targets=["docker-compose.yml"],
                                          pattern="mem=XXX",
                                          replacements=["mem=1", "mem=2"])
                                  ])
                          ],
                          implementation=DockerFile("server/Dockerfile"))
            ],
            goals=Goals(services=[Service("Awesome")]))

        server = model.resolve("server")
        configuration = Configuration(
            model,
            instances = [
                Instance(name="server_0",
                         definition=server,
                         configuration=[(server.variables[0], "2GB")])
            ])

        self.realize(configuration)

        self.assert_file_contains("config_1/docker-compose.yml", "mem=2")


    def realize(self, configuration):
        source = self.WORKSPACE
        destination = join_paths(self.WORKSPACE, "config_1")
        self._builder.build(configuration, source, destination)


    def assert_file_contains(self, resource, pattern):
        path = join_paths(self.WORKSPACE, resource)
        with open(path, "r") as resource_file:
            content = resource_file.read()
            self.assertIn(pattern, content)
