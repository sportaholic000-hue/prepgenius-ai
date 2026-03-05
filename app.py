"""
PrepGenius AI — FastAPI Backend
================================
AI-powered 7-day meal prep planner using OpenAI GPT-4o-mini.
Generates structured meal plans with macros, grocery lists, cost estimates,
and batch-prep instructions.
"""

import os
import json
import logging
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepgenius")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="PrepGenius AI",
    description="AI-powered 7-day meal prep planner with macros, grocery lists & batch-prep instructions.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — open for all origins (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate-limiting placeholder
# ---------------------------------------------------------------------------
# To add rate limiting, install `slowapi`:
#
#   pip install slowapi
#
# Then uncomment the following:
#
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded
#
# limiter = Limiter(key_func=get_remote_address)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
#
# Add `@limiter.limit("5/minute")` above any endpoint you want to throttle,
# and include `request: Request` as the first parameter.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pydantic models — Request
# ---------------------------------------------------------------------------
VALID_GOALS = {"cut", "bulk", "maintain", "recomp"}

VALID_RESTRICTIONS = {
    "vegan", "vegetarian", "pescatarian",
    "gluten-free", "dairy-free", "nut-free",
    "keto", "paleo", "low-fodmap", "halal", "kosher",
}


class MealPlanRequest(BaseModel):
    """Incoming request body for /api/generate-plan."""

    goal: str = Field(
        ...,
        description="Fitness goal: cut, bulk, maintain, or recomp.",
        examples=["cut"],
    )
    restrictions: list[str] = Field(
        default_factory=list,
        description="Dietary restrictions (e.g. vegan, gluten-free).",
        examples=[["vegan", "gluten-free"]],
    )
    details: Optional[str] = Field(
        None,
        max_length=500,
        description="Optional free-text preferences or constraints.",
        examples=["I hate broccoli. Budget under $80/week."],
    )

    def validate_goal(self) -> None:
        if self.goal.lower() not in VALID_GOALS:
            raise ValueError(
                f"Invalid goal '{self.goal}'. Must be one of: {', '.join(sorted(VALID_GOALS))}"
            )

    def validate_restrictions(self) -> None:
        bad = [r for r in self.restrictions if r.lower() not in VALID_RESTRICTIONS]
        if bad:
            raise ValueError(
                f"Unknown restriction(s): {', '.join(bad)}. "
                f"Allowed: {', '.join(sorted(VALID_RESTRICTIONS))}"
            )


# ---------------------------------------------------------------------------
# Pydantic models — Response (mirrors the JSON the LLM must produce)
# ---------------------------------------------------------------------------
class Macros(BaseModel):
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


class Meal(BaseModel):
    name: str
    description: str
    macros: Macros
    ingredients: list[str]
    prep_time_min: int


class DayPlan(BaseModel):
    day: str
    breakfast: Meal
    snack_1: Meal
    lunch: Meal
    snack_2: Meal
    dinner: Meal
    daily_totals: Macros


class GroceryItem(BaseModel):
    item: str
    quantity: str
    estimated_cost_usd: float


class GroceryList(BaseModel):
    produce: list[GroceryItem]
    protein: list[GroceryItem]
    dairy: list[GroceryItem]
    grains: list[GroceryItem]
    pantry: list[GroceryItem]
    frozen: list[GroceryItem]


class BatchPrepStep(BaseModel):
    step_number: int
    task: str
    duration_min: int
    tips: str


class MealPlanResponse(BaseModel):
    goal: str
    restrictions: list[str]
    weekly_calorie_target: int
    days: list[DayPlan]
    grocery_list: GroceryList
    estimated_weekly_cost_usd: float
    batch_prep_instructions: list[BatchPrepStep]
    storage_tips: list[str]


# ---------------------------------------------------------------------------
# OpenAI prompt engineering
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are PrepGenius AI, a world-class sports-nutrition coach and meal-prep expert.

