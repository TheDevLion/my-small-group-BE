from flask import Blueprint, Response, jsonify


docs_bp = Blueprint("docs", __name__)


@docs_bp.route("/openapi.json", methods=["GET"])
def openapi_spec():
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "My Small Group API",
            "version": "1.0.0",
        },
        "servers": [
            {"url": "http://127.0.0.1:5010", "description": "Local"},
            {"url": "https://manage-group-api.vercel.app", "description": "Production"},
        ],
        "components": {
            "securitySchemes": {
                "cookieAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "msg_session",
                }
            }
        },
        "paths": {
            "/login": {
                "post": {
                    "summary": "Login and set session cookie",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "payload": {"type": "string"}
                                    },
                                    "required": ["payload"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Login successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "groupID": {"type": "string"}
                                        },
                                    }
                                }
                            },
                        },
                        "400": {"description": "Missing password"},
                        "401": {"description": "Wrong password"},
                    },
                }
            },
            "/logout": {
                "post": {
                    "summary": "Logout and clear session cookie",
                    "responses": {
                        "200": {
                            "description": "Logout successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"ok": {"type": "boolean"}},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/group": {
                "get": {
                    "summary": "Fetch group data",
                    "security": [{"cookieAuth": []}],
                    "responses": {
                        "200": {"description": "Group payload"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/group/name": {
                "put": {
                    "summary": "Update group name",
                    "security": [{"cookieAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"}
                                    },
                                    "required": ["name"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Group updated"},
                        "400": {"description": "Invalid name"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/group/participants": {
                "put": {
                    "summary": "Update participants list",
                    "security": [{"cookieAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "participants": {"type": "array", "items": {"type": "object"}}
                                    },
                                    "required": ["participants"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Group updated"},
                        "400": {"description": "Invalid payload"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/group/events": {
                "put": {
                    "summary": "Update events list",
                    "security": [{"cookieAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "events": {"type": "array", "items": {"type": "object"}}
                                    },
                                    "required": ["events"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Group updated"},
                        "400": {"description": "Invalid payload"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/group/template": {
                "put": {
                    "summary": "Update group template",
                    "security": [{"cookieAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "template": {"type": "object"}
                                    },
                                    "required": ["template"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Group updated"},
                        "400": {"description": "Invalid payload"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/event-photos": {
                "get": {
                    "summary": "Fetch event photos",
                    "security": [{"cookieAuth": []}],
                    "parameters": [
                        {
                            "name": "eventId",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "Event photos list"},
                        "400": {"description": "Missing eventId"},
                        "401": {"description": "Unauthorized"},
                    },
                },
                "post": {
                    "summary": "Upload event photo",
                    "security": [{"cookieAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "fileUpload": {"type": "string", "format": "binary"},
                                        "eventId": {"type": "string"},
                                    },
                                    "required": ["fileUpload", "eventId"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Photo uploaded"},
                        "400": {"description": "Missing payload"},
                        "401": {"description": "Unauthorized"},
                    },
                },
            },
            "/event-photos/{eventPhotoId}": {
                "delete": {
                    "summary": "Unpublish event photo",
                    "security": [{"cookieAuth": []}],
                    "parameters": [
                        {
                            "name": "eventPhotoId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "Photo unpublished"},
                        "401": {"description": "Unauthorized"},
                    },
                }
            },
            "/stock_price": {
                "get": {
                    "summary": "Get stock price info",
                    "parameters": [
                        {
                            "name": "stock",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "Stock price data"},
                    },
                }
            },
        },
    }
    return jsonify(spec)


@docs_bp.route("/docs", methods=["GET"])
def swagger_ui():
    html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>API Docs</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.onload = () => {
        window.ui = SwaggerUIBundle({
          url: '/openapi.json',
          dom_id: '#swagger-ui'
        });
      };
    </script>
  </body>
</html>
"""
    return Response(html, mimetype="text/html")
