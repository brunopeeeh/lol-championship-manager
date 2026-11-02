"""Environment settings shared by HTTP readers and the administrative importer."""
import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT/'.env',override=False)

def storage():
    return os.getenv('LCM_STORAGE','sqlite')

def supabase_config(admin=False):
    url=os.getenv('SUPABASE_URL','').rstrip('/')
    key=os.getenv('SUPABASE_SERVICE_KEY' if admin else 'SUPABASE_PUBLISHABLE_KEY','')
    if not url.startswith('https://') or not key:
        raise RuntimeError('Supabase environment is not configured')
    return url,key
