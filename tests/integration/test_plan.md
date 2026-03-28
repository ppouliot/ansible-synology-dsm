# DSM 7 Action Plugin Integration Test Plan

**Target:** http://172.19.0.43:5000  
**Executor:** Cornholio (qwen2.5-coder:32b)  
**Container:** `ghcr.io/ansible/community-ansible-dev-tools:latest`  
**Output:** `assets/test-run.cast` (asciinema), `tests/integration/logs/` (plain logs)

---

## Pre-flight

- [ ] Pull `ghcr.io/ansible/community-ansible-dev-tools:latest`
- [ ] Verify DSM reachable: `curl -s -o /dev/null -w "%{http_code}" http://172.19.0.43:5000`
- [ ] Confirm `asciinema` available in container (or install via pip)

---

## Test 1 — API Info (unauthenticated, GET)

**Purpose:** Verify the plugin can make a basic GET request without auth and parse the DSM API info endpoint.

```yaml
- name: "T1 - Get DSM API info (no auth)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    api_name: SYNO.API.Info
    api_version: "1"
    api_method: query
    api_params:
      query: "SYNO.API.Auth"
  register: t1_result

- name: "T1 - Assert success"
  assert:
    that:
      - t1_result.json.success == true
      - "'SYNO.API.Auth' in t1_result.json.data"
```

**Pass criteria:** `success: true`, `data` contains `SYNO.API.Auth` version info.

---

## Test 2 — DSM 7 SID Login (POST)

**Purpose:** Authenticate using DSM 7 SID-based login. The SID returned here is used in all subsequent tests.

```yaml
- name: "T2 - Login and obtain SID (DSM 7)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    cgi_name: auth.cgi
    api_name: SYNO.API.Auth
    api_version: "6"
    api_method: login
    request_method: POST
    api_params:
      account: "beavis"
      passwd: "B3@v!$&Butth3@d"
      format: sid
  register: t2_login

- name: "T2 - Assert SID obtained"
  assert:
    that:
      - t2_login.json.success == true
      - t2_login.json.data.sid is defined
      - t2_login.json.data.sid | length > 0

- name: "T2 - Store SID as fact"
  set_fact:
    dsm_sid: "{{ t2_login.json.data.sid }}"
```

**Pass criteria:** `success: true`, `sid` non-empty string returned.

---

## Test 3 — Authenticated GET with SID

**Purpose:** Verify `login_sid` is correctly appended to GET query string as `_sid`.

```yaml
- name: "T3 - Authenticated GET (SID in query string)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    api_name: SYNO.FileStation.Info
    api_version: "2"
    api_method: get
    request_method: GET
    login_sid: "{{ dsm_sid }}"
  register: t3_result

- name: "T3 - Assert success"
  assert:
    that:
      - t3_result.json.success == true
```

**Pass criteria:** `success: true` (authenticated response, not 403/auth error).

---

## Test 4 — Authenticated POST with SID

**Purpose:** Verify `login_sid` is correctly injected into POST body as `_sid`.

```yaml
- name: "T4 - Authenticated POST (SID in body)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    api_name: SYNO.FileStation.List
    api_version: "2"
    api_method: list_share
    request_method: POST
    login_sid: "{{ dsm_sid }}"
  register: t4_result

- name: "T4 - Assert success"
  assert:
    that:
      - t4_result.json.success == true
      - t4_result.json.data.shares is defined
```

**Pass criteria:** `success: true`, `shares` list returned.

---

## Test 5 — GET with `api_params` (URL encoding)

**Purpose:** Verify `api_params` dict is correctly URL-encoded and appended to GET requests.

```yaml
- name: "T5 - GET with api_params (URL encoding)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    api_name: SYNO.FileStation.List
    api_version: "2"
    api_method: list_share
    request_method: GET
    login_sid: "{{ dsm_sid }}"
    api_params:
      additional: '["real_path","size"]'
  register: t5_result

- name: "T5 - Assert success and params encoded"
  assert:
    that:
      - t5_result.json.success == true
```

**Pass criteria:** `success: true`, no URL encoding errors.

---

## Test 6 — POST with `request_json` (raw body)

**Purpose:** Verify the `request_json` raw body path works for POST requests.

```yaml
- name: "T6 - POST with raw request_json"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    api_name: SYNO.API.Auth
    api_version: "6"
    api_method: login
    request_method: POST
    request_json:
      api: SYNO.API.Auth
      version: "6"
      method: login
      account: "beavis"
      passwd: "B3@v!$&Butth3@d"
      format: sid
  register: t6_result

- name: "T6 - Assert raw JSON POST worked"
  assert:
    that:
      - t6_result.json.success == true
      - t6_result.json.data.sid is defined
```

**Pass criteria:** `success: true`, `sid` returned via raw JSON body path.

---

## Test 7 — Failed auth (error propagation)

**Purpose:** Verify that an API `success: false` response is correctly surfaced as `failed: true` in Ansible.

```yaml
- name: "T7 - Bad credentials (expect failure)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    cgi_name: auth.cgi
    api_name: SYNO.API.Auth
    api_version: "6"
    api_method: login
    request_method: POST
    api_params:
      account: "wronguser"
      passwd: "wrongpass"
      format: sid
  register: t7_result
  ignore_errors: true

- name: "T7 - Assert task failed"
  assert:
    that:
      - t7_result.failed == true
```

**Pass criteria:** Task is marked `failed: true` when DSM returns `success: false`.

---

## Test 8 — Logout (SID invalidation)

**Purpose:** Clean up — logout the SID obtained in T2.

```yaml
- name: "T8 - Logout (invalidate SID)"
  synology_dsm_api_request:
    base_url: "http://172.19.0.43:5000"
    validate_certs: false
    cgi_name: auth.cgi
    api_name: SYNO.API.Auth
    api_version: "6"
    api_method: logout
    request_method: POST
    login_sid: "{{ dsm_sid }}"
  register: t8_result

- name: "T8 - Assert logout success"
  assert:
    that:
      - t8_result.json.success == true
```

**Pass criteria:** `success: true` on logout.

---

## Execution Instructions for Cornholio

1. Write the full playbook to `tests/integration/test_dsm7_plugin.yml` using all tests above.
2. Write inventory to `tests/integration/inventory.ini`:
   ```ini
   [local]
   localhost ansible_connection=local
   ```
3. Pull and run inside the community-ansible-dev-tools container:
   ```bash
   docker pull ghcr.io/ansible/community-ansible-dev-tools:latest
   docker run --rm \
     -v $(pwd):/workspace \
     -w /workspace \
     ghcr.io/ansible/community-ansible-dev-tools:latest \
     bash -c "pip install asciinema -q && \
       asciinema rec assets/test-run.cast --command \
       'ansible-playbook -i tests/integration/inventory.ini tests/integration/test_dsm7_plugin.yml -v' \
       --title 'DSM7 action plugin integration tests'"
   ```
4. Save full stdout/stderr log to `tests/integration/logs/run-$(date +%Y%m%d-%H%M%S).log`.
5. If all 8 tests pass, report `ALL TESTS PASSED` and the path to the `.cast` file.
6. If any test fails, report the exact task name, error message, and the raw JSON response from DSM.
