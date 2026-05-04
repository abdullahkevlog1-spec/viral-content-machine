def analyze_post_logs(logs):
    if not logs:
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "success_rate": 0,
            "errors": [],
            "slots": {},
            "niches": {},
            "recent_7d": 0,
            "last_post": None,
        }

    # ... the rest of the original function ...