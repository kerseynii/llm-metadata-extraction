"""
LLM Client for interacting with Ollama-hosted language models.
"""
from typing import Optional, Dict, Any
import ollama


class LLMClient:
    """Client for interacting with LLMs via Ollama."""
    
    def __init__(self, base_url: str, model: str):
        """
        Initialize the LLM client.
        
        Args:
            base_url: The base URL of the Ollama server
            model: The name of the model to use
        """
        self.base_url = base_url
        self.model = model
        self.client = ollama.Client(host=base_url)
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text based on a prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the generation
            
        Returns:
            Generated text response
        """
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            **kwargs
        )
        return response['response']
    
    def chat(self, messages: list[Dict[str, str]], **kwargs) -> str:
        """
        Have a chat conversation with the model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for the chat
            
        Returns:
            Model's response message
        """
        response = self.client.chat(
            model=self.model,
            messages=messages,
            **kwargs
        )
        return response['message']['content']
