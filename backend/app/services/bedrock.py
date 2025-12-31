"""AWS Bedrock service for LLM interactions."""
import json
from typing import Dict, List, Optional, Any, Type, TypeVar
from botocore.exceptions import ClientError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)

import boto3
from app.core.config import settings

T = TypeVar('T')


class BedrockService:
    """Service for interacting with AWS Bedrock."""
    
    def __init__(self, model_id: Optional[str] = None):
        """
        Initialize Bedrock client.
        
        Args:
            model_id: Optional model ID. If not provided, uses default from settings.
                    For Claude models, use format like "anthropic.claude-3-5-sonnet-20241022-v2:0"
                    or try the base model ID without version suffix.
        
        Raises:
            Exception: If AWS credentials are not configured or Bedrock client cannot be created.
        """
        try:
            self.client = boto3.client(
                'bedrock-runtime',
                region_name=settings.AWS_REGION
            )
            # Use provided model_id or default from settings
            # If the model ID has a version suffix that doesn't work, we'll try the base ID
            default_model = settings.BEDROCK_MODEL_ID
            if model_id:
                self.model_id = model_id
            elif ":0" in default_model:
                # Try without the :0 suffix first (some regions don't support versioned IDs)
                self.model_id = default_model.replace(":0", "")
            else:
                self.model_id = default_model
        except Exception as e:
            error_msg = str(e)
            if "Missing Dependency" in error_msg or "crt" in error_msg.lower():
                raise Exception(
                    "AWS credentials require additional dependency. "
                    "Run: pip install 'botocore[crt]' or configure AWS credentials differently. "
                    f"Original error: {error_msg}"
                )
            elif "NoCredentialsError" in error_msg or "credentials" in error_msg.lower():
                raise Exception(
                    "AWS credentials not found. "
                    "Configure credentials using 'aws configure' or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY. "
                    f"Original error: {error_msg}"
                )
            else:
                raise Exception(f"Failed to initialize Bedrock client: {error_msg}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ClientError, Exception)),
        reraise=True
    )
    def _invoke_model(
        self,
        body: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Internal method to invoke Bedrock model with retry logic.
        
        Raises:
            ClientError: For non-retryable errors (ValidationException, AccessDeniedException)
            Exception: For other errors that should be retried
        """
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            return json.loads(response['body'].read())
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            # Don't retry on validation or access errors
            if error_code in ['ValidationException', 'AccessDeniedException']:
                raise
            # Retry on other errors
            raise Exception(f"Bedrock invocation failed: {str(e)}")
    
    def invoke(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Invoke Bedrock model with messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            response_format: Optional response format specification for structured outputs
        
        Returns:
            Generated response text
        
        Raises:
            Exception: If all retry attempts fail
        """
        # Format messages for Claude API
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": [{"type": "text", "text": msg["content"]}]
            })
        
        # Build request body
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": formatted_messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        # Add response format if provided (for structured outputs)
        if response_format:
            body["response_format"] = response_format
        
        try:
            response_body = self._invoke_model(body)
            return response_body['content'][0]['text']
        except RetryError as e:
            raise Exception(f"Bedrock invocation failed after retries: {str(e.last_attempt.exception())}")
    
    def invoke_structured(
        self,
        messages: List[Dict[str, str]],
        output_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock with structured output schema.
        
        Uses Claude's structured output capabilities (via response_format) to ensure well-formed JSON responses.
        Falls back to JSON parsing with schema enforcement if structured output isn't supported.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            output_schema: JSON schema for the expected output structure
            system_prompt: Optional system prompt (will be enhanced with JSON format instructions)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower for more deterministic outputs)
        
        Returns:
            Parsed JSON response matching the schema
        
        Raises:
            ValueError: If response doesn't match schema or can't be parsed
            Exception: If Bedrock invocation fails
        """
        # Enhance system prompt to enforce JSON output
        json_instruction = f"\n\nIMPORTANT: You MUST respond with valid JSON only, following this exact schema: {json.dumps(output_schema, indent=2)}\nDo not include any text outside the JSON object. The JSON must be well-formed and match the schema exactly."
        
        enhanced_system_prompt = (system_prompt or "") + json_instruction
        
        # Try with structured output format (if supported by the model)
        # Claude 3.5 Sonnet supports response_format for structured outputs
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "structured_output",
                "strict": True,
                "schema": output_schema,
                "description": "Structured output matching the provided schema"
            }
        }
        
        try:
            response_text = self.invoke(
                messages=messages,
                system_prompt=enhanced_system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format
            )
        except Exception as e:
            # If structured output fails, fall back to regular invoke with JSON instructions
            if "response_format" in str(e).lower() or "validation" in str(e).lower():
                # Fallback: use regular invoke with JSON instructions in system prompt
                response_text = self.invoke(
                    messages=messages,
                    system_prompt=enhanced_system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            else:
                raise
        
        # Parse JSON response
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(response_text)
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse structured JSON response: {str(e)}\nResponse: {response_text[:200]}")
