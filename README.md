# dsc26-swe-w02 · Tawseel parcel API, contract first

DSC Summer Internship 2026 · Software Engineering track · Week 2
**Python 3.12 · FastAPI 0.141.1 · pytest 9.1.1** · expected time 2.5–3.5 hours

## Scenario

Tawseel's dispatch backend needs its first real endpoint: parcels. The courier app team and
the merchant integration team will build against your contract this week, so the contract has
to be right, errors and pagination included. The lifecycle rules (dispatch, fail, retry,
return) will change as Sherif learns more, so they live in one pure module that the HTTP layer
calls. You also write two ADRs.

## Set up

```bash
# your repository must be named exactly dsc26-swe-w02, public, in your own GitHub account
git init -b main
uv venv --python 3.12
source .venv/bin/activate          # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt  # pinned versions; do not change them
pytest -q                           # public tests: they fail until you build the task
```

Run the API by hand with `uvicorn app.api:app --reload` and open http://127.0.0.1:8000/docs.

## Files

```
app/__init__.py        empty
app/domain.py          the lifecycle, pure Python (you write apply_event)
app/api.py             the HTTP layer (you write create_app)
docs/adr/0000-template.md   blank ADR; does not count towards your two
docs/adr/NNNN-....md   your two ADRs
tests/test_public.py   the public tests (keep tests/__init__.py so `pytest -q` finds app/)
AI_USAGE.md            required, see the end of this file
requirements.txt       pinned versions; the grader has exactly these and no network
```

## What to build

### 1. `app/domain.py`: the lifecycle, pure Python

No imports from `fastapi`, `starlette`, `pydantic` or `sqlalchemy` (a hidden test checks).
Keep these exact names (they are already in the starter):

```python
from dataclasses import dataclass
from enum import StrEnum

MAX_ATTEMPTS = 3

class ParcelState(StrEnum):
    CREATED = "created"
    OUT_FOR_DELIVERY = "out_for_delivery"
    FAILED_ATTEMPT = "failed_attempt"
    DELIVERED = "delivered"
    RETURNED = "returned"

class EventType(StrEnum):
    DISPATCH = "dispatch"
    DELIVER = "deliver"
    FAIL = "fail"
    RETURN = "return"

class InvalidTransition(Exception): ...

@dataclass(frozen=True)
class Parcel:
    id: str
    merchant_ref: str
    cod_amount_piastres: int
    address_text: str
    state: ParcelState = ParcelState.CREATED
    attempts: int = 0

def apply_event(parcel: Parcel, event: EventType) -> Parcel:
    """Return a new Parcel. Raise InvalidTransition if the event is not allowed."""
```

The rules:

- `created` + `dispatch` → `out_for_delivery`, `attempts` + 1
- `out_for_delivery` + `deliver` → `delivered`
- `out_for_delivery` + `fail` → `failed_attempt`
- `failed_attempt` + `dispatch` → `out_for_delivery`, `attempts` + 1, **only if `attempts < MAX_ATTEMPTS`**
- `failed_attempt` + `return` → `returned`
- `delivered` and `returned` are final. Every other combination raises `InvalidTransition`.
  `apply_event` never mutates its input, and only `state` and `attempts` change.

### 2. `app/api.py`: the HTTP layer

Expose `create_app() -> FastAPI`, which returns a **new** app with its own empty in-memory
store each time it is called (the tests call it once per test, so no module-level dicts or
counters for parcels), and a module-level `app = create_app()` for `uvicorn` (the starter has
a placeholder line to replace).

| Operation | operationId | Success | Errors |
|---|---|---|---|
| `POST /v1/parcels` | `createParcel` | 201, the parcel, `Location: /v1/parcels/{id}` | 409 duplicate `merchant_ref`; 422 invalid body |
| `GET /v1/parcels/{parcel_id}` | `getParcel` | 200, the parcel | 404 |
| `GET /v1/parcels?state=&limit=&cursor=` | `listParcels` | 200, `{"items": [...], "next_cursor": str \| null}` | 400 bad cursor; 422 bad `state` or `limit` |
| `POST /v1/parcels/{parcel_id}/events` with `{"type": "<event>"}` | `recordParcelEvent` | 200, the updated parcel | 404; 409 invalid transition (parcel unchanged); 422 unknown or missing event type |

- Request body for create: `merchant_ref` (string, 1–64 chars), `cod_amount_piastres`
  (integer, 0–5,000,000), `address_text` (string, 1–500 chars). Both ends of each range are valid.
- A parcel in JSON: `id`, `merchant_ref`, `cod_amount_piastres`, `address_text`, `state`,
  `attempts`. Ids start with `pcl_` and are unique within an app. `GET` returns exactly what
  `POST` returned until the parcel changes.
- The `Location` header is `/v1/parcels/{id}` (an absolute URL ending in that path is also accepted).
- **Every** error, including 422 validation errors and 422s for query parameters, is
  `application/problem+json` (RFC 9457) with at least `type`, `title` and `status` (the same
  number as the HTTP status).
- A 422 also has `errors`: a list with **exactly one entry per invalid field**, each entry an
  object whose `loc` names the field, for example
  `{"loc": ["body", "cod_amount_piastres"], "msg": "Input should be greater than or equal to 0"}`.
  The handler in the W2 teaching notes produces exactly this from FastAPI's
  `RequestValidationError`.
