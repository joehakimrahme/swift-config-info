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

    def __call__(self, env, start_response):
        req = Request(env)
        try:
            if req.path == "/configcheck":
                handler = self.GET
                return handler(req)(env, start_response)

        except UnicodeError:
            # What should I do here?
            pass

        return self.app(env, start_response)

    def GET(self, req):

        config = ConfigParser()

        try:
            config.read(self.conf["__file__"])
        except IOError:
            return self.app
        except KeyError:
            return self.app

        public_config = [section.strip() for section in
                         self.conf.get("public_config", None).split(",")]

        config_dict = {}
        for section in public_config:
            if config.has_section(section):
                section_dict = {}
                for name, value in config.items(section):
                    section_dict[name] = value
                config_dict[section] = section_dict

            else:
                config_dict[section] = None

        return Response(request=req,
                        body=json.dumps(config_dict),
                        content_type="application/json")


def filter_factory(global_conf, **local_conf):
    conf = global_conf
    conf.update(local_conf)

    def capability_filter(app):
        return ConfigInfoMiddleware(app, conf)
    return capability_filter
