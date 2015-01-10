#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Easily test HTTP APIs for expected responses. Tests are
defined in YAML config files like this:

    request:
      method: GET
      url: http://my.example.com/api/v1/something?arg=foo
    response:
      headers:
        content-type: application/json; charset=utf-8
        x-powered-by: Express
      status: 200
      eval: |
        # Make sure there are exactly 10 results in JSON format
        s = json.loads(response.body)
        assert len(s) == 10, "expected 10 results, received %s" % len(s)

The API test fails if any of the required conditions is not met by
the received response.

You can get additional debug output by using the `DEBUG` environment variable
like this: `DEBUG=1 ./apitest.py configs/myconfig.yaml`

Copyright (c) 2015, Chris Hager <chris@linuxuser.at>
License: GPLv3
"""
import os
import sys
import time
import yaml
import glob
from pprint import pprint
import optparse
import threading

import json
import datetime

from libs import requests

METHODS = ["get", "post", "put", "patch", "delete", "head"]
REQUEST_TIMEOUT = 6  # seconds

DEBUG=bool(os.environ.get("DEBUG", False))


def log_debug(s):
    if DEBUG:
        print s


class InvalidResponseError(Exception):
    """ Gets thrown on an unexpected API response """
    pass


class ApiTestThread(threading.Thread):
    """
    Thread which performs API tests defined in a single config file.

    Usage:
    >>> thread = ApiTestThread(config_filename)
    >>> thread.start()
    """
    config_fn = None
    running = False
    completed = False
    success = 0
    error = None
    num_tests_run = 0
    requests = []

    def __init__(self, config_fn):
        threading.Thread.__init__(self)
        self.config_fn = config_fn
        self.requests = []

    def run(self):
        running = True
        try:
            config = yaml.load(open(self.config_fn))
            if type(config) == list:
                for c in config:
                    self.run_test(c)
                    self.success += 1
            else:
                self.run_test(config)
                self.success += 1

        except KeyError as e:
            self.error = "Config file KeyError: %s" % str(e)

        except Exception as e:
            self.error = str(e)

        finally:
            self.running = False
            self.completed = True

    def run_test(self, config):
        log_debug("Config: %s\n" % config)

        self.num_tests_run += 1
        self.requests.append("%s %s" % (config["request"]["method"], config["request"]["url"]))

        log_debug("Request: %s %s" % (config["request"]["method"], config["request"]["url"]))
        if not config["request"]["method"].lower() in METHODS:
            raise ValueError("Invalid method: %s" % config["request"]["method"].lower())

        auth = None
        if config["request"].get("auth"):
            auth = tuple(config["request"].get("auth").split(":"))

        req = requests.Request(
                method=config["request"]["method"],
                url=config["request"]["url"],
                params=config["request"].get("url_params"),
                data=config["request"].get("body"),
                headers=config["request"].get("headers"),
                auth=auth
            )

        r = req.prepare()
        s = requests.Session()
        response = s.send(r, timeout=REQUEST_TIMEOUT)
        response.body = response.text

        log_debug("Response status: %s" % response.status_code)
        # pprint(dict(response.headers))
        # pprint(response.text)

        # Check response status
        if config["response"].get("status"):
            if config["response"].get("status") != response.status_code:
                raise InvalidResponseError("Status code %s should be %s" % (response.status_code, config["response"].get("status")))

        # Check response headers
        if config["response"].get("headers"):
            for header, value in config["response"].get("headers").iteritems():
                try:
                    if not response.headers[header] == value:
                        raise InvalidResponseError("Header '%s' is '%s', should be '%s'" % (header, response.headers[header], value))
                except KeyError:
                    raise InvalidResponseError("Expected header '%s' not found" % (header))

        # Check response body
        if config["response"].get("contents"):
            if response.body.strip('"') != config["response"].get("contents"):
                raise InvalidResponseError("Unexpected response content")

        # Check response custom eval script
        custom_eval = config["response"].get("eval")
        if custom_eval:
            log_debug("\nCustom eval:\n>>> %s\n" % "\n>>> ".join(custom_eval.strip().split("\n")))
            try:
                exec(custom_eval.strip())
            except Exception as e:
                err = e if str(e) else "Response validation failed"
                raise InvalidResponseError(err)


def get_files(patterns, recursive=False):
    """
    Returns a list of files as found by the patterns
    """
    # Expand wildcard etc
    _files = []
    for fn in patterns:
        for fn2 in glob.glob(fn):
            _files.append(fn2)

    files = []
    fn_longest = 0

    for fn in _files:
        if os.path.isfile(fn):
            if fn.endswith(".yaml") or fn.endswith(".yml"):
                if len(fn) > fn_longest:
                    fn_longest = len(fn)
                files.append(fn)
            continue

        # traverse root directory, and list directories as dirs and files as files
        if recursive:
            for root, dirs, fns in os.walk(fn):
                for fn2 in fns:
                    if fn2.endswith(".yaml") or fn2.endswith(".yml"):
                        _fn = os.path.join(root, fn2)
                        if len(_fn) > fn_longest:
                            fn_longest = len(_fn)
                        files.append(_fn)

    return files, fn_longest


def main():
    usage = "usage: %prog [options] file_or_path1 file_or_path2 ..."
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-r', '--recursive', action="store_true", dest="recursive", help="Recursively find config files")
    parser.add_option('-l', '--loop', action="store_true", dest="loop", help="Keep testing until no test returns an error")
    parser.add_option('-v', '--verbose', action="store_true", help="Show details for every request")
    options, args = parser.parse_args()
    if not args:
        parser.print_help()
        exit(1)

    # Grab files
    files, fn_longest = get_files(sys.argv[1:], options.recursive)

    # Start Threads
    success = 0
    errors = 0
    error_files = []
    threads = []

    def start_threads(files):
        for fn in files:
            t = ApiTestThread(fn)
            t.start()
            threads.append(t)

    start_threads(files)

    # Wait for threads to finish
    running = True
    try:
        while running:
            time.sleep(0.2)
            running = False
            for t in threads[:]:
                if t.completed:
                    threads.remove(t)
                    if t.success:
                        success += 1
                    if t.error:
                        errors += 1
                        error_files.append(t.config_fn)

                    if options.verbose:
                        print t.config_fn
                    else:
                        fn = t.config_fn
                        dots = "." * (fn_longest + 3 - len(t.config_fn))
                        if t.error:
                            # ♿
                            sys.stderr.write("%s %s %s⛔  %s\n" % (fn, dots, "✅ " * t.success, t.error))
                        elif t.success:
                            print "%s %s %s" % (fn, dots, "✅ " * t.success)

                    if options.verbose:
                        for i, r in enumerate(t.requests):
                            print "- %s ... %s " % (r, "✅ " if i < t.success else "⛔  " + t.error)
                else:
                    running = True

            # All threads are done. If there are errors perhaps we don't yet quit
            if not threads and error_files and options.loop:
                running = True
                time.sleep(4)
                files = error_files[:]
                error_files = []
                start_threads(files)

    except (KeyboardInterrupt, SystemExit):
        pass

    print "%s success, %s error(s)" % (success, errors)
    exit(1 if errors else 0)


if __name__ == "__main__":
    main()
