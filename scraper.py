import requests
from bs4 import BeautifulSoup
import streamlit as st
import json
from openai import OpenAI
import re

# Use gpt-4o-mini as it's a capable and cost-effective recent model.
# The user can change this if they have access to a specific "gpt-4.1-mini".
DEFAULT_MODEL = "gpt-4o-mini"

def scrape_website_text(url: str) -> str:
    """Scrapes main textual content from a website URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml') # 'lxml' is generally faster

        # Remove script and style elements
        for script_or_style in soup(["script", "style", "nav", "footer", "aside"]):
            script_or_style.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Basic cleaning: reduce multiple spaces/newlines
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except requests.exceptions.RequestException as e:
        st.error(f"Error scraping website {url}: {e}")
        return ""
    except Exception as e:
        st.error(f"An unexpected error occurred during website scraping: {e}")
        return ""


def extract_key_info_from_text(text_content: str, openai_client: OpenAI, model: str = DEFAULT_MODEL) -> dict:
    """Uses OpenAI to extract specific company info from text."""
    prompt = f"""
    Analyze the following text from a company's website and any provided additional materials.
    Extract the following information. If a piece of information is not found, use "Not found" or an empty list/string as appropriate.
    Return the information ONLY as a single JSON object.

    JSON Structure:
    {{
      "company_name": "string (Company's official name)",
      "tagline": "string (Company's tagline or slogan, if any)",
      "mission_statement": "string (Company's mission statement, if explicitly stated or clearly inferable)",
      "industry": "string (e.g., SaaS, E-commerce, Healthcare Technology)",
      "offerings": ["string (Product/Service 1)", "string (Product/Service 2)"],
      "USPs": ["string (Unique Selling Proposition 1)", "string (Unique Selling Proposition 2)"],
      "value_proposition": "string (Concise statement of the unique benefit provided to customers)",
      "target_audience": "string (Description of the primary target audience, e.g., 'Small to medium-sized businesses in the retail sector')",
      "tone_of_voice": "string (Describe the typical tone of voice, e.g., 'Professional and authoritative', 'Friendly and approachable', 'Witty and informal')",
      "CTAs": ["string (Common Call-to-Action phrase 1 found on site)", "string (CTA phrase 2)"]
    }}

    Text Content to Analyze (max 15000 chars for this extraction):
    ---
    {text_content[:15000]}
    ---

    Provide ONLY the JSON object. Do not include any explanatory text before or after the JSON.
    """
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse JSON from company info extraction: {e}")
            st.text_area("Problematic AI Response for Key Info Extraction:", content, height=200)
            return {
                "company_name": "Error", "tagline": "Error", "mission_statement": "Error",
                "industry": "Error", "offerings": [], "USPs": [],
                "value_proposition": "Error", "target_audience": "Error",
                "tone_of_voice": "Error", "CTAs": []
            }
    except Exception as e:
        st.error(f"OpenAI API call failed during company info extraction: {e}")
        return {
            "company_name": "API Error", "tagline": "API Error", "mission_statement": "API Error",
            "industry": "API Error", "offerings": [], "USPs": [],
            "value_proposition": "API Error", "target_audience": "API Error",
            "tone_of_voice": "API Error", "CTAs": []
        }

def scrape_downloadable_material_text(url: str) -> str:
    """Scrapes text from a downloadable material URL (assuming it's a webpage)."""
    # This is similar to scrape_website_text. If it's a direct PDF/DOCX link,
    # it would need different handling (downloading and then parsing).
    # For now, assuming it's a webpage with text content.
    return scrape_website_text(url)