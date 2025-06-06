# github_pr_reviewer.py
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import requests
import json
import os
from typing import Dict, List

class GitHubPRReviewer:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        
    async def get_pr_details(self, owner: str, repo: str, pr_number: int) -> Dict:
        """Get PR details from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get PR diff from GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
        
        print(f"    🔗 Fetching diff from: {url}")
        response = requests.get(url, headers=headers)
        
        print(f"    📊 Response status: {response.status_code}")
        if response.status_code != 200:
            print(f"    ❌ Error response: {response.text[:200]}")
            
        response.raise_for_status()
        diff_content = response.text
        
        print(f"    📏 Diff length: {len(diff_content)} characters")
        if len(diff_content) < 50:
            print(f"    🔍 Diff preview: {repr(diff_content)}")
            
        return diff_content
    
    async def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get changed files in PR"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    async def analyze_pr(self, owner: str, repo: str, pr_number: int) -> Dict:
        """Comprehensive PR analysis"""
        try:
            print("  📋 Fetching PR details...")
            pr_details = await self.get_pr_details(owner, repo, pr_number)
            
            print("  📊 Getting PR diff...")
            diff = await self.get_pr_diff(owner, repo, pr_number)
            
            print("  📁 Analyzing changed files...")
            files = await self.get_pr_files(owner, repo, pr_number)
            
            print("  🤖 Generating AI review...")
            
            # Check if we have valid data
            if not diff:
                print("  ⚠️  Warning: No diff content available")
                diff = "No diff content available"
            
            if not files:
                print("  ⚠️  Warning: No file changes found")
                files = []
            
            # Analyze each file
            file_reviews = []
            for file_info in files[:10]:  # Limit to first 10 files to avoid token limits
                if file_info.get('status') != 'removed':
                    try:
                        file_review = await self.analyze_file_changes(file_info, diff)
                        file_reviews.append(file_review)
                    except Exception as e:
                        print(f"  ⚠️  Warning: Could not analyze {file_info.get('filename', 'unknown')}: {e}")
                        # Add a basic review for the file
                        file_reviews.append({
                            "file": file_info.get('filename', 'unknown'),
                            "analysis": f"Could not analyze this file: {str(e)}",
                            "code_changes": "Analysis failed",
                            "changes": {
                                "additions": file_info.get('additions', 0),
                                "deletions": file_info.get('deletions', 0)
                            }
                        })
            
            # Overall PR review
            overall_review = await self.generate_overall_review(pr_details, diff, file_reviews)
            
            # Generate summary
            summary = await self.generate_summary(overall_review, file_reviews)
            
            return {
                "pr_details": pr_details,
                "overall_review": overall_review,
                "file_reviews": file_reviews,
                "summary": summary
            }
            
        except Exception as e:
            print(f"  ❌ Error in PR analysis: {str(e)}")
            raise
    
    async def analyze_file_changes(self, file_info: Dict, full_diff: str) -> Dict:
        """Analyze changes in a specific file"""
        file_path = file_info['filename']
        
        # Extract file-specific diff
        file_diff = self.extract_file_diff(full_diff, file_path)
        
        # Parse the diff to extract old and new code
        code_changes = self.parse_diff_changes(file_diff)
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior code reviewer. Analyze this file change and provide detailed feedback:

            1. **Code Quality Assessment**: Rate the code quality and adherence to best practices
            2. **Potential Issues**: Identify bugs, logic errors, or problematic patterns
            3. **Security Concerns**: Flag any security vulnerabilities or risky patterns
            4. **Performance Implications**: Assess performance impact of changes
            5. **Specific Recommendations**: Provide actionable suggestions with exact code fixes

            For each issue found, provide:
            - Line numbers where issues occur
            - Description of the problem
            - Suggested fix with code example
            - Severity level (Critical/High/Medium/Low)

            Be specific and reference exact line numbers from the diff."""),
            ("user", """File: {filename}
Changes: {additions} additions, {deletions} deletions

Diff with line numbers:
{diff}

Code Changes Summary:
{changes_summary}""")
        ])
        
        chain = analysis_prompt | self.llm
        analysis = await chain.ainvoke({
            "filename": file_path,
            "additions": file_info.get('additions', 0),
            "deletions": file_info.get('deletions', 0),
            "diff": file_diff[:4000],  # Increased limit for better analysis
            "changes_summary": code_changes
        })
        
        return {
            "file": file_path,
            "analysis": analysis.content,
            "code_changes": code_changes,
            "changes": {
                "additions": file_info.get('additions', 0),
                "deletions": file_info.get('deletions', 0)
            }
        }
    
    async def generate_overall_review(self, pr_details: Dict, diff: str, file_reviews: List[Dict]) -> str:
        """Generate overall PR review"""
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior code reviewer. Provide a comprehensive PR review with this structure:

## 🎯 Overall Assessment
- **Recommendation**: APPROVE/REQUEST_CHANGES/COMMENT
- **Summary**: Brief overview of the changes

## 📋 Code Changes Analysis
For each file, show:
- File name and change summary
- Old vs New code comparison
- Specific issues found with line numbers
- Suggested fixes

## 🔍 Detailed Findings
### Critical Issues (if any)
### Moderate Issues (if any) 
### Minor Suggestions (if any)

## ✅ Positive Aspects
## 🚀 Recommendations

Be specific with line numbers and provide exact code examples for fixes."""),
            ("user", """PR Title: {title}
PR Description: {description}

Detailed File Analysis:
{detailed_file_analysis}

Full Diff Summary:
{diff_summary}""")
        ])
        
        # Create detailed file analysis
        detailed_analysis = []
        for review in file_reviews:
            detailed_analysis.append(f"""
### 📁 {review['file']}
**Changes**: {review['changes']['additions']} additions, {review['changes']['deletions']} deletions

**Code Changes**:
{review.get('code_changes', 'No specific changes parsed')}

**Analysis**:
{review['analysis']}
""")
        
        chain = review_prompt | self.llm
        review = await chain.ainvoke({
            "title": pr_details.get('title', ''),
            "description": pr_details.get('body', '')[:800],
            "detailed_file_analysis": '\n'.join(detailed_analysis),
            "diff_summary": diff[:2000]
        })
        
        return review.content
    
    async def post_review_to_github(self, owner: str, repo: str, pr_number: int, 
                                  review_content: str, event: str = "COMMENT") -> Dict:
        """Post review back to GitHub"""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        data = {
            "body": review_content,
            "event": event
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def extract_file_diff(self, full_diff: str, filename: str) -> str:
        """Extract diff for a specific file"""
        lines = full_diff.split('\n')
        file_diff = []
        in_file = False
        
        for line in lines:
            if line.startswith(f'diff --git a/{filename}'):
                in_file = True
            elif line.startswith('diff --git') and in_file:
                break
            elif in_file:
                file_diff.append(line)
        
    def parse_diff_changes(self, diff: str) -> str:
        """Parse diff to extract old vs new code changes"""
        if not diff:
            return "No diff content available"
            
        lines = diff.split('\n')
        changes = []
        current_section = None
        line_number = 0
        
        for line in lines:
            if line.startswith('@@'):
                # Extract line numbers from hunk header
                import re
                match = re.search(r'@@\s*-(\d+)(?:,\d+)?\s*\+(\d+)(?:,\d+)?\s*@@', line)
                if match:
                    old_line, new_line = match.groups()
                    current_section = f"Lines around {new_line}"
                    changes.append(f"\n=== {current_section} ===")
                    line_number = int(new_line)
            elif line.startswith('-') and not line.startswith('---'):
                changes.append(f"❌ REMOVED (Line ~{line_number}): {line[1:]}")
            elif line.startswith('+') and not line.startswith('+++'):
                changes.append(f"✅ ADDED (Line {line_number}): {line[1:]}")
                line_number += 1
            elif line.startswith(' '):
                # Context line
                changes.append(f"   CONTEXT (Line {line_number}): {line[1:]}")
                line_number += 1
        
        return '\n'.join(changes) if changes else "No meaningful changes found in diff"
    
    async def generate_summary(self, overall_review: str, file_reviews: List[Dict]) -> str:
        """Generate concise summary"""
        summary_prompt = ChatPromptTemplate.from_messages([
            ("system", "Create a concise 2-3 sentence summary of this PR review."),
            ("user", "Overall Review: {overall}\n\nFile Count: {file_count}")
        ])
        
        chain = summary_prompt | self.llm
        summary = await chain.ainvoke({
            "overall": overall_review[:1000],  # Limit content
            "file_count": len(file_reviews)
        })
        
        return summary.content