- A duplicate `merchant_ref` and an invalid transition store nothing and change nothing.
- Every error status in the table is documented in the OpenAPI `responses` of its operation
  (`app.openapi()`), next to the success status.
- **Lists** are in creation order. `limit` defaults to 20 and must be an integer 1–100;
  anything else is 422. An unknown `state` is 422. `cursor` is opaque: return the cursor you
  issued as `next_cursor`, and answer anything you did not issue with 400. `next_cursor` is
  `null` on the page that contains the last matching item (no extra empty page at the end).
  Paging with a `state` filter must not skip or repeat items when earlier items change state
  between requests (offset pagination fails this).

### 3. `docs/adr/`: two ADRs

Two files named `NNNN-kebab-case-title.md` (four digits, lower-case words joined by hyphens,
for example `0001-parcel-state-machine.md`; `0000-template.md` does not count). Each has the
headings `Status`, `Context`, `Decision` and `Consequences` as `##` or `###` headings, and the
first line under `Status` starts with one of Proposed, Accepted, Superseded, Deprecated or
Rejected. Suggested topics: why the lifecycle lives in a pure module; why cursor pagination.
Write them yourself; they are short. Track Mentors read the content at the design review.

### 4. `AI_USAGE.md`

AI tools are allowed. Keep the three headings `## Tools`, `## What AI got wrong` and
`## In my own words`. If the file is missing or a heading is missing, the grader stops and
gives 0 with the reason "AI_USAGE.md missing or incomplete". Under `## In my own words`,
answer in one or two sentences each, without AI: "Why does `listParcels` need a cursor rather
than an offset?" and "Which of your four operations would break the courier app if you
renamed one field, and who would have to approve that change?"

## Public tests

`pytest -q` runs `tests/test_public.py` (5 tests). They fail on the starter and pass on a
correct solution. Passing them is necessary, not sufficient: the hidden tests decide the score.

## How grading works

Push to `dsc26-swe-w02`, then press **Submit for grading** on DSC Hex (5 runs per task per
day). The grader clones your latest commit, copies DSC's hidden tests into `tests_hidden/`,
removes any `conftest.py` and `pytest.ini` at the repository root, ignores pytest settings
in `pyproject.toml`, `setup.cfg` or `tox.ini`, and runs each hidden test with
`python -m pytest` from the repository root, network off, 30 s per test and 3 minutes in all.
Your own tests are not run by the grader. You see each hidden test's name, pass or fail, and a
short hint; never the test code.

| ID | Public name | What it checks | Weight |
|---|---|---|---|
| H01 | domain: random event sequences keep valid state | Hypothesis generates 200 random event sequences; every accepted event gives the state and attempts the rules say, `attempts` stays between 0 and 3, any non-`created` state has `attempts ≥ 1`, refused events raise `InvalidTransition`, and the input is never changed | 12 |
| H02 | domain: every forbidden transition raises | All 15 forbidden (state, event) pairs raise `InvalidTransition`; the input parcel is unchanged | 10 |
| H03 | domain: after the third failure only return is allowed | Three dispatch/fail cycles, then `dispatch` raises and `return` works | 6 |
| H04 | architecture: domain imports no framework | `app/domain.py` imports none of `fastapi`, `starlette`, `pydantic`, `sqlalchemy` | 6 |
| H05 | create: 201, Location, body | Status, `Location` header, all six fields, `pcl_` prefix, unique ids | 8 |
| H06 | validation errors are problem documents | Several invalid bodies (empty or too long ref, negative or too large COD, missing field, wrong types, several bad fields at once) give 422, `application/problem+json`, and `errors` with one entry per bad field; boundary values are accepted | 8 |
| H07 | duplicate merchant_ref is 409 | Second create with the same `merchant_ref` gives a 409 problem; only one parcel exists | 6 |
| H08 | unknown parcel is a 404 problem | On `getParcel` and `recordParcelEvent` | 5 |
| H09 | event endpoint: invalid transition is 409, parcel unchanged | Includes the third-failure case over HTTP and an unknown or missing event type (422) | 8 |
| H10 | pagination: full walk returns every parcel once, in order | 57 parcels, `limit=10` and the default limit, with and without a `state` filter; last page has `next_cursor: null` | 7 |
| H11 | pagination: a cursor survives state changes mid-walk | Filter `state=created`, take page 1, dispatch those parcels, page 2 must be items 11–20 | 5 |
| H12 | pagination: bad cursor 400, bad limit 422 | Garbage cursors, `limit` 0, 101, -1 or not a number, unknown `state` | 5 |
| H13 | contract: operationIds, paths, documented errors | `app.openapi()` has the four operationIds on the right path and method, and the statuses in the table appear in each operation's `responses` | 8 |
| H14 | ADRs: two well-formed records | At least two files matching `NNNN-kebab-title.md` (template excluded), each with the four headings and a valid status | 6 |
| | | **Total** | **100** |

The hidden tests build their own data through your API, so hard-coded ids or answers fail.
A hidden test file that cannot import a name it needs (for example you renamed `Parcel`)
fails all of its tests, so keep the names above exactly.

Late policy: ×1.0 within 72 hours of the session starting, ×0.6 for the following 7 days,
×0.5 after that until Thu 3 Dec 23:59. W5 reopens W2–W4 at ×1.0. Your best attempt counts.
