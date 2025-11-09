"""
Simple database models for Njuskalo HR system.
Pydantic models that correspond to the MySQL database schema.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json


# Simple models matching the SQL schema tables
class User(BaseModel):
    """User table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    newemail: Optional[str] = None
    group: Optional[str] = None
    photo: Optional[str] = None
    mainUser: Optional[bool] = None
    consent: Optional[bool] = None
    deleted: Optional[bool] = None
    profile: Optional[Dict[str, Any]] = None
    company: Optional[Dict[str, Any]] = None
    logo: Optional[str] = None
    avtonet: Optional[Dict[str, Any]] = None
    njuskalo: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class UserToken(BaseModel):
    """User tokens table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    userUuid: Optional[str] = None
    type: Optional[str] = None
    token: Optional[str] = None
    created: Optional[datetime] = None
    expires: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """User logins table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    created: Optional[datetime] = None
    expires: Optional[datetime] = None
    userUuid: Optional[str] = None
    tokenUuid: Optional[str] = None
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None
    extToken: Optional[str] = None

    class Config:
        from_attributes = True


class File(BaseModel):
    """Files table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    parent: Optional[str] = None
    filename: Optional[str] = None
    size: Optional[int] = None
    uploaded: Optional[datetime] = None
    type: Optional[str] = None
    description: Optional[str] = None
    mimetype: Optional[str] = None
    variants: Optional[Dict[str, Any]] = None
    deleted: Optional[bool] = None

    class Config:
        from_attributes = True


class FileGroup(BaseModel):
    """File groups table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    files: Optional[str] = None

    class Config:
        from_attributes = True


class Menu(BaseModel):
    """Menus table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    parent: Optional[str] = None
    orderindex: Optional[int] = None
    title: Optional[str] = None
    slug: Optional[str] = None

    class Config:
        from_attributes = True


class MenuItem(BaseModel):
    """Menu items table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    menu: Optional[str] = None
    parent: Optional[str] = None
    orderindex: Optional[int] = None
    title: Optional[str] = None
    target: Optional[str] = None
    photo: Optional[str] = None
    language: Optional[str] = None

    class Config:
        from_attributes = True


class Page(BaseModel):
    """Pages table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    parent: Optional[str] = None
    slug: Optional[str] = None
    target: Optional[str] = None
    template: Optional[str] = None
    title: Optional[str] = None
    intro: Optional[str] = None
    photo: Optional[str] = None
    pageBlockGroup: Optional[str] = None
    blockGroup: Optional[str] = None
    htmlTitle: Optional[str] = None
    htmlDescription: Optional[str] = None
    language: Optional[str] = None
    updated: Optional[datetime] = None
    deleted: Optional[bool] = None

    class Config:
        from_attributes = True


class BlockGroup(BaseModel):
    """Block groups table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None

    class Config:
        from_attributes = True


class Block(BaseModel):
    """Blocks table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    blockGroup: Optional[str] = None
    orderindex: Optional[int] = None
    type: Optional[str] = None
    content: Optional[str] = None

    class Config:
        from_attributes = True


class PageBlockGroup(BaseModel):
    """Page block groups table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None

    class Config:
        from_attributes = True


class PageBlock(BaseModel):
    """Page blocks table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    pageBlockGroup: Optional[str] = None
    orderindex: Optional[int] = None
    type: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    video: Optional[str] = None
    photo: Optional[str] = None

    class Config:
        from_attributes = True


class PageBlockPhoto(BaseModel):
    """Page block photos table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    pageBlock: Optional[str] = None
    photo: Optional[str] = None

    class Config:
        from_attributes = True


class AdItem(BaseModel):
    """Ad item table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    user: Optional[str] = None
    title: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    status: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    adCode: Optional[str] = None
    doberAvtoCode: Optional[str] = None
    publishDoberAvto: Optional[bool] = None
    publishAvtoNet: Optional[bool] = None
    publishNjuskalo: Optional[bool] = None

    class Config:
        from_attributes = True


class AdPhoto(BaseModel):
    """Ad photos table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    aditem: Optional[str] = None
    orderindex: Optional[int] = None
    photo: Optional[str] = None
    extUuid: Optional[str] = None

    class Config:
        from_attributes = True


class AvtoAdItem(BaseModel):
    """Avto ad item table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    user: Optional[str] = None
    title: Optional[str] = None
    adCode: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    status: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    doberAvtoCode: Optional[str] = None

    class Config:
        from_attributes = True


class AvtoAdPhoto(BaseModel):
    """Avto ad photos table model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    aditem: Optional[str] = None
    orderindex: Optional[int] = None
    photo: Optional[str] = None
    extUuid: Optional[str] = None

    class Config:
        from_attributes = True


class ScrapedStore(BaseModel):
    """Scraped stores table model (existing)"""
    id: Optional[int] = None
    url: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    is_valid: Optional[bool] = None
    is_automoto: Optional[bool] = None
    total_vehicle_count: Optional[int] = None
    used_vehicle_count: Optional[int] = None
    new_vehicle_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Utility function to parse JSON fields from database
def parse_json_field(value):
    """Parse JSON field from database"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value