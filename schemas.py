from pydantic import BaseModel, EmailStr, Field


class OrganizationCreateRequest(BaseModel):
    organization_name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=1)


class OrganizationResponse(BaseModel):
    id: str
    organization_name: str
    collection_name: str
    admin_id: str


class OrganizationUpdateRequest(BaseModel):
    organization_name: str | None = None
    admin_email: EmailStr | None = None
    admin_password: str | None = None


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
