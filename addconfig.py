#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import yaml
from pprint import pprint
import optparse

import requests

methods = ["get", "post", "put", "patch", "delete", "head"]


def create_config(method, url, params=None, data=None, headers=None, auth=None):
    if not method.lower() in methods:
        raise ValueError("Invalid Method")

    if type(headers) == list:
        _headers = headers[:]
        headers = {}
        for h in _headers:
            key, val = h.split("=")
            headers[key] = val

    req = requests.Request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            auth=auth
        )

    r = req.prepare()
    s = requests.Session()
    response = s.send(r)

    res_headers = dict(response.headers)
    if "date" in res_headers:
        del res_headers["date"]
    if "etag" in res_headers:
        del res_headers["etag"]
    if "content-length" in res_headers:
        del res_headers["content-length"]
    if "last-modified" in res_headers:
        del res_headers["last-modified"]

    obj = {
        "request": {
            "method": method.upper(),
            "url": url
        },

        "response": {
            "status": response.status_code,
            "headers": res_headers
        }
    }
    if params:
        obj["request"]["params"] = params
    if data:
        obj["request"]["data"] = data
    if headers:
        obj["request"]["headers"] = headers
    if auth:
        obj["request"]["auth"] = ":".join(auth)

    # print "Actual Response:", response.status_code
    # pprint(dict(response.headers))
    # pprint(response.text)
    return obj

def main():
    usage = "usage: %prog [options] url"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-m', '--method', action="store", dest="method", default="get", help="find vm/images by name/wildcard")
    parser.add_option("-H", "--header", action="append", metavar="header", dest="headers", help="eg. -H user-agent=test")
    parser.add_option('-o', '--outfile', action="store", dest="outfile", help="output file (default: stdout)")
    parser.add_option('--auth', action="store", dest="auth", help="authentication: username:password")
    options, args = parser.parse_args()
    # print options, args
    if not args:
        parser.print_help()
        exit(1)

    auth = tuple(options.auth.split(":")) if options.auth else None

    if len(args) == 1:
        obj = create_config(options.method, args[0], headers=options.headers, auth=auth)
    else:
        obj = []
        for url in args:
            obj.append(create_config(options.method, url, headers=options.headers, auth=auth))

    y = yaml.dump(obj, default_flow_style=False)
    if options.outfile:
        if not options.outfile.endswith(".yaml") and not options.outfile.endswith(".yml"):
            options.outfile += ".yaml"
        with open(options.outfile, "w") as f:
            f.write(y)
        os.system("$EDITOR %s" % options.outfile)
    else:
        print y

if __name__ == "__main__":
    main()
