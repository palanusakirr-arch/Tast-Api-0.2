# Warehouse Inventory API

A FastAPI backend that lets users sign up with email OTP verification, log in (password or OTP), and manage their own personal inventory of items. Data is stored in SQLite, OTPs and revoked sessions are kept in Redis, and sessions use JWT bearer tokens.

## Features

- **Email OTP verification** for registration, login and password reset (6-digit code, valid for 2 minutes)
- **Two login methods**: password or one-time code
- **Argon2** password hashing
- **JWT authentication** (HS256, 30-minute expiry)
- **Account deletion** with immediate token revocation via Redis
- **Per-user inventory CRUD**: every user only sees and modifies their own items
- **Rate limiting** (5 requests/minute per IP) on all auth endpoints
- **Centralised error messages** through `error_config.json`

## Tech Stack

| Component        | Technology                  |
| ---------------- | --------------------------- |
| Framework        | FastAPI + Uvicorn           |
| Validation       | Pydantic v2                 |
| Database         | SQLite (WAL mode)           |
| Cache / OTP store| Redis                       |
| Auth             | PyJWT, argon2-cffi          |
| Rate limiting    | SlowAPI                     |
| Email            | SMTP (`smtplib`, STARTTLS)  |

## Project Structure

```
API/
├── main.py               # FastAPI app, routes, dependencies, token checks
├── auth.py               # AuthLogic: OTP, register, login, password reset, delete
├── micro_logic.py        # MicroLogic: business logic for inventory items
├── sqlite3_database.py   # UsersAuth and UsersData database classes
├── sqlite3_validator.py  # Validation helpers for create/update operations
├── pydantic_body.py      # Request body schemas
├── error_translator.py   # Maps internal error codes to HTTP status + message
├── error_config.json     # Error code -> status code / message table
├── requirements.txt
└── .env.example
```

## Getting Started

### Prerequisites

- Python 3.10+ (developed on 3.13)
- A running Redis server
- An SMTP account for sending OTP emails (e.g. a Gmail app password)

### Installation

```bash
git clone <your-repo-url>
cd API

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### Configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

| Variable         | Description                                         | Example                      |
| ---------------- | --------------------------------------------------- | ---------------------------- |
| `warehouse_path` | Path to the SQLite database file                    | `warehouse.db`               |
| `jwtkey`         | Secret used to sign JWTs (use a long random value)  | output of `openssl rand -hex 32` |
| `sender_email`   | Address OTP emails are sent from                    | `you@gmail.com`              |
| `password`       | SMTP password / app password                        | `xxxx xxxx xxxx xxxx`        |
| `server`         | SMTP host                                           | `smtp.gmail.com`             |
| `port`           | SMTP port (STARTTLS)                                | `587`                        |
| `redis_url`      | Redis connection URL                                | `redis://localhost:6379/0`   |

> **Never commit your real `.env` file.** Add it to `.gitignore`.

### Run

```bash
uvicorn main:app --reload
```

The API is served at `http://127.0.0.1:8000`. Interactive docs are available at `/docs` (Swagger) and `/redoc`.

On startup the app pings Redis and prints `True` if the connection works. Database tables are created automatically on first use.

## Authentication Flow

1. **Request an OTP**: `POST /api/auth/email_taker/` with a `type` (`registration`, `login` or `password_reset`) and your `email`.
2. **Use the OTP** with the matching endpoint (register, login or password reset) within 2 minutes.
3. Receive a **bearer token** and send it on protected requests:

```
Authorization: Bearer <token>
```

Tokens expire after 30 minutes.

## API Reference

### Auth endpoints

All auth endpoints are limited to **5 requests per minute** per IP.

| Method | Endpoint                    | Auth   | Description                                  |
| ------ | --------------------------- | ------ | -------------------------------------------- |
| POST   | `/api/auth/email_taker/`    | No     | Send an OTP to the given email               |
| POST   | `/api/auth/register/`       | No     | Create an account using the OTP              |
| POST   | `/api/auth/login/`          | No     | Log in with password **or** OTP              |
| PATCH  | `/api/auth/password_reset/` | Bearer | Set a new password using a `password_reset` OTP |
| DELETE | `/api/auth/ac_delete/`      | Bearer | Delete the account and all its data          |

**Send OTP**

```json
POST /api/auth/email_taker/
{ "type": "registration", "email": "user@example.com" }
```

**Register**

```json
POST /api/auth/register/
{
  "email": "user@example.com",
  "otp": "123456",
  "user_name": "alice",
  "set_password": "a-strong-password"
}
```

**Login** (provide either `password` or `otp`, never both)

```json
POST /api/auth/login/
{ "user_name": "alice", "email": "user@example.com", "password": "a-strong-password" }
```

**Reset password** (requires a bearer token and an OTP of type `password_reset`)

