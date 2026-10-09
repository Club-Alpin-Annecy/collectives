# New admin feature: Data export

## Goals
- Allow an admin to execute a raw database export.
- Ensure that no unauthorized personal data can be downloaded (and misused)

## Design

### Export queries

An Export Query is a predefined, hard-coded query joining between several related
tables. It is defined once in `DatabaseExportService` (see implementation section),
not extracted from configuration.

The queries below are the base queries. The selected stats filters (year, event
types, activity) are appended to them programmatically as `WHERE` conditions (see
"Filtering"). The export at this stage performs the following queries.

registrations -> users (participant), events, event_types, event_activity_types
```
SELECT
    -- ===== REGISTRATIONS =====
    reg.id AS registration_id,
    reg.event_id,
    reg.status AS registration_status,
    reg.level AS registration_level,
    reg.is_self AS registration_is_self,
    reg.registration_time,

    -- ===== PARTICIPANT (USER) =====
    u.id AS user_id,
    CONCAT(u.first_name, ' ', u.last_name) AS user_name,
    u.license_category,
    u.type AS user_type,
    u.gender,

    -- ===== EVENTS =====
    e.title AS event_title,
    e.start AS event_start,
    e.end AS event_end,
    e.num_slots AS event_num_slots,
    e.num_online_slots AS event_num_online_slots,
    e.num_waiting_list AS event_num_waiting_list,
    e.include_leaders_in_counts AS event_include_leaders_in_counts,
    e.registration_open_time AS event_registration_open_time,
    e.registration_close_time AS event_registration_close_time,
    e.status AS event_status,
    e.visibility AS event_visibility,
    e.main_leader_id AS event_main_leader_id,

    -- ===== EVENT TYPE =====
    et.name AS event_type_name,

    -- ===== EVENT ACTIVITY TYPES =====
    eat_at.name AS event_activity_type_name

FROM registrations reg

LEFT JOIN users u ON reg.user_id = u.id
LEFT JOIN events e ON reg.event_id = e.id
LEFT JOIN event_types et ON e.event_type_id = et.id
LEFT JOIN event_activity_types eat ON eat.event_id = e.id
LEFT JOIN activity_types eat_at ON eat.activity_id = eat_at.id;
```


event_leaders -> events, users (leader), event_types, event_activity_types
```
SELECT
    -- ===== EVENT LEADERS =====
    el.event_id,
    el.user_id AS leader_user_id,

    -- ===== LEADER (USER) =====
    CONCAT(u.first_name, ' ', u.last_name) AS leader_name,
    u.license_category,
    u.type AS user_type,
    u.gender,

    -- ===== EVENTS =====
    e.title AS event_title,
    e.start AS event_start,
    e.end AS event_end,
    e.num_slots AS event_num_slots,
    e.num_online_slots AS event_num_online_slots,
    e.num_waiting_list AS event_num_waiting_list,
    e.include_leaders_in_counts AS event_include_leaders_in_counts,
    e.registration_open_time AS event_registration_open_time,
    e.registration_close_time AS event_registration_close_time,
    e.status AS event_status,
    e.visibility AS event_visibility,
    e.main_leader_id AS event_main_leader_id,

    -- ===== EVENT TYPE =====
    et.name AS event_type_name,

    -- ===== EVENT ACTIVITY TYPES =====
    eat_at.name AS event_activity_type_name

FROM event_leaders el

LEFT JOIN users u ON el.user_id = u.id
LEFT JOIN events e ON el.event_id = e.id
LEFT JOIN event_types et ON e.event_type_id = et.id
LEFT JOIN event_activity_types eat ON eat.event_id = e.id
LEFT JOIN activity_types eat_at ON eat.activity_id = eat_at.id;
```

### Filtering

The database export reuses the same filter dimensions as the stats page, carried by
the submitted form: FFCAM `year`, `event_type_ids` and `activity_id`.

Constraints:

- `year` restricts `event.start` to the FFCAM year, i.e. `[YYYY-09-01 00:00, YYYY+1-08-30 23:59]`
  (same range as `StatisticsEngine`).
- `event_type_ids`, when non-empty, restricts to events whose `event_type_id` is in the list.
- `activity_id`, when not the "all activities" value, restricts to events having that activity type.

