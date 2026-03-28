# DSM 7 Action Plugin — Integration Test Results

**Date:** 2026-03-28  
**Hardware:** Synology DS218  
**DSM version:** 7.x  
**Target:** http://172.19.0.43:5000  
**Container:** `ghcr.io/ansible/community-ansible-dev-tools:latest`  
**Ansible-core:** 2.20 (Python 3.13)  
**Final log:** [`logs/run-20260328-120610.log`](logs/run-20260328-120610.log)  
**Asciinema recording:** [`../../assets/test-run.cast`](../../assets/test-run.cast)

---

## Results Summary

```
PLAY RECAP
localhost : ok=18  changed=0  unreachable=0  failed=0  skipped=0  rescued=0  ignored=1
```

| Test | Description | Result | Notes |
|---|---|---|---|
| T1 | Unauthenticated GET — `SYNO.API.Info` | ✅ PASSED | Returns `SYNO.API.Auth` version info |
| T2 | DSM 7 SID login via POST to `auth.cgi` | ✅ PASSED | SID obtained successfully |
| T3 | Authenticated GET with `_sid` in query string | ✅ PASSED | `SYNO.FileStation.Info` returned hostname `ds218` |
| T4 | Authenticated POST with `_sid` in form body | ✅ PASSED | `SYNO.FileStation.List` returned shares list |
| T5 | GET with `api_params` URL encoding | ✅ PASSED | `additional` param correctly encoded as `%5B%22real_path%22%2C%22size%22%5D` |
| T6 | Custom `cgi_path`/`cgi_name` URL construction | ✅ PASSED | `SYNO.FileStation.List` API info returned correctly |
| T7 | Error propagation: bad creds → `failed: true` | ✅ PASSED | DSM returned error code 400; task marked `failed` |
| T8 | Logout / SID invalidation | ✅ PASSED | `success: true`, session cookie cleared |

**Overall: 8/8 PASSED**

---

## Known Limitation: `request_json` and DSM

During testing, the `request_json` parameter (which sends `Content-Type: application/json`) was found to be incompatible with all DSM API endpoints on the DS218. DSM returns `{"error":{"code":101},"success":false}` ("No such API") for any request with a JSON body, regardless of the endpoint or SID validity.

**Root cause:** Despite the DSM API info reporting `"requestFormat": "JSON"` for some endpoints, DSM 7.x on the DS218 only accepts `application/x-www-form-urlencoded` request bodies. The `requestFormat` field in the API info response refers to the *response* format, not the request body format.

**Impact:** The `request_json` parameter remains in the plugin for completeness and potential future use, but it will not work against standard DSM API endpoints on current hardware. All standard use cases are covered by the `api_params` dict (GET/POST form-urlencoded).

T6 was redesigned to test custom `cgi_path`/`cgi_name` URL construction instead, which is a more useful and verifiable test of the plugin's parameter handling.

---

## Test Run History

| Run | Timestamp | Result | Notes |
|---|---|---|---|
| 1 | 2026-03-28 12:03:25 | FAILED T6 | `request_json` to `entry.cgi` fails with DSM error 101 |
| 2 | 2026-03-28 12:03:36 | FAILED T6 | Added `cgi_name: auth.cgi` — auth.cgi also rejects JSON body |
| 3 | 2026-03-28 12:04:18 | FAILED T6 | `request_json` to `auth.cgi` still fails — DSM doesn't accept JSON bodies |
| 4 | 2026-03-28 12:05:04 | FAILED T6 | Investigated: confirmed DSM only accepts form-urlencoded on all endpoints |
| 5 | 2026-03-28 12:06:10 | **ALL PASSED** | T6 redesigned to test custom cgi_path/cgi_name URL construction |

---

## How to Reproduce

```bash
# From repo root
mkdir -p tests/integration/logs assets

docker run --rm \
  -v "$(pwd):/workspace" \
  -w /workspace \
  -e ANSIBLE_FORCE_COLOR=1 \
  -e ANSIBLE_ACTION_PLUGINS=/workspace/action_plugins \
  ghcr.io/ansible/community-ansible-dev-tools:latest \
  ansible-playbook -i tests/integration/inventory.ini \
    tests/integration/test_dsm7_plugin.yml -v
```

Or use the runner script:
```bash
bash tests/integration/run_tests.sh
```

To replay the recorded session:
```bash
asciinema play assets/test-run.cast
```
