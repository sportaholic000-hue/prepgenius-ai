# PrepGenius AI

Your AI nutritionist. 60 seconds. Zero guesswork.

PrepGenius AI generates complete 7-day meal plans with macros, grocery lists, batch prep instructions, and cost estimates — powered by GPT-4o-mini.

## Features

- **Goal-Based Plans:** Cut, bulk, maintain, or recomp
- **Dietary Support:** Vegetarian, vegan, keto, gluten-free, dairy-free, halal, nut-free
- **Full Macro Breakdown:** Calories, protein, carbs, fat per meal and daily totals
- **Smart Grocery Lists:** Organized by store section (produce, protein, dairy, grains, pantry, frozen)
- **Cost Estimates:** Know your weekly grocery spend before you shop
- **Batch Prep Guide:** Sunday prep instructions to cook once, eat all week

## Tech Stack

- **Backend:** FastAPI (Python)
- **AI:** OpenAI GPT-4o-mini with structured JSON output
- **Validation:** Pydantic models
- **Deploy:** Docker + Render/Railway ready

## Quick Start

1. Clone the repo
2. Copy `.env.example` to `.env` and add your OpenAI API key
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn app:app --reload`
5. Visit: http://localhost:8000/docs

## API Endpoints

- `POST /api/generate-plan` — Generate a 7-day meal plan
- `GET /api/health` — Health check

## Pricing

- **Free:** 1 plan/week
- **Pro:** $9.99/mo — unlimited plans, PDF export, recipe scaling
- **Team:** $24.99/mo — family plans, shared calendar

## License

MIT