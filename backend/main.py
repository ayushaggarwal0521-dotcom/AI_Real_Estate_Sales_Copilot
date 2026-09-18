# backend/main.py
#
# FastAPI layer for the V2 website.
#
# This file does NOT reimplement any property or AI logic.
# It calls straight into the existing, working modules:
#
#   real_estate_client.py  -> talks to the MCP server (server.py) -> SQLite
#   property_llm.py        -> talks to OpenAI, using real_estate_client
#                              for inventory + verification
#
# Website (HTML/CSS/JS)  --->  FastAPI (this file)  --->  MCP  --->  SQLite
#                                        |
#                                        +--> OpenAI (property_llm.py)

import json
import os
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from real_estate_client import (
    get_all_properties,
    search_properties,
    get_properties_by_location,
    get_property_details,
)
from property_llm import find_properties_for_customer
from property_images import attach_images
from leads_db import init_leads_db, save_lead


# ---------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------

app = FastAPI(title="Real Estate Copilot API")

# Allow the frontend to call this API even if it's ever served
# from a different origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make sure the leads table exists before any /api/appointments request
# comes in. See the warning at the top of leads_db.py about Render's
# free-tier ephemeral disk before treating this as durable storage.
init_leads_db()


# ---------------------------------------------------------
# SESSION STORAGE (in-memory)
# ---------------------------------------------------------
#
# Mirrors whatsapp_webhook.py's `customer_states` dict, but keyed
# by a browser-generated session_id instead of a phone number.
# This resets whenever the server restarts. For production, swap
# this dict for Redis or a database table keyed on session_id.

CONVERSATIONS: dict[str, list[dict]] = {}


def get_history(session_id: str) -> list[dict]:
    if session_id not in CONVERSATIONS:
        CONVERSATIONS[session_id] = []
    return CONVERSATIONS[session_id]


# ---------------------------------------------------------
# REQUEST / RESPONSE MODELS
# ---------------------------------------------------------

class AISearchRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class NewSessionResponse(BaseModel):
    session_id: str


class AppointmentRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = ""
    property_id: Optional[str] = ""
    property_title: Optional[str] = ""
    message: Optional[str] = ""


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------
# SESSION MANAGEMENT
# ---------------------------------------------------------

@app.post("/api/new-session", response_model=NewSessionResponse)
def new_session():
    session_id = str(uuid.uuid4())
    CONVERSATIONS[session_id] = []
    return {"session_id": session_id}


# ---------------------------------------------------------
# FILTER METADATA (populates the dropdowns on the site)
# ---------------------------------------------------------

@app.get("/api/meta")
def meta():
    try:
        properties = get_all_properties()
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach the property inventory: {error}",
        )

    cities = sorted({p["city"] for p in properties if p.get("city")})
    property_types = sorted(
        {p["property_type"] for p in properties if p.get("property_type")}
    )
    furnished_options = sorted(
        {p["furnished"] for p in properties if p.get("furnished")}
    )
    bhk_options = sorted(
        {int(p["bhk"]) for p in properties if p.get("bhk")}
    )

    return {
        "cities": cities,
        "property_types": property_types,
        "furnished_options": furnished_options,
        "bhk_options": bhk_options,
        "total_properties": len(properties),
    }


# ---------------------------------------------------------
# SIMPLE FILTER SEARCH (the "Property Search" path)
# ---------------------------------------------------------

@app.get("/api/filter-search")
def filter_search(
    city: str = "",
    location: str = "",
    property_type: str = "",
    bhk: int = 0,
    max_price: int = 0,
    min_area: int = 0,
    parking: bool = False,
    furnished: str = "",
    max_metro_distance: float = 0,
):
    try:
        properties = search_properties(
            city=city,
            location=location,
            property_type=property_type,
            bhk=bhk,
            max_price=max_price,
            min_area=min_area,
            parking=parking,
            furnished=furnished,
            max_metro_distance=max_metro_distance,
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Search failed: {error}",
        )

    return {
        "total": len(properties),
        "properties": [attach_images(p) for p in properties],
    }


# ---------------------------------------------------------
# PROPERTY DETAILS
# ---------------------------------------------------------

@app.get("/api/property/{property_id}")
def property_details(property_id: str):
    try:
        details = get_property_details(property_id)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Lookup failed: {error}",
        )

    if not details or details.get("success") is False:
        raise HTTPException(status_code=404, detail="Property not found.")

    return attach_images(details)


# ---------------------------------------------------------
# AI SEARCH (the "Ask AI" path)
# ---------------------------------------------------------

@app.post("/api/ai-search")
def ai_search(payload: AISearchRequest):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty.")

    session_id = payload.session_id or str(uuid.uuid4())
    history = get_history(session_id)

    try:
        results = find_properties_for_customer(payload.message, history)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"AI search failed: {error}",
        )

    # property_llm.py intentionally leaves conversation_history storage
    # commented out (see its find_properties_for_customer), so this is
    # where the turn actually gets remembered for the next request.
    history.append({"role": "user", "content": payload.message})
    history.append({"role": "assistant", "content": json.dumps(results)})

    for result in results["results"]:
        attach_images(result.get("property"))

    return {
        "session_id": session_id,
        "customer_query": results["customer_query"],
        "total_matches": results["total_matches"],
        "results": results["results"],
    }


# ---------------------------------------------------------
# BOOK AN APPOINTMENT (saves a lead to leads.db)
# ---------------------------------------------------------

@app.post("/api/appointments")
def create_appointment(payload: AppointmentRequest):
    name = payload.name.strip()
    phone = payload.phone.strip()

    if not name or not phone:
        raise HTTPException(status_code=400, detail="Name and phone are required.")

    try:
        lead_id = save_lead(
            name=name,
            phone=phone,
            email=(payload.email or "").strip(),
            property_id=(payload.property_id or "").strip(),
            property_title=(payload.property_title or "").strip(),
            message=(payload.message or "").strip(),
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not save that: {error}")

    return {"success": True, "lead_id": lead_id}


# ---------------------------------------------------------
# SERVE THE WEBSITE
# ---------------------------------------------------------
# Must be mounted LAST - it's a catch-all for "/".

app.mount("/", StaticFiles(directory="static", html=True), name="static")


# ---------------------------------------------------------
# LOCAL / RENDER ENTRYPOINT
# ---------------------------------------------------------
#
# Render assigns the port dynamically via the PORT env var - it does NOT
# use 8000. This lets "python main.py" work correctly as a Start Command
# too, as an alternative to setting the uvicorn command directly.

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
