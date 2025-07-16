import openai
import logging
from config import get_openai_api_key

# Set up logging
logger = logging.getLogger(__name__)

# Generates a freelance proposal using OpenAI's API (OpenAI Python >=1.0.0)
def generate_proposal(client_name, job_description, skills, model="gpt-3.5-turbo"):
    try:
        # Debug: Log the API key (masked) and any environment variables
        api_key = get_openai_api_key()
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        logger.debug(f"Initializing OpenAI client with API key: {masked_key}")
        
        # Debug: Check for proxy environment variables
        import os
        http_proxy = os.environ.get('HTTP_PROXY')
        https_proxy = os.environ.get('HTTPS_PROXY')
        if http_proxy or https_proxy:
            logger.debug(f"Proxy environment variables found: HTTP_PROXY={http_proxy}, HTTPS_PROXY={https_proxy}")
        
        # Debug: Log the client initialization
        logger.debug("About to initialize openai.OpenAI client")
        
        client = openai.OpenAI(api_key=api_key)
        
        logger.debug("OpenAI client initialized successfully")
        
        prompt = f"""
Write a professional freelance proposal for the following client and job:

Client Name: {client_name}
Job Description: {job_description}
Skills to Highlight: {skills}

The proposal should be concise, persuasive, and tailored to the client's needs.
"""
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful freelance proposal writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise RuntimeError(f"OpenAI API error: {e}")
