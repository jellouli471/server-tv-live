import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import schedule
import time
from datetime import datetime
import re

def clean_and_organize_stream_links(links):
    cleaned_links = []
    seen_urls = set()
    
    for link in links:
        url = link['url']
        name = link['name']
        
        # تجاهل الروابط المكررة
        if url in seen_urls:
            continue
        
        # تجاهل روابط وسائل التواصل الاجتماعي والصفحات الرئيسية
        if any(domain in url for domain in ['facebook.com', 'twitter.com', 't.me', 'bein-live.live']):
            continue
        
        # تجاهل الروابط التي لا تبدو كروابط بث
        if not any(keyword in url.lower() for keyword in ['player', 'stream', 'watch', 'live', 'embed']):
            continue
        
        cleaned_links.append({'url': url, 'name': name})
        seen_urls.add(url)
    
    return cleaned_links

def get_stream_links_from_watch_page(watch_url):
    try:
        print(f"جاري الدخول إلى رابط المشاهدة: {watch_url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(watch_url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        
        # البحث عن العنصر <ul> بالفئة albaplayer_name
        ul_element = soup.find('ul', class_='albaplayer_name')
        if ul_element:
            for li in ul_element.find_all('li'):
                a_tag = li.find('a')
                if a_tag and 'href' in a_tag.attrs:
                    href = a_tag['href']
                    stream_name = a_tag.text.strip()
                    if 'albaplayer' in href:  # تأكد من أن الرابط هو رابط بث فعلي
                        links.append({'url': href, 'name': stream_name})
        
        # إذا لم نجد روابط البث في القائمة، نبحث في النص
        if not links:
            iframe_tags = soup.find_all('iframe')
            for iframe in iframe_tags:
                src = iframe.get('src', '')
                if 'embed' in src or 'player' in src:
                    links.append({'url': src, 'name': 'Embedded Player'})
        
        # تنظيف وتنظيم الروابط
        cleaned_links = clean_and_organize_stream_links(links)
        
        print(f"تم العثور على {len(cleaned_links)} رابط بث صالح في {watch_url}")
        for link in cleaned_links:
            print(f"رابط البث: {link['name']} - {link['url']}")
        
        time.sleep(5)
        return cleaned_links
    except Exception as e:
        print(f"خطأ في استخراج روابط البث من {watch_url}: {str(e)}")
        return []

def get_matches():
    url = "https://kooora.bein-live.live/"
    
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"فشل في الحصول على الصفحة. كود الحالة: {response.status_code}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    matches = []
    for match in soup.find_all('div', class_='match-event'):
        try:
            # استخراج عنوان المباراة وروابط المشاهدة
            match_link = match.find('a', href=True)
            match_title = match_link['title'] if match_link else "غير متوفر"
            watch_url = match_link['href'] if match_link else "غير متوفر"
            
            # تصحيح رابط المشاهدة
            if watch_url.startswith('http'):
                full_watch_url = watch_url
            else:
                full_watch_url = url + watch_url.lstrip('/')
            
            # استخراج روابط البث من صفحة المشاهدة
            stream_links = get_stream_links_from_watch_page(full_watch_url)
            
            # استخراج معلومات الفريق الأول
            team1_div = match.find('div', class_='right-team')
            team1_name = team1_div.find('div', class_='team-name').text.strip()
            team1_logo = team1_div.find('img')['data-img']
            
            # استخراج معلومات الفريق الثاني
            team2_div = match.find('div', class_='left-team')
            team2_name = team2_div.find('div', class_='team-name').text.strip()
            team2_logo = team2_div.find('img')['data-img']
            
            # استخراج معلومات التوقيت
            match_timing = match.find('div', class_='match-timing')
            match_time = match_timing.find('div', id='match-time').text.strip()
            match_status = match_timing.find('div', class_='date')
            match_start = match_status['data-start']
            match_end = match_status['data-gameends']
            match_status_text = match_status.text.strip()
            
            # استخراج النتيجة إذا كانت متاحة
            result = match_timing.find('div', id='result').text.strip() if match_timing.find('div', id='result') else "غير متاح"
            
            # استخراج معلومات إضافية
            match_info = match.find('div', class_='match-info')
            info_items = match_info.find_all('li')
            commentator = info_items[0].text.strip() if len(info_items) > 0 else "غير متوفر"
            channel = info_items[1].text.strip() if len(info_items) > 1 else "غير متوفر"
            tournament = info_items[2].text.strip() if len(info_items) > 2 else "غير متوفر"
            
            match_info = {
                "title": match_title,
                "team1": {
                    "name": team1_name,
                    "logo": team1_logo
                },
                "team2": {
                    "name": team2_name,
                    "logo": team2_logo
                },
                "time": match_time,
                "start_time": match_start,
                "end_time": match_end,
                "status": match_status_text,
                "result": result,
                "commentator": commentator,
                "channel": channel,
                "tournament": tournament,
                "watch_url": full_watch_url,
                "stream_links": stream_links
            }
            matches.append(match_info)
            
            print(f"تم استخراج بيانات المباراة: {match_title}")
            print(f"رابط المشاهدة: {full_watch_url}")
            print(f"عدد روابط البث: {len(stream_links)}")
            print("-" * 50)
        except Exception as e:
            print(f"خطأ في معالجة المباراة: {e}")
    
    return matches

def create_table():
    conn = sqlite3.connect('matches.db')
    c = conn.cursor()
    
    # إنشاء جدول المباريات مع تضمين رابط البث
    c.execute('''CREATE TABLE IF NOT EXISTS matches
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  team1_name TEXT,
                  team1_logo TEXT,
                  team2_name TEXT,
                  team2_logo TEXT,
                  start_time TEXT,
                  end_time TEXT,
                  status TEXT,
                  result TEXT,
                  commentator TEXT,
                  channel TEXT,
                  tournament TEXT,
                  watch_url TEXT,
                  stream_url TEXT)''')
    
    conn.commit()
    conn.close()

def save_to_sqlite(matches):
    conn = sqlite3.connect('matches.db')
    c = conn.cursor()
    
    # حذف البيانات القديمة
    c.execute('DELETE FROM matches')
    
    for match in matches:
        # استخراج رابط البث الأول (إذا وجد)
        stream_url = match['stream_links'][0]['url'] if match['stream_links'] else None
        
        # إدخال بيانات المباراة مع رابط البث
        c.execute('''INSERT INTO matches 
                     (title, team1_name, team1_logo, team2_name, team2_logo,
                      start_time, end_time, status, result, commentator,
                      channel, tournament, watch_url, stream_url)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (match['title'],
                   match['team1']['name'], match['team1']['logo'],
                   match['team2']['name'], match['team2']['logo'],
                   match['start_time'], match['end_time'],
                   match['status'], match['result'],
                   match['commentator'], match['channel'],
                   match['tournament'], match['watch_url'],
                   stream_url))
    
    conn.commit()
    conn.close()
    print(f"تم تحديث البيانات في قاعدة البيانات SQLite بنجاح. ({datetime.now()})")

# تأكد من استدعاء هذه الدالة عند بدء تشغيل البرنامج
create_table()

# استخدم هذه الدالة لحفظ البيانات بعد كل تحديث
# save_to_sqlite(matches)

def update_and_print_data():
    matches = get_matches()
    print("\n=== المباريات المتاحة ===\n")
    for index, match in enumerate(matches, 1):
        print(f"المباراة {index}:")
        print(f"العنوان: {match['title']}")
        print(f"الفريق الأول: {match['team1']['name']} (شعار: {match['team1']['logo']})")
        print(f"الفريق الثاني: {match['team2']['name']} (شعار: {match['team2']['logo']})")
        print(f"التوقيت: {match['time']}")
        print(f"بداية المباراة: {match['start_time']}")
        print(f"نهاية المباراة: {match['end_time']}")
        print(f"الحالة: {match['status']}")
        print(f"النتيجة: {match['result']}")
        print(f"المعلق: {match['commentator']}")
        print(f"القناة: {match['channel']}")
        print(f"البطولة: {match['tournament']}")
        print(f"رابط المشاهدة: {match['watch_url']}")
        
        # طباعة روابط البث المنظمة
        stream_links = match['stream_links']
        if stream_links:
            print(f"روابط البث ({len(stream_links)}):")
            for link in stream_links:
                print(f"  - {link['name']}: {link['url']}")
        else:
            print("لا توجد روابط بث متاحة")
        
        print("\n" + "-"*50 + "\n")
    
    save_to_sqlite(matches)
    print(f"تم تحديث وطباعة البيانات بنجاح. ({datetime.now()})")

# جدولة تحديث قاعدة البيانات كل 5 دقائق
schedule.every(5).minutes.do(update_and_print_data)

if __name__ == "__main__":
    print("بدء تشغيل البرنامج. سيتم طباعة البيانات في الـ terminal.")
    update_and_print_data()  # تحديث فوري عند بدء التشغيل
    while True:
        schedule.run_pending()
        time.sleep(1)