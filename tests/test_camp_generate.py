#
# CAMP
#
# Copyright (C) 2017, 2018 SINTEF Digital
# All rights reserved.
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.
#


from os import makedirs
from os.path import isfile, isdir, join, exists

from shutil import rmtree, copytree

from unittest import TestCase

from camp.main import Runner



class GenerateXWikiTests(TestCase):


    @classmethod
    def setUpClass(cls):
        if isdir(cls.WORKING_DIRECTORY):
            rmtree(cls.WORKING_DIRECTORY)
        copytree(cls.XWIKI_SOURCES, cls.WORKING_DIRECTORY)



    WORKING_DIRECTORY = "temp/xwiki"

    XWIKI_SOURCES = "samples/stamp/xwiki"


    def test_that_tests_run(self):
        self.assertEqual(2, 2)


    def test_that_camp_generates_files(self):
        self.invoke_camp_generate()

        self.verify_generated_files()


    def invoke_camp_generate(self):
        runner = Runner()
        runner.start_camp(["generate", "-d", self.WORKING_DIRECTORY])


    def verify_generated_files(self):
        for each in self.EXPECTED_GENERATED_FILES:
            path = join(self.WORKING_DIRECTORY, each)
            self.assertTrue(exists(path),
                            "Expecting file '%s', but could not find it!" % each)



    EXPECTED_GENERATED_FILES = [
        # Generated by the docker images finder
        "out/genimages.yml",
        "out/ampimages.yml",
        # Generated by the docker images builder
        "build/tomcat7--openjdk-9",
        "build/tomcat85--openjdk-9",
        "build/tomcat8--openjdk-8",
        "build/tomcat9--openjdk-9",
        "build/xwiki8mysql--tomcat8-openjdk-8",
        "build/xwiki8postgres--tomcat7-openjdk-9",
        "build/xwiki9mysql--tomcat85-openjdk-9",
        "build/xwiki9postgres--tomcat9-openjdk-9",
        # Generated by the docker compose finder
        "out/ampcompose.yml"
    ]
