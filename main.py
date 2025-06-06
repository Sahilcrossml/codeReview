#!/usr/bin/env python3
"""
Interactive GitHub PR Reviewer - FIXED VERSION
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
            "type": "all"
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_repository_prs(self, owner, repo, state="open", page=1, per_page=20):
        """Get PRs for a specific repository"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        params = {
            "state": state,
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
                name = repo.get('name', 'Unknown')
                description = repo.get('description') or 'No description'
                html_url = repo.get('html_url', 'No URL')
                
                updated_at = repo.get('updated_at')
                if updated_at:
                    try:
                        updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        updated_str = updated.strftime('%Y-%m-%d %H:%M')
                    except:
                        updated_str = updated_at
                else:
                    updated_str = 'Unknown'
                
                private_marker = "🔒" if repo.get('private', False) else "🌐"
                fork_marker = "🍴" if repo.get('fork', False) else ""
                
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
            try:
                created = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                updated = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
                created_str = created.strftime('%Y-%m-%d')
                updated_str = updated.strftime('%Y-%m-%d')
                
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
            except Exception as e:
                print(f"{i:2d}. ❌ Error displaying PR: {e}")
                print()

    def show_create_pr_instructions(self, owner, repo):
        """Show instructions for creating a PR"""
        print(f"\n📝 How to create a Pull Request in {owner}/{repo}:")
        print("="*60)
        print("🚀 QUICK METHOD (GitHub Web Interface):")
        print(f"1. Go to: https://github.com/{owner}/{repo}")
        print("2. Click on any file (like README.md) or create new file")
        print("3. Click the pencil icon (✏️) to edit")
        print("4. Make some changes")
        print("5. Scroll down → Select 'Create a new branch'")
        print("6. Click 'Propose changes' → 'Create pull request'")
        print()
        print("💻 COMMAND LINE METHOD:")
        print("1. Clone your repository:")
        print(f"   git clone https://github.com/{owner}/{repo}.git")
        print(f"   cd {repo}")
        print()
        print("2. Create a new branch:")
        print("   git checkout -b feature/test-pr")
        print()
        print("3. Make some changes:")
        print("   echo '# Test Change for PR Review' >> README.md")
        print()
        print("4. Commit and push:")
        print("   git add .")
        print("   git commit -m 'Test: Add changes for PR review'")
        print("   git push origin feature/test-pr")
        print()
        print("5. Create PR:")
        print(f"   🔗 Go to: https://github.com/{owner}/{repo}/compare")
        print()
        print("🌟 TIP: The web interface method is much faster!")

    def suggest_public_repos(self):
        """Suggest popular public repositories with active PRs"""
        print("\n🌟 Popular repositories with active PRs:")
        print("="*50)
        
        suggestions = [
            ("microsoft", "vscode", "Popular code editor"),
            ("facebook", "react", "JavaScript library"),
            ("django", "django", "Python web framework"),
            ("nodejs", "node", "JavaScript runtime"),
            ("vercel", "next.js", "React framework"),
            ("vuejs", "vue", "Progressive framework"),
            ("golang", "go", "Go programming language"),
            ("microsoft", "TypeScript", "TypeScript language"),
            ("angular", "angular", "Web application framework"),
            ("kubernetes", "kubernetes", "Container orchestration")
        ]
        
        for i, (owner, repo, desc) in enumerate(suggestions, 1):
            print(f"{i:2d}. {owner}/{repo}")
            print(f"    📝 {desc}")
            print(f"    🔗 https://github.com/{owner}/{repo}/pulls")
            print()
        
        print("Commands:")
        print("  • Enter number (1-10) to review that repository")
        print("  • 'custom owner/repo' to specify different repository")
        print("  • 'back' to return to your repositories")
        
        while True:
            choice = input("\n🌟 Select public repository: ").strip()
            
            if choice.lower() == 'back':
                return "back"
            
            if choice.lower().startswith('custom '):
                repo_path = choice[7:].strip()
                if '/' in repo_path:
                    owner, repo = repo_path.split('/', 1)
                    return owner, repo
                else:
                    print("❌ Please use format: custom owner/repo")
                    continue
            
            try:
                suggestion_index = int(choice) - 1
                if 0 <= suggestion_index < len(suggestions):
                    owner, repo, _ = suggestions[suggestion_index]
                    return owner, repo
                else:
                    print("❌ Invalid number")
            except ValueError:
                print("❌ Please enter a valid number or command")

    async def interactive_repository_selection(self):
        """Interactive repository selection"""
        print("🔍 Fetching your repositories...")
        
        try:
            repos = self.get_user_repositories()
            
            if not repos:
                print("📭 No repositories found.")
                return None, None
            
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
                
                if choice.lower().startswith('search '):
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
                            print(f"❌ Could not get owner/name from repo")
                            continue
                    else:
                        print("❌ Invalid repository number")
                except ValueError:
                    print("❌ Please enter a valid number or command")
                    
        except Exception as e:
            print(f"❌ Error fetching repositories: {e}")
            return None, None

    async def interactive_pr_selection(self, owner, repo):
        """Interactive PR selection"""
        print(f"\n🔍 Fetching PRs for {owner}/{repo}...")
        
        try:
            open_prs = self.get_repository_prs(owner, repo, state="open")
            closed_prs = self.get_repository_prs(owner, repo, state="closed", per_page=10)
            
            all_prs = open_prs + closed_prs[:5]
            
            if not all_prs:
                print("📭 No pull requests found in this repository.")
                print("\n💡 Options:")
                print("  1. Create a test PR in this repository")
                print("  2. Try a different repository") 
                print("  3. Review a public repository")
                print("  4. Back to repository selection")
                print("  5. Quit")
                
                while True:
                    choice = input("\nWhat would you like to do? (1-5): ").strip()
                    
                    if choice == '1':
                        self.show_create_pr_instructions(owner, repo)
                        input("\nPress Enter when you've created a PR...")
                        return "back"
                    elif choice == '2' or choice == '4':
                        return "back"
                    elif choice == '3':
                        result = self.suggest_public_repos()
                        if result == "back":
                            return "back"
                        else:
                            # result is (owner, repo) tuple
                            return result
                    elif choice == '5':
                        return None
                    else:
                        print("❌ Please enter a number between 1-5")
            
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
        
        try:
            result = await self.reviewer.analyze_pr(owner, repo, pr_number)
            
            print("\n" + "="*80)
            print("📋 PR REVIEW SUMMARY")
            print("="*80)
            print(f"🔗 PR URL: {pr_url}")
            print(f"📝 Title: {result['pr_details'].get('title', 'N/A')}")
            print(f"👤 Author: {result['pr_details'].get('user', {}).get('login', 'N/A')}")
            print(f"📊 Status: {result['pr_details'].get('state', 'N/A')}")
            print(f"📁 Files changed: {len(result['file_reviews'])}")
            print(f"📄 Summary: {result['summary']}")
            
            # Show code quality metrics
            print(f"\n🎯 CODE QUALITY ANALYSIS:")
            for review in result['file_reviews']:
                file_name = review['file']
                language = review.get('language', 'Unknown')
                changes = review['changes']
                print(f"  📁 {file_name} ({language})")
                print(f"     📊 Changes: +{changes['additions']} -{changes['deletions']}")
                if 'improvements' in review and review['improvements']:
                    print(f"     🔧 Has specific code improvements")
                print()
            
            print("Options:")
            print("  1. See detailed review")
            print("  2. See code improvements & suggestions")
            print("  3. See both review & improvements")
            print("  4. Post review to GitHub")
            print("  5. Save complete analysis to file")
            print("  6. Back to PR selection")
            print("  7. Back to repository selection")
            
            while True:
                choice = input("\nWhat would you like to do? (1-7): ").strip()
                
                if choice == '1':
                    print("\n" + "="*80)
                    print("🔎 DETAILED REVIEW")
                    print("="*80)
                    print(result['overall_review'])
                    
                elif choice == '2':
                    print("\n" + "="*80)
                    print("🔧 CODE IMPROVEMENTS & SUGGESTIONS")
                    print("="*80)
                    for review in result['file_reviews']:
                        print(f"\n📁 {review['file']} ({review.get('language', 'Unknown')})")
                        print("="*60)
                        if 'improvements' in review and review['improvements']:
                            print(review['improvements'])
                        else:
                            print("No specific code improvements generated for this file.")
                        print()
                    
                elif choice == '3':
                    print("\n" + "="*80)
                    print("📋 COMPLETE ANALYSIS")
                    print("="*80)
                    print("🔎 DETAILED REVIEW:")
                    print("-" * 40)
                    print(result['overall_review'])
                    print("\n🔧 CODE IMPROVEMENTS:")
                    print("-" * 40)
                    for review in result['file_reviews']:
                        print(f"\n📁 {review['file']} ({review.get('language', 'Unknown')})")
                        if 'improvements' in review and review['improvements']:
                            print(review['improvements'])
                        print()
                    
                elif choice == '4':
                    confirm = input(f"Post review to {pr_url}? (y/N): ").lower().strip()
                    if confirm == 'y':
                        print("📤 Posting review to GitHub...")
                        review_response = await self.reviewer.post_review_to_github(
                            owner, repo, pr_number, 
                            result['overall_review'],
                            "COMMENT"
                        )
                        print("✅ Review posted successfully!")
                        
                elif choice == '5':
                    filename = f"review_{owner}_{repo}_PR_{pr_number}.md"
                    with open(filename, 'w') as f:
                        f.write(f"# Complete PR Analysis: {result['pr_details'].get('title', 'N/A')}\n\n")
                        f.write(f"**Repository:** {owner}/{repo}\n")
                        f.write(f"**PR URL:** {pr_url}\n")
                        f.write(f"**Author:** {result['pr_details'].get('user', {}).get('login', 'N/A')}\n\n")
                        
                        f.write(f"## Executive Summary\n{result['summary']}\n\n")
                        f.write(f"## Detailed Review\n{result['overall_review']}\n\n")
                        
                        f.write("## Code Improvements by File\n\n")
                        for review in result['file_reviews']:
                            f.write(f"### {review['file']} ({review.get('language', 'Unknown')})\n\n")
                            if 'improvements' in review and review['improvements']:
                                f.write(review['improvements'])
                                f.write("\n\n")
                        
                        f.write("## Technical Analysis\n\n")
                        for review in result['file_reviews']:
                            f.write(f"### {review['file']}\n")
                            f.write(f"**Changes:** +{review['changes']['additions']} -{review['changes']['deletions']}\n\n")
                            f.write(review['analysis'])
                            f.write("\n\n")
                    
                    print(f"💾 Complete analysis saved to {filename}")
                    
                elif choice == '6':
                    return "back_to_pr"
                    
                elif choice == '7':
                    return "back_to_repo"
                    
                else:
                    print("❌ Please enter a number between 1-7")
                    
        except Exception as e:
            print(f"❌ Error during review: {str(e)}")
            return "error"

    async def run_interactive_mode(self):
        """Main interactive loop"""
        print("🚀 Welcome to Interactive GitHub PR Reviewer!")
        print("="*50)
        
        try:
            config = GitHubConfig()
            config.validate()
            print("✅ Configuration validated")
        except ValueError as e:
            print(f"❌ Configuration error: {e}")
            return
        
        while True:
            # Select repository
            selection = await self.interactive_repository_selection()
            if selection[0] is None:
                print("👋 Goodbye!")
                break
                
            owner, repo = selection
                
            while True:
                # Select PR
                pr_result = await self.interactive_pr_selection(owner, repo)
                if pr_result is None:
                    print("👋 Goodbye!")
                    return
                elif pr_result == "back":
                    break  # Back to repository selection
                elif isinstance(pr_result, tuple):
                    # It's a new (owner, repo) from public repos
                    owner, repo = pr_result
                    continue
                
                # pr_result is a PR number
                pr_number = pr_result
                
                # Review PR
                result = await self.review_selected_pr(owner, repo, pr_number)
                if result == "back_to_repo":
                    break  # Back to repository selection
                elif result == "back_to_pr":
                    continue  # Back to PR selection

def main():
    """Main function"""
    reviewer = InteractivePRReviewer()
    asyncio.run(reviewer.run_interactive_mode())

if __name__ == "__main__":
    main()