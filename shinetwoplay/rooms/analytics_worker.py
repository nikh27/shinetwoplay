import threading
import json
import logging
import time
import urllib.request
import redis
from django.conf import settings

# Initialize Loggers
home_logger = logging.getLogger('shinetwoplay.analytics.home')
room_logger = logging.getLogger('shinetwoplay.analytics.room')

def start_worker():
    """Starts the background analytics worker as a daemon thread."""
    print("[*] Analytics Background Worker is waking up and watching Redis queues...")
    thread = threading.Thread(target=run_worker, daemon=True)
    thread.start()

def run_worker():
    """Continuously processes analytics events from Redis."""
    try:
        redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', '127.0.0.1'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            db=getattr(settings, 'REDIS_DB', 0),
            decode_responses=True
        )
    except Exception as e:
        print(f"Analytics Worker Failed to Connect to Redis: {e}")
        return

    while True:
        try:
            # BLPOP blocks until an item is available in EITHER queue
            result = redis_client.blpop(['shinetwoplay:analytics_home', 'shinetwoplay:analytics_room'], timeout=0)
            if not result:
                continue
            
            queue_name, raw_data = result
            data = json.loads(raw_data)
            
            ip = data.get('ip', 'Unknown')
            # Local IP Check
            if ip in ['127.0.0.1', 'localhost', '::1', 'Unknown']:
                country, city, isp = 'Local', 'Local', 'Local'
            else:
                # API Lookup
                try:
                    url = f'http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp'
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=3) as response:
                        api_data = json.loads(response.read().decode())
                        if api_data.get('status') == 'success':
                            country = api_data.get('country', 'N/A')
                            city = f"{api_data.get('city', 'N/A')}, {api_data.get('regionName', '')}"
                            isp = api_data.get('isp', 'N/A')
                        else:
                            country, city, isp = 'Unknown', 'Unknown', 'Unknown'
                except Exception:
                    country, city, isp = 'Error', 'Error', 'Error'
                    
            # Parse User Agent briefly
            ua = data.get('user_agent', '')
            device = "Mobile" if "Mobi" in ua else "Desktop"
            browser = ua.split()[-1] if ua else "Unknown"
            
            # Format and Log based on Queue
            if queue_name == 'shinetwoplay:analytics_home':
                log_msg = (
                    f"HOME VISITOR | IP: {ip} | Loc: {city}, {country} | "
                    f"ISP: {isp} | Device: {device} | Browser: {browser} | "
                    f"Ref: {data.get('referer', 'None')}"
                )
                home_logger.info(log_msg)
                
            elif queue_name == 'shinetwoplay:analytics_room':
                # Room queue includes Name and Gender
                name = data.get('name', 'Unknown')
                gender = data.get('gender', 'Unknown')
                room_path = data.get('path', 'Unknown')
                log_msg = (
                    f"ROOM VISITOR | Room: {room_path} | Name: {name} | Gender: {gender} | "
                    f"IP: {ip} | Loc: {city}, {country} | "
                    f"ISP: {isp} | Device: {device} | Browser: {browser} | "
                    f"Ref: {data.get('referer', 'None')}"
                )
                room_logger.info(log_msg)
            
            # Rate limit slightly to avoid API bans (ip-api allows 45 req/min)
            time.sleep(1.5)
            
        except Exception as e:
            time.sleep(5)  # Backoff on error
