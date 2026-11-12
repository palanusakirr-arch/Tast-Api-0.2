from datetime import date
import json
import os
import sys
from typing import Any
from pathlib import Path

APP_DIR = Path("/storage/emulated/0/Documents/API")
if APP_DIR.exists():
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    os.chdir(APP_DIR)  
    

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic_settings import BaseSettings, SettingsConfigDict
import redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from auth import AuthLogic
from error_translator import ErrorTranslator
from micro_logic import MicroLogic
from pydantic_body import (
    CreateItems,
    DeleteItems,
    EmailTaker,
    Login,
    Register,
    ResetPassword,
    ShowItems,
    UpdateItems,
)
from sqlite3_database import UsersAuth, UsersData
from sqlite3_validator import DataBaseValidator


class Settings(BaseSettings):
    jwtkey: str
    warehouse_path: str
    redis_url: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

security_scheme = HTTPBearer()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_redis():
    settings = Settings()
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return client 
 

def get_config() -> dict[str, Any]:
    with open("error_config.json", "r") as file:
        config: dict[str, Any] = json.load(file)
        return config


def get_database(
    validator: DataBaseValidator = Depends(DataBaseValidator),
) -> UsersAuth:
    settings = Settings()
    database = UsersAuth(settings.warehouse_path, validator)
    return database


def get_logic(database: UsersAuth = Depends(get_database), client: Any = Depends (get_redis)) -> AuthLogic:
    logic = AuthLogic(database, client)
    return logic


def get_translator(config: dict[str, Any] = Depends(get_config)) -> ErrorTranslator:
    translator: ErrorTranslator = ErrorTranslator(config)
    return translator


def get_micro_database(
    validator: DataBaseValidator = Depends(DataBaseValidator),
) -> UsersData:
    settings = Settings()
    database = UsersData(settings.warehouse_path, validator)
    return database


def get_micro_logic(
    database: UsersData = Depends(get_micro_database),
) -> MicroLogic:
    logic = MicroLogic(database)
    return logic

def redis_helper(id: int) -> dict[str, Any] | None:
    client = get_redis()
    if client.exists(f"revoked_user:{id}"):
        return {
            "code": 401,
            "details": "This account has been revoked."
        }
    return None
    
def token_helper(token: str) -> int | dict[str, Any]:
    settings = Settings()
    try:
        payload = jwt.decode(token, settings.jwtkey, algorithms=["HS256"])
        check = redis_helper(payload['user_id'])
        if isinstance(check, dict):
            return check
    except ExpiredSignatureError:
        return {"code": 401, "details": "It looks like your session has expired."}
    except InvalidTokenError:
        return {
            "code": 401,
            "details": "It looks like something went wrong with verification. Try to log in again.",
        }
    return payload["user_id"]


