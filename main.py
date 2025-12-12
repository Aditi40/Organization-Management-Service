from fastapi import FastAPI, HTTPException
from .schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    AdminLoginRequest,
)
from .services.org_service import (
    create_organization,
    get_organization_by_name,
    update_organization,
    delete_organization,
    authenticate_admin,
)


app = FastAPI(title="Organization Management Service")


@app.post("/org/create", response_model=OrganizationResponse)
async def create_org(payload: OrganizationCreateRequest):
    try:
        org = await create_organization(
            org_name=payload.organization_name,
            email=payload.email,
            password=payload.password,
        )
        return org

    except ValueError as e:
        # Business logic errors (e.g., org already exists)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # ✅ Print the REAL error so we can debug bcrypt
        print("ERROR in /org/create:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/org/{org_name}", response_model=OrganizationResponse)
async def get_org(org_name: str):
    try:
        org = await get_organization_by_name(org_name)
        return org
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print("ERROR in GET /org:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/org/{org_name}", response_model=OrganizationResponse)
async def update_org(org_name: str, update: OrganizationUpdateRequest):
    try:
        updated_org = await update_organization(org_name, update)
        return updated_org
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print("ERROR in UPDATE /org:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/org/{org_name}")
async def delete_org(org_name: str):
    try:
        await delete_organization(org_name)
        return {"detail": "Organization deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print("ERROR in DELETE /org:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/admin/login")
async def admin_login(body: AdminLoginRequest):
    try:
        return await authenticate_admin(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
