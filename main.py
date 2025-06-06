#!/usr/bin/env python3
"""
Interactive GitHub PR Reviewer
Browse your repositories and select PRs to review
"""

import asyncio
import sys
import os
from pathlib import Path
import requests
from datetime import datetime

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from github_pr_reviewer import GitHubPRReviewer
from config import GitHubConfig

class InteractivePRReviewer:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        self.reviewer = GitHubPRReviewer()

    def get_user_repositories(self, page=1, per_page=30):
        """Get user's repositories"""
        url = f"{self.base_url}/user/repos"
        params = {
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "type": "all"  # all, owner, member
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_repository_prs(self, owner, repo, state="open", page=1, per_page=20):
        """Get PRs for a specific repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {
            "state": state,  # open, closed, all
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def display_repositories(self, repos):
        """Display repositories in a formatted way"""
        print("\n" + "="*80)
        print("📚 YOUR REPOSITORIES")
        print("="*80)
        
        for i, repo in enumerate(repos, 1):
            try:
                # Safely get repository data with defaults
                name = repo.get('name', 'Unknown')
                description = repo.get('description') or 'No description'
                html_url = repo.get('html_url', 'No URL')
                
                # Handle dates safely
                updated_at = repo.get('updated_at')
                if updated_at:
                    try:
                        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        updated_str = updated.strftime('%Y-%m-%d %H:%M')
                    except:
                        updated_str = updated_at
                else:
                    updated_str = 'Unknown'
                
                # Repository info with safe access
                private_marker = "🔒" if repo.get('private', False) else "🌐"
                fork_marker = "🍴" if repo.get('fork', False) else ""
                
                # Safe access to numeric fields
                stars = repo.get('stargazers_count', 0)
                forks = repo.get('forks_count', 0)
                issues = repo.get('open_issues_count', 0)
                
                print(f"{i:2d}. {private_marker} {name} {fork_marker}")
                print(f"    📝 {description[:70]}")
                print(f"    🔗 {html_url}")
                print(f"    📊 ⭐{stars} 🍴{forks} 📝{issues}")
                print(f"    🕐 Updated: {updated_str}")
                print()
                
            except Exception as e:
                print(f"{i:2d}. ❌ Error displaying repository: {e}")
                print(f"    Raw data: {repo}")
                print()

    def display_pull_requests(self, prs, owner, repo):
        """Display PRs in a formatted way"""
        print("\n" + "="*80)
        print(f"🔄 PULL REQUESTS in {owner}/{repo}")
        print("="*80)
        
        if not prs:
            print("📭 No pull requests found.")
            return
        
        for i, pr in enumerate(prs, 1):
            # Format dates
            created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
            updated = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
            created_str = created.strftime('%Y-%m-%d')
            updated_str = updated.strftime('%Y-%m-%d')
            
            # PR status
            status_icon = "🟢" if pr['state'] == 'open' else "🔴"
            draft_marker = "📝" if pr.get('draft', False) else ""
            
            print(f"{i:2d}. {status_icon} #{pr['number']} {draft_marker}")
            print(f"    📋 {pr['title']}")
            print(f"    👤 by {pr['user']['login']}")
            print(f"    🔗 {pr['html_url']}")
            print(f"    📊 +{pr.get('additions', 0)} -{pr.get('deletions', 0)} files: {pr.get('changed_files', 0)}")
            print(f"    📅 Created: {created_str} | Updated: {updated_str}")
            if pr.get('labels'):
                labels = [f"🏷️{label['name']}" for label in pr['labels'][:3]]
                print(f"    🏷️  {' '.join(labels)}")
            print()

    async def interactive_repository_selection(self):
        """Interactive repository selection"""
        print("🔍 Fetching your repositories...")
        
        try:
            repos = self.get_user_repositories()
            
            print(f"📊 Debug: Found {len(repos) if repos else 0} repositories")
            
            if not repos:
                print("📭 No repositories found.")
                # Let's also try to get more info about the API response
                print("🔍 Checking API access...")
                url = f"{self.base_url}/user"
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    user_info = response.json()
                    print(f"✅ API access OK. User: {user_info.get('login', 'Unknown')}")
                    print(f"📊 You have {user_info.get('public_repos', 0)} public repos")
                else:
                    print(f"❌ API access failed: {response.status_code}")
                return None, None
            
            # Debug: print first repo structure
            if repos:
                print(f"🔍 Debug: First repo keys: {list(repos[0].keys())}")
            
            self.display_repositories(repos)
            
            print("Commands:")
            print("  • Enter repository number (1-{})".format(len(repos)))
            print("  • 'n' for next page")
            print("  • 'q' to quit")
            print("  • 'search <owner/repo>' to search specific repo")
            
            while True:
                choice = input("\n📚 Select repository: ").strip()
                
                if choice.lower() == 'q':
                    return None, None
                
                if choice.lower() == 'n':
                    # Load next page (implement pagination if needed)
                    print("📄 Loading more repositories...")
                    continue
                
                if choice.lower().startswith('search '):
                    # Direct repo search
                    repo_path = choice[7:].strip()
                    if '/' in repo_path:
                        owner, repo = repo_path.split('/', 1)
                        return owner, repo
                    else:
                        print("❌ Please use format: search owner/repo")
                        continue
                
                try:
                    repo_index = int(choice) - 1
                    if 0 <= repo_index < len(repos):
                        selected_repo = repos[repo_index]
                        owner = selected_repo.get('owner', {}).get('login')
                        name = selected_repo.get('name')
                        
                        if owner and name:
                            return owner, name
                        else:
                            print(f"❌ Could not get owner/name from repo: {selected_repo}")
                            continue
                    else:
                        print("❌ Invalid repository number")
                except ValueError:
                    print("❌ Please enter a valid number or command")
                    
        except Exception as e:
            print(f"❌ Error fetching repositories: {e}")
            print(f"🔍 Debug: Exception type: {type(e)}")
            import traceback
            print("📋 Full traceback:")
            traceback.print_exc()
            return None, None

    async def interactive_pr_selection(self, owner, repo):
        """Interactive PR selection"""
        print(f"\n🔍 Fetching PRs for {owner}/{repo}...")
        
        try:
            # Get both open and recently closed PRs
            open_prs = self.get_repository_prs(owner, repo, state="open")
            closed_prs = self.get_repository_prs(owner, repo, state="closed", per_page=10)
            
            all_prs = open_prs + closed_prs[:5]  # Show 5 recent closed PRs
            
            if not all_prs:
                print("📭 No pull requests found.")
                return None
            
            self.display_pull_requests(all_prs, owner, repo)
            
            print("Commands:")
            print("  • Enter PR number (1-{})".format(len(all_prs)))
            print("  • 'back' to select different repository")
            print("  • 'q' to quit")
            print("  • 'direct <pr_number>' to review specific PR number")
            
            while True:
                choice = input(f"\n🔄 Select PR to review: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                if choice.lower() == 'back':
                    return "back"
                
                if choice.lower().startswith('direct '):
                    try:
                        pr_number = int(choice[7:].strip())
                        return pr_number
                    except ValueError:
                        print("❌ Please enter a valid PR number")
                        continue
                
                try:
                    pr_index = int(choice) - 1
                    if 0 <= pr_index < len(all_prs):
                        selected_pr = all_prs[pr_index]
                        return selected_pr['number']
                    else:
                        print("❌ Invalid PR number")
                except ValueError:
                    print("❌ Please enter a valid number or command")
                    
        except Exception as e:
            print(f"❌ Error fetching PRs: {e}")
            return None

    async def review_selected_pr(self, owner, repo, pr_number):
        """Review the selected PR"""
        pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
        repo_url = f"https://github.com/{owner}/{repo}"
        
        print(f"\n🔍 Starting review for PR #{pr_number}")
        print(f"📍 Repository: {repo_url}")
        print(f"🔗 PR URL: {pr_url}")
        print(f"📊 Analyzing PR in {owner}/{repo}...")
        
        try:
            # Analyze the PR
            print("📊 Analyzing PR...")
            result = await self.reviewer.analyze_pr(owner, repo, pr_number)
            
            # Display results (simplified for interactive mode)
            print("\n" + "="*80)
            print("📋 PR REVIEW SUMMARY")
            print("="*80)
            print(f"🔗 PR URL: {pr_url}")
            print(f"📝 Title: {result['pr_details'].get('title', 'N/A')}")
            print(f"👤 Author: {result['pr_details'].get('user', {}).get('login', 'N/A')}")
            print(f"📊 Status: {result['pr_details'].get('state', 'N/A')}")
            print(f"📁 Files changed: {len(result['file_reviews'])}")
            print(f"📄 Summary: {result['summary']}")
            
            # Ask what to do next
            print("\nOptions:")
            print("  1. See detailed review")
            print("  2. Post review to GitHub")
            print("  3. Save review to file")
            print("  4. Back to PR selection")
            print("  5. Back to repository selection")
            
            while True:
                choice = input("\nWhat would you like to do? (1-5): ").strip()
                
                if choice == '1':
                    print("\n" + "="*80)
                    print("🔎 DETAILED REVIEW")
                    print("="*80)
                    print(result['overall_review'])
                    
                elif choice == '2':
                    confirm = input(f"Post review to {pr_url}? (y/N): ").lower().strip()
                    if confirm == 'y':
                        print("📤 Posting review to GitHub...")
                        review_response = await self.reviewer.post_review_to_github(
                            owner, repo, pr_number, 
                            result['overall_review'],
                            "COMMENT"
                        )
                        print("✅ Review posted successfully!")
                        print(f"🔗 View review: {review_response.get('html_url', pr_url)}")
                        
                elif choice == '3':
                    filename = f"review_{owner}_{repo}_PR_{pr_number}.md"
                    with open(filename, 'w') as f:
                        f.write(f"# PR Review: {result['pr_details'].get('title', 'N/A')}\n\n")
                        f.write(f"**Repository:** {owner}/{repo}\n")
                        f.write(f"**PR URL:** {pr_url}\n\n")
                        f.write(f"## Summary\n{result['summary']}\n\n")
                        f.write(f"## Detailed Review\n{result['overall_review']}\n")
                    print(f"💾 Review saved to {filename}")
                    
                elif choice == '4':
                    return "back_to_pr"
                    
                elif choice == '5':
                    return "back_to_repo"
                    
                else:
                    print("❌ Please enter a number between 1-5")
                    
        except Exception as e:
            print(f"❌ Error during review: {str(e)}")
            print(f"🔗 PR URL for manual review: {pr_url}")
            return "error"

    async def run_interactive_mode(self):
        """Main interactive loop"""
        print("🚀 Welcome to Interactive GitHub PR Reviewer!")
        print("="*50)
        
        # Validate configuration first
        try:
            config = GitHubConfig()
            config.validate()
            print("✅ Configuration validated")
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            return
        
        while True:
            # Select repository
            owner, repo = await self.interactive_repository_selection()
            if owner is None:
                print("👋 Goodbye!")
                break
                
            while True:
                # Select PR
                pr_number = await self.interactive_pr_selection(owner, repo)
                if pr_number is None:
                    print("👋 Goodbye!")
                    return
                elif pr_number == "back":
                    break  # Back to repository selection
                
                # Review PR
                result = await self.review_selected_pr(owner, repo, pr_number)
                if result == "back_to_repo":
                    break  # Back to repository selection
                elif result == "back_to_pr":
                    continue  # Back to PR selection
                # Continue with current repository for other results

def main():
    """Main function"""
    reviewer = InteractivePRReviewer()
    asyncio.run(reviewer.run_interactive_mode())

if __name__ == "__main__":
    main()   