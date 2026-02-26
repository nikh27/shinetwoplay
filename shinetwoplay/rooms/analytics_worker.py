import threading
import json
import logging
import time
import urllib.request
import redis
from django.conf import settings

logger = logging.getLogger('shinetwoplay.analytics')

def start_worker():
    """Starts the background analytics worker as a daemon thread."""
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
            # BLPOP blocks until an item is available or timeout (0 = wait forever)
            result = redis_client.blpop('shinetwoplay:analytics_queue', timeout=0)
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
            
            # Format and Log
            log_msg = (
                f"VISITOR | IP: {ip} | Loc: {city}, {country} | "
                f"ISP: {isp} | Device: {device} | Browser: {browser} | "
                f"Path: {data.get('method')} {data.get('path')} | "
                f"Status: {data.get('status_code')} | "
                f"Ref: {data.get('referer', 'None')}"
            )
            logger.info(log_msg)
            
            # rate limit slightly to avoid API bans (ip-api allows 45 req/min)
            time.sleep(1.5)
            
        except Exception as e:
            time.sleep(5)  # Backoff on error
