Easy API/Webserver Test Automation
==================================

Check whether your API/website is working, and if the response headers and payload
are correct.

Tests are defined in YAML config files, and can check headers
and custom scripts against the response body.

Exits with status code 1 if encountered an error, else with 0.

---

Example Usage:

    $ ./apitest.py configs/example.com.yaml
    configs/example.com.yaml ... ✅
    1 success, 0 error(s)

Testing all configs together (in parallel):

    $ ./apitest.py configs/*
    configs/example.com.yaml ............ ✅
    configs/metachris.com.yaml .......... ✅ ✅
    configs/linuxuser.at.yaml ........... ✅
    configs/some-other-domain.at.yaml ... ✅
    4 success, 0 error(s)

---

Easy to use from cronjobs with emails if one of the tests fail:

    # Cron Contents
    MAILTO=email@example.com
    0 */2 * * * /opt/apitest/apitest-all.sh

---

Adding a http request: `--help`

    $ ./addconfig.py
    Usage: addconfig.py [options] url

    Options:
    -h, --help            show this help message and exit
    -m METHOD, --method=METHOD
                        find vm/images by name/wildcard
    -H header, --header=header
                        eg. -H user-agent=test
    -o OUTFILE, --outfile=OUTFILE
                        output file (default: stdout)
    --auth=AUTH           authentication: username:password

Adding http://example.com:

    $ ./addconfig.py http://example.com -o configs/example.com.yaml
    $ cat configs/example.com.yaml
    request:
      method: GET
      url: http://example.com
    response:
      headers:
        Accept-Ranges: bytes
        Cache-Control: max-age=604800
        Content-Length: '1270'
        Content-Type: text/html
        ...
      status: 200

Adding a payload evaluation (see [configs/example.com.yaml](https://github.com/metachris/apitest/blob/master/configs/example.com.yaml)):

    response:
      eval: assert """<title>Example Domain</title>""" in response.body


---

* Author: Chris Hager <chris@linuxuser.at>
* License: MIT
