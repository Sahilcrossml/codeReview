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
        """Analyze changes in a specific file with detailed code quality assessment"""
        file_path = file_info['filename']
        
        # Extract file-specific diff
        file_diff = self.extract_file_diff(full_diff, file_path)
        
        # Parse the diff to extract old and new code
        code_changes = self.parse_diff_changes(file_diff)
        
        # Enhanced analysis prompt for better code quality
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a senior software architect and code reviewer. Provide comprehensive analysis focusing on:

**CODE QUALITY ASSESSMENT:**
1. **Design Patterns & Architecture**: Identify anti-patterns, suggest better architectural approaches
2. **Performance Analysis**: Identify bottlenecks, memory issues, algorithmic complexity problems
3. **Security Review**: Find vulnerabilities, injection risks, authentication issues
4. **Maintainability**: Code readability, modularity, documentation needs
5. **Best Practices**: Language-specific conventions, error handling, testing gaps

**DETAILED FEEDBACK FORMAT:**
For each issue found:
- **Severity**: CRITICAL/HIGH/MEDIUM/LOW
- **Category**: Performance/Security/Maintainability/Style/Logic
- **Location**: Exact line numbers from the diff
- **Problem**: Clear description of the issue
- **Impact**: Why this matters (performance, security, maintenance)
- **Solution**: Specific code improvement with examples

**CODE SUGGESTIONS:**
- Show ORIGINAL code vs IMPROVED code side-by-side
- Explain WHY the improvement is better
- Consider edge cases and error handling
- Suggest performance optimizations
- Recommend additional features or refactoring

Be specific, actionable, and focus on making the code production-ready."""),
            ("user", """
**File**: {filename}
**Language**: {language}
**Changes**: +{additions} -{deletions} lines

**Diff Analysis**:
{diff}

**Code Changes Summary**:
{changes_summary}

Please provide detailed analysis with specific code improvements.
""")
        ])
        
        # Detect programming language
        language = self.detect_language(file_path)
        
        chain = analysis_prompt | self.llm
        analysis = await chain.ainvoke({
            "filename": file_path,
            "language": language,
            "additions": file_info.get('additions', 0),
            "deletions": file_info.get('deletions', 0),
            "diff": file_diff[:5000],  # Increased for better context
            "changes_summary": code_changes
        })
        
        # Generate specific code improvements
        improvement_suggestions = await self.generate_code_improvements(file_path, file_diff, language)
        
        return {
            "file": file_path,
            "language": language,
            "analysis": analysis.content,
            "code_changes": code_changes,
            "improvements": improvement_suggestions,
            "changes": {
                "additions": file_info.get('additions', 0),
                "deletions": file_info.get('deletions', 0)
            }
        }
    
    async def generate_overall_review(self, pr_details: Dict, diff: str, file_reviews: List[Dict]) -> str:
        """Generate comprehensive PR review with code quality focus"""
        review_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Principal Software Engineer conducting a comprehensive code review. Provide structured feedback:

## 🎯 EXECUTIVE SUMMARY
- **Recommendation**: APPROVE/REQUEST_CHANGES/COMMENT with clear reasoning
- **Overall Quality Score**: X/10 with justification
- **Key Impact**: Performance/Security/Maintainability assessment

## 📊 DETAILED ANALYSIS

### 🏗️ Architecture & Design
- Design pattern usage
- Code organization
- Separation of concerns
- Scalability considerations

### ⚡ Performance Analysis
- Algorithm complexity
- Memory usage patterns
- Database efficiency
- Caching opportunities
- Async/concurrency usage

### 🔒 Security Review
- Input validation
- Authentication/authorization
- Data sanitization
- Vulnerability assessment

### 🧹 Code Quality
- Readability and maintainability
- Error handling robustness
- Testing coverage gaps
- Documentation needs

### 📋 Specific Improvements
For each file, provide:
- **Critical Issues** (must fix before merge)
- **Performance Optimizations** (should implement)
- **Code Quality Improvements** (recommended)

## 🚀 ACTIONABLE RECOMMENDATIONS
1. **Immediate Actions** (blocking issues)
2. **Short-term Improvements** (next sprint)
3. **Long-term Enhancements** (technical debt)

## ✅ POSITIVE ASPECTS
Highlight good practices and well-implemented features.

Be specific, actionable, and focus on production readiness."""),
            ("user", """
**PR Title**: {title}
**Description**: {description}

**Detailed File Analysis**:
{detailed_file_analysis}

**Performance & Quality Focus**:
{improvements_summary}

Provide comprehensive review with emphasis on code quality and performance.
""")
        ])
        
        # Create detailed analysis with improvements
        detailed_analysis = []
        improvements_summary = []
        
        for review in file_reviews:
            detailed_analysis.append(f"""
### 📁 {review['file']} ({review.get('language', 'Unknown')})
**Changes**: +{review['changes']['additions']} -{review['changes']['deletions']} lines

**Quality Analysis**:
{review['analysis']}

**Code Improvements**:
{review.get('improvements', 'No specific improvements generated')}
""")
            
            if 'improvements' in review:
                improvements_summary.append(f"**{review['file']}**: {review['improvements'][:200]}...")
        
        chain = review_prompt | self.llm
        review = await chain.ainvoke({
            "title": pr_details.get('title', ''),
            "description": pr_details.get('body', '')[:1000],
            "detailed_file_analysis": '\n'.join(detailed_analysis),
            "improvements_summary": '\n'.join(improvements_summary)
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
        
    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.html': 'HTML',
            '.css': 'CSS',
            '.sql': 'SQL',
            '.sh': 'Shell',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.json': 'JSON',
            '.xml': 'XML',
            '.md': 'Markdown'
        }
        
        for ext, lang in ext_map.items():
            if file_path.lower().endswith(ext):
                return lang
        return 'Unknown'

    async def generate_code_improvements(self, file_path: str, diff: str, language: str) -> str:
        """Generate specific code improvement suggestions"""
        improvement_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert {language} developer and performance optimizer. 

**TASK**: Analyze the code changes and provide specific improvements focusing on:

1. **Performance Optimizations**:
   - Algorithm efficiency improvements
   - Memory usage optimization
   - Database query optimization
   - Caching strategies
   - Async/await improvements

2. **Code Quality Enhancements**:
   - Better error handling
   - Input validation
   - Code organization
   - Design patterns
   - Testing strategies

3. **Security Improvements**:
   - Input sanitization
   - Authentication/authorization
   - Data validation
   - SQL injection prevention
   - XSS protection

**OUTPUT FORMAT**:
```
## 🎯 ORIGINAL CODE vs IMPROVED CODE

### Issue 1: [Problem Description]
**Severity**: HIGH/MEDIUM/LOW
**Category**: Performance/Security/Quality

**Original Code:**
```{language}
[show original code from diff]
```

**Improved Code:**
```{language}
[show improved version]
```

**Why This Is Better:**
- [Specific reason 1]
- [Specific reason 2]
- [Performance/security benefit]

### Issue 2: [Next Problem]
[Continue pattern]
```

Focus on actionable, production-ready improvements."""),
            ("user", f"""
**File**: {file_path}
**Language**: {language}

**Diff to analyze**:
{diff}

Provide specific code improvements with before/after examples.
""")
        ])
        
        chain = improvement_prompt | self.llm
        improvements = await chain.ainvoke({
            "file_path": file_path,
            "language": language,
            "diff": diff[:3000]  # Limit for context
        })
        
        return improvements.content
    
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