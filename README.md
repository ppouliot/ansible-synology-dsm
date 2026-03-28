# ansible-synology-dsm

Ansible role and action plugin for configuring a Synology NAS running DSM 7.x (with backwards compatibility for DSM 6.x).

## Overview

`ansible-synology-dsm` provides an Ansible role and a custom action plugin (`synology_dsm_api_request`) for managing a Synology NAS via the [Synology DSM API](https://global.download.synology.com/download/Document/Software/DeveloperGuide/Package/FileStation/All/enu/Synology_File_Station_API_Guide.pdf).

### What's New in This Fork (DSM 7 Update)

The `action_plugins/synology_dsm_api_request.py` plugin has been fully updated for DSM 7.x and modern Ansible:

- **DSM 7 SID-based authentication** — new `login_sid` parameter; passes `_sid` correctly in both GET query strings and POST form bodies. Legacy `login_cookie` (DSM 6.x) is retained as a fallback.
- **Python 3 only** — removed the Python 2/3 `urllib` try/except shim; uses `from urllib.parse import urlencode` directly.
- **SSL certificate validation** — new `validate_certs` parameter (default `True`), passed through to Ansible's `uri` module.
- **Default port updated** — default `base_url` changed from `http://localhost:5000` to `https://localhost:5001` (DSM 7 HTTPS default).
- **Removed deprecated call** — dropped `_remove_tmp_path()` which was removed in Ansible 2.8+.
- **Fixed `TRANSFERS_FILES`** — set to `False` (action plugin does not transfer files).
- **Full DOCUMENTATION block** — added `DOCUMENTATION`, `EXAMPLES`, and `RETURN` blocks per Ansible plugin standards.
- **SPDX license headers** added.
- **PEP 8** cleanup throughout.

> **Note on `request_json`:** The `request_json` parameter passes the body as `application/json`. Real-world testing against a DS218 (DSM 7.x) confirmed that DSM does **not** accept `application/json` request bodies on any endpoint — all DSM API endpoints require `application/x-www-form-urlencoded`. The `request_json` option remains in the plugin for potential use against custom DSM packages that may accept JSON, but it will not work against the standard DSM API.

---

## `synology_dsm_api_request` Action Plugin

### Parameters

| Parameter | Required | Default | Description |
|---|---|---|---|
| `base_url` | no | `https://localhost:5001` | Base URL of the DSM (e.g. `http://nas.example.com:5000`) |
| `request_method` | no | `GET` | HTTP method: `GET` or `POST` |
| `login_sid` | no | — | **DSM 7.x** Session ID (SID) from login. Preferred over `login_cookie`. Appended as `_sid` to GET query string and POST body. |
| `login_cookie` | no | — | **DSM 6.x** legacy cookie string. Used only if `login_sid` is not set. |
| `validate_certs` | no | `True` | Set `false` to skip SSL cert validation (useful for self-signed certs). |
| `cgi_path` | no | `/webapi/` | Path to the CGI directory. |
| `cgi_name` | no | `entry.cgi` | CGI script name. Use `auth.cgi` for authentication endpoints. |
| `api_name` | yes | — | Synology API name (e.g. `SYNO.API.Auth`, `SYNO.FileStation.List`) |
| `api_version` | no | `1` | API version number. |
| `api_method` | yes | — | API method (e.g. `login`, `logout`, `list`, `get`) |
| `api_params` | no | — | Additional parameters as a dict. URL-encoded and appended for GET; merged into body for POST. |
| `request_json` | no | — | Raw JSON body for POST requests. Bypasses normal body construction. See note above re: DSM compatibility. |

### Return Values

| Key | Type | Description |
|---|---|---|
| `json` | dict | Parsed JSON response from the DSM API |
| `status` | int | HTTP status code |

The task is marked `failed: true` if the HTTP request fails **or** if the DSM API returns `success: false`.

---

## Usage

### Login (DSM 7 — SID-based)

```yaml
- name: Login to DSM 7
  synology_dsm_api_request:
    base_url: "http://{{ synology_dsm_host }}:5000"
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
  register: dsm_login

- name: Store SID
  set_fact:
    dsm_sid: "{{ dsm_login.json.data.sid }}"
```

### Authenticated GET Request

```yaml
- name: Get FileStation info
  synology_dsm_api_request:
    base_url: "http://{{ synology_dsm_host }}:5000"
    api_name: SYNO.FileStation.Info
    api_version: "2"
    api_method: get
    request_method: GET
    login_sid: "{{ dsm_sid }}"
    validate_certs: false
  register: fs_info
```

### Authenticated POST Request

```yaml
- name: List shared folders
  synology_dsm_api_request:
    base_url: "http://{{ synology_dsm_host }}:5000"
    api_name: SYNO.FileStation.List
    api_version: "2"
    api_method: list_share
    request_method: POST
    login_sid: "{{ dsm_sid }}"
    validate_certs: false
  register: shares
```

### Logout

```yaml
- name: Logout
  synology_dsm_api_request:
    base_url: "http://{{ synology_dsm_host }}:5000"
    cgi_name: auth.cgi
    api_name: SYNO.API.Auth
    api_version: "6"
    api_method: logout
    request_method: POST
    login_sid: "{{ dsm_sid }}"
    validate_certs: false
```

### Role-Level Usage (File Services, SSH, Users, Packages)

```yaml
- name: Configure File Services
  hosts: synology_nas
  roles:
    - ansible-synology-dsm
  vars:
    synology_dsm_nfs_enable: true
    synology_dsm_smb_enable: true
    synology_dsm_afp_enable: false

- name: Configure Terminal Services
  hosts: synology_nas
  roles:
    - ansible-synology-dsm
  vars:
    synology_dsm_ssh_enable: true
    synology_dsm_ssh_port: 22
    synology_dsm_telnet_enable: false

- name: Configure User Home Service
  hosts: synology_nas
  roles:
    - ansible-synology-dsm
  vars:
    synology_dsm_user_home_service_enable: true
    synology_dsm_user_home_location: "/volume1/homes"
    synology_dsm_user_home_enable_recycle_bin: false

- name: Add Package Sources
  hosts: synology_nas
  roles:
    - ansible-synology-dsm
  vars:
    synology_dsm_package_sources:
      - name: "Example Source"
        feed: "http://example.com/package/source"
```

---

## Requirements

- Ansible 2.9+
- Python 3.6+
- Access to a Synology NAS running DSM 6.x or 7.x

---

## Installation

```yaml
# requirements.yml
- src: https://github.com/ppouliot/ansible-synology-dsm
  name: ansible-synology-dsm
```

```bash
ansible-galaxy install -r requirements.yml
```

---

## Integration Tests

All 8 integration tests pass against a real Synology DS218 running DSM 7.x.

| Test | What it validates | Result |
|---|---|---|
| T1 | Unauthenticated GET — API info endpoint | ✅ PASSED |
| T2 | DSM 7 SID login via POST (`auth.cgi`) | ✅ PASSED |
| T3 | Authenticated GET with `_sid` in query string | ✅ PASSED |
| T4 | Authenticated POST with `_sid` in form body | ✅ PASSED |
| T5 | `api_params` dict URL-encoding in GET | ✅ PASSED |
| T6 | Custom `cgi_path` / `cgi_name` URL construction | ✅ PASSED |
| T7 | Error propagation: `success: false` → `failed: true` | ✅ PASSED |
| T8 | Logout / SID invalidation | ✅ PASSED |

**Test environment:**
- Hardware: Synology DS218
- DSM version: 7.x
- Container: `ghcr.io/ansible/community-ansible-dev-tools:latest`
- Ansible-core: 2.20 (Python 3.13)

### Test Artifacts

- **Playbook:** [`tests/integration/test_dsm7_plugin.yml`](tests/integration/test_dsm7_plugin.yml)
- **Test plan:** [`tests/integration/test_plan.md`](tests/integration/test_plan.md)
- **Run logs:** [`tests/integration/logs/`](tests/integration/logs/)
- **Asciinema recording:** [`assets/test-run.cast`](assets/test-run.cast)

### Replay the Test Run

Install [asciinema](https://asciinema.org) and replay the recorded test session:

```bash
asciinema play assets/test-run.cast
```

Or view it inline if your terminal supports it:

[![asciicast](assets/test-run.cast)](assets/test-run.cast)

---

## Contributing

Contributions welcome. Please submit pull requests for any enhancements.
