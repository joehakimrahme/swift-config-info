# -*- encoding: utf-8 -*-
__author__ = "Joe H. Rahme <joe@enovance.com>"

# Copyright 2013 eNovance.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import json
import tempfile
import unittest

from swift.common.swob import Request, Response
import swift_config_info.middleware as configinfo


conf_file_text = """
[section1]
option1 = value1
option2 = value2
[section2]
option1 = value1
option2 = value2
"""


class FakeApp(object):
    def __call__(self, env, start_response):
        req = Request(env)
        return Response(request=req, body='FAKE APP')(env, start_response)


class TestConfigInfo(unittest.TestCase):

    def get_app(self, app, global_conf, **local_conf):
        factory = configinfo.filter_factory(global_conf, **local_conf)
        return factory(app)

    def start_response(self, status, headers):
        self.got_statuses.append(status)

    def setUp(self):

        self.got_statuses = []
        self.conf_file = tempfile.NamedTemporaryFile()
        self.conf_file.write(conf_file_text)
        self.conf_file.flush()
        self.app = self.get_app(FakeApp(),
                                {"__file__": self.conf_file.name},
                                public_config="section1, section3")

    def tearDown(self):
        self.conf_file.close()

    def test_public_config(self):
        self.assertTrue("section1" in self.app.public_config)
        self.assertTrue("section3" in self.app.public_config)

    def test_config_info(self):
        req = Request.blank('/configinfo', environ={'REQUEST_METHOD': 'GET'})
        resp = self.app(req.environ, self.start_response)

        _expected_dict = {'section1': {'option1': 'value1',
                                       'option2': 'value2'},
                          'section3': None}

        self.assertEquals(['200 OK'], self.got_statuses)
        self.assertEquals(resp, [json.dumps(_expected_dict)])

    def test_config_info_pass(self):
        req = Request.blank('/', environ={'REQUEST_METHOD': 'GET'})
        resp = self.app(req.environ, self.start_response)
        self.assertEquals(['200 OK'], self.got_statuses)
        self.assertEquals(resp, ['FAKE APP'])

    def test_config_section(self):
        req = Request.blank('/configinfo/section1',
                            environ={'REQUEST_METHOD': 'GET'})
        resp = self.app(req.environ, self.start_response)

        _expected_dict = {'section1': {'option1': 'value1',
                                       'option2': 'value2'}}
        self.assertEquals(['200 OK'], self.got_statuses)
        self.assertEquals(resp, [json.dumps(_expected_dict)])

    def test_config_empty_section(self):
        """This tests the request of a section not existing in the conf file
        but explicitly allowed by the admin in public_config.
        """
        req = Request.blank('/configinfo/section3',
                            environ={'REQUEST_METHOD': 'GET'})
        resp = self.app(req.environ, self.start_response)

        _expected_dict = {'section3': None}

        self.assertEquals(['200 OK'], self.got_statuses)
        self.assertEquals(resp, [json.dumps(_expected_dict)])

    def test_config_option(self):
        req = Request.blank('/configinfo/section1/option1',
                            environ={'REQUEST_METHOD': 'GET'})
        resp = self.app(req.environ, self.start_response)

        _expected_dict = {'section1': {'option1': 'value1'}}

        self.assertEquals(['200 OK'], self.got_statuses)
        self.assertEquals(resp, [json.dumps(_expected_dict)])

    def test_config_bad_section(self):
        req = Request.blank('/configinfo/section40',
                            environ={'REQUEST_METHOD': 'GET'})
        resp = self.app(req.environ, self.start_response)

        self.assertEquals(['404 Not Found'], self.got_statuses)


if __name__ == '__main__':
    unittest.main()
