import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class GitHubConfig:
    token: str = os.getenv("GITHUB_TOKEN")
    openai_api_key: str = os.getenv("OPENAI_API_KEY")
    
    def validate(self):
        """Validate required configuration"""
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Set OpenAI API key
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        
        return True