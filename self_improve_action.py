def analyze_post_logs(logs):
    # Early return if logs is empty
    if not logs:
        return {'niches': [], 'recent_7d': [], 'last_post': None}

    # Process logs to analyze niches, recent posts over the last 7 days, and the last post
    niches = set()
    recent_posts = []
    last_post = None

    # Iterate through logs to analyze content
    for log in logs:
        niches.update(log.get('niche', []))
        post_date = log.get('date')
        # Check if the post is within the last 7 days
        if post_date and (datetime.utcnow() - post_date).days <= 7:
            recent_posts.append(log)
        last_post = log

    return {'niches': list(niches), 'recent_7d': recent_posts, 'last_post': last_post}