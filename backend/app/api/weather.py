"""Weather API for JARVIS (Open-Meteo, no API key required)."""
from fastapi import APIRouter, Query

from app.services import weather as weather_service

router = APIRouter(tags=["weather"])


@router.get("/weather")
async def get_weather(city: str = Query("Hyderabad", min_length=1, max_length=80)):
    return await weather_service.current(city)
