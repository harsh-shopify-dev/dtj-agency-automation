"""What each platform accepts. The gate checks every post against these before anyone is asked to approve it.

Text limits are each platform's own published limits (sources in docs/smm/README.md, "Platform facts"). `house_*` values are
DTJ's own style choices, not platform rules.
"""
from __future__ import annotations

PLATFORMS: dict[str, dict] = {
    "instagram": {
        "text_fields": {"caption": 2200},
        "max_hashtags": 30, "house_max_hashtags": 5,
        "links_clickable": False,       # a link in a caption is not clickable: say "link in bio" instead
        "formats": {"image", "carousel", "video"},
        "carousel_max": 20,
        "image_types": {".jpg", ".jpeg"},   # JPEG only, max 8 MB, 320-1440 px wide
        "image_ratio": (0.8, 1.91),     # width / height: 4:5 portrait to 1.91:1 landscape
        "video_ratio": (0.5, 0.6),      # 9:16 reels
        "video_max_seconds": 180,       # the API takes up to 15 min; DTJ keeps reels short
    },
    "facebook": {
        "text_fields": {"caption": 63206},
        "max_hashtags": 30, "house_max_hashtags": 3,
        "links_clickable": True,
        "formats": {"image", "carousel", "video", "text"},
        "carousel_max": 10,
        "image_types": {".jpg", ".jpeg", ".png"},
        "image_ratio": (0.5, 2.0),
        "video_ratio": (0.5, 0.6),
        "video_max_seconds": 90,        # Facebook reels
    },
    "linkedin": {
        "text_fields": {"caption": 3000},
        "max_hashtags": 30, "house_max_hashtags": 3,
        "links_clickable": True,
        "formats": {"image", "carousel", "video", "text"},
        "carousel_max": 9,              # multi-image post
        "image_types": {".jpg", ".jpeg", ".png"},
        "image_ratio": (0.5, 2.0),
        "video_ratio": (0.5, 2.4),
        "video_max_seconds": 600,
    },
    "x": {
        "text_fields": {"text": 280},   # links count as 23 characters (t.co)
        "max_hashtags": 10, "house_max_hashtags": 2,
        "links_clickable": True,
        "formats": {"image", "carousel", "video", "text"},
        "carousel_max": 4,
        "image_types": {".jpg", ".jpeg", ".png"},
        "image_ratio": (0.5, 2.0),
        "video_ratio": (0.5, 2.4),
        "video_max_seconds": 140,
    },
    "youtube": {
        "text_fields": {"title": 100, "description": 5000},
        "max_hashtags": 15, "house_max_hashtags": 3,
        "links_clickable": True,
        "formats": {"video"},           # Shorts only
        "carousel_max": 0,
        "image_types": set(),
        "image_ratio": (0, 0),
        "video_ratio": (0.5, 0.6),      # vertical, so YouTube treats it as a Short
        "video_max_seconds": 180,
    },
}

URL_LENGTH_ON_X = 23
