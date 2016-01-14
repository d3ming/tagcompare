import cherrypy

import api

from tagcompare import settings

from tagcompare import output


server_conf = {
    'server.socket_port': 1313,
}


class Root(object):
    conf = {
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.root': "/Users/dongming/tagcompare",
            'tools.staticdir.dir': "default",
            'tools.staticdir.debug': True
        }
    }

    @cherrypy.expose
    def index(self):
        return "tagcompare service!"

    @cherrypy.expose
    def domain(self):
        return "target domain: {}!".format(settings.DEFAULT.domain)

    @cherrypy.expose
    def output(self):
        return "output path: {}!".format(output.DEFAULT_BUILD_PATH)


if __name__ == '__main__':
    cherrypy.config.update(server_conf)
    cherrypy.tree.mount(Root(), '/', Root.conf)

    cherrypy.tree.mount(api.CaptureApi(), '/api/v1/capture',
                        api.CaptureApi.conf)
    cherrypy.engine.start()
    cherrypy.engine.block()

