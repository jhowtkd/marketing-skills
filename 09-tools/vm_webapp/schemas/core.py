from __future__ import annotations

from typing import Literal, Optional

from .base import VMBaseModel, Timestamped


class BrandCreate(VMBaseModel):
    brand_id: Optional[str] = None
    name: str
    description: Optional[str] = None


class BrandUpdate(VMBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class BrandResponse(Timestamped):
    brand_id: str
    name: str
    description: Optional[str] = None
    status: Literal["active", "frozen", "archived"] = "active"
    event_id: Optional[str] = None


class BrandsListResponse(VMBaseModel):
    brands: list[BrandResponse]


class ProjectCreate(VMBaseModel):
    project_id: Optional[str] = None
    name: str
    brand_id: str
    description: Optional[str] = None
    objective: str = ""
    channels: list[str] = []
    due_date: Optional[str] = None


class ProjectUpdate(VMBaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    channels: Optional[list[str]] = None
    due_date: Optional[str] = None


class ProjectResponse(Timestamped):
    project_id: str
    brand_id: str
    name: str
    description: Optional[str] = None
    status: Literal["active", "archived"] = "active"
    event_id: Optional[str] = None


class ProjectsListResponse(VMBaseModel):
    projects: list[ProjectResponse]


class ThreadCreate(VMBaseModel):
    thread_id: Optional[str] = None
    title: str
    brand_id: str
    project_id: str


class ThreadUpdate(VMBaseModel):
    title: Optional[str] = None


class ThreadResponse(Timestamped):
    thread_id: str
    brand_id: str
    project_id: str
    title: str
    status: Literal["open", "closed"] = "open"
    event_id: Optional[str] = None


class ThreadsListResponse(VMBaseModel):
    threads: list[ThreadResponse]


class CampaignCreate(VMBaseModel):
    title: str
    brand_id: str
    project_id: str


class CampaignUpdate(VMBaseModel):
    title: Optional[str] = None


class CampaignResponse(Timestamped):
    campaign_id: str
    brand_id: str
    project_id: str
    title: str
    status: Literal["active", "archived"] = "active"


class CampaignsListResponse(VMBaseModel):
    campaigns: list[CampaignResponse]
