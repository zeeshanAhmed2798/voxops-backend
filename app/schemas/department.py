"""Department API contracts."""

import uuid
from datetime import datetime
from typing import Literal

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DepartmentBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class DepartmentCreate(DepartmentBase):
    categories: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, categories: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for category in categories:
            name = category.strip()
            if not name:
                raise ValueError("Category names cannot be empty.")
            if len(name) > 100:
                raise ValueError("Category names cannot exceed 100 characters.")
            key = name.casefold()
            if key in seen:
                raise ValueError("Category names must be unique within the department.")
            seen.add(key)
            cleaned.append(name)
        return cleaned


class DepartmentUpdate(DepartmentBase):
    pass


class DepartmentCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DepartmentResponse(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class DepartmentWithCategoriesResponse(DepartmentResponse):
    categories: list[DepartmentCategoryResponse]


class DepartmentCreateResponse(DepartmentWithCategoriesResponse):
    pass


class DepartmentCategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Category name cannot be empty.")
        return name


class DepartmentCategoryUpdate(DepartmentCategoryCreate):
    is_active: bool


class DepartmentRoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def clean_name(cls, name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("Role name cannot be empty.")
        return name


class DepartmentRoleUpdate(DepartmentRoleCreate):
    is_active: bool


class DepartmentRoleResponse(DepartmentRoleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


Priority = Literal["LOW", "NORMAL", "HIGH"]


class DepartmentRoutingRuleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_id: uuid.UUID
    department_role_id: uuid.UUID
    priority_override: Priority | None = None
    is_active: bool = True


class DepartmentRoutingRuleResponse(DepartmentRoutingRuleCreate):
    id: uuid.UUID
    category_name: str
    department_role_name: str
    created_at: datetime
    updated_at: datetime


class DepartmentEscalationPolicyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after_hours: int = Field(gt=0, le=8760)
    escalate_to_role_id: uuid.UUID
    is_enabled: bool = True


class DepartmentEscalationPolicyResponse(DepartmentEscalationPolicyWrite):
    id: uuid.UUID
    escalate_to_role_name: str
    created_at: datetime
    updated_at: datetime


class DepartmentConfigurationResponse(BaseModel):
    department: DepartmentResponse
    categories: list[DepartmentCategoryResponse]
    roles: list[DepartmentRoleResponse]
    routing_rules: list[DepartmentRoutingRuleResponse]
    escalation_policy: DepartmentEscalationPolicyResponse | None = None
