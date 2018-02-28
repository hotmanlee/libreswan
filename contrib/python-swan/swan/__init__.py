# -*- coding: utf-8 -*-

"""Random functions for Libreswan."""

from __future__ import print_function
from __future__ import unicode_literals
import socket
import subprocess
import sys
try:
    import ipaddress
except ImportError:
    sys.exit('Please install https://pypi.python.org/pypi/ipaddress')


def run_command(params):
    """Run command and return it's output"""
    try:
        output = subprocess.check_output(params, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return ''
    return output.decode('utf-8', 'ignore')


def is_encrypted(destination, port=None, source=None, timeout=1.0,
                 debug=False):
    """Is connection encrypted?
    Returns True/False or raises ValueError
    """
    # Parse destination, autodetect source if not specified
    destination = ipaddress.ip_address(unicode(destination))
    if not source:
        output = run_command([
            '/sbin/ip', '-oneline', 'route', 'get', unicode(destination)])
        try:
            source = output.split(' src ')[1].split()[0]
        except IndexError:
            raise ValueError('failed to detect source IP')
    source = ipaddress.ip_address(unicode(source))
    if debug:
        print('Checking {} to {} port {}'.format(source, destination, port))

    # Connect to port if specified, ignore errors
    if port:
        try:
            sock = socket.create_connection(
                (unicode(destination), port),
                timeout,
                (unicode(source), 0))
            sock.close()
        except socket.error as error:
            if debug:
                print('Connection error: {}'.format(error))

    # Get "ip xfrm" output
    output = run_command(['/sbin/ip', '-oneline', 'xfrm', 'policy', 'list'])

    # Parse output
    encrypted = False
    priority = 65536
    for line in output.splitlines():
        # Parse single line
        parsed = {
            'src': None,
            'dst': None,
            'dir': None,
            'priority': None,
            'proto': None,
            'reqid': None,
        }
        keyword = None
        for item in line.replace('\\', ' ').split():
            if item in parsed and not parsed[item]:
                keyword = item
            elif keyword:
                parsed[keyword] = item
                keyword = None

        # Is it our line?
        if not (
                parsed['dir'] == 'out' and
                source in ipaddress.ip_network(parsed['src']) and
                destination in ipaddress.ip_network(parsed['dst']) and
                priority > int(parsed['priority'])
        ):
            continue

        # It is, update priority/encrypted
        if debug:
            print(line)
        priority = int(parsed['priority'])
        encrypted = (
            parsed['reqid'] not in (None, '0') and
            parsed['proto'] == 'esp')

    return encrypted