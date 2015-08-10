#!/bin/env python
#
#  Copyright 2014 Alcatel-Lucent Enterprise.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
#  except in compliance with the License. You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software distributed under the License
#  is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
#  either express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

import cookielib
import getopt
import re
import sys
import traceback
import urllib
import urllib2

from pprint import pprint
from time import sleep
from xml.dom.minidom import parseString

try:
    import json
except ImportError:
    import simplejson as json

try:
    from prettytable import PrettyTable
    pretty_tables = True
except ImportError:
    pretty_tables = False

"""
# TODO

Original check-in (SS: Server-side, CS: Client-side, ALL: Both sides):

'*'' = 'todo' / '='' = 'done'

= [SS ] Get with limit=1, twice: do we get the same value due to GetNextAsGet?
= [ALL] Versioning needs to be added
= [ALL] Add XML support!
= [ALL] Caching headers?
= [SS ] check what happens when empty username is provided: guarded in web_service
= [SS ] what happens when mibObjectx: contains an empty value? (likely use case)
= [SS ] Map /info/!
= [ALL] error even with prettylinks off. Read mibTable == ?
= [ALL] CLI: unable to execute CLI commands via web service
= [ALL] CLI error: message improperly wrapped in message?
= [CS ] User name: userName v. username?
= [SS ] API call without being logged in returns login page
= [CS ] Check login call return

# MANUAL

## Compatibility

Python 2.4, Python 2.7

### Python 2.4 compatibility

This library was created for a recent version of Python (2.7)

However, many Linux distros still offer an older version (2.4) and nothing more recent.

Thus, the script was adapted to work with Python 2.4 with the following caveat:

Python 2.4 will require a third-party library: simplejson

This library may already be installed; it may be the wrong version (recent
versions break 2.4 compatibility)

Provided you have pip installed, here is how to work with the proper version:

     virtualenv virtual_env
     cd virtual_env
     . bin/activate
     pip install simplejson==2.3.0

### Ternary operator

This code, to maintain compatibility with older versions of Python,
uses a hack since the ternary operator appeared belatedly.
This code was written to be compatible, not performant.
lambda x,y:(lambda:my false expr, lambda:my true expr)[condition]()

## Dependencies

Another package, optional with any version of Python, is prettytable:
http://code.google.com/p/prettytable/

If it is not installed, the sample code's display will not be rendered as nicely.

"""


class AOSException(Exception):
    pass


class AOSErrorHandler(urllib2.HTTPDefaultErrorHandler):

    def __init__(self):
        pass

    def http_error_default(self, req, fp, code, msg, headers):
        result = urllib2.HTTPError(
            req.get_full_url(), code, msg, headers, fp)
        result.status = code
        return result


class AOSRedirectHandler(urllib2.HTTPRedirectHandler):

    def __init__(self):
        pass

    def http_error_redirect(self, req, fp, code, msg, headers):
        raise AOSException("ERROR:\nA redirect was detected while communicating with the web service.\n"
                           "This is most likely due to a mismatch between the local"
                           "'--nossl' and the remote 'webview force-ssl' settings.\n"
                           "Please make sure that both producer and consumer agree on a common security level.")

    http_error_301 = http_error_302 = http_error_303 = http_error_307 = http_error_redirect


class AOSXMLDecoder(dict):

    def __init__(self, node):
        super(AOSXMLDecoder, self).__init__()
        self[node.nodeName] = self.xml2dict(node)

    # Despite its name, sometimes this method will return a string.
    def xml2dict(self, node):
        if len(node.childNodes) == 1 and node.firstChild.nodeType == node.TEXT_NODE:
            return node.firstChild.nodeValue
        else:
            cur_node_dict = {}
            for child in node.childNodes:
                node_name = child.nodeName
                if child.nodeType == node.ELEMENT_NODE:
                    if child.hasAttributes() and 'name' in child.attributes.keys():
                        node_name = child.attributes['name'].nodeValue
                    child_dict = self.xml2dict(child)
                    if node_name in cur_node_dict.keys():
                        cur_node_dict[node_name].append(child_dict)
                    else:
                        cur_node_dict.setdefault(node_name, child_dict)
        if len(cur_node_dict) == 0:
            cur_node_dict = ''
        return cur_node_dict


class AOSHeaders(dict):

    def __init__(self, config):
        super(AOSHeaders, self).__init__()
        self['Accept'] = 'application/vnd.alcatellucentaos+%s; version=%s' % (
            (AOSAPI.ENC_DEFAULT, AOSAPI.ENC_ALT)[config[AOSAPI.ENC_ALT]],
            config['api'])
        vrf = config.get('vrf')
        if vrf is not None:
            self['ALU-context'] = "vrf=%s" % vrf