@app.post("/api/auth/email_taker/")
@limiter.limit("5/minute")
def email_taker(
    request: Request,
    data: EmailTaker,
    logic: AuthLogic = Depends(get_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str]:
    response = logic.email_taker(data.type, data.email)
    if isinstance(response, dict):
        name: str = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    return {
        "message": "A verification email has been successfully sent to your provided email address.",
        "hint": "Please check your spam or junk folder if you do not see it in your inbox.",
        "instructions": "Please enter the OTP along with your other credentials in the subsequent endpoint according to your selected type.",
    }


@app.post("/api/auth/register/")
@limiter.limit("5/minute")
def register(
    request: Request,
    data: Register,
    logic: AuthLogic = Depends(get_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str]:
    response = logic.register(data.email, data.otp, data.user_name, data.set_password)
    try:
        return {
            "info": f"Registration successful! Welcome aboard, {data.user_name}.",
            "hint": "Your account has been successfully created. You can now log in using your credentials.",
            "token": response["token"],
            "type": response["type"],
        }
    except KeyError:
        name: str = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)


@app.post("/api/auth/login/")
@limiter.limit("5/minute")
def login(
    request: Request,
    data: Login,
    logic: AuthLogic = Depends(get_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str]:
    response = logic.login(data.email, data.otp, data.user_name, data.password)
    try:
        return {
            "info": f"Welcome back, {data.user_name}.",
            "token": response["token"],
            "type": response["type"],
        }
    except KeyError:
        name: str = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)


@app.patch("/api/auth/password_reset/")
@limiter.limit("5/minute")
def password_reset(
    request: Request,
    data: ResetPassword,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    logic: AuthLogic = Depends(get_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> None:
    token = credentials.credentials
    verify = token_helper(token)
    if isinstance(verify, dict):
        raise HTTPException(status_code=verify["code"], detail=verify["details"])
    user_id = verify
    response = logic.password_reset(user_id, data.otp, data.new_password)
    if isinstance(response, dict):
        name: str = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    return {"info": "password is updated successfully."}


@app.delete("/api/auth/ac_delete/")
@limiter.limit("5/minute")
def ac_delete(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    logic: AuthLogic = Depends(get_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str] | None:
    settings = Settings()
    token = credentials.credentials 
    verify = token_helper(token)
    if isinstance(verify, dict):
        raise HTTPException(status_code=verify["code"], detail=verify["details"])
    user_id = verify
    response = logic.ac_delete(user_id)
    if isinstance(response, dict):
        name: str = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    if response:
        return {
            "info": "Your account and all related data have been successfully deleted.",
            "hint": "We hope you had a great experience.",
        }
    return None


@app.post("/api/service/items/")
def create(
    request: Request,
    data: CreateItems,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    logic: MicroLogic = Depends(get_micro_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str]:
    token = credentials.credentials 
    verify = token_helper(token)
    if isinstance(verify, dict):
        raise HTTPException(status_code=verify["code"], detail=verify["details"])
    
    user_id: int = verify
    names = [item.name for item in data.items]
    quantities = [item.quantity for item in data.items]
    costs_per_unit = [item.cost_per_unit for item in data.items]
    arrived_date = [item.arrived_date for item in data.items]
    discount_start_date = [item.discount_start_date for item in data.items]
    discount_end_date = [item.discount_end_date for item in data.items]
    discount_percentages = [item.discount_percentage for item in data.items]
    barcodes = [item.barcode for item in data.items]
    statuses = [item.status for item in data.items]
    
    response = logic.logic_create(
        user_id,
        names,
        quantities,
        costs_per_unit,
        arrived_date,
        discount_start_date,
        discount_end_date,
        discount_percentages,
        barcodes,
        statuses,
    )
    if isinstance(response, dict):
        name = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    return {"info": "Item created successfully."}


@app.get("/api/service/items/")
def show(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    logic: MicroLogic = Depends(get_micro_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, dict[str, Any]]:
    token = credentials.credentials 
    verify = token_helper(token)
    if isinstance(verify, dict):
        raise HTTPException(status_code=verify["code"], detail=verify["details"])
    user_id: int = verify
    response = logic.logic_show(user_id)
    if isinstance(response, dict):
        name = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    
    response_dict: dict[str, dict[str, Any]] = {}
    ids = [row[0] for row in response if row]
    user_ids = [row[1] for row in response if row]
    names = [row[2] for row in response if row]
    quantities = [row[3] for row in response if row]
    price_per_units = [row[4] for row in response if row]
    totals = [row[5] for row in response if row]
    arrived_dates = [row[6] for row in response if row]
    discount_start_dates = [row[7] for row in response if row]
    discount_end_dates = [row[8] for row in response if row]
    discount_percentages = [row[9] for row in response if row]
    barcodes = [row[10] for row in response if row]
    statuses = [row[11] for row in response if row]
    
    for (
        item_id,
        u_id,
        name,
        quantity,
        price_per_unit,
        total,
        arrived_date,
        discount_start_date,
        discount_end_date,
        discount_percentage,
        barcode,
        status,
    ) in zip(
        ids,
        user_ids,
        names,
        quantities,
        price_per_units,
        totals,
        arrived_dates,
        discount_start_dates,
        discount_end_dates,
        discount_percentages,
        barcodes,
        statuses,
    ):
        response_dict[name] = {
            "id": item_id,
            "user_id": u_id,
            "quantity": quantity,
            "price_per_unit": price_per_unit,
            "total": total,
            "arrived_date": arrived_date,
            "discount_start_date": discount_start_date,
            "discount_end_date": discount_end_date,
            "discount_percentage": discount_percentage,
            "barcode": barcode,
            "status": status,
        }
    return response_dict


@app.patch("/api/service/items/")
def update(
    request: Request,
    data: UpdateItems,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    logic: MicroLogic = Depends(get_micro_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str] | None:
    token = credentials.credentials 
    verify = token_helper(token)
    if isinstance(verify, dict):
        raise HTTPException(status_code=verify["code"], detail=verify["details"])
    user_id: int = verify
    response = logic.logic_update(
        user_id,
        data.field_names,
        data.update_values,
        data.identifier_names,
        data.identifier_values,
    )
    if isinstance(response, dict):
        name = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    if response:
        return {"info": "Items updated successfully."}
    return None


@app.delete("/api/service/items/")
def delete(
    request: Request,
    data: DeleteItems,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    logic: MicroLogic = Depends(get_micro_logic),
    translator: ErrorTranslator = Depends(get_translator),
) -> dict[str, str] | None:
    token = credentials.credentials 
    verify = token_helper(token)
    if isinstance(verify, dict):
        raise HTTPException(status_code=verify["code"], detail=verify["details"])
    user_id: int = verify
    response = logic.logic_delete(user_id, data.product_ids)
    if isinstance(response, dict):
        name = response["code"]
        code, details = translator.translate(name)
        raise HTTPException(status_code=code, detail=details)
    if response:
        return {"info": "Deletion completed successfully."}
    return None

settings = Settings()
client = redis.Redis.from_url(settings.redis_url, decode_responses=True) 
print(client.ping())
  