RULES:
1. Generate a COMPLETE 7-day meal plan (Monday through Sunday).
2. Each day has exactly 5 meals: breakfast, snack_1, lunch, snack_2, dinner.
3. Every meal includes realistic macros (calories, protein_g, carbs_g, fat_g), \
a short ingredient list, and prep_time_min.
4. Daily macro totals MUST equal the sum of the 5 meals for that day.
5. The plan must be nutritionally sound, goal-appropriate, and respect ALL \
dietary restrictions provided by the user.
6. Generate a consolidated grocery list split into sections: produce, protein, \
dairy, grains, pantry, frozen. Each item has a quantity and estimated_cost_usd.
7. estimated_weekly_cost_usd is the sum of all grocery item costs, rounded to 2 decimals.
8. Provide 6-10 batch_prep_instructions for a Sunday meal-prep session. \
Each step has step_number, task, duration_min, and tips.
9. Include 3-5 storage_tips for keeping prepped food fresh all week.
10. Prefer whole, nutrient-dense foods over processed. Vary proteins and \
vegetables across the week for micronutrient coverage.
11. Keep meals practical — most people have 15-30 min for weekday cooking. \
Batch-preppable meals are preferred.
12. Respond with ONLY the JSON object — no markdown fences, no commentary, \
no extra whitespace outside the object.

CALORIE TARGETS BY GOAL (adjust +/- based on user details if provided):
- cut:      1,600-1,800 kcal/day, protein >= 40%% of calories
- maintain: 2,000-2,200 kcal/day, balanced macros
- bulk:     2,800-3,200 kcal/day, caloric surplus with adequate protein
- recomp:   2,000-2,400 kcal/day, high protein (>= 35%%), moderate carbs

