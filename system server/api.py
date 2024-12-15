from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json
from typing import List, Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # السماح لجميع الأصول (origins)
    allow_credentials=True,
    allow_methods=["*"],  # السماح لجميع الطرق HTTP
    allow_headers=["*"],  # السماح لجميع الترويسات
)

class Match(BaseModel):
    title: str
    team1: str
    team2: str
    team1_logo: str
    team2_logo: str
    start_time: str
    end_time: str
    commentator: str
    channel: str
    tournament: str
    watch_Id: str
    stream_url: Optional[str]  # إضافة رابط البث

class MatchesResponse(BaseModel):
    matches: List[Match]

def get_db_connection():
    conn = sqlite3.connect('matches.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/matches", response_model=MatchesResponse)
async def read_matches():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches")
    matches = cursor.fetchall()
    conn.close()

    if not matches:
        raise HTTPException(status_code=404, detail="No matches found")

    formatted_matches = [
        Match(
            title=match['title'],
            team1=match['team1_name'],
            team2=match['team2_name'],
            team1_logo=match['team1_logo'],
            team2_logo=match['team2_logo'],
            start_time=match['start_time'],
            end_time=match['end_time'],
            commentator=match['commentator'],
            channel=match['channel'],
            tournament=match['tournament'],
            watch_Id=match['watch_url'],
            stream_url=match['stream_url']  # إضافة رابط البث
        ) for match in matches
    ]

    return MatchesResponse(matches=formatted_matches)

@app.get("/matches/{match_id}", response_model=Match)
async def read_match(match_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
    match = cursor.fetchone()
    conn.close()

    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    return Match(
        title=match['title'],
        team1=match['team1_name'],
        team2=match['team2_name'],
        team1_logo=match['team1_logo'],
        team2_logo=match['team2_logo'],
        start_time=match['start_time'],
        end_time=match['end_time'],
        commentator=match['commentator'],
        channel=match['channel'],
        tournament=match['tournament'],
        watch_Id=match['watch_url'],
        stream_url=match['stream_url']  # إضافة رابط البث
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
