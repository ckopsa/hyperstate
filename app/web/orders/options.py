# app/web/orders/options.py

from fastapi import APIRouter, Query
from app.hyperstate.dependencies import OptionsResponse
from app.hyperstate.fields import FieldOption

router = APIRouter(prefix="/api", tags=["options"])

# Static data — in practice this might query a database
REGIONS = {
    "US": [
        FieldOption(value="AL", label="Alabama"),
        FieldOption(value="AK", label="Alaska"),
        FieldOption(value="UT", label="Utah"),
        FieldOption(value="WY", label="Wyoming"),
    ],
    "CA": [
        FieldOption(value="AB", label="Alberta"),
        FieldOption(value="BC", label="British Columbia"),
        FieldOption(value="ON", label="Ontario"),
    ],
    "MX": [
        FieldOption(value="AGU", label="Aguascalientes"),
        FieldOption(value="BCN", label="Baja California"),
    ],
}


@router.get("/regions", response_model=OptionsResponse)
async def get_regions(country: str = Query(...)):
    return OptionsResponse(options=REGIONS.get(country, []))