class AOSConnection(object):
    USER_AGENT = "'AOSConsumer/1.0 (compatible; MSIE 5.5; Windows NT)'"

    def __init__(self, username, password, hostaddress, secure=True, obeyproxy=True,
                 prettylinks=True, useport=-1,
                 aosheaders=None, linger=0,
                 debug=False):
        self.username = username
        self.password = password
        self.hostaddress = hostaddress
        self.secure = secure
        self.obeyproxy = obeyproxy
        self.prettylinks = prettylinks
        self.useport = useport
        self.aosheaders = aosheaders
        self.linger = linger
        self.debug = debug
        # cookiejar is public so that we can inspect it
        # should anything go wrong
        self.cookiejar = cookielib.LWPCookieJar()
        if obeyproxy:
            urllib2.install_opener(
                urllib2.build_opener(
                    urllib2.HTTPCookieProcessor(self.cookiejar),
                    urllib2.HTTPHandler(debuglevel=0),
                    AOSErrorHandler(),
                    AOSRedirectHandler()))
        else:
            urllib2.install_opener(
                urllib2.build_opener(
                    urllib2.ProxyHandler({}),
                    urllib2.HTTPCookieProcessor(self.cookiejar),
                    urllib2.HTTPHandler(debuglevel=0),
                    AOSErrorHandler(),
                    AOSRedirectHandler()))

    def endpoint(self):
        return "%s://%s%s/" % (("http", "https")[self.secure is True],
                               self.hostaddress, ('', ':' + str(self.useport))[str(self.useport) != '-1'])

    def headers(self, request):
        if self.aosheaders is not None:
            for aheader in self.aosheaders:
                request.add_header(aheader, self.aosheaders[aheader])
        return request

    def delete(self, domain, urn, data):
        if self.debug:
            print "DELETE Request: [%s]" % (
                self.endpoint() +
                ('?domain=' + domain, domain)[self.prettylinks] +
                (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks])
            print urllib.urlencode(data)

        request = urllib2.Request(
            self.endpoint() +
            ('?domain=' + domain, domain)[self.prettylinks] +
            (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks],
            urllib.urlencode(data),
            {'User-Agent': self.USER_AGENT})
        request.get_method = lambda: 'DELETE'
        request = self.headers(request)

        return urllib2.urlopen(request)

    def put(self, domain, urn, data):
        if self.debug:
            print "PUT Request: [%s]" % (
                self.endpoint() +
                ('?domain=' + domain, domain)[self.prettylinks] +
                (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks])
            print urllib.urlencode(data)

        request = urllib2.Request(
            self.endpoint() +
            ('?domain=' + domain, domain)[self.prettylinks] +
            (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks],
            urllib.urlencode(data),
            {'User-Agent': self.USER_AGENT})
        request.get_method = lambda: 'PUT'
        request = self.headers(request)

        return urllib2.urlopen(request)

    def post(self, domain, urn, data):
        if self.debug:
            print "POST Request: [%s]" % (
                self.endpoint() +
                ('?domain=' + domain, domain)[self.prettylinks] +
                (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks])
            print urllib.urlencode(data)

        request = urllib2.Request(
            self.endpoint() +
            ('?domain=' + domain, domain)[self.prettylinks] +
            (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks],
            urllib.urlencode(data),
            {'User-Agent': self.USER_AGENT})
        request = self.headers(request)

        return urllib2.urlopen(request)

    def get(self, domain, urn='', args={}):
        if self.debug:
            print "GET Request: [%s%s%s%s]" % (
                self.endpoint(),
                ('?domain=' + domain, domain)[self.prettylinks],
                (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks],
                ('&' + urllib.urlencode(args), '')[not args])

        request = urllib2.Request(
            "%s%s%s%s" % (
                self.endpoint(),
                ('?domain=' + domain, domain)[self.prettylinks],
                (('', '&urn=' + urn)[urn != ''], ('/?', '/' + urn + '?')[urn != ''])[self.prettylinks],
                ('&' + urllib.urlencode(args), '')[not args]))

        request.add_header('User-Agent', self.USER_AGENT)
        request = self.headers(request)

        return urllib2.urlopen(request)


class AOSAPI(object):
    ENC_JSON = "json"
    ENC_XML = "xml"
    # Switch these two to make the other the default consumer encoding scheme
    ENC_DEFAULT = ENC_XML
    ENC_ALT = ENC_JSON

    def __init__(self, connection):
        self.connection = connection
        self.cruft = re.compile('<!--.+?-->[\n]{0,1}')
        self.ws_diag = 200

    def login(self):
        result = self.query('auth', '', {'username': self.connection.username, 'password': self.connection.password})
        # Bad result? Let me stop you right there...
        if not self.success():
            raise AOSException(result['result']['error'])

    def logout(self):
        if self.connection.linger > 0:
            if self.connection.debug:
                print "Lingering for %d seconds" % int(self.connection.linger)
            sleep(float(self.connection.linger))
        self.query('auth')

    def query(self, domain, urn='', args={}):
        result = self.connection.get(domain, urn, args)
        try:
            obj = self.decode_type(result.info(), result.read())
        except ValueError:
            print "Error decoding [%s]" % result.read()
            raise
        return obj

    def post(self, domain, urn='', args={}):
        result = self.connection.post(domain, urn, args)
        try:
            obj = self.decode_type(result.info(), result.read())
        except ValueError:
            print "Error decoding [%s]" % result.read()
            raise
        return obj

    def put(self, domain, urn='', args={}):
        result = self.connection.put(domain, urn, args)
        try:
            obj = self.decode_type(result.info(), result.read())
        except ValueError:
            print "Error decoding [%s]" % result.read()
            raise
        return obj

    def delete(self, domain, urn='', args={}):
        result = self.connection.delete(domain, urn, args)
        try:
            obj = self.decode_type(result.info(), result.read())
        except ValueError:
            print "Error decoding [%s]" % result.read()
            raise
        return obj

    # UTIL
    def store_ws_diag(self, ws_diag):
        if isinstance(ws_diag, (str, unicode)):
            self.ws_diag = int(ws_diag)
        else:
            self.ws_diag = ws_diag

    def diag(self):
        return self.ws_diag

    # Various 20x
    def success(self):
        return self.ws_diag == 200

    def decode_type(self, info, data):
        if self.connection.debug:
            print('Raw Response: '),
            pprint(data)
        clean_data = self.cruft.sub('', data)
        # Be strict when you write,
        # forgiving when you read:
        # If *someone* killed our content-type header,
        # assume latest version, XML-encoded.
        enc_type = info.gettype().replace('application/vnd.alcatellucentaos+', '')
        if enc_type not in [AOSAPI.ENC_ALT, AOSAPI.ENC_DEFAULT]:
            enc_type = AOSAPI.ENC_DEFAULT
        if enc_type == AOSAPI.ENC_XML:
            dom = parseString(clean_data)
            decoded = AOSXMLDecoder(dom.getElementsByTagName("result")[0])
        else:
            decoded = json.loads(clean_data)

        if (decoded.get('result') is not None and type(decoded['result']) is not str
                and decoded['result']['diag'] is not None):
            self.store_ws_diag(decoded['result']['diag'])
        return decoded


