import requests
from requests_oauthlib import OAuth1
import json
import os

# ------------------------------------------------------------------
# 1. NEW HELPER: append a block of text to tweets.txt
# ------------------------------------------------------------------
def append_to_file(text_block, file_name='tweets.txt'):
    """
    Append the given text_block to file_name.
    Creates the file if it does not exist.
    """
    with open(file_name, 'a', encoding='utf-8') as f:
        f.write(text_block)
        f.write('\n')   # extra blank line between tweets
# ------------------------------------------------------------------

def fetch_latest_tweets(consumer_key, consumer_secret,
                        access_token, access_token_secret):
    url = (
        "https://api.twitter.com/2/tweets/search/recent"
        "?query=%23Ai%20-is%3Aretweet%20has%3Amedia"
        "&expansions=attachments.media_keys,author_id"
        "&tweet.fields=created_at,author_id,public_metrics,attachments"
        "&media.fields=media_key,type,url,preview_image_url,height,width,public_metrics"
        "&max_results=10"
    )

    auth = OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)

    try:
        response = requests.get(url, auth=auth)
        print("Request Headers:", response.request.headers)
        response.raise_for_status()
        data = response.json()

        tweets      = data.get('data', [])
        includes    = data.get('includes', {})
        users       = {u['id']: u for u in includes.get('users', [])}
        media_dict  = {m['media_key']: m for m in includes.get('media', [])}

        for tweet in tweets:
            author      = users.get(tweet['author_id'], {})
            attachments = tweet.get('attachments', {})
            media_keys  = attachments.get('media_keys', [])

            # Build a nicely formatted block
            block  = f"Tweet ID: {tweet['id']}\n"
            block += f"Created at: {tweet['created_at']}\n"
            block += f"Author: {author.get('username', 'Unknown')}\n"
            block += f"Text: {tweet['text']}\n"

            for mk in media_keys:
                m = media_dict.get(mk, {})
                block += f"Media Type: {m.get('type')}\n"
                if m.get('url'):
                    block += f"Media URL: {m.get('url')}\n"
                if m.get('preview_image_url'):
                    block += f"Preview Image URL: {m.get('preview_image_url')}\n"

            metrics = tweet.get('public_metrics', {})
            block += f"Likes: {metrics.get('like_count', 0)}\n"
            block += f"Retweets: {metrics.get('retweet_count', 0)}\n"
            block += f"Replies: {metrics.get('reply_count', 0)}\n"
            block += "-" * 50

            # ------------------------------------------------------------------
            # 2. NEW: write the block to file
            # ------------------------------------------------------------------
            append_to_file(block)

            # Also keep printing to console (optional)
            print(block)

        return tweets

    except requests.exceptions.RequestException as e:
        print(f"Error fetching tweets: {e}")
        print("Response Content:", e.response.text if e.response else "No response content")
        return []

# ------------------------------------------------------------------
# Same driver code as before
# ------------------------------------------------------------------
if __name__ == "__main__":
    CONSUMER_KEY        = "<consumer_key>"
    CONSUMER_SECRET     = "<consumer_secret>"
    ACCESS_TOKEN        = "<access_token>"
    ACCESS_TOKEN_SECRET = "<access_tokey_secret>"

    fetch_latest_tweets(CONSUMER_KEY, CONSUMER_SECRET,
                        ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
