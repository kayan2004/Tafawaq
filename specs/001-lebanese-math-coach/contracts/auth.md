# Contract: Authentication

All auth endpoints are provided by `fastapi-users`. JWT Bearer token required on all protected
routes. Error responses follow the standard shape: `{"error": "<message>", "request_id": "<uuid>"}`.

---

## POST /auth/register

Register a new student account.

**Auth**: None required

**Request**:
```json
{ "email": "student@example.com", "password": "securepassword" }
```

**Response 201**:
```json
{ "id": "<uuid>", "email": "student@example.com", "is_active": true }
```

**Response 400** — email already registered:
```json
{ "error": "REGISTER_USER_ALREADY_EXISTS", "request_id": "<uuid>" }
```

---

## POST /auth/jwt/login

Login and receive a JWT access token.

**Auth**: None required

**Request** (form data, not JSON — fastapi-users default):
```
username=student@example.com&password=securepassword
```

**Response 200**:
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

**Response 400** — wrong credentials:
```json
{ "error": "LOGIN_BAD_CREDENTIALS", "request_id": "<uuid>" }
```

---

## GET /auth/me

Return the current authenticated student's profile.

**Auth**: Bearer token required

**Response 200**:
```json
{
  "id": "<uuid>",
  "email": "student@example.com",
  "is_active": true,
  "created_at": "2026-06-03T10:00:00Z",
  "last_login": "2026-06-03T10:00:00Z"
}
```

**Response 401** — missing or invalid token:
```json
{ "error": "Unauthorized", "request_id": "<uuid>" }
```