class WSConsumer(object):

    API_VERSION = '1.0'

    def __init__(self, config, argv):
        if len(argv) < 3:
            self.usage("A consumer needs two arguments or more.")
        else:
            self.config = config

            self.config['api'] = self.API_VERSION

            if self.config.get('secure') is None:
                self.config['secure'] = True
            if self.config.get('obeyproxy') is None:
                self.config['obeyproxy'] = True
            if self.config.get('prettylinks') is None:
                self.config['prettylinks'] = True
            if self.config.get(AOSAPI.ENC_ALT) is None:
                self.config[AOSAPI.ENC_ALT] = False
            if self.config.get('linger') is None:
                self.config['linger'] = 0
            if self.config.get('debug') is None:
                self.config['debug'] = False
            try:
                {"mib": self.mibquery,
                 "cli": self.cliquery,
                 "onetouch": self.otquery,
                 "push": self.pushquery,
                 "file": self.batchfile}[argv[1]](argv[2:])
            except KeyError, e:
                print e
                self.usage()
            except AOSException, e:
                print e

    def usage(self, msg=None):
        if msg is not None:
            print "\n%s" % msg

        print "\nArguments: <mib|cli|onetouch|file|push> <arguments>"
        print "           mib <tablename> <col1> <col2...>"
        print "           mib <scalar>"
        print "           cli \"<command line>\""
        print "           onetouch <tablename> <...>"
        print "           file <filename>"
        print "           push <filename>"
        print ""
        print "Options:   [-s|--server <server host/ip>]"
        print "           [-u|--username <user name>]"
        print "           [-p|--password <user password>]"
        print "           [--startindex <start mib query index>]"
        print "           [--limit <max number of rows returned>]"
        print "           [--vrf <vrf name>]"
        print "           [--noproxy]"
        print "           [--noprettylinks]"
        print "           [--nossl]"
        print "           [--port <port number>]"
        print "           [--sim]"
        print "           [--linger <duration in seconds>]"
        print "           [--debug]"
        # print "           [--scalar]"
        print "           [--modify]"
        print "           [--create]"
        print "           [--delete]"
        print "           [--info]"
        print "           [--%s]" % AOSAPI.ENC_ALT
        print ""
        print "OneTouch:"
        print "           vlan"
        print "           vlan <number> \"<description>\" --create"
        print "           vlan <number> <variable> <new value> --modify"
        print "           vlan <number> --delete"
        print "           interface"
        print "           interface \"<name>\" <ip address> <net mask> <vlan id> --create"
        print "           interface <number> <variable> <new value> --modify"
        print "           interface \"<name>\" --delete"
        print "           assign"
        print "           assign <c/s/p> <vlan id> tagged|untagged --create"
        print "           assign <c/s/p> <vlan id> --delete"
        print "           speed"
        print "           speed <c/s/p> auto|10|100|1000|max100|max1000 auto|half|full --modify"
        print "           linkagg"
        print "           linkagg <agg number> \"<name>\" <size> static\n                   " \
              "source-mac|destination-mac|source+destination-mac|\n                   " \
              "sourcee-ip|destination-ip|source+destination-ip|\n                   " \
              "tunnel-protocol enable|disable --create"
        print "           linkagg <agg number> \"<name>\" <size> LACP\n                   " \
              "source-mac|destination-mac|source+destination-mac|\n                   " \
              "sourcee-ip|destination-ip|source+destination-ip|\n                   " \
              "tunnel-protocol enable|disable\n                   " \
              "<actor admin key> <actor system priority> <actor system id>\n                   " \
              "<partner admin key> <partner system priority> <partner system id> --create"
        print "           linkagg <number> <variable> <new value> --modify"
        print "           linkagg <agg number> --delete"
        print "           portagg"
        print "           portagg <c/s/p> <agg number> --create"
        print "           portagg <c/s/p> --delete"
        print "           traffic"
        print "           status"
        print "           configuration"
        print "Notes:"
        print "            You cannot change vlan type after creation"
        print "            A link aggregation size can be 2/4/8"

    def printerrors(self, diag, errs):
        print "ERROR#%d:" % diag
        if isinstance(errs, (str, unicode)):
            print "- %s" % errs
        else:
            for err in errs:
                if err.isdigit():
                    print "- %s" % errs[err]
                else:
                    print "- %s" % err

    def otquery(self, argv):
        try:
            if self.config.get('modify'):
                {"vlan": self.otpostquery_vlan,
                 "speed": self.otpostquery_speed,
                 "linkagg": self.otpostquery_linkagg,
                 "interface": self.otpostquery_interface}[argv[0]](argv[1:])
            elif self.config.get('create'):
                {"vlan": self.otputquery_vlan,
                 "assign": self.otputquery_assign,
                 "linkagg": self.otputquery_linkagg,
                 "portagg": self.otputquery_portagg,
                 "interface": self.otputquery_interface}[argv[0]](argv[1:])
            elif self.config.get('delete'):
                {"vlan": self.otdeletequery_vlan,
                 "assign": self.otdeletequery_assign,
                 "linkagg": self.otdeletequery_linkagg,
                 "portagg": self.otdeletequery_portagg,
                 "interface": self.otdeletequery_interface}[argv[0]](argv[1:])
            else:
                {"vlan": self.otgetquery_vlan,
                 "assign": self.otgetquery_assign,
                 "speed": self.otgetquery_speed,
                 "linkagg": self.otgetquery_linkagg,
                 "portagg": self.otgetquery_portagg,
                 "traffic": self.otgetquery_traffic,
                 "status": self.otgetquery_status,
                 "configuration": self.otgetquery_configuration,
                 "interface": self.otgetquery_interface}[argv[0]](argv[1:])
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_type == KeyError:
                self.usage("Wrong key. Likely due to wrong onetouch command.")
                traceback.print_tb(exc_traceback, limit=100, file=sys.stdout)
            else:
                if self.config.get('debug'):
                    print "---------------------------------------------------------\n" \
                          "Exception: %s\nTraceback follows:" % exc_value
                    traceback.print_tb(exc_traceback, limit=100, file=sys.stdout)
                    print "---------------------------------------------------------"
                else:
                    raise

    def pushquery(self, argv):
        file_name = argv[0]
        try:
            api = AOSAPI(AOSConnection(self.config['username'], self.config['password'],
                                       self.config['server'], self.config['secure'],
                                       self.config['obeyproxy'], self.config['prettylinks'],
                                       self.config['port'], AOSHeaders(self.config),
                                       self.config['linger'], self.config['debug']))
            api.login()
            print "Authenticated..."

            payload = {'payload': open(file_name, "rb").read()}
            results = api.post('push', file_name, payload)['result']
            if api.diag() == 200:
                print "Success."
            else:
                self.printerrors(api.diag(), results['error'])
            api.logout()
        except urllib2.HTTPError, e:
            api.logout()
            self.printerrors(e.code, e.msg)
        api.logout()

    def batchfile(self, argv):
        re_cliormib = re.compile('(cli|mib[\+|\-|\=]{0,1})\s(.*)')
        dequoter = lambda s: re.sub('^"|"$', '', s)

        api = AOSAPI(AOSConnection(self.config['username'], self.config['password'], self.config['server'],
                                   self.config['secure'], self.config['obeyproxy'],
                                   self.config['prettylinks'], self.config['port'],
                                   AOSHeaders(self.config), self.config['linger'], self.config['debug']))
        api.login()
        print "Authenticated..."

        for line in [raw_line.strip() for raw_line in open(argv[0], 'r')]:
            for action in ('create', 'delete', 'modify'):
                if self.config.get(action):
                    del self.config[action]
            if self.config.get('debug'):
                print "Line: [%s]" % line
            matches = re_cliormib.match(line)
            if matches:
                if matches.group(1) == 'cli':
                    self.cliquery([dequoter(matches.group(2))], api)
                elif matches.group(1)[:3] == 'mib':
                    if matches.group(1)[-1] == '+':
                        self.config['create'] = True
                    elif matches.group(1)[-1] == '-':
                        self.config['delete'] = True
                    elif matches.group(1)[-1] == '=':
                        self.config['modify'] = True
                    self.mibquery(matches.group(2).split(), api)
            if not api.success():
                if self.config.get('debug'):
                    print "Interrupting batch execution due to error detected."
                break

        api.logout()

    # ONETOUCH VLANS #
    def otdeletequery_vlan(self, argv):
        self.mibdeletequery(['vlanTable', 'vlanNumber:' + argv[0]])

    def otpostquery_vlan(self, argv):
        self.mibpostquery(['vlanTable', 'vlanNumber:' + argv[0], argv[1] + ':' + self.pack(argv[1], argv[2])])

    def otputquery_vlan(self, argv):
        self.mibputquery(['vlanTable', 'vlanNumber:' + argv[0],
                          'vlanDescription:' + argv[1], 'vlanAdmStatus:1', 'vlanType:5'])

    def otgetquery_vlan(self):
        self.mibgetquery(['vlanTable', 'vlanNumber', 'vlanDescription', 'vlanAdmStatus', 'vlanOperStatus',
                          'vlanRouterStatus', 'vlanSrcLearningStatus', 'vlanType', 'vlanMtu'])

    # ONETOUCH PORT ASSOCIATION #
    def otdeletequery_assign(self, argv):
        parts = argv[0].split('/')
        ifindex = str((int(parts[0]) - 1) * 100000 + int(parts[1]) * 1000 + int(parts[2]))
        self.mibdeletequery(['vpaTable', 'vpaIfIndex:' + ifindex, 'vpaVlanNumber:' + argv[1]])

    def otputquery_assign(self, argv):
        self.mibputquery(['vpaTable',
                          'vpaIfIndex:' + self.pack('vpaIfIndex', argv[0]),
                          'vpaVlanNumber:' + argv[1],
                          'vpaType:' + self.pack('vpaType', argv[2])])

    def otgetquery_assign(self):
        self.mibgetquery(['vpaTable', 'vpaIfIndex', 'vpaVlanNumber', 'vpaType'],
                         None, self.beautify)

    # ONETOUCH PORT CONFIGURATION #
    def otgetquery_speed(self):
        self.mibgetquery(['esmConfTable', 'ifIndex', 'esmPortAdminStatus',
                          'esmPortAutoSpeed', 'esmPortAutoDuplexMode',
                          'esmPortCfgSpeed', 'esmPortCfgDuplexMode'],
                         None, self.beautify)

    def otpostquery_speed(self, argv):
        self.mibpostquery(['esmConfTable',
                           'ifIndex:' + self.pack('ifIndex', argv[0]),
                           'esmPortCfgSpeed:' + self.pack('esmPortCfgSpeed', argv[1]),
                           'esmPortCfgDuplexMode:' + self.pack('esmPortCfgDuplexMode', argv[2])])

    # ONETOUCH LINK AGGREGATION #
    def otgetquery_linkagg(self):
        self.mibgetquery(['alclnkaggAggTable', 'alclnkaggAggIndex', 'alclnkaggAggNumber', 'alclnkaggAggLacpType',
                          'alclnkaggAggSize', 'alclnkaggAggPortSelectionHash', 'alclnkaggAggAdminState',
                          'alclnkaggAggName', 'alclnkaggAggOperState', 'alclnkaggAggNbrSelectedPorts',
                          'alclnkaggAggNbrAttachedPorts', 'alclnkaggAggPrimaryPortIndex'],
                         None, self.beautify)

    def otputquery_linkagg(self, argv):
        lacp_type = self.pack('alclnkaggAggLacpType', argv[3])
        if int(lacp_type) == 1:  # 'LACP'
            extra = ['alclnkaggAggActorAdminKey:' + argv[6],
                     'alclnkaggAggActorSystemPriority:' + argv[7],
                     'alclnkaggAggActorSystemID:' + argv[8],
                     'alclnkaggAggPartnerAdminKey:' + argv[9],
                     'alclnkaggAggPartnerSystemPriority:' + argv[10],
                     'alclnkaggAggPartnerSystemID:' + argv[11]]
        else:
            extra = []

        coll = ['alclnkaggAggTable',
                'alclnkaggAggIndex:' + self.pack('alclnkaggAggIndex', argv[0]),
                'alclnkaggAggName:' + argv[1],
                'alclnkaggAggSize:' + str(argv[2]),
                'alclnkaggAggLacpType:' + lacp_type,
                'alclnkaggAggMcLagType:0',
                'alclnkaggAggPortSelectionHash:' + self.pack('alclnkaggAggPortSelectionHash', argv[4]),
                'alclnkaggAggAdminState:' + self.pack('alclnkaggAggAdminState', argv[5])] + extra

        self.mibputquery(coll)

    def otpostquery_linkagg(self, argv):
        self.mibpostquery(['alclnkaggAggTable',
                           'alclnkaggAggIndex:' + self.pack('alclnkaggAggIndex', argv[0]),
                           argv[1] + ':' + self.pack(argv[1], argv[2])])

    def otdeletequery_linkagg(self, argv):
        self.mibdeletequery(['alclnkaggAggTable',
                             'alclnkaggAggIndex:' + self.pack('alclnkaggAggIndex', argv[0])])

    # ONETOUCH PORT/LINK AGGREGATION #
    def otgetquery_portagg(self):
        self.mibgetquery(['alclnkaggAggPortTable', 'alclnkaggAggPortIndex', 'alclnkaggAggPortSelectedAggNumber',
                          'alclnkaggAggPortOperState', 'alclnkaggAggPortState',
                          'alclnkaggAggPortLinkState', 'alclnkaggAggPortPrimary'],
                         None, self.beautify)

    def otputquery_portagg(self, argv):
        self.mibputquery(['alclnkaggAggPortTable',
                          'alclnkaggAggPortIndex:' + self.pack('alclnkaggAggPortIndex', argv[0]),
                          'alclnkaggAggPortSelectedAggNumber:' + argv[1],
                          'alclnkaggAggPortLacpType:0'])

    def otdeletequery_portagg(self, argv):
        self.mibdeletequery(['alclnkaggAggPortTable',
                             'alclnkaggAggPortIndex:' + self.pack('alclnkaggAggPortIndex', argv[0])])

    # ONETOUCH STATISTICS: TRAFFIC #
    def otgetquery_traffic(self):
        self.mibgetquery(['ifXTable', 'ifIndex', 'ifHCInOctets', 'ifHCInUcastPkts', 'ifHCInMulticastPkts',
                          'ifHCInBroadcastPkts', 'ifHCOutOctets', 'ifHCOutUcastPkts', 'ifHCOutMulticastPkts',
                          'ifHCOutBroadcastPkts'], None, self.beautify)

    # ONETOUCH IP INTERFACES #
    def otdeletequery_interface(self, argv):
        self.mibdeletequery(['alaIpItfConfigTable', 'alaIpItfConfigName:' + argv[0]])

    def otpostquery_interface(self, argv):
        self.mibpostquery(['alaIpInterfaceTable', 'ifIndex:' + argv[0], argv[1] + ':' + argv[2]])

    def otputquery_interface(self, argv):
        try:
            api = AOSAPI(AOSConnection(self.config['username'], self.config['password'], self.config['server'],
                                       self.config['secure'], self.config['obeyproxy'],
                                       self.config['prettylinks'], self.config['port'],
                                       AOSHeaders(self.config), self.config['linger'], self.config['debug']))
            api.login()
            print "Authenticated..."
            # 1- Create interface
            results = api.put('mib', 'alaIpItfConfigTable',
                              {'mibObject0': 'alaIpItfConfigIfIndex:0',
                               'mibObject1': 'alaIpItfConfigName:' + argv[0]})['result']
            if api.diag() == 200:
                # 2- Retrieve new index
                results = api.query('mib', 'alaIpItfConfigTable',
                                    {'mibObject0': 'alaIpItfConfigName',
                                     'mibObject1': 'alaIpItfConfigIfIndex'})['result']
                if api.diag() == 200:
                    oid = filter(lambda k: results['data']['rows'][k]['alaIpItfConfigName'] == argv[0],
                                 results['data']['rows'])
                    if len(oid) == 1:
                        idx = results['data']['rows'][oid[0]]['alaIpItfConfigIfIndex']
                        # 3- Use index to update with other arguments
                        # alaIpInterfaceAddress | alaIpInterfaceMask
                        results = api.post('mib', 'alaIpInterfaceTable',
                                           {'mibObject0': 'ifIndex:' + idx,
                                            'mibObject1': 'alaIpInterfaceAddress:' + argv[1],
                                            'mibObject2': 'alaIpInterfaceMask:' + argv[2],
                                            'mibObject3': 'alaIpInterfaceVlanID:' + argv[3]})['result']
                        if api.diag() != 200:
                            self.printerrors(api.diag(), results['error'])
                        else:
                            print "Success."
            else:
                self.printerrors(api.diag(), results['error'])
            api.logout()
        except urllib2.HTTPError, e:
            api.logout()
            self.printerrors(e.code, e.msg)

    def otgetquery_interface(self):
        self.mibgetquery(['alaIpInterfaceTable', 'ifIndex', 'alaIpInterfaceName',
                          'alaIpInterfaceAddress', 'alaIpInterfaceMask', 'alaIpInterfaceVlanID'])

    # ONETOUCH DEVICE STATUS #
    # snmpwalk -Os -M snmp/mibs -m all -CI -c public -v 1 192.168.4.1 chasChassisTable
    # do not forget to run sim as: ./simulation.rb OS10K cfra A B 2 C48 4 X32
    def otgetquery_status(self):
        try:
            api = AOSAPI(AOSConnection(self.config['username'], self.config['password'],
                                       self.config['server'], self.config['secure'],
                                       self.config['obeyproxy'], self.config['prettylinks'],
                                       self.config['port'], AOSHeaders(self.config),
                                       self.config['linger'], self.config['debug']))
            api.login()
            print "Authenticated..."
            chas_results = api.query('mib', 'chasChassisTable',
                                     {'mibObject0': 'chasPrimaryPhysicalIndex'})['result']
            if api.diag() == 200:
                primary_chassis = '65'
                for row in chas_results['data']['rows'].values():
                    primary_chassis = str(row['chasPrimaryPhysicalIndex'])
                sync_results = api.query('mib', 'chasControlModuleTable',
                                         {'mibObject0': 'chasControlCertifyStatus',
                                          'mibObject1': 'chasControlSynchronizationStatus',
                                          'startIndex': primary_chassis, 'limit': '1'})['result']
                if api.diag() == 200:
                    sync_certify = self.beautify('chasControlCertifyStatus',
                                                 sync_results['data']['rows']
                                                 [primary_chassis]['chasControlCertifyStatus'])
                    sync_syncd = self.beautify('chasControlSynchronizationStatus',
                                               sync_results['data']['rows']
                                               [primary_chassis]['chasControlSynchronizationStatus'])
                else:
                    sync_certify = 'unknown'
                    sync_syncd = 'unknown'
                health_results = api.query('mib', 'healthModuleTable',
                                           {'mibObject0': 'healthModuleSlot', 'mibObject1': 'healthModuleCpu1MinAvg',
                                            'mibObject2': 'healthModuleCpu1HrAvg',
                                            'mibObject3': 'healthModuleCpu1DayAvg',
                                            'mibObject4': 'healthModuleMemory1MinAvg',
                                            'mibObject5': 'healthModuleMemory1HrAvg',
                                            'mibObject6': 'healthModuleMemory1DayAvg'})['result']
                if api.diag() == 200:
                    phys_results = api.query('mib', 'chasEntPhysicalTable',
                                             {'mibObject0': 'chasEntPhysAdminStatus',
                                              'mibObject1': 'chasEntPhysOperStatus',
                                              'mibObject2': 'chasEntPhysModuleType',
                                              'mibObject3': 'chasEntPhysUbootRev'})['result']
                    if api.diag() == 200:
                        print "Active CMM (%s)\n--------------" % chr(int(primary_chassis))
                        if phys_results['data']['rows'].get(primary_chassis) is not None:
                            print "Admin: [%s] Operational: [%s] Config: [%s] Redundancy: [%s]" % (
                                self.beautify('chasEntPhysAdminStatus',
                                              phys_results['data']['rows'][primary_chassis]['chasEntPhysAdminStatus']),
                                self.beautify('chasEntPhysOperStatus',
                                              phys_results['data']['rows'][primary_chassis]['chasEntPhysOperStatus']),
                                sync_certify,
                                sync_syncd)

                        # seems like this table, when only 1 CMM is present, is just empty.
                        if isinstance(health_results['data'], dict):
                            if isinstance(health_results['data']['rows'], list):
                                typed_idx = 0
                            else:
                                typed_idx = '0'
                            try:
                                print "CPU: %s%% (1 min), %s%% (1 hr), %s%% (1 day)" % (
                                    health_results['data']['rows'][typed_idx]['healthModuleCpu1MinAvg'],
                                    health_results['data']['rows'][typed_idx]['healthModuleCpu1HrAvg'],
                                    health_results['data']['rows'][typed_idx]['healthModuleCpu1DayAvg'])
                                print "RAM: %s%% (1 min), %s%% (1 hr), %s%% (1 day)" % (
                                    health_results['data']['rows'][typed_idx]['healthModuleMemory1MinAvg'],
                                    health_results['data']['rows'][typed_idx]['healthModuleMemory1HrAvg'],
                                    health_results['data']['rows'][typed_idx]['healthModuleMemory1DayAvg'])
                            except KeyError:
                                pass

                        for ni_ctr in range(1, 16):
                            ni_str = str(ni_ctr)
                            if isinstance(health_results['data'], dict):
                                health_result = None
                                try:
                                    if (isinstance(health_results['data']['rows'], dict) and
                                            health_results['data']['rows'].get(ni_str) is not None):
                                        health_result = health_results['data']['rows'][ni_str]
                                    elif (isinstance(health_results['data']['rows'], list) and
                                            health_results['data']['rows'][ni_ctr]):
                                        health_result = health_results['data']['rows'][ni_ctr]
                                except Exception:
                                    pass
                                if health_result is not None:
                                    print "\nNI #%s\n------" % ni_str
                                    if phys_results['data']['rows'].get(ni_str) is not None:
                                        print "UBoot: %s Admin: [%s] Operational: [%s]" % (
                                            phys_results['data']['rows'][ni_str]['chasEntPhysUbootRev'],
                                            self.beautify('chasEntPhysAdminStatus',
                                                          phys_results['data']['rows']
                                                          [ni_str]['chasEntPhysAdminStatus']),
                                            self.beautify('chasEntPhysOperStatus',
                                                          phys_results['data']['rows']
                                                          [ni_str]['chasEntPhysOperStatus']))
                                    print "CPU: %s%% (1 min), %s%% (1 hr), %s%% (1 day)" % (
                                        health_result['healthModuleCpu1MinAvg'],
                                        health_result['healthModuleCpu1HrAvg'],
                                        health_result['healthModuleCpu1DayAvg'])
                                    print "RAM: %s%% (1 min), %s%% (1 hr), %s%% (1 day)" % (
                                        health_result['healthModuleMemory1MinAvg'],
                                        health_result['healthModuleMemory1HrAvg'],
                                        health_result['healthModuleMemory1DayAvg'])
                    else:
                        self.printerrors(api.diag(), phys_results['error'])
                else:
                    self.printerrors(api.diag(), health_results['error'])
            else:
                self.printerrors(api.diag(), chas_results['error'])
            api.logout()
        except urllib2.HTTPError, e:
            api.logout()
            self.printerrors(e.code, e.msg)

    # ONETOUCH DEVICE CONFIGURATION #
    def otgetquery_configuration(self):
        try:
            self.cliquery(["show configuration snapshot"])
        except urllib2.HTTPError, e:
            self.printerrors(e.code, e.msg)

    def mibquery(self, argv, api=None):
        try:
            if self.config.get('modify'):
                self.mibpostquery(argv, api)
            elif self.config.get('create'):
                self.mibputquery(argv, api)
            elif self.config.get('delete'):
                self.mibdeletequery(argv, api)
            else:
                self.mibgetquery(argv, api)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if self.config.get('debug'):
                print "---------------------------------------------------------\n" \
                      "Exception: %s\nTraceback follows:" % exc_value
                traceback.print_tb(exc_traceback, limit=100, file=sys.stdout)
                print "---------------------------------------------------------"
            else:
                raise

    def mibputquery(self, argv, api=None):
        managed_api = (api is not None)
        items = dict([('mibObject' + str(i - 1), argv[i]) for i in range(1, len(argv))])
        mib_table = argv[0]
        try:
            if not managed_api:
                api = AOSAPI(AOSConnection(self.config['username'], self.config['password'],
                                           self.config['server'],
                                           self.config['secure'], self.config['obeyproxy'],
                                           self.config['prettylinks'], self.config['port'],
                                           AOSHeaders(self.config), self.config['linger'], self.config['debug']))
                api.login()
                print "Authenticated..."
            results = api.put('mib', mib_table, items)['result']
            if api.diag() == 200:
                print "Success."
            else:
                self.printerrors(api.diag(), results['error'])
            if not managed_api:
                api.logout()
        except urllib2.HTTPError, e:
            if not managed_api:
                api.logout()
            self.printerrors(e.code, e.msg)

    def mibdeletequery(self, argv, api=None):
        managed_api = (api is not None)
        items = dict([('mibObject' + str(i - 1), argv[i]) for i in range(1, len(argv))])
        mib_table = argv[0]
        try:
            if not managed_api:
                api = AOSAPI(AOSConnection(self.config['username'], self.config['password'], self.config['server'],
                                           self.config['secure'], self.config['obeyproxy'],
                                           self.config['prettylinks'], self.config['port'],
                                           AOSHeaders(self.config), self.config['linger'], self.config['debug']))
                api.login()
                print "Authenticated..."
            results = api.delete('mib', mib_table, items)['result']
            if api.diag() == 200:
                print "Success."
            else:
                self.printerrors(api.diag(), results['error'])
            if not managed_api:
                api.logout()
        except urllib2.HTTPError, e:
            if not managed_api:
                api.logout()
            self.printerrors(e.code, e.msg)

    def mibpostquery(self, argv, api=None):
        managed_api = (api is not None)
        items = dict([('mibObject' + str(i - 1), argv[i]) for i in range(1, len(argv))])
        mib_table = argv[0]
        try:
            if not managed_api:
                api = AOSAPI(AOSConnection(self.config['username'], self.config['password'], self.config['server'],
                                           self.config['secure'], self.config['obeyproxy'],
                                           self.config['prettylinks'], self.config['port'],
                                           AOSHeaders(self.config), self.config['linger'], self.config['debug']))
                api.login()
                print "Authenticated..."
            results = api.post('mib', mib_table, items)['result']
            if api.diag() == 200:
                print "Success."
            else:
                self.printerrors(api.diag(), results['error'])
            if not managed_api:
                api.logout()
        except urllib2.HTTPError, e:
            if not managed_api:
                api.logout()
            self.printerrors(e.code, e.msg)

    def mibgetquery(self, argv, api=None, callback=None):
        managed_api = (api is not None)
        items = dict([('mibObject' + str(i - 1), argv[i]) for i in range(1, len(argv))])
        mib_table = argv[0]

        if self.config.get('startindex'):
            items['startIndex'] = self.config['startindex']
        if self.config.get('limit'):
            items['limit'] = self.config['limit']

        domain = ('mib', 'info')[self.config.get('info') is True]

        try:
            if not managed_api:
                api = AOSAPI(AOSConnection(self.config['username'], self.config['password'],
                                           self.config['server'],
                                           self.config['secure'], self.config['obeyproxy'],
                                           self.config['prettylinks'], self.config['port'],
                                           AOSHeaders(self.config), self.config['linger'], self.config['debug']))
                api.login()
                print "Authenticated..."
            results = api.query(domain, mib_table, items)['result']
            if api.diag() == 200:
                if results['domain'] == 'info':
                    print "           Object: %s" % results['data']['table']
                    print "             Type: %s" % results['data']['type']
                    if results['data'].get('rowstatus'):
                        print "row status column: %s" % results['data']['rowstatus']
                    if results['data'].get('firstobject'):
                        print "  first non index: %s" % results['data']['firstobject']
                elif len(results['data']) == 0:
                    print "No results."
                else:
                    # todo check result instead
                    if len(items) == 0 or items.get('scalar'):
                        print "\nDisplaying value:\n-----------------------------------------"
                        for k, v in results['data']['rows'].iteritems():
                                print k + ': ' + v
                        print "-----------------------------------------"
                    else:
                        if pretty_tables:
                            table = PrettyTable(list(self.lname(clean_names) for clean_names in sorted(
                                [items[colname] for colname in items if colname[:9] == 'mibObject'])))
                            table.align = 'r'
                            for idx in results['data']['rows']:
                                if callback is None:
                                    table.add_row([v for k, v in sorted(results['data']['rows'][idx].items())])
                                else:
                                    table.add_row([callback(k, v) for k, v in sorted(results['data']['rows'][idx].items())])
                            print table
                        else:
                            print "\nListing objects:\n-----------------------------------------"
                            for idx in results['data']['rows']:
                                for k, v in results['data']['rows'][idx].iteritems():
                                    print k + ': ' + v,
                                print
                            print "-----------------------------------------"
            else:
                self.printerrors(api.diag(), results['error'])
            if not managed_api:
                api.logout()
        except urllib2.HTTPError, e:
            if not managed_api:
                api.logout()
            self.printerrors(e.code, e.msg)

    def cliquery(self, argv, api=None):
        if len(argv) > 1:
            self.usage("Too many arguments for CLI domain.")
        else:
            managed_api = (api is not None)
            try:
                if not managed_api:
                    api = AOSAPI(AOSConnection(self.config['username'], self.config['password'],
                                               self.config['server'], self.config['secure'],
                                               self.config['obeyproxy'], self.config['prettylinks'],
                                               self.config['port'], AOSHeaders(self.config),
                                               self.config['linger'], self.config['debug']))
                    api.login()
                    print "Authenticated..."
                items = {'cmd': argv[0]}
                results = api.query('cli', 'aos', items)['result']
                if api.diag() == 200:
                    print "Command \"%s\": Success\n%s" % (results['cmd'], results['output'])
                else:
                    self.printerrors(api.diag(), results['error'])
                if not managed_api:
                    api.logout()
            except urllib2.HTTPError, e:
                if not managed_api:
                    api.logout()
                self.printerrors(e.code, e.msg)

    # UTILS #
    def beautify(self, name, value):
        if self.config.get('debug'):
            beautified = value
        elif name in ['ifIndex', 'vpaIfIndex', 'alclnkaggAggPortIndex']:
            beautified = (str(int(value) / 100000 + 1) + '/'
                          + str(int(value) % 100000 / 1000)
                          + '/' + str(int(value) % 100000 % 1000))
        elif name in ['esmPortAdminStatus', 'alclnkaggAggAdminState']:
            beautified = ('unknown', 'enabled', 'disabled')[int(value)]
        elif name in ['alclnkaggAggPortLinkState']:
            beautified = ('unknown', 'up', 'down')[int(value)]
        elif name in ['alclnkaggAggPortState']:
            beautified = ('unknown', 'created', 'configurable',
                          'configured', 'selected', 'reserved', 'attached')[int(value)]
        elif name in ['alclnkaggAggPortOperState']:
            beautified = ('unknown', 'up', 'down', 'not attached', 'not aggregable')[int(value)]
        elif name in ['esmPortAutoSpeed', 'esmPortCfgSpeed']:
            beautified = ('unknown', '100', '10', 'auto',
                          'unknown', '1000', '10000', '40000',
                          'max 100', 'max 1000')[int(value)]
        elif name in ['esmPortAutoDuplexMode', 'esmPortCfgDuplexMode']:
            beautified = ('unknown', 'full', 'half', 'auto', 'unknown')[int(value)]
        elif name in ['vpaType']:
            beautified = ('invalid', 'cfgDefault', 'qTagged',
                          'dynamic', 'vstkDoubleTag', 'vstkTranslate', 'forbidden')[int(value)]
        elif name in ['alclnkaggAggLacpType']:
            beautified = ('static', 'LACP')[int(value)]
        elif name in ['alclnkaggAggPortSelectionHash']:
            beautified = ('?', 'source mac', 'destination mac', 'source+destination mac', 'source ip', 'destination ip',
                          'source+destination ip', 'tunnel protocol')[int(value)]
        elif name in ['chasEntPhysAdminStatus']:
            beautified = ('unknown', 'unknown', 'no power', 'powered up', 'reset', 'secondary takeover',
                          'reset whole switch', 'standby', 'reset with fabric', 'take over with fabric',
                          'VC takeover', 'reset whole VC')[int(value)]
        elif name in ['chasEntPhysOperStatus']:
            beautified = ('unknown', 'powered up', 'down', 'testing', 'unknown',
                          'secondary', 'not present', 'down', 'master', 'idle', 'power save')[int(value)]
        elif name in ['chasControlCertifyStatus']:
            beautified = ('unknown', 'unknown', 'need certify', 'certified')[int(value)]
        elif name in ['chasControlSynchronizationStatus']:
            beautified = ('unknown', 'unknown', 'only module', 'not synchronized', 'synchronized')[int(value)]
        else:
            beautified = value
        return beautified

    def pack(self, name, value):
        if name in ['ifIndex', 'vpaIfIndex', 'alclnkaggAggPortIndex']:
            parts = value.split('/')
            packed = str((int(parts[0]) - 1) * 100000 + int(parts[1]) * 1000 + int(parts[2]))
        elif name in ['alclnkaggAggIndex']:
            packed = str(40000000 + int(value))
        elif name in ['alclnkaggAggAdminState']:
            packed = str({'enable': 1, 'disable': 2}[value])
        elif name in ['vpaType']:
            packed = ('1', '2')[value == 'tagged']
        elif name in ['esmPortCfgSpeed']:
            packed = str({'auto': 3, '10': 2, '100': 1, '1000': 5, 'max100': 8, 'max1000': 9}[value])
        elif name in ['esmPortAutoDuplexMode', 'esmPortCfgDuplexMode']:
            packed = str({'auto': 3, 'half': 2, 'full': 1}[value])
        elif name in ['alclnkaggAggLacpType']:
            packed = str({'static': 0, 'LACP': 1}[value])
        elif name in ['alclnkaggAggPortSelectionHash']:
            packed = str({'source-mac': 1, 'destination-mac': 2, 'source+destination-mac': 3,
                          'source-ip': 4, 'destination-ip': 5, 'source+destination-ip': 6, 'tunnel-protocol': 7}[value])
        else:
            packed = value
        return packed

    def lname(self, src_name):
        if self.config.get('debug'):
            return src_name
        else:
            return ' '.join(re.sub('([a-z0-9])([A-Z])', r'\1 \2', src_name).split()[-2:])


