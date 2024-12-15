from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # السماح لجميع الأصول (origins)
    allow_credentials=True,
    allow_methods=["*"],  # السماح لجميع الطرق HTTP
    allow_headers=["*"],  # السماح لجميع الترويسات
)

class IFrame(BaseModel):
    watch_link: str

class PageAnalysis(BaseModel):
    iframes: List[IFrame]

class Channel(BaseModel):
    name: str
    link: str
    image: str
    alt_text: str
    full_title: str
    watch_link: str
    page_analysis: PageAnalysis

def get_db_connection():
    conn = sqlite3.connect('sports_channels.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/channels", response_model=List[Channel])
async def get_all_channels():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''SELECT c.*, GROUP_CONCAT(pa.iframe_link, '|') as iframes
                      FROM channels c
                      LEFT JOIN page_analysis pa ON c.id = pa.channel_id
                      GROUP BY c.id''')
    
    rows = cursor.fetchall()
    conn.close()

    channels = []
    for row in rows:
        channel = Channel(
            name=row['name'],
            link=row['link'],
            image=row['image'],
            alt_text=row['alt_text'],
            full_title=row['full_title'],
            watch_link=row['watch_link'],
            page_analysis=PageAnalysis(
                iframes=[IFrame(watch_link=link) for link in row['iframes'].split('|') if link]
            )
        )
        channels.append(channel)

    return channels
