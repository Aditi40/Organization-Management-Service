from datetime import datetime
from passlib.context import CryptContext
from bson import ObjectId
from ..db import organizations_collection, admins_collection, master_db
from app.schemas import OrganizationUpdateRequest
from app.config import settings
from jose import jwt
from datetime import datetime, timedelta
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def authenticate_admin(email: str, password: str) -> dict:
    admin = await admins_collection.find_one({"email": email})
    if not admin:
        raise ValueError("Invalid credentials")

    # ✅ Use passlib to verify
    if not pwd_context.verify(password, admin["password_hash"]):
        raise ValueError("Invalid credentials")

    org = await organizations_collection.find_one({"admin_id": admin["_id"]})
    if not org:
        raise ValueError("Organization not found for this admin")

    payload = {
        "admin_id": str(admin["_id"]),
        "org_id": str(org["_id"]),
        "org_name": org["organization_name"],
        "exp": datetime.utcnow() + timedelta(minutes=settings.jwt_exp_minutes),
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return {"access_token": token, "token_type": "bearer"}


def hash_password(password: str) -> str:
    print("PASSWORD RECEIVED:", password, type(password))
    return pwd_context.hash(password)


def org_collection_name(org_name: str) -> str:
    # simple normalization: lowercase, replace spaces with underscores
    normalized = org_name.strip().lower().replace(" ", "_")
    return f"org_{normalized}"


async def get_organization_by_name(org_name: str) -> dict:
    org = await organizations_collection.find_one({"organization_name": org_name})
    if not org:
        raise ValueError("Organization not found")

    return {
        "id": str(org["_id"]),
        "organization_name": org["organization_name"],
        "collection_name": org["collection_name"],
        "admin_id": str(org["admin_id"]),
    }


async def create_organization(org_name: str, email: str, password: str):
    # 1. Check if organization already exists
    existing = await organizations_collection.find_one({"organization_name": org_name})
    if existing:
        raise ValueError("Organization already exists")

    # 2. Determine collection name
    coll_name = org_collection_name(org_name)

    # 3. Create dynamic org collection (empty for now)
    org_collection = master_db[coll_name]
    # Optional: create an index to "materialize" collection
    await org_collection.create_index("created_at")

    # 4. Create admin user
    hashed_pw = hash_password(password)
    admin_doc = {
        "email": email,
        "password_hash": hashed_pw,
        "role": "admin",
        "created_at": datetime.utcnow(),
    }
    admin_result = await admins_collection.insert_one(admin_doc)
    admin_id = admin_result.inserted_id

    # 5. Store organization metadata in Master DB
    org_doc = {
        "organization_name": org_name,
        "collection_name": coll_name,
        "admin_id": admin_id,
        "created_at": datetime.utcnow(),
    }
    org_result = await organizations_collection.insert_one(org_doc)

    return {
        "id": str(org_result.inserted_id),
        "organization_name": org_name,
        "collection_name": coll_name,
        "admin_id": str(admin_id),
    }


async def delete_organization(org_name: str):
    # 1. Find org
    org = await organizations_collection.find_one({"organization_name": org_name})
    if not org:
        raise ValueError("Organization not found")

    coll_name = org["collection_name"]

    # 2. Drop dynamic collection if exists
    existing_collections = await master_db.list_collection_names()
    if coll_name in existing_collections:
        await master_db.drop_collection(coll_name)

    # 3. Delete admin
    await admins_collection.delete_one({"_id": org["admin_id"]})

    # 4. Delete org metadata
    await organizations_collection.delete_one({"_id": org["_id"]})


async def update_organization(org_name: str, update: OrganizationUpdateRequest) -> dict:
    # 1. Fetch existing org
    org = await organizations_collection.find_one({"organization_name": org_name})
    if not org:
        raise ValueError("Organization not found")

    updates = {}

    # 2. Handle organization name change
    if update.organization_name and update.organization_name != org_name:
        # Check for name conflict
        existing = await organizations_collection.find_one(
            {"organization_name": update.organization_name}
        )
        if existing:
            raise ValueError("Organization name already exists")

        old_collection = org["collection_name"]
        new_collection = f"org_{update.organization_name}"

        # Rename collection
        await master_db[old_collection].rename(new_collection)

        updates["organization_name"] = update.organization_name
        updates["collection_name"] = new_collection

    # 3. Handle admin updates
    admin_updates = {}
    if update.admin_email:
        admin_updates["email"] = update.admin_email

    if update.admin_password:
        hashed_pw = bcrypt.hashpw(
            update.admin_password.encode(), bcrypt.gensalt()
        ).decode()
        admin_updates["password_hash"] = hashed_pw

    if admin_updates:
        await admins_collection.update_one(
            {"_id": org["admin_id"]}, {"$set": admin_updates}
        )

    # 4. Apply org updates
    if updates:
        await organizations_collection.update_one(
            {"_id": org["_id"]}, {"$set": updates}
        )

        # Refresh org
        org.update(updates)

    # 5. Return updated org
    return {
        "id": str(org["_id"]),
        "organization_name": org["organization_name"],
        "collection_name": org["collection_name"],
        "admin_id": str(org["admin_id"]),
    }
