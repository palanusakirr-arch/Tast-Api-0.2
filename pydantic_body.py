from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, EmailStr, Field, model_validator


# Level Easy
class EmailTaker(BaseModel):
    type: Literal["registration", "login", "password_reset"]
    email: EmailStr


class Register(BaseModel):
    email: EmailStr 
    otp: str
    user_name: str
    set_password: str


class Login(BaseModel):
    user_name: str
    email: EmailStr 
    otp: str | None = None
    password: str | None = None
        
    @model_validator(mode="after")
    def check(self) -> "Login":
        if self.password is None and self.otp is None:
            raise ValueError("Please either provide password or otp to login")
        if self.password is not None and self.otp is not None:
            raise ValueError("Please either provide password or otp and not together")
        return self


# Unindented to make it a top-level class
class ResetPassword(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


# Level Medium 
class Item(BaseModel):
    name: str
    quantity: float | int = Field(gt=0)
    cost_per_unit: float | int = Field(gt=0)
    arrived_date: date
    discount_start_date: date | None = None
    discount_end_date: date | None = None
    discount_percentage: float | None = None
    barcode: str
    status: Literal["pending", "arrived", "returned"]


class CreateItems(BaseModel):
    items: list[Item]
        

class ShowItems(BaseModel):
    filter_enable: bool = Field(default=False)
    filter_name: str | None = None
    filter_value: Any | None = None
    target: list[str | None ] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def check(self) -> "ShowItems":
        if self.filter_enable is True and not self.target:
            raise ValueError("target was not specified")
        return self
           
       
class UpdateItems(BaseModel):
    field_names: list[str]
    update_values: list[str | float | int | date]
    identifier_names: list[str]
    identifier_values: list[str | float | int | date]
    
    @model_validator(mode="after")
    def check(self) -> "UpdateItems":
        length_limit: int = len(self.field_names)
        if (
            len(self.update_values) != length_limit or
            len(self.identifier_names) != length_limit or
            len(self.identifier_values) != length_limit
        ):
            raise ValueError("all lists must have same length")
        return self
                
                 
class DeleteItems(BaseModel):
    product_ids: list[int]
    