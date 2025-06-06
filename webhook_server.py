# webhook_server.py
from flask import Flask, request, jsonify
import asyncio
import threading
from github_pr_reviewer import GitHubPRReviewer

app = Flask(__name__)
reviewer = GitHubPRReviewer("github_mcp_server.py")

def run_async_review(owner, repo, pr_number):
    """Run review in separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Analyze PR
        review_result = loop.run_until_complete(
            reviewer.analyze_pr(owner, repo, pr_number)
        )
        
        # Post review to GitHub
        loop.run_until_complete(
            reviewer.post_review_to_github(
                owner, repo, pr_number, 
                review_result['overall_review'],
                "COMMENT"
            )
        )
    finally:
        loop.close()

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle GitHub webhook events"""
    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    if event == 'pull_request':
        action = payload['action']
        if action in ['opened', 'reopened', 'synchronize']:
            pr = payload['pull_request']
            repo = payload['repository']
            
            # Start review in background thread
            thread = threading.Thread(
                target=run_async_review,
                args=(repo['owner']['login'], repo['name'], pr['number'])
            )
            thread.start()
            
            return jsonify({"status": "review_started"})
    
    return jsonify({"status": "ignored"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)