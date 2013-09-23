from ConfigParser import ConfigParser

from swift.common.swob import Request, Response
from swift.common.utils import json


class ConfigcheckMiddleware(object):
    """
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
        return ConfigcheckMiddleware(app, conf)
    return capability_filter
