import cherrypy

from tagcompare import capture


class CaptureApi(object):
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }
    exposed = True

    def GET(self):
        return "Capture!"

    def PUT(self, cid):
        """
        Captures a campaign

        Test:
         curl -i -X PUT -d "cid=[:cid]" http://localhost:1313/api/v1/capture
        :param cid: the campaign id
        :return: success or errors
        """
        if not cid:
            cherrypy.response.status = 400
            return "No campaign ID specified!"

        # TODO: validate campaign id further
        if not int(cid) > 0:
            cherrypy.response.status = 400
            return "Invalid campaign ID specified!"

        # TODO: Give proper responses
        # TODO: Make none-blocking call
        errors = capture.main(cids=[cid])
        if not errors:
            cherrypy.response.status = 200
            return "GREAT SUCCESS!"
        else:
            cherrypy.response.status = 500
            return "Errors found: \n{}".format(errors)
