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


def require_valid_combo(sport: str, division: str):
    if not db.division_sport_valid(division, sport):
        raise HTTPException(status_code=404, detail="Unknown sport/division combination")


@app.get("/evaluate/{sport}/{year}/{season}/{division}", response_class=HTMLResponse)
def list_skill_groups(request: Request, sport: str, year: int, season: str, division: str):
    require_valid_combo(sport, division)
    division_id = db.get_division_id(division)
    if not division_id:
        raise HTTPException(status_code=404, detail="Unknown division")
    skill_groups = db.get_skill_groups(division_id)
    return templates.TemplateResponse(
        "skill_groups.html",
        {
            "request": request,
            "sport": sport,
            "year": year,
            "season": season,
            "division": division,
            "skill_groups": skill_groups,
        },
    )


@app.get("/evaluate/{sport}/{year}/{season}/{division}/{skill_group_id}", response_class=HTMLResponse)
def select_player(request: Request, sport: str, year: int, season: str, division: str, skill_group_id: int):
    require_valid_combo(sport, division)
    division_id = db.get_division_id(division)
    if not division_id:
        raise HTTPException(status_code=404, detail="Unknown division")
    
    skill_group = db.get_skill_groups(division_id)
    if not any(g["id_skill_group"] == skill_group_id for g in skill_group):
        raise HTTPException(status_code=404, detail="Unknown skill group")
    
    group_name = next((g["group_name"] for g in skill_group if g["id_skill_group"] == skill_group_id), None)
    players = db.get_unevaluated_players_for_group(division, sport, year, season, skill_group_id)
    
    return templates.TemplateResponse(
        "group_players.html",
        {
            "request": request,
            "sport": sport,
            "year": year,
            "season": season,
            "division": division,
            "skill_group_id": skill_group_id,
            "group_name": group_name,
            "players": players,
        },
    )


@app.get("/evaluate/{sport}/{year}/{season}/{division}/{skill_group_id}/{player_id}/{position}", response_class=HTMLResponse)
def evaluate_group_skill(
    request: Request, sport: str, year: int, season: str, division: str, skill_group_id: int, player_id: int, position: int
):
    require_valid_combo(sport, division)
    division_id = db.get_division_id(division)
    if not division_id:
        raise HTTPException(status_code=404, detail="Unknown division")
    
    # Get the skill at this position
    skill = db.get_skill_at_position(skill_group_id, position)
    if not skill:
        raise HTTPException(status_code=404, detail="Unknown position in group")
    
    # Get all skills in the group to show progress
    all_skills = db.get_skills_in_group(skill_group_id)
    
    # Get criteria for this skill/division
    criteria = db.get_skill_criteria(skill["id_eval_skill"], division_id)
    
    # Get player info
    player = db.get_player_by_id(player_id, division, sport, year, season)
    if not player:
        raise HTTPException(status_code=404, detail="Unknown player")
    
    return templates.TemplateResponse(
        "evaluate_group_skill.html",
        {
            "request": request,
            "sport": sport,
            "year": year,
            "season": season,
            "division": division,
            "skill_group_id": skill_group_id,
            "player_id": player_id,
            "player": player,
            "skill": skill,
            "criteria": criteria,
            "position": position,
            "total_skills": len(all_skills),
        },
    )


class RatingSubmission(BaseModel):
    score: int


@app.post("/api/evaluate/{sport}/{year}/{season}/{division}/{skill_group_id}/{player_id}/{skill_id}")
def submit_group_rating(
    request: Request, sport: str, year: int, season: str, division: str, skill_group_id: int, player_id: int, skill_id: int,
    body: RatingSubmission,
):
    require_valid_combo(sport, division)
    division_id = db.get_division_id(division)
    if not division_id:
        raise HTTPException(status_code=404, detail="Unknown division")
    
    skill = db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Unknown skill")
    if not (skill["min_score"] <= body.score <= skill["max_score"]):
        raise HTTPException(status_code=400, detail="Score out of range for this skill")

    db.insert_registered_eval(player_id, skill_id, body.score, client_ip(request))
    
    # Return the next position (or signal completion)
    current_position = db.get_position_in_group(skill_group_id, skill_id)
    all_skills = db.get_skills_in_group(skill_group_id)
    next_position = current_position + 1 if current_position < len(all_skills) else None
    
    return JSONResponse({
        "status": "ok",
        "next_position": next_position
    })
