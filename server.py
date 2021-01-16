#  coding: utf-8 
import socketserver
import os
from exceptions import (InvalidMethodException, PathNotFoundException, MovedPermanentlyException)

# Copyright 2013 Abram Hindle, Eddie Antonio Santos
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Furthermore it is derived from the Python documentation examples thus
# some of the code is Copyright © 2001-2013 Python Software
# Foundation; All Rights Reserved
#
# http://docs.python.org/2/library/socketserver.html
#
# run: python freetests.py

# try: curl -v -X GET http://127.0.0.1:8080/

# Global Vars
logging = False

mime_types = {
    'html': 'text/html',
    'css' : 'text/css'
}

# Simple Parser Class, did not want parsing code cluttering the request handler
class RequestParser:
    @staticmethod
    def parse_request(request):
        # Retrieve request data from the client
        data = request.recv(1024).strip()

        # Convert request to a string first
        str_data = str(data, "utf-8").split("\r\n")
        if logging:
            print(f"Request Recieved: {str_data}")
        # Parse Relevant Information
        method = RequestParser.parse_method(str_data[0])
        path = RequestParser.parse_path(str_data[0])
        return Request(request, method, path, str_data)

    @staticmethod
    def parse_method(data):
        split_data = data.split(' ')
        return split_data[0]

    @staticmethod
    def parse_path(data):
        split_data = data.split(' ')
        return split_data[1]


class Request:
    # Custom Request object to handle the actual functionality needed
    def __init__(self, request, method, path, raw_request):
        self._request = request  # Socket Object
        self._method = method # Str Method
        self._path = path # Str Path
        self._raw_request = raw_request # Str Request
        self._status_code = None # Holds the status code of the response
        self._message = None # Holds the message that will accompany the statis code, maybe join into object
        self._response_headers = {} # All headers
        self._response_content = "" # Content in response, like html or css

    # Getters
    def getMethod(self):
        return self._method

    def getPath(self):
        return self._path

    def getSplitPath(self):
        # First we want to split the path by /
        return self._path.split('/')

    def getStatusCode(self):
        return self._status_code

    def getMessage(self):
        return self._message

    def getRawRequest(self):
        return self._raw_request

    def getResponseHeaders(self):
        header_str = ""
        for k,v in self._response_headers.items():
            header_str += f"{k}: {v}\r\n"
        return header_str

    def getResponseContent(self):
        return self._response_content

    def setStatusCode(self, code):
        self._status_code = code

    def setResponseHeader(self, key, value):
        self._response_headers[key] = value

    def setResponseContent(self, content):
        self._response_content = content

    def setMessage(self, msg):
        self._message = msg

    # Simply responsible for sending information, no processing should take place here
    def send(self, protocol):
        response = ""
        status_line = f"{protocol} {self.getStatusCode()} {self._message}\r\n{self.getResponseHeaders()}\r\n"
        response += status_line
        response += self.getResponseContent()
        if logging:
            print(f"Sending Response: {response.encode()}")
        self._request.sendall(bytearray(response, "utf-8"))

class MyWebServer(socketserver.BaseRequestHandler):
    # Protocol handled by this webserver
    protocol = "HTTP/1.1"
    allowed_request_methods = ["GET"]

    @staticmethod
    def serve_directory(request, abs_path):
        # Ensure that the abs_path ends with a /
        if abs_path[-1] != '/':
            raise MovedPermanentlyException
        # Simply serve up an index.html if we are in a directory path that is found
        # Ensure that an index.html file exists within the directory
        if 'index.html' not in os.listdir(abs_path):
            raise PathNotFoundException # Make this error more explicit!!!
        # Have an index.html file to serve so set the content type
        request.setResponseHeader("Content-Type", mime_types["html"])
        # Read in index.html file
        content = open(abs_path + "index.html", "r").read()
        request.setResponseContent(content)

    @staticmethod
    def serve_file(request, abs_path):
        file_ext = os.path.splitext(abs_path)[1][1:]

        # This means the current type of file is not handled
        if file_ext not in mime_types:
            raise PathNotFoundException

        request.setResponseHeader("Content-Type", mime_types[file_ext])
        content = open(abs_path, "r").read()
        request.setResponseContent(content)

    # This method handles each client connection
    def handle(self):
        request = None
        # Perform any checking on the request object
        try:
            # Get a request and that is immediately parsed, returning a Request Object
            # This object wraps the actual request from the socket
            request = RequestParser.parse_request(self.request)
            # == Request Validation ==
            # Ensure that the request being received is actually supported
            if request.getMethod() not in MyWebServer.allowed_request_methods:
                raise InvalidMethodException

            # Ensure that the path makes sense
            if logging:
                print("Listed directories:", os.listdir())

            # Change directory into the www directory since that is the assumed base
            abs_path = os.getcwd() + "/www"+ request.getPath()
            if logging:
                print(f"Absolute Path: {abs_path}")

            # Based on the path, determine whether to serve up a specific index.html file or a specific html or css file
            if os.path.isdir(abs_path):
                MyWebServer.serve_directory(request, abs_path)
            elif os.path.isfile(abs_path):
                MyWebServer.serve_file(request, abs_path)
            else:
                # Could not find either a directory or a file that is valid
                raise PathNotFoundException

        except InvalidMethodException:
            request.setStatusCode(405)
            request.setMessage("Method Not Allowed")
        except PathNotFoundException:
            request.setResponseHeader("Content-Type", mime_types["html"])
            request.setResponseContent(
                "<html><body><h1>"
                "Error 404: Path Not Found"
                "</h1></body></html>"
            )
            request.setStatusCode(404)
            request.setMessage("Not Found")
        except MovedPermanentlyException:
            fixed_addr = f"http://{self.server.server_address[0]}:{str(self.server.server_address[1])}{request.getPath()}/"
            request.setResponseHeader("Content-Type", mime_types["html"])
            request.setResponseHeader("Location", fixed_addr)
            request.setResponseContent(
                "<html><body>"
                "<h1>"
                "301 Moved"
                "</h1>"
                "The document has been moved"
                "</body></html>"
            )
            request.setStatusCode(301)
            request.setMessage("Moved Permanently")
        except Exception as e:
            # This is an unhandled webserver Exception
            request.setResponseHeader("Content-Type", mime_types["html"])
            request.setResponseContent(
                "<html><body>"
                "<h1>"
                "500 Internal Server Error"
                "</h1>"
                "<h3>"
                f"{e}"
                "</h3>"
                "</body></html>"
            )
            request.setStatusCode(500)
            request.setMessage("Internal Server Error")
        else:
            # If no exceptions found, we will send the request with a 200 status code
            request.setStatusCode(200)
            request.setMessage("OK")
        finally:
            request.send(MyWebServer.protocol)

if __name__ == "__main__":
    HOST = "localhost"
    PORT = 8080

    socketserver.TCPServer.allow_reuse_address = True
    # Create the server, binding to localhost on port 8080
    server = socketserver.TCPServer((HOST, PORT), MyWebServer)
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
