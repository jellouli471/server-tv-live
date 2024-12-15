import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import json
import sqlite3
import schedule
import threading

def get_sports_channels():
    url = "https://tv.aflam4you.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    channels = []
    channel_list = soup.find('ul', class_='row pm-ul-browse-videos list-unstyled')
    
    if channel_list:
        for channel in channel_list.find_all('li'):
            channel_info = {}
            
            # استخراج اسم القناة
            channel_name = channel.find('h3').text.strip()
            channel_info['name'] = channel_name
            
            # استخراج رابط القناة
            channel_link = channel.find('a')['href']
            channel_info['link'] = channel_link
            
            # استخراج رابط الصورة
            img_tag = channel.find('img')
            if img_tag:
                channel_info['image'] = img_tag['src']
                channel_info['alt_text'] = img_tag['alt']
            
            # استخراج العنوان الكامل (title)
            title_tag = channel.find('a', title=True)
            if title_tag:
                channel_info['full_title'] = title_tag['title']
            
            channels.append(channel_info)
    
    return channels

def get_stream_url(channel_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(channel_url, headers=headers)
    
    analysis_results = analyze_page(response.content)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # البحث عن العنصر <a> الذي يحتوي على رابط البث
    stream_link = soup.find('a', class_='xtgo')
    if stream_link and 'href' in stream_link.attrs:
        # استخراج الرابط النسبي
        relative_url = stream_link['href']
        # تحويل الرابط النسبي إلى رابط مطلق
        base_url = urllib.parse.urljoin(channel_url, '/')
        absolute_url = urllib.parse.urljoin(base_url, relative_url)
        
        # الدخول إلى الرابط الجديد
        new_response = requests.get(absolute_url, headers=headers)
        
        new_soup = BeautifulSoup(new_response.content, 'html.parser')
        
        # البحث عن رابط البث في الصفحة الجديدة
        iframe = new_soup.find('iframe', id='video_player')
        if iframe and 'src' in iframe.attrs:
            return iframe['src'], analysis_results
    
    # إذا لم يتم العثور على الرابط، نبحث عن نص JavaScript
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and 'var video_url' in script.string:
            # استخراج رابط البث من النص البرمجي
            start = script.string.find("var video_url = '") + 17
            end = script.string.find("'", start)
            return script.string[start:end], analysis_results
    
    # إذا لم يتم العثور على الرابط
    return "No stream URL found", analysis_results

def analyze_page(content):
    soup = BeautifulSoup(content, 'html.parser')
    results = []
    
    # البحث عن جميع عناصر iframe
    iframes = soup.find_all('iframe')
    if iframes:
        results.append(f"Found {len(iframes)} iframe elements:")
        for i, iframe in enumerate(iframes, 1):
            src = iframe.get('src', 'No src')
            results.append(f"  {i}. src: {src}")
    else:
        results.append("No iframe elements found.")
    
    return "\n".join(results)

def save_to_sqlite(channels):
    conn = sqlite3.connect('sports_channels.db')
    cursor = conn.cursor()

    # إنشاء الجداول إذا لم تكن موجودة
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT,
                       link TEXT,
                       image TEXT,
                       alt_text TEXT,
                       full_title TEXT,
                       watch_link TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS page_analysis
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       channel_id INTEGER,
                       iframe_link TEXT,
                       FOREIGN KEY (channel_id) REFERENCES channels (id))''')

    # حذف البيانات القديمة
    cursor.execute('DELETE FROM page_analysis')
    cursor.execute('DELETE FROM channels')

    # إدخال البيانات الجديدة
    for channel in channels:
        cursor.execute('''INSERT INTO channels 
                          (name, link, image, alt_text, full_title, watch_link) 
                          VALUES (?, ?, ?, ?, ?, ?)''',
                       (channel['name'], channel['link'], channel['image'],
                        channel['alt_text'], channel['full_title'], channel['watch_link']))
        
        channel_id = cursor.lastrowid

        for iframe in channel['page_analysis']['iframes']:
            cursor.execute('''INSERT INTO page_analysis 
                              (channel_id, iframe_link) 
                              VALUES (?, ?)''',
                           (channel_id, iframe['watch_link']))

    conn.commit()
    conn.close()

def update_database():
    print("Updating database...")
    channels = get_sports_channels()
    
    print(f"Found {len(channels)} channels. Processing...")
    all_channels = []
    for i, channel in enumerate(channels, 1):
        print(f"Processing channel {i}/{len(channels)}: {channel['name']}")
        channel_info = {
            "name": channel['name'],
            "link": channel['link'],
            "image": channel.get('image', 'Not available'),
            "alt_text": channel.get('alt_text', 'Not available'),
            "full_title": channel.get('full_title', 'Not available')
        }
        
        stream_url, analysis_results = get_stream_url(channel['link'])
        channel_info["watch_link"] = stream_url
        channel_info["page_analysis"] = parse_analysis_results(analysis_results)
        
        all_channels.append(channel_info)
        
        # إضافة تأخير قصير بين الطلبات
        time.sleep(2)
    
    print("Saving data to SQLite...")
    save_to_sqlite(all_channels)
    print("Database updated successfully.")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def parse_analysis_results(analysis_results):
    parsed_results = {
        "iframes": []
    }
    
    for line in analysis_results.split('\n'):
        if line.startswith("  "):
            parts = line.split(": ", 1)
            if len(parts) == 2:
                parsed_results["iframes"].append({"watch_link": parts[1]})
    
    return parsed_results

def main():
    print("Starting the sports channels update service...")
    
    # تحديث قاعدة البيانات فورًا عند بدء التشغيل
    update_database()
    
    # جدولة التحديث كل 10 دقائق
    schedule.every(10).minutes.do(update_database)
    
    # تشغيل المجدول في خيط منفصل
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    
    print("Service is running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping the service...")

if __name__ == "__main__":
    main()