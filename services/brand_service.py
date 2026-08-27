"""
Brand Memory & Voice Profiling Service
Hardened with NULL Database Protections and Zero-Division Guards.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from db.repository import (
    get_active_brand, get_brand, list_brands, switch_active_brand,
    create_brand, get_connection
)

logger = logging.getLogger("clawagent.brand")

class BrandService:
    def __init__(self):
        pass

    def get_active(self) -> Dict[str, Any]:
        brand = get_active_brand()
        if not brand:
            return {
                "id": 1,
                "name": "DefaultBrand",
                "tone_of_voice": "casual, engaging, authentic",
                "color_palette": "[]",
                "prohibited_words": "",
                "mandatory_elements": "",
                "sample_hooks": "[]"
            }
        return brand

    def get_by_id(self, brand_id: int) -> Optional[Dict[str, Any]]:
        return get_brand(brand_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return list_brands()

    def switch_brand(self, name: str) -> bool:
        if not name:
            return False
        return switch_active_brand(name.strip())

    def create(self, name: str, tone_of_voice: str = "casual", color_palette: Optional[List[str]] = None) -> int:
        clean_name = str(name or "").strip()
        clean_tone = str(tone_of_voice or "casual").strip()
        return create_brand(clean_name, clean_tone, color_palette)

    def update_profile(self, brand_id: int, updates: Dict[str, Any]) -> bool:
        conn = get_connection()
        try:
            fields = []
            values = []
            for k, v in updates.items():
                if k in ("name", "tone_of_voice", "color_palette", "typography_style",
                         "visual_mood", "logo_url", "avg_sentence_length", "emoji_frequency",
                         "emoji_style", "hashtag_count_range", "prohibited_words",
                         "mandatory_elements", "sample_hooks", "instagram_user_id",
                         "linkedin_urn", "twitter_handle", "youtube_channel_id"):
                    fields.append(f"{k} = ?")
                    values.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
            
            if not fields:
                return False
            
            values.append(brand_id)
            query = f"UPDATE brands SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            conn.execute(query, values)
            conn.commit()
            return True
        finally:
            conn.close()

    def analyze_brand_voice(self, brand_id: int) -> Dict[str, Any]:
        """
        Analyzes historical captions to learn voice parameters.
        Guarded against empty post histories and single-word/emoji captions.
        """
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT caption FROM posts WHERE brand_id = ? AND caption IS NOT NULL AND caption != '' ORDER BY id DESC LIMIT 50",
                (brand_id,)
            ).fetchall()
            
            if not rows:
                default_analysis = {
                    "avg_sentence_length": 15.0,
                    "emoji_frequency": 2.0,
                    "hashtag_count_range": "5-7",
                    "sample_hooks": []
                }
                self.update_profile(brand_id, default_analysis)
                return default_analysis
            
            captions = [str(r["caption"] or "") for r in rows if r["caption"]]
            total_captions = len(captions)
            if total_captions == 0:
                return {
                    "avg_sentence_length": 15.0,
                    "emoji_frequency": 2.0,
                    "hashtag_count_range": "5-7",
                    "sample_hooks": []
                }
            
            # 1. Emoji frequency
            emoji_pattern = re.compile(
                "[\U00010000-\U0010ffff]|[\u2600-\u26ff]|[\u2700-\u27bf]",
                flags=re.UNICODE
            )
            total_emojis = sum(len(emoji_pattern.findall(c)) for c in captions)
            avg_emojis = round(total_emojis / total_captions, 1)
            
            # 2. Hashtags
            hashtag_counts = [len(re.findall(r"#\w+", c)) for c in captions]
            avg_hashtags = round(sum(hashtag_counts) / total_captions) if total_captions else 5
            ht_range = f"{max(1, avg_hashtags-2)}-{avg_hashtags+2}"
            
            # 3. Sentence length
            all_sentences = []
            for c in captions:
                clean_text = re.sub(r"#\w+", "", c).strip()
                sents = [s.strip() for s in re.split(r"[.!?\n]+", clean_text) if s.strip()]
                all_sentences.extend(sents)
            
            words_per_sentence = [len(s.split()) for s in all_sentences if s]
            avg_words = round(sum(words_per_sentence) / len(words_per_sentence), 1) if words_per_sentence else 15.0
            
            # 4. Extract hooks
            sample_hooks = []
            for c in captions[:10]:
                lines = [l.strip() for l in c.strip().split("\n") if l.strip()]
                if lines:
                    first_line = lines[0]
                    if len(first_line) > 10 and not first_line.startswith("#"):
                        sample_hooks.append(first_line[:80])

            analysis = {
                "avg_sentence_length": avg_words,
                "emoji_frequency": avg_emojis,
                "hashtag_count_range": ht_range,
                "sample_hooks": sample_hooks
            }
            
            self.update_profile(brand_id, analysis)
            return analysis
        finally:
            conn.close()

    def check_compliance(self, caption: str, brand_id: Optional[int] = None) -> Tuple[bool, List[str]]:
        """Verifies caption against brand prohibited words with NULL guards."""
        brand = self.get_by_id(brand_id) if brand_id else self.get_active()
        if not brand:
            return True, []
        
        issues = []
        raw_prohibited = brand.get("prohibited_words")
        if raw_prohibited:
            prohibited_str = str(raw_prohibited)
            bad_words = [w.strip().lower() for w in prohibited_str.split(",") if w.strip()]
            caption_lower = str(caption or "").lower()
            for bw in bad_words:
                if bw in caption_lower:
                    issues.append(f"Contains prohibited term: '{bw}'")
                    
        return len(issues) == 0, issues
