from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio

app = FastAPI()
# إضافة middleware الخاص بـ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # السماح لجميع الأصول (origins)
    allow_credentials=True,
    allow_methods=["*"],  # السماح لجميع الطرق HTTP
    allow_headers=["*"],  # السماح لجميع الترويسات
)

async def fetch_page(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        await asyncio.sleep(1)  # انتظار ثانية واحدة بعد كل طلب
        return response.content

async def print_match_div(match, index):
    print(f"\n--- معالجة المباراة {index + 1} ---")
    print("محتوى div الخاص بالمباراة:")
    print(match.prettify())  # طباعة محتوى div بتنسيق جميل
    print("----------------------------")
    await asyncio.sleep(0.1)  # تأخير صغير لضمان اكتمال الطباعة

@app.get("/matches")
async def get_matches():
    url = "https://kooora.bein-live.live/"
    content = await fetch_page(url)
    soup = BeautifulSoup(content, 'html.parser')
    
    matches = []
    for index, match in enumerate(soup.find_all('div', class_='match-event')):
        try:
            await print_match_div(match, index)
            
            # استخراج عنوان المباراة وروابط المشاهدة
            match_link = match.find('a', href=True)
            match_title = match_link['title'] if match_link else "غير متوفر"
            watch_url = match_link['href'] if match_link else "غير متوفر"
            
            # تعديل رابط المشاهدة لإزالة الجزء الأولي من URL
            if watch_url.startswith("https://kooora.bein-live.live/"):
                watch_url = watch_url.replace("https://kooora.bein-live.live/", "")
            
            # استخراج أسماء الفرق
            team_names = match.find_all('div', class_='team-name')
            team1 = team_names[0].text.strip() if len(team_names) > 0 else "غير متوفر"
            team2 = team_names[1].text.strip() if len(team_names) > 1 else "غير متوفر"
            
            # استخراج روابط الصور
            team_logos = match.find_all('img')
            team1_logo = team_logos[0].get('data-img') or team_logos[0].get('src') if len(team_logos) > 0 else "غير متوفر"
            team2_logo = team_logos[1].get('data-img') or team_logos[1].get('src') if len(team_logos) > 1 else "غير متوفر"
            
            # استخراج توقيت المباراة
            date_element = match.find('div', class_='date')
            start_time = date_element.get('data-start') if date_element else "غير متوفر"
            end_time = date_element.get('data-gameends') if date_element else "غير متوفر"
            
            # استخراج معلومات إضافية
            match_info = match.find('div', class_='match-info')
            info_items = match_info.find_all('li') if match_info else []
            commentator = info_items[0].text.strip() if len(info_items) > 0 else "غير متوفر"
            channel = info_items[1].text.strip() if len(info_items) > 1 else "غير متوفر"
            tournament = info_items[2].text.strip() if len(info_items) > 2 else "غير متوفر"
            
            match_info = {
                "title": match_title,
                "team1": team1,
                "team2": team2,
                "team1_logo": team1_logo,
                "team2_logo": team2_logo,
                "start_time": start_time,
                "end_time": end_time,
                "commentator": commentator,
                "channel": channel,
                "tournament": tournament,
                "watch_Id": watch_url
            }
            print(f"تمت معالجة المباراة {index + 1} بنجاح: {match_info}")
            matches.append(match_info)
        except Exception as e:
            print(f"خطأ في معالجة المباراة {index + 1}: {e}")
    
    if not matches:
        return {"error": "لم يتم العثور على أي مباريات"}
    
    print(f"تم العثور على {len(matches)} مباراة")
    print(f"إرجاع: {{'matches': {matches}}}")
    return {"matches": matches}

@app.get("/stream_links/{watch_Id:path}")
async def get_stream_links(watch_Id: str):
    url = f"https://kooora.bein-live.live/{watch_Id}"
    try:
        print(f"محاولة الوصول إلى الرابط: {url}")
        content = await fetch_page(url)
        soup = BeautifulSoup(content, 'html.parser')
        
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            iframe_url = iframe['src']
            print(f"تم العثور على iframe. الرابط: {iframe_url}")
            
            # جلب محتوى الـ iframe
            iframe_content = await fetch_page(iframe_url)
            iframe_soup = BeautifulSoup(iframe_content, 'html.parser')
            
            # البحث عن روابط البث داخل الـ iframe
            player_links = iframe_soup.find('ul', class_='albaplayer_name')
            if player_links:
                links = []
                for li in player_links.find_all('li'):
                    a_tag = li.find('a')
                    if a_tag and a_tag.has_attr('href'):
                        links.append({
                            'text': a_tag.text.strip(),
                            'href': a_tag['href'],
                            'is_active': 'active' in a_tag.get('class', [])
                        })
                print("تم العثور على روابط البث:")
                print(links)
                return {"links": links}
            else:
                print("لم يتم العثور على روابط البث داخل الـ iframe")
        else:
            print("لم يتم العثور على iframe في الصفحة")
        
        return {"error": "لم يتم العثور على روابط البث"}

    except Exception as e:
        print(f"حدث خطأ: {str(e)}")
        return {
            "error": f"حدث خطأ أثناء جلب روابط البث: {str(e)}",
            "url": url
        }

# يمكنك إضافة المزيد من النقاط النهائية (endpoints) حسب احتياجاتك
