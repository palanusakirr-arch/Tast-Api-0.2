import os
from pathlib import Path
from dotenv import load_dotenv

candidates = [
    Path("/storage/emulated/0/Documents/API/.env"),  
    Path(".env"),                                    
]
try:
    candidates.append(Path(__file__).resolve().parent / ".env")
except NameError:
    pass

ENV_FILE = next((p for p in candidates if p.exists()), None)


import sys  
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Dict, Optional, Union

import jwt
import redis
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ph: PasswordHasher = PasswordHasher()
class Settings(BaseSettings):
    sender_email: str
    password: str
    jwtkey: str
    port: int
    server: str

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"
    )

setting = Settings()

class AuthLogic:

    def __init__(self, data_class: Any, redis_dict: Any) -> None:
        self.data_class: Any = data_class
        self.redis_dict: Any = redis_dict

    def create_token(
        self, otp: str, email: str, expiration_time: int, purpose: str
    ) -> bool:
        # Level Zero
        key: str = f"otp:{purpose}.{email}"
        self.redis_dict.setex(key, expiration_time, otp)
        return True

    def email_taker(
        self, type: str, email: str
    ) -> Union[bool, Dict[str, str]]:
        # Level Medium
        msg: EmailMessage = EmailMessage()

        if type == "registration":
            check: Any = self.data_class.get_email_by_email(email)
            if check:
                return {
                    "error": "ValueError",
                    "reason": "it looks like you already have an account please log in instead",
                    "code": "email_taker_A",
                    "semantic": "duplication_attempt",
                }
            otp: str = f"{secrets.randbelow(1000000):06d}"
            self.create_token(otp, email, 120, "registration")
            msg["Subject"] = "Registration OTP"
            msg["From"] = setting.sender_email
            msg["To"] = email
            msg.set_content(f"Your registration OTP code is {otp}.")

        elif type == "login":
            check = self.data_class.get_email_by_email(email)
            if not check:
                return {
                    "error": "ValueError",
                    "reason": "it looks like you entered wrong email/invalid one",
                    "code": "email_taker_B",
                    "semantic": "email_not_found",
                }
            otp = f"{secrets.randbelow(1000000):06d}"
            self.create_token(otp, email, 120, "login")
            msg["Subject"] = "Login OTP"
            msg["From"] = setting.sender_email
            msg["To"] = email
            msg.set_content(f"Your Login OTP code is {otp}.")

        elif type == "password_reset":
            check = self.data_class.get_email_by_email(email)
            if not check:
                return {
                    "error": "ValueError",
                    "reason": "it looks like you entered wrong email/invalid one",
                    "code": "email_taker_C",
                    "semantic": "email_not_found",
                }
            otp = f"{secrets.randbelow(1000000):06d}"
            self.create_token(otp, email, 120, "password_reset")
            msg["Subject"] = "Password Reset OTP"
            msg["From"] = setting.sender_email
            msg["To"] = email
            msg.set_content(f"Your Password Reset OTP code is {otp}.")

        else:
            return {
                "error": "ValueError",
                "reason": "invalid email taker type requested",
                "code": "email_taker_D",
                "semantic": "invalid_action_type",
            }

        with smtplib.SMTP(setting.server, setting.port) as server:
            server.starttls()
            server.login(setting.sender_email, setting.password)
            server.send_message(msg)
        return True

    def verify_token(
        self, email: str, user_otp: str, purpose: str
    ) -> Union[bool, Dict[str, str]]:
        # Level Easy
        raw_otp: Any = self.redis_dict.get(f"otp:{purpose}.{email}")
        if not raw_otp:
            return {
                "error": "ValueError",
                "reason": "please check email address or otp might be invalid by time",
                "code": "verify_token_A",
                "semantic": "email_not_found",
            }

        stored_otp: str = (
            raw_otp.decode("utf-8") if isinstance(raw_otp, bytes) else str(raw_otp)
        )

        if stored_otp == user_otp:
            self.redis_dict.delete(f"otp:{purpose}.{email}")
            return True
        return {
            "error": "ValueError",
            "reason": "please check otp",
            "code": "verify_token_B",
            "semantic": "invalid_otp",
        }

    def register(
        self, email: str, otp: str, user_name: str, set_password: str
    ) -> Union[Dict[str, str], bool, None]:
        # Level Hard
        check: Any = self.data_class.get_email_by_email(email)
        if check:
            return {
                "error": "ValueError",
                "reason": "it looks like email is already taken",
                "code": "register_A",
                "semantic": "duplication_attempt",
            }

        action: Union[bool, Dict[str, str]] = self.verify_token(
            email, otp, "registration"
        )
        if isinstance(action, dict):
            return action

        hash_val: str = ph.hash(set_password)
        save: Any = self.data_class.db_register(email, user_name, hash_val)
        user_name = self.data_class.get_user_name(email)
        user_id: Any = self.data_class.get_id(email)
        payload: Dict[str, Any] = {
            "user_name": user_name,
            "user_id": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token: str = jwt.encode(payload, setting.jwtkey, algorithm="HS256")
        if save:
            return {"token": token, "type": "bearer"}
        return None

    def login(
        self,
        email: str,
        otp: Optional[str] = None,
        user_name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Union[Dict[str, str], bool]:
        # Level Hard
        user_id: Any = self.data_class.get_id(email)
        if not user_id:
            return {
                "error": "ValueError",
                "reason": "it looks like you don't have an account",
                "code": "login_A",
                "semantic": "email_not_found",
            }
        user_name = self.data_class.get_user_name(email)

        if password:
            hashed_password: str = self.data_class.get_password(email)
            try:
                ph.verify(hashed_password, password)
            except VerifyMismatchError:
                return {
                    "error": "ValueError",
                    "reason": "please check the password",
                    "code": "login_B",
                    "semantic": "invalid_password",
                }

            payload: Dict[str, Any] = {
                "user_name": user_name,
                "user_id": user_id,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            }
            token: str = jwt.encode(payload, setting.jwtkey, algorithm="HS256")
            return {"token": token, "type": "bearer"}

        if otp:
            action: Union[bool, Dict[str, str]] = self.verify_token(
                email, otp, "login"
            )
            if isinstance(action, dict):
                return action

            payload = {
                "user_name": user_name,
                "user_id": user_id,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            }
            token = jwt.encode(payload, setting.jwtkey, algorithm="HS256")
            return {"token": token, "type": "bearer"}

        return {
            "error": "ValueError",
            "reason": "please provide either password or otp",
            "code": "login_C",
            "semantic": "missing_credentials",
        }

    def password_reset(
        self, id: int, otp: str, new_password: str
    ) -> Union[Dict[str, str], bool]:
        # Level Easy
        check: Any = self.data_class.get_email(id)
        if not check:
            return {
                "error": "ValueError",
                "reason": "it looks like email is not registered",
                "code": "reset_password_A",
                "semantic": "email_not_found",
            }

        action: Union[bool, Dict[str, str]] = self.verify_token(
            check, otp, "password_reset"
        )
        if isinstance(action, dict):
            return action

        new_hash_val: str = ph.hash(new_password)

        update_status: Any = self.data_class.password_reset(new_hash_val, id)

        if update_status:
            return True

        return {
            "error": "DatabaseError",
            "reason": "failed to update password in database",
            "code": "reset_password_B",
            "semantic": "db_update_failed",
        }
        
    def ac_delete(self, id: int) -> bool:
        # Level Zero
        action: Any = self.data_class.db_ac_delete(id)
        if action:
            self.redis_dict.setex(f"revoked_user:{id}", 1800, "deleted")
            return True
        return False
        