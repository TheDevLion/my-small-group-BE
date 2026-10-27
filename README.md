API Deploy URL: https://manage-group-api.vercel.app

## Project Overview
My Small Group API provides authentication and data access for a small group management app. The frontend uses a password-based login to receive a signed, HttpOnly session cookie, and all Hygraph GraphQL operations are executed server-side. The API also supports event photo uploads and a stock price scraper endpoint.

## Technical Overview
This backend is a Flask API with modular route and service layers. Sessions are stateless, signed cookies (no server-side session storage), and bearer tokens are never sent to the browser. Hygraph is used as the data store via GraphQL, and assets are uploaded via Hygraph's upload endpoint. The API exposes OpenAPI docs at `/openapi.json` and Swagger UI at `/docs`.

## Technologies (Libraries and Versions)
From `requirements.txt`:
- blinker==1.7.0
- certifi==2023.11.17
- charset-normalizer==3.3.2
- click==8.1.7
- colorama==0.4.6
- cssselect==1.2.0
- Flask==3.0.0
- Flask-Cors==4.0.0
- python-dotenv==1.0.1
- idna==3.6
- importlib-metadata==7.0.1
- itsdangerous==2.1.2
- Jinja2==3.1.2
- lxml==5.1.0
- MarkupSafe==2.1.3
- pyquery==2.0.0
- requests==2.31.0
- urllib3==2.1.0
- Werkzeug==3.0.1
- zipp==3.17.0

## Run locally
Prereqs:
- Python 3.10+ (3.11 recommended)
- pip

Environment variables (set in your shell before running):
- HYGRAPH_ADMIN_TOKEN (required)
- SESSION_SECRET_KEY (required; used to sign the session cookie)
- HYGRAPH_API_URL (optional, defaults to the current Hygraph project)
- CORS_ORIGINS (optional, comma-separated list)
- COOKIE_SECURE (optional, true/false)
- COOKIE_SAMESITE (optional, Lax/Strict/None)
- SESSION_TTL_SECONDS (optional)
- SESSION_COOKIE_SALT (optional)
- PORT (optional, defaults to 5010)

Commands:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The API starts on http://127.0.0.1:5010 by default.

## Endpoints
### GET /docs
Swagger UI for the API (uses `/openapi.json`).

```bash
open http://127.0.0.1:5010/docs
```

### GET /openapi.json
OpenAPI spec in JSON format.

### POST /login
Validates a password, sets a signed HttpOnly session cookie, and returns the group ID.
The cookie stores only the group ID; bearer tokens stay server-side and are fetched per request.

```bash
curl -X POST http://127.0.0.1:5000/login \
  -H 'Content-Type: application/json' \
  -d '{"payload":"YOUR_PASSWORD"}' \
  -c cookies.txt
```

### POST /logout
Clears the session cookie.

```bash
curl -X POST http://127.0.0.1:5000/logout -b cookies.txt
```

### GET /group
Fetches the group payload for the authenticated session.

```bash
curl http://127.0.0.1:5000/group -b cookies.txt
```

### PUT /group/name
Updates the group name.

```bash
curl -X PUT http://127.0.0.1:5000/group/name \
  -H 'Content-Type: application/json' \
  -d '{"name":"New Name", "updatedAt":"REVISION_FROM_GET_GROUP"}' \
  -b cookies.txt
```

### PUT /group/participants
Updates the participants list.

```bash
curl -X PUT http://127.0.0.1:5000/group/participants \
  -H 'Content-Type: application/json' \
  -d '{"participants":[], "updatedAt":"REVISION_FROM_GET_GROUP"}' \
  -b cookies.txt
```

### PUT /group/events
Updates the events list.

```bash
curl -X PUT http://127.0.0.1:5000/group/events \
  -H 'Content-Type: application/json' \
  -d '{"events":[], "updatedAt":"REVISION_FROM_GET_GROUP"}' \
  -b cookies.txt
```

### PUT /group/template
Updates the group template.

```bash
curl -X PUT http://127.0.0.1:5000/group/template \
  -H 'Content-Type: application/json' \
  -d '{"template":{}, "updatedAt":"REVISION_FROM_GET_GROUP"}' \
  -b cookies.txt
```

### GET /event-photos?eventId=EVENT_ID
Fetches event photos for the given event.

```bash
curl "http://127.0.0.1:5000/event-photos?eventId=EVENT_ID" -b cookies.txt
```

### POST /event-photos
Uploads an event photo (multipart form with `fileUpload` and `eventId`).

```bash
curl -X POST http://127.0.0.1:5000/event-photos \
  -F "fileUpload=@/path/to/file.jpg" \
  -F "eventId=EVENT_ID" \
  -b cookies.txt
```

### DELETE /event-photos/:id
Unpublishes the event photo after checking its group.

```bash
curl -X DELETE http://127.0.0.1:5000/event-photos/EVENT_PHOTO_ID -b cookies.txt
```

### GET /stock_price?stock=SYMBOL
Fetches price data for a supported stock symbol.

```bash
curl "http://127.0.0.1:5000/stock_price?stock=vale3"
```

## CORS (front-end)
This API uses `Flask-Cors` and supports credentials. Configure `CORS_ORIGINS` and cookie settings
if your front-end runs on a different origin.

Example (local + GitHub Pages):
```
CORS_ORIGINS=http://localhost:4200,https://thedevlion.github.io
```


## Updated write contract

All four `/group/*` PUTs require `updatedAt` from `GET /group` and return the new revision on success. Missing/stale revisions return 409, without overwriting newer edits. Validation returns 400. A participant referenced by attendance cannot be deleted (409). Group reads use DRAFT so a saved but unpublished change can be inspected and retried after publication failure.

Deploy the frontend and backend changes together: older frontends do not send revisions and their writes will be rejected. The group token needs DRAFT reads, conditional `updateManyGroupsConnection`, and the existing update/publish permissions. Photo deletion retains the existing `unpublishEventPhoto` operation. Schema support was verified by read-only introspection; group-specific token permissions and production writes still require staging verification.

Photo uploads accept JPEG/PNG/GIF/WebP signatures, with a 4 MiB file limit. The API scopes photo operations to the authenticated group. GET lists only PUBLISHED photos. POST `/event-photos/{id}/publish` explicitly retries a failed upload whose photo ID is known, without reuploading. A publication error includes the existing photo ID. Deleting a photo unpublishes it. Old drafts are never automatically republished or included in the event gallery. Uploaded assets are retained: if the upstream response is lost after a write, the API cannot safely infer that the asset is unused. Storage cleanup after an ambiguous upstream failure remains an operational limitation; no automatic destructive cleanup was added.

`X-Group-ID` lets the frontend reject use of a cookie belonging to a different group in another tab. Token-service outages return 503, not 401. Keep `CORS_ORIGINS` restricted to frontend origins and verify cookie settings in the deployment environment.
