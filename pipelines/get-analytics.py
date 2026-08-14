#!/usr/bin/env python3
"""
Instagram Analytics Pipeline
Fetches posts within a date range, analyzes performance by content type,
and asks Claude to summarize in plain English with recommendations.

Usage:
  python3 get-analytics.py                          # last 7 days
  python3 get-analytics.py 14                       # last 14 days
  python3 get-analytics.py 2026-06-01 2026-06-30     # custom date range
"""

import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
from datetime import datetime, timedelta, timezone
import sys
sys.path.insert(0, PROJECT_ROOT)
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
from pipelines.ai_router import generate_analytics_summary
from pipelines.ig_connection import get_instagram_client, NoActiveInstagramConnection


def get_composio_client():
    return get_instagram_client()


def get_recent_posts(client, user_id, connected_account_id, ig_user_id, limit=50):
    result = client.tools.execute(
        slug='INSTAGRAM_GET_IG_USER_MEDIA',
        arguments={
            'ig_user_id': ig_user_id,
            'fields': 'id,caption,media_type,timestamp,permalink',
            'limit': limit
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not result['successful']:
        raise Exception(f"Failed to fetch posts: {result.get('error')}")
    return result['data'].get('data', [])


def filter_by_date(posts, start_date, end_date):
    filtered = []
    for p in posts:
        ts = p.get('timestamp')
        if not ts:
            continue
        try:
            post_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except ValueError:
            continue
        if start_date <= post_dt <= end_date:
            filtered.append(p)
    return filtered


def get_post_insights(client, user_id, connected_account_id, post_id):
    result = client.tools.execute(
        slug='INSTAGRAM_GET_IG_MEDIA_INSIGHTS',
        arguments={
            'ig_media_id': post_id,
            'metric': 'reach,likes,comments,saved,shares'
        },
        connected_account_id=connected_account_id,
        user_id=user_id,
        dangerously_skip_version_check=True
    )
    if not result['successful']:
        return None
    return result['data']


def extract_metric_value(insights_data, metric_name):
    if not insights_data:
        return 0
    items = insights_data.get('data', []) if isinstance(insights_data, dict) else []
    for item in items:
        if item.get('name') == metric_name:
            values = item.get('values', [])
            if values:
                return values[0].get('value', 0)
    return 0


def analyze_by_content_type(posts_with_insights):
    buckets = {}
    for p in posts_with_insights:
        mtype = p.get('media_type', 'UNKNOWN')
        insights = p.get('insights')
        reach = extract_metric_value(insights, 'reach')
        likes = extract_metric_value(insights, 'likes')
        comments = extract_metric_value(insights, 'comments')
        saved = extract_metric_value(insights, 'saved')
        engagement = likes + comments + saved

        if mtype not in buckets:
            buckets[mtype] = {'count': 0, 'total_reach': 0, 'total_engagement': 0}
        buckets[mtype]['count'] += 1
        buckets[mtype]['total_reach'] += reach
        buckets[mtype]['total_engagement'] += engagement

    ranked = []
    for mtype, stats in buckets.items():
        avg_engagement = stats['total_engagement'] / stats['count'] if stats['count'] else 0
        avg_reach = stats['total_reach'] / stats['count'] if stats['count'] else 0
        ranked.append({
            'type': mtype,
            'count': stats['count'],
            'avg_engagement': round(avg_engagement, 1),
            'avg_reach': round(avg_reach, 1)
        })
    ranked.sort(key=lambda x: x['avg_engagement'], reverse=True)
    return ranked


def parse_args(args):
    now = datetime.now(timezone.utc)

    if len(args) == 0:
        start = now - timedelta(days=7)
        end = now
        label = "Last 7 days"
    elif len(args) == 1:
        days = int(args[0])
        start = now - timedelta(days=days)
        end = now
        label = f"Last {days} days"
    elif len(args) == 2:
        start = datetime.strptime(args[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(args[1], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        label = f"{args[0]} to {args[1]}"
    else:
        raise ValueError("Usage: get-analytics.py [days] OR get-analytics.py START_DATE END_DATE")

    return start, end, label


def format_posts_for_summary(posts_with_insights):
    data_text = ""
    for p in posts_with_insights:
        insights = p.get('insights')
        reach = extract_metric_value(insights, 'reach')
        likes = extract_metric_value(insights, 'likes')
        comments = extract_metric_value(insights, 'comments')
        saved = extract_metric_value(insights, 'saved')
        data_text += f"\nPost ({p.get('media_type', 'UNKNOWN')}): {p.get('permalink', 'unknown')}\n"
        data_text += f"Caption: {(p.get('caption') or '')[:80]}\n"
        data_text += f"Posted: {p.get('timestamp', 'unknown')}\n"
        data_text += f"Reach: {reach}, Likes: {likes}, Comments: {comments}, Saved: {saved}\n"
        data_text += "---\n"
    return data_text


def format_ranking_for_summary(content_type_ranking):
    return "\n".join([
        f"{r['type']}: {r['count']} posts, avg engagement {r['avg_engagement']}, avg reach {r['avg_reach']}"
        for r in content_type_ranking
    ])


def main():
    args = sys.argv[1:]
    start_date, end_date, date_range_label = parse_args(args)

    print(f"Date range: {date_range_label}")
    print("Connecting to Composio...")
    client, user_id, connected_account_id, ig_user_id = get_composio_client()

    print("Fetching posts (overfetching to filter by date)...")
    all_posts = get_recent_posts(client, user_id, connected_account_id, ig_user_id, limit=50)

    posts = filter_by_date(all_posts, start_date, end_date)

    if not posts:
        print(f"NO_POSTS: No posts found in range {date_range_label}.")
        return

    print(f"Found {len(posts)} posts in range. Fetching insights...")
    posts_with_insights = []
    for post in posts:
        insights = get_post_insights(client, user_id, connected_account_id, post['id'])
        post['insights'] = insights
        posts_with_insights.append(post)

    print("Analyzing performance by content type...")
    content_type_ranking = analyze_by_content_type(posts_with_insights)

    print("Summarizing with AI Router...")
    data_text = format_posts_for_summary(posts_with_insights)
    ranking_text = format_ranking_for_summary(content_type_ranking)
    summary = generate_analytics_summary(data_text, ranking_text, date_range_label)

    print("\n=== ANALYTICS SUMMARY ===")
    print(f"Period: {date_range_label}")
    print(summary)
    print("=== END SUMMARY ===")


if __name__ == '__main__':
    try:
        main()
    except NoActiveInstagramConnection as e:
        print(f"FAILED: {e}")
        sys.exit(1)