if __name__ == "__main__":
    config = {'username': 'admin', 'password': 'switch', 'server': '192.168.1.1', 'port': '-1'}
    try:
        opts, args = getopt.gnu_getopt(sys.argv, 'u:p:s:',
                                       ['username=', 'password=', 'server=', 'startindex=', 'limit=',
                                        'vrf=', 'modify', 'create', 'delete', 'info', AOSAPI.ENC_ALT,
                                        'noproxy', 'noprettylinks', 'port=', 'nossl', 'sim', 'linger=', 'debug'])
    except getopt.GetoptError, err:
        print str(err)
        WSConsumer([], [])
        sys.exit(1)

    hasMIBArg = False

    for o, v in opts:
        if o in ('-u', '--username'):
            config['username'] = v
        elif o in ('-p', '--password'):
            config['password'] = v
        elif o in ('-s', '--server'):
            config['server'] = v
        elif o == '--startindex':
            hasMIBArg = True
            config['startindex'] = v
        elif o == '--limit':
            hasMIBArg = True
            config['limit'] = v
        elif o == '--vrf':
            hasMIBArg = True
            config['vrf'] = v
        # elif o == '--scalar':
            # hasMIBArg = True
            # config['scalar'] = True
        elif o == '--modify':
            hasMIBArg = True
            config['modify'] = True
        elif o == '--create':
            hasMIBArg = True
            config['create'] = True
        elif o == '--delete':
            hasMIBArg = True
            config['delete'] = True
        elif o == '--info':
            hasMIBArg = True
            config['info'] = True
        elif o == '--%s' % AOSAPI.ENC_ALT:
            config[AOSAPI.ENC_ALT] = True
        elif o == '--noproxy':
            config['obeyproxy'] = False
        elif o == '--noprettylinks':
            config['prettylinks'] = False
        elif o == '--port':
            config['port'] = v
        elif o == '--nossl':
            config['secure'] = False
        elif o == '--sim':
            config['server'] = '127.0.0.1'
            config['port'] = '5000'
            config['secure'] = False
            config['obeyproxy'] = False
        elif o == '--linger':
            config['linger'] = v
        elif o == '--debug':
            config['debug'] = True

    if len(args) > 1 and args[1] == 'cli' and hasMIBArg:
        print "Wrong options for cli method."
        WSConsumer([], [])
        sys.exit(1)

    c = WSConsumer(config, args)
