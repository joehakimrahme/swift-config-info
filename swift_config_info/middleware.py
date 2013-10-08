# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright (C) 2013 eNovance SAS <licensing@enovance.com>
#
# Author: Joe H. Rahme <joe.hakim.rahme@enovance.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from ConfigParser import ConfigParser

from swift.common.swob import Request, Response
from swift.common.swob import HTTPBadRequest
from swift.common.swob import HTTPMethodNotAllowed
from swift.common.swob import HTTPNotFound
from swift.common.swob import HTTPServerError
from swift.common.utils import json


class ConfigInfoMiddleware(object):
    """
    Config Info middleware used to programmatically request info about the
    cluster.

    If the path is /configinfo it will respond with a JSON formatted string
    revealing info about the configuration of the cluster. The administrator
    can decide which parts of the conf file are made public, so that sensitive
    information can remain private.

    To enable this middleware, add it to the pipeline in your proxy-server.conf
    file. It should be added before any authentication (e.g., tempauth or
    keystone) middleware::

        [pipeline:main]
        pipeline = ... configinfo ... authtoken ... proxy-server

    And add a filter section, such as::
        [filter:configinfo]
        use = egg:swift#configinfo
        public_config = pipeline:main filter:tempurl

    public_config is a variable that holds the sections of the conf file that
    are included in the JSON response.
    """

    def __init__(self, app, conf):
        self.app = app
        self.conf = conf
        self.endpoint_path = "/configinfo"
        self.config = ConfigParser()
        self.public_config = [section.strip() for section in
                              self.conf.get("public_config", None).split(",")]

    def __call__(self, env, start_response):
        request = Request(env)

        if not request.path.startswith(self.endpoint_path):
            return self.app(env, start_response)

        if request.method != 'GET':
            resp = HTTPMethodNotAllowed(req=request, headers={"Allow": "GET"})
            return resp(env, start_response)

        try:
            self.config.read(self.conf["__file__"])
        except (IOError, KeyError):
            resp = HTTPServerError(req=request,
                                   body="An error occurred",
                                   content_type="text/plain")
            return resp(env, start_response)

        config_dict = self._config_parser_to_nested_dict()

        try:
            endpoint, section, option = request.split_path(1, 3, False)
        except ValueError:
            resp = HTTPBadRequest(req=request, headers={})
            return resp(env, start_response)

        try:
            if section and option:
                config_dict = {section: {option: config_dict[section][option]}}
            elif section and not option:
                config_dict = {section: config_dict[section]}
        except KeyError:
            resp = HTTPNotFound(req=request,
                                body="Requested values aren't available",
                                content_type="text/plain")
            return resp(env, start_response)

        resp = Response(req=request,
                        body=json.dumps(config_dict),
                        content_type="application/json")

        return resp(env, start_response)

    def _config_parser_to_nested_dict(self):
        """A helper function that returns a dictionary whose keys are the
        sections specified in self.public_config and the values are mappings
        of options and their values for each section, read in self.config.

        For instance, if self.config has parsed a this file::

            [section1]
            option1 = value1
            option2 = value2
            [section2]
            option1 = value1
            [section3]
            option1 = value1
            option2 = value2
            option3 = value3

        and self.public_config is this::

            ["section1", "section2"]

        then this function will return this dictionary::

            {"section1": {"option1": "value1",
                          "option2": "value2"
                         },
             "section2": {"option1": "value1"}}
        """
        config_dict = {}

        for sect in self.public_config:
            if self.config.has_section(sect):
                section_dict = {}
                for name, value in self.config.items(sect):
                    section_dict[name] = value
                config_dict[sect] = section_dict

            else:
                config_dict[sect] = None

        return config_dict


def filter_factory(global_conf, **local_conf):
    conf = global_conf
    conf.update(local_conf)

    return lambda app: ConfigInfoMiddleware(app, conf)