```json
PATCH /api/auth/password_reset/
{ "email": "user@example.com", "otp": "123456", "new_password": "new-password" }
```

Successful register and login responses return:

```json
{ "info": "...", "token": "<jwt>", "type": "bearer" }
```

### Inventory endpoints

All inventory endpoints require a bearer token and only operate on the current user's items.

| Method | Endpoint              | Description                   |
| ------ | --------------------- | ----------------------------- |
| POST   | `/api/service/items/` | Create one or more items      |
| GET    | `/api/service/items/` | List all of your items        |
| PATCH  | `/api/service/items/` | Update fields on items        |
| DELETE | `/api/service/items/` | Delete items by ID            |

**Create items**

```json
POST /api/service/items/
{
  "items": [
    {
      "name": "Rice 5kg",
      "quantity": 40,
      "cost_per_unit": 320.5,
      "arrived_date": "2026-11-01",
      "discount_start_date": "2026-11-10",
      "discount_end_date": "2026-11-20",
      "discount_percentage": 10,
      "barcode": "8901234567890",
      "status": "arrived"
    }
  ]
}
```

- `quantity` and `cost_per_unit` must be greater than 0.
- `status` must be one of `pending`, `arrived`, `returned`.
- Discount fields are optional.
- The `total` (`quantity × cost_per_unit`) is calculated automatically.
- Item names must be unique per user.

**List items**: returns a dictionary keyed by item name:

```json
{
  "Rice 5kg": {
    "id": 1,
    "user_id": 3,
    "quantity": 40,
    "price_per_unit": 320.5,
    "total": 12820.0,
    "arrived_date": "2026-11-01",
    "discount_start_date": "2026-11-10",
    "discount_end_date": "2026-11-20",
    "discount_percentage": 10.0,
    "barcode": "8901234567890",
    "status": "arrived"
  }
}
```

**Update items**: the four lists are paired by position and must all have the same length. Each pair `field_names[i] = update_values[i]` is applied to rows where `identifier_names[i] = identifier_values[i]`.

```json
PATCH /api/service/items/
{
  "field_names": ["quantity", "status"],
  "update_values": [35, "returned"],
  "identifier_names": ["name", "barcode"],
  "identifier_values": ["Rice 5kg", "8901234567890"]
}
```

Allowed columns: `name`, `quantity`, `price_per_unit`, `total`, `arrived_date`, `discount_start_date`, `discount_end_date`, `discount_percentage`, `barcode`, `status`. The product `id` cannot be modified.

**Delete items**

```json
DELETE /api/service/items/
{ "product_ids": [1, 2, 3] }
```

## Error Handling

Internal error codes are translated into HTTP responses by `ErrorTranslator`, using `error_config.json`. Unknown codes fall back to a `500` response. Examples:

| Code               | Status | Message                                            |
| ------------------ | ------ | -------------------------------------------------- |
| `email_taker_A`    | 409    | An account with this email address already exists. |
| `verify_token_B`   | 400    | Invalid OTP. Please check the code and try again.  |
| `login_B`          | 400    | Invalid password. Please try again.                |
| `update_helper_D`  | 403    | Modification restricted: Product ID cannot be updated. |

Token problems return `401` (expired session, invalid token, or revoked account).

To change a message or status code, edit `error_config.json`. No code changes are needed.

## Database Schema

**`users_auth`**

| Column          | Type                          |
| --------------- | ----------------------------- |
| `id`            | INTEGER, primary key, autoincrement |
| `email`         | TEXT, unique                  |
| `user_name`     | TEXT, unique                  |
| `user_password` | TEXT (Argon2 hash)            |

**`users_data`**

| Column                                          | Type                                           |
| ----------------------------------------------- | ---------------------------------------------- |
| `id`                                            | INTEGER, primary key, autoincrement            |
| `user_id`                                       | INTEGER, foreign key to `users_auth.id` (cascade delete) |
| `name`                                          | TEXT, unique per user                          |
| `quantity`, `price_per_unit`, `total`           | numeric                                        |
| `arrived_date`                                  | DATE                                           |
| `discount_start_date`, `discount_end_date`      | DATE                                           |
| `discount_percentage`                           | FLOAT                                          |
| `barcode`, `status`                             | TEXT                                           |

## Redis Keys

| Key                         | Purpose                          | TTL     |
| --------------------------- | -------------------------------- | ------- |
| `otp:<purpose>.<email>`     | Pending OTP for a given action   | 120 s   |
| `revoked_user:<id>`         | Marks a deleted account's tokens as revoked | 1800 s |

## Security Notes

- Use a long, random `jwtkey` in production. The value in `.env.example` is a placeholder only.
- Serve the API over HTTPS so tokens and passwords are not sent in plain text.
- Keep `.env` out of version control.
- Consider adding rate limiting to the inventory endpoints, which currently have none.

## License

Add your license here (e.g. MIT).
