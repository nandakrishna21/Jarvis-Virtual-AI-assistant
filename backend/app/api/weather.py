"""Weather API for JARVIS (Open-Meteo, no API key required)."""
from fastapi import APIRouter

from app.services import weather as weather_service

router = APIRouter(tags=["weather"])


@router.get("/weather")
async def get_weather(city: str = "Hyderabad"):
    return await weather_service.current(city)