Unlike the stats engine, **all event statuses are included** (draft, confirmed,
archived, cancelled, ...): the raw export is not restricted to
`Event.status == Confirmed`.

### PII handling

The hard-coded queries select a fixed, authorized set of columns. As of now this
includes the user full name (first and last name concatenated, space separated),
`gender`, `license_category` and `user.type`.
No email, phone, license number, address or emergency contact is ever selected.

There is no runtime column exclusion list: the SQL is frozen in the service. A unit
test must assert that the queries select only these approved columns, so any
addition of a PII column is caught in review.

### Export flow

1. export request received
2. validate that requestor is admin (`current_user.is_admin`), otherwise abort 403
3. build the two base queries (`registrations`, `event_leaders`), appending the
   filter conditions derived from the submitted form
4. queries invoked in sequence.
5. each produces a temp csv file with the data (semicolon delimiter, UTF-8 with BOM,
   header row) in a temporary directory
6. zip file created bundling both csv files
7. `send_file` response created from the zip path (this is a streaming response, so
   the view returns *before* the client receives the bytes)
8. temp files and directory removed **when the response is closed**, not when the view
   returns (see "Cleanup")
9. log the export: admin id, timestamp and row count per csv file

### Cleanup

Because `send_file` streams the response *after* the view returns, cleanup cannot be
done in the view body (a `TemporaryDirectory` context manager or `@after_this_request`
would delete the files before the body is sent).

`send_file` responses use `direct_passthrough=True`: Werkzeug returns the file wrapper
directly and never calls `Response.close()`, so `response.call_on_close` is **not**
invoked and the temp directory leaks. Cleanup must instead run when the response
iterator is closed, which the WSGI server does after sending the body (or on client
disconnect). This is done by wrapping the response body in a `ClosingIterator`:

```python
from werkzeug.wsgi import ClosingIterator

tmpdir = tempfile.mkdtemp()
try:
    zip_path = build_zip(tmpdir)          # CSVs + zip written under tmpdir
    response = send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=<name>,
    )
except Exception:
    shutil.rmtree(tmpdir, ignore_errors=True)
    raise

response.response = ClosingIterator(response.response, export.cleanup)
return response
```

Notes:

- `ClosingIterator.close` closes the underlying file wrapper before running the
  cleanup callback, so the directory can be removed even where deleting open files
  is not allowed.
- `ignore_errors=True` makes cleanup idempotent and safe on client disconnect.
- The same temp path is passed to both CSV writers and the zip builder so a single
  `rmtree` cleans everything.
- If a reverse proxy buffers the response, the app-to-proxy stream completes first,
  so cleanup may happen while the proxy still streams to the client; that is fine.
- Regression test: closing the export response must remove the temp directory
  (`test_database_export_cleans_up_temp_files`).

### User interface 

Button "export database" (label `Export base de données`) added in "stats" page,
visible to admins only (`current_user.is_admin`).
Click starts the export flow.

## implementation

### new `/stats` parameter

The `GET /stats` request is used to get stats for the export and the html page.
The `excel` submit button is used today to get a stats excel file.
The `submit` button is used to get html.

A new submit button `database` is added, using the same mechanism as the `excel`
button: the presence of the `database` key in the query args requests a DB export.
As with `excel`, the exact submitted value is irrelevant.

The controller is responsible for authorization: when `database` is present it must
reject non-admin users (403).

### DatabaseExportService 

responsible for building the filtered queries, csv generation, zip and returning
data stream and file name to the controller.

- location: `collectives/utils/export.py` (or a dedicated module)
- file name: `export_<club>_<year>_<timestamp>.zip`, where `<club>` is the codified
  club identifier (`CLUB_PREFIX`) when set, otherwise the club name with every
  non-alphanumeric character removed (no spaces or special characters)
- archive contains `registrations.csv` and `leaders.csv`
- uses a temporary directory on disk; each query result is streamed to its csv file,
  then both are zipped
- builds the `send_file` response for the zip and wires cleanup through a
  `ClosingIterator` so the temporary directory is removed once the response is sent
  (see "Cleanup"). On any exception before the response is returned, removes the
  directory immediately.
