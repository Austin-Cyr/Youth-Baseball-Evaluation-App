from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import db

app = FastAPI(title="Player Evaluation App")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def client_ip(request: Request) -> str:
    """Prefer X-Forwarded-For (if behind a proxy/load balancer), fall back to direct connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def require_valid_division_sport(division: str, sport: str):
    if not db.division_sport_valid(division, sport):
        raise HTTPException(status_code=404, detail="Unknown division/sport combination")


@app.get("/evaluate/{division}/{sport}", response_class=HTMLResponse)
def list_skills(request: Request, division: str, sport: str):
    require_valid_division_sport(division, sport)
    skills = db.get_skills()
    return templates.TemplateResponse(
        "skills.html",
        {"request": request, "division": division, "sport": sport, "skills": skills},
    )


@app.get("/evaluate/{division}/{sport}/{skill_id}", response_class=HTMLResponse)
def evaluate_skill(request: Request, division: str, sport: str, skill_id: int):
    require_valid_division_sport(division, sport)
    skill = db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Unknown skill")
    players = db.get_unevaluated_players(division, sport, skill_id)
    return templates.TemplateResponse(
        "evaluate.html",
        {
            "request": request,
            "division": division,
            "sport": sport,
            "skill": skill,
            "players": players,
        },
    )


class RatingSubmission(BaseModel):
    score: int


class ManualSubmission(BaseModel):
    first_name: str
    last_name: str
    score: int


@app.post("/api/evaluate/{division}/{sport}/{skill_id}/player/{id_reg}")
def submit_rating(request: Request, division: str, sport: str, skill_id: int, id_reg: int, body: RatingSubmission):
    require_valid_division_sport(division, sport)
    skill = db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Unknown skill")
    if not (skill["min_score"] <= body.score <= skill["max_score"]):
        raise HTTPException(status_code=400, detail="Score out of range for this skill")

    db.insert_registered_eval(id_reg, skill_id, body.score, client_ip(request))
    return JSONResponse({"status": "ok"})


@app.post("/api/evaluate/{division}/{sport}/{skill_id}/manual")
def submit_manual_rating(request: Request, division: str, sport: str, skill_id: int, body: ManualSubmission):
    require_valid_division_sport(division, sport)
    skill = db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Unknown skill")
    if not (skill["min_score"] <= body.score <= skill["max_score"]):
        raise HTTPException(status_code=400, detail="Score out of range for this skill")
    if not body.first_name.strip() or not body.last_name.strip():
        raise HTTPException(status_code=400, detail="First and last name are required")

    db.insert_manual_eval(
        body.first_name.strip(), body.last_name.strip(), skill_id, body.score, client_ip(request)
    )
    return JSONResponse({"status": "ok"})
