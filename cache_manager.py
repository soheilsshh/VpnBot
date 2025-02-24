from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import json
import os
from advanced_config import CACHE_SETTINGS, PATH_SETTINGS

class CacheManager:
    def __init__(self):
        self.memory_cache: Dict[str, Any] = {}
        self.disk_cache_dir = PATH_SETTINGS['cache_dir']
        os.makedirs(self.disk_cache_dir, exist_ok=True)
        
    async def get_from_memory(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        if key in self.memory_cache:
            data = self.memory_cache[key]
            if datetime.utcnow() < data['expire_time']:
                return data['value']
            else:
                del self.memory_cache[key]
        return None
        
    async def set_in_memory(self, key: str, value: Any, expire_seconds: int = None):
        """Set value in memory cache"""
        if not expire_seconds:
            expire_seconds = CACHE_SETTINGS['expire_time']
            
        self.memory_cache[key] = {
            'value': value,
            'expire_time': datetime.utcnow() + timedelta(seconds=expire_seconds)
        }
        
        # Cleanup if cache is too large
        if len(self.memory_cache) > CACHE_SETTINGS['max_size']:
            oldest_key = min(
                self.memory_cache.items(),
                key=lambda x: x[1]['expire_time']
            )[0]
            del self.memory_cache[oldest_key]
            
    async def get_from_disk(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        cache_file = os.path.join(self.disk_cache_dir, f"{key}.cache")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    if datetime.fromisoformat(data['expire_time']) > datetime.utcnow():
                        return data['value']
                    else:
                        os.remove(cache_file)
            except Exception:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
        return None
        
    async def set_in_disk(self, key: str, value: Any, expire_seconds: int = None):
        """Set value in disk cache"""
        if not expire_seconds:
            expire_seconds = CACHE_SETTINGS['expire_time']
            
        cache_file = os.path.join(self.disk_cache_dir, f"{key}.cache")
        data = {
            'value': value,
            'expire_time': (datetime.utcnow() + timedelta(seconds=expire_seconds)).isoformat()
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f)
            
    async def clear_expired(self):
        """Clear expired cache entries"""
        # Clear memory cache
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in self.memory_cache.items()
            if data['expire_time'] < now
        ]
        for key in expired_keys:
            del self.memory_cache[key]
            
        # Clear disk cache
        for filename in os.listdir(self.disk_cache_dir):
            if filename.endswith('.cache'):
                filepath = os.path.join(self.disk_cache_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if datetime.fromisoformat(data['expire_time']) < now:
                            os.remove(filepath)
                except Exception:
                    if os.path.exists(filepath):
                        os.remove(filepath) 