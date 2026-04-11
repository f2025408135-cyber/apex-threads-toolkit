from dataclasses import dataclass
from typing import List

@dataclass
class Endpoint:
    id: str
    method: str
    url_template: str
    required_scope: str
    fields: str
    description: str
    expected_auth: str
    is_write: bool = False
    is_fresh_code: bool = False
    risk_level: str = "LOW"

# Complete registry of Threads API endpoints
endpoints_registry: List[Endpoint] = [
    # PROFILE ENDPOINTS
    Endpoint(
        id="me_profile",
        method="GET",
        url_template="https://graph.threads.net/v1.0/me",
        required_scope="threads_basic",
        fields="id,username,name,biography,profile_picture_url,followers_count,following_count,is_verified,link_in_bio,threads_profile_audience_type",
        description="Fetch current user profile",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="user_b_profile",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{USER_B_THREADS_ID}",
        required_scope="threads_basic",
        fields="id,username,name,biography,profile_picture_url,followers_count,following_count,is_verified,link_in_bio",
        description="Fetch Account B profile",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="me_profile_wildcard",
        method="GET",
        url_template="https://graph.threads.net/v1.0/me",
        required_scope="threads_basic",
        fields="*",
        description="Fetch current user profile with wildcard fields",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="user_b_profile_wildcard",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{USER_B_THREADS_ID}",
        required_scope="threads_basic",
        fields="*",
        description="Fetch Account B profile with wildcard fields",
        expected_auth="THREADS_USER"
    ),

    # THREADS (POSTS) ENDPOINTS
    Endpoint(
        id="me_threads",
        method="GET",
        url_template="https://graph.threads.net/v1.0/me/threads",
        required_scope="threads_basic",
        fields="id,media_type,text,timestamp,permalink,shortcode,is_reply,root_post,replied_to,hide_status,reply_audience",
        description="Fetch current user threads",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="user_b_threads",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{USER_B_THREADS_ID}/threads",
        required_scope="threads_basic",
        fields="id,text,timestamp,media_type",
        description="Fetch Account B threads",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="single_thread_b",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}",
        required_scope="threads_basic",
        fields="id,text,timestamp,media_type,reply_audience,hide_status",
        description="Fetch a single text thread from Account B",
        expected_auth="THREADS_USER"
    ),

    # INSIGHTS / ANALYTICS
    Endpoint(
        id="me_insights",
        method="GET",
        url_template="https://graph.threads.net/v1.0/me/insights?metric=views,likes,replies,reposts,quotes,followers_count&period=day&since=1704067200&until=1735689600",
        required_scope="threads_manage_insights",
        fields="",
        description="Fetch current user insights",
        expected_auth="THREADS_USER",
        risk_level="HIGH"
    ),
    Endpoint(
        id="user_b_insights",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{USER_B_THREADS_ID}/insights?metric=views,likes,replies,reposts&period=day",
        required_scope="threads_manage_insights",
        fields="",
        description="Fetch Account B insights (BOLA test)",
        expected_auth="THREADS_USER",
        risk_level="CRITICAL"
    ),
    Endpoint(
        id="thread_b_insights",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}/insights?metric=views,likes,replies,reposts,quotes",
        required_scope="threads_manage_insights",
        fields="",
        description="Fetch Account B thread insights (BOLA test)",
        expected_auth="THREADS_USER",
        risk_level="CRITICAL"
    ),
    Endpoint(
        id="publishing_limit_me",
        method="GET",
        url_template="https://graph.threads.net/v1.0/me/threads_publishing_limit",
        required_scope="threads_basic",
        fields="config,quota_usage",
        description="Fetch current user publishing limit",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="publishing_limit_user_b",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{USER_B_THREADS_ID}/threads_publishing_limit",
        required_scope="threads_basic",
        fields="config,quota_usage",
        description="Fetch Account B publishing limit (BOLA test)",
        expected_auth="THREADS_USER",
        risk_level="HIGH"
    ),

    # REPLIES
    Endpoint(
        id="thread_b_replies",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}/replies",
        required_scope="threads_read_replies",
        fields="",
        description="Fetch replies for Account B thread",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="thread_b_conversation",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}/conversation",
        required_scope="threads_read_replies",
        fields="",
        description="Fetch conversation for Account B thread",
        expected_auth="THREADS_USER"
    ),
    Endpoint(
        id="manage_reply_hide",
        method="POST",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}/manage_reply",
        required_scope="threads_manage_replies",
        fields="",
        description="Hide a reply on Account B thread",
        expected_auth="THREADS_USER",
        is_write=True,
        risk_level="HIGH"
    ),

    # SEARCH
    Endpoint(
        id="keyword_search",
        method="GET",
        url_template="https://graph.threads.net/v1.0/threads?q=test",
        required_scope="threads_keyword_search",
        fields="id,text,timestamp",
        description="Search threads",
        expected_auth="THREADS_USER"
    ),

    # POLLS
    Endpoint(
        id="poll_b_results",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_POLL_ID}",
        required_scope="threads_basic",
        fields="id,text,poll_options,poll_results",
        description="Fetch Account B poll results",
        expected_auth="THREADS_USER",
        is_fresh_code=True,
        risk_level="HIGH"
    ),
    Endpoint(
        id="poll_b_vote",
        method="POST",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_POLL_ID}/poll_vote",
        required_scope="threads_basic",  # Usually not required explicitly to specify for vote if not detailed, but assume basic for now.
        fields="",
        description="Vote on Account B poll",
        expected_auth="THREADS_USER",
        is_write=True,
        is_fresh_code=True,
        risk_level="HIGH"
    ),
    Endpoint(
        id="poll_b_close",
        method="POST",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_POLL_ID}",
        required_scope="threads_basic",
        fields="",
        description="Close Account B poll",
        expected_auth="THREADS_USER",
        is_write=True,
        is_fresh_code=True,
        risk_level="HIGH"
    ),

    # GEOLOCATION
    Endpoint(
        id="thread_b_location",
        method="GET",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}",
        required_scope="threads_basic",
        fields="id,text,location,place_name,place_id,coordinates",
        description="Fetch Account B thread geolocation",
        expected_auth="THREADS_USER",
        is_fresh_code=True,
        risk_level="HIGH"
    ),

    # DELETE
    Endpoint(
        id="delete_thread_b",
        method="DELETE",
        url_template="https://graph.threads.net/v1.0/{THREAD_B_TEXT_ID}",
        required_scope="threads_basic",
        fields="",
        description="Delete Account B thread",
        expected_auth="THREADS_USER",
        is_write=True,
        risk_level="CRITICAL"
    ),
]
