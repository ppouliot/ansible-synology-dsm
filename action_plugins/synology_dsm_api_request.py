# -*- coding: utf-8 -*-
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2019 Andrew Gaffney <andrew@gaffney.ca>
# SPDX-FileCopyrightText: 2026 Peter Pouliot / Interoperable Systems <peter@interoperable.systems>

"""
Ansible action plugin for making Synology DSM API requests.

DOCUMENTATION:
    name: synology_dsm_api_request
    short_description: Make API requests to a Synology DSM
    description:
        - Sends HTTP requests to the Synology DSM API via the C(uri) Ansible module.
        - Supports DSM 7.x SID-based session authentication.
        - Supports both GET and POST request methods.
    options:
        base_url:
            description: Base URL of the Synology DSM (e.g. https://nas.example.com:5001)
            required: true
            type: str
        request_method:
            description: HTTP method to use (GET or POST)
            default: GET
            type: str
        login_sid:
            description: Session ID (SID) obtained from DSM 7.x login. Preferred over login_cookie.
            required: false
            type: str
        login_cookie:
            description: Legacy cookie-based auth string (DSM 6.x). Use login_sid for DSM 7.x.
            required: false
            type: str
        validate_certs:
            description: Whether to validate SSL certificates. Set to false for self-signed certs.
            default: true
            type: bool
        cgi_path:
            description: Path to the CGI endpoint.
            default: /webapi/
            type: str
        cgi_name:
            description: CGI script name.
            default: entry.cgi
            type: str
        api_name:
            description: Synology API name (e.g. SYNO.API.Auth)
            required: true
            type: str
        api_version:
            description: API version number.
            default: '1'
            type: str
        api_method:
            description: API method to call (e.g. login, logout, list)
            required: true
            type: str
        api_params:
            description: Additional API parameters passed as key/value pairs.
            required: false
            type: dict
        request_json:
            description: Raw JSON body for POST requests (overrides api_params).
            required: false
            type: raw

EXAMPLES:
    - name: Login to DSM 7
      synology_dsm_api_request:
        base_url: "https://{{ synology_dsm_host }}:5001"
        cgi_name: auth.cgi
        api_name: SYNO.API.Auth
        api_version: "6"
        api_method: login
        request_method: POST
        validate_certs: false
        api_params:
          account: "{{ synology_dsm_username }}"
          passwd: "{{ synology_dsm_password }}"
          format: sid
      register: synology_dsm_login_response

RETURN:
    json:
        description: Parsed JSON response from the DSM API.
        returned: always
        type: dict
    status:
        description: HTTP status code returned by the DSM API.
        returned: always
        type: int
"""

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from urllib.parse import urlencode

from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):

    TRANSFERS_FILES = False

    PARAM_DEFAULTS = dict(
        base_url='https://localhost:5001',
        request_method='GET',
        login_sid=None,
        login_cookie=None,
        validate_certs=True,
        login_user=None,
        login_password=None,
        cgi_path='/webapi/',
        cgi_name='entry.cgi',
        api_name=None,
        api_version='1',
        api_method=None,
        api_params=None,
        request_json=None,
    )

    def run(self, tmp=None, task_vars=None):
        self._supports_async = True

        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        # Build task args
        task_args = self.PARAM_DEFAULTS.copy()
        task_args.update(self._task.args)
        for arg in list(task_args.keys()):
            if task_args[arg] is None:
                del task_args[arg]

        # Build 'uri' module params
        uri_params = dict(
            url="%s/%s/%s" % (
                task_args['base_url'],
                task_args['cgi_path'].strip('/'),
                task_args['cgi_name'],
            ),
            method=task_args['request_method'],
            validate_certs=task_args.get('validate_certs', True),
        )

        # Auth: prefer SID (DSM 7.x) over legacy cookie (DSM 6.x)
        if 'login_sid' in task_args:
            sid = task_args['login_sid']
        else:
            sid = None

        if 'login_cookie' in task_args and not sid:
            uri_params['headers'] = dict(Cookie=task_args['login_cookie'])

        if task_args['request_method'] == 'POST':
            if 'request_json' in task_args:
                uri_params['body'] = task_args['request_json']
                uri_params['body_format'] = 'json'
            else:
                tmp_body = dict(
                    api=task_args['api_name'],
                    version=task_args['api_version'],
                    method=task_args['api_method'],
                )
                if 'api_params' in task_args:
                    tmp_body.update(task_args['api_params'])
                if sid:
                    tmp_body['_sid'] = sid
                uri_params['body'] = tmp_body
                uri_params['body_format'] = 'form-urlencoded'

        elif task_args['request_method'] == 'GET':
            uri_params['url'] += '?api=%s&version=%s&method=%s' % (
                task_args['api_name'],
                task_args['api_version'],
                task_args['api_method'],
            )
            if 'api_params' in task_args:
                uri_params['url'] += '&%s' % urlencode(task_args['api_params'])
            if sid:
                uri_params['url'] += '&_sid=%s' % sid

        result = self._execute_module(
            'uri',
            module_args=uri_params,
            task_vars=task_vars,
            wrap_async=self._task.async_val,
        )

        # Ansible handles tmp cleanup automatically; _remove_tmp_path removed (deprecated 2.8+)

        if result.get('failed', False) or (result.get('json', {}).get('success', None) is False):
            result['failed'] = True

        return result