GROCERY COST GUIDELINES (2026 US averages):
- Budget-friendly plans: $60-$90/week
- Standard plans: $90-$130/week
- Premium/specialty diets: $120-$170/week
"""


def build_user_prompt(req: MealPlanRequest) -> str:
    """Build the user message from the validated request."""
    parts = [f"Goal: {req.goal}"]
    if req.restrictions:
        parts.append(f"Dietary restrictions: {', '.join(req.restrictions)}")
    else:
        parts.append("Dietary restrictions: none")
    if req.details:
        parts.append(f"Additional preferences: {req.details}")
    parts.append(
        "\nGenerate the full 7-day meal plan as a single JSON object "
        "matching the schema exactly. Do not wrap in markdown."
    )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# JSON schema for structured output (OpenAI response_format)
# ---------------------------------------------------------------------------
RESPONSE_JSON_SCHEMA = {
    "name": "meal_plan",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "restrictions": {"type": "array", "items": {"type": "string"}},
            "weekly_calorie_target": {"type": "integer"},
            "days": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day": {"type": "string"},
                        "breakfast": {"$ref": "#/$defs/meal"},
                        "snack_1": {"$ref": "#/$defs/meal"},
                        "lunch": {"$ref": "#/$defs/meal"},
                        "snack_2": {"$ref": "#/$defs/meal"},
                        "dinner": {"$ref": "#/$defs/meal"},
                        "daily_totals": {"$ref": "#/$defs/macros"},
                    },
                    "required": [
                        "day", "breakfast", "snack_1", "lunch",
                        "snack_2", "dinner", "daily_totals",
                    ],
                    "additionalProperties": False,
                },
            },
            "grocery_list": {
                "type": "object",
                "properties": {
                    "produce": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/grocery_item"},
                    },
                    "protein": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/grocery_item"},
                    },
                    "dairy": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/grocery_item"},
                    },
                    "grains": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/grocery_item"},
                    },
                    "pantry": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/grocery_item"},
                    },
                    "frozen": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/grocery_item"},
                    },
                },
                "required": [
                    "produce", "protein", "dairy",
                    "grains", "pantry", "frozen",
                ],
                "additionalProperties": False,
            },
            "estimated_weekly_cost_usd": {"type": "number"},
            "batch_prep_instructions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_number": {"type": "integer"},
                        "task": {"type": "string"},
                        "duration_min": {"type": "integer"},
                        "tips": {"type": "string"},
                    },
                    "required": ["step_number", "task", "duration_min", "tips"],
                    "additionalProperties": False,
                },
            },
            "storage_tips": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "goal", "restrictions", "weekly_calorie_target", "days",
            "grocery_list", "estimated_weekly_cost_usd",
            "batch_prep_instructions", "storage_tips",
        ],
        "additionalProperties": False,
        "$defs": {
            "macros": {
                "type": "object",
                "properties": {
                    "calories": {"type": "integer"},
                    "protein_g": {"type": "integer"},
                    "carbs_g": {"type": "integer"},
                    "fat_g": {"type": "integer"},
                },
                "required": ["calories", "protein_g", "carbs_g", "fat_g"],
                "additionalProperties": False,
            },
            "meal": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "macros": {"$ref": "#/$defs/macros"},
                    "ingredients": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "prep_time_min": {"type": "integer"},
                },
                "required": [
                    "name", "description", "macros",
                    "ingredients", "prep_time_min",
                ],
                "additionalProperties": False,
            },
            "grocery_item": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "string"},
                    "estimated_cost_usd": {"type": "number"},
                },
                "required": ["item", "quantity", "estimated_cost_usd"],
                "additionalProperties": False,
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["System"])
async def health_check():
    """Simple health check — returns 200 if the service is alive."""
    return {
        "status": "healthy",
        "service": "PrepGenius AI",
        "version": "1.0.0",
        "model": OPENAI_MODEL,
    }


@app.post(
    "/api/generate-plan",
    response_model=MealPlanResponse,
    tags=["Meal Plans"],
    summary="Generate a 7-day AI meal plan",
)
async def generate_plan(body: MealPlanRequest, request: Request):
    """
    Generate a full 7-day meal plan powered by GPT-4o-mini.

    Accepts a fitness goal, dietary restrictions, and optional free-text
    preferences. Returns structured JSON with daily meals (5 per day),
    per-meal and daily macros, a categorized grocery list with cost
    estimates, and Sunday batch-prep instructions.
    """

    # --- Validate inputs ------------------------------------------------
    try:
        body.validate_goal()
        body.validate_restrictions()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Normalize
    body.goal = body.goal.lower().strip()
    body.restrictions = [r.lower().strip() for r in body.restrictions]

    # --- Ensure API key is configured -----------------------------------
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is not set.")
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: OpenAI API key is not set. "
                   "Set OPENAI_API_KEY in your .env file.",
        )

    # --- Call OpenAI ----------------------------------------------------
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    logger.info(
        "Generating meal plan | goal=%s restrictions=%s details=%s",
        body.goal,
        body.restrictions,
        body.details or "(none)",
    )

    try:
        completion = await client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.7,
            max_tokens=16_000,
            response_format={
                "type": "json_schema",
                "json_schema": RESPONSE_JSON_SCHEMA,
            },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(body)},
            ],
        )
    except OpenAIError as exc:
        logger.exception("OpenAI API error")
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {exc}",
        )

    # --- Parse the response ---------------------------------------------
    raw = completion.choices[0].message.content
    if not raw:
        raise HTTPException(status_code=502, detail="AI returned an empty response.")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse AI response as JSON: %s", raw[:500])
        raise HTTPException(
            status_code=502,
            detail="AI returned invalid JSON. Please try again.",
        )

    # Validate against our Pydantic response model
    try:
        plan = MealPlanResponse(**data)
    except Exception as exc:
        logger.error("Pydantic validation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI response did not match expected schema. Please try again.",
        )

    logger.info(
        "Meal plan generated successfully | weekly_kcal_target=%s cost=$%.2f",
        plan.weekly_calorie_target,
        plan.estimated_weekly_cost_usd,
    )
    return plan


# ---------------------------------------------------------------------------
# Global exception handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ---------------------------------------------------------------------------
# Dev entry point: python app.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)