import openai
import logging
from config import get_openai_api_key

# Set up logging
logger = logging.getLogger(__name__)

def generate_proposal(client_name, job_description, skills, model="gpt-3.5-turbo"):
    """
    Generates a freelance proposal using OpenAI's API.
    Args:
        client_name (str): The name of the client.
        job_description (str): The job description.
        skills (str): Skills to highlight.
        model (str): OpenAI model to use (default: gpt-3.5-turbo).
    Returns:
        str: The generated proposal text.
    Raises:
        RuntimeError: If the OpenAI API call fails.
    """
    try:
        api_key = get_openai_api_key()
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        logger.debug(f"Initializing OpenAI client with API key: {masked_key}")
        client = openai.OpenAI(api_key=api_key)
        logger.debug("OpenAI client initialized successfully")

        prompt = (
            f"Write a professional freelance proposal for the following client and job:\n\n"
            f"Client Name: {client_name}\n"
            f"Job Description: {job_description}\n"
            f"Skills to Highlight: {skills}\n\n"
            "The proposal should be concise, persuasive, and tailored to the client's needs."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful freelance proposal writer."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        logger.info("Proposal generated successfully via OpenAI API.")
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        raise RuntimeError(f"OpenAI API error: {e}")
