import json
import time
import streamlit as st
from openai import OpenAI

# Use gpt-4o-mini as it's a capable and cost-effective recent model.
# The user can change this if they have access to a specific "gpt-4.1-mini".
DEFAULT_MODEL = "gpt-4o-mini" 

def _call_openai_api_sync(prompt: str, openai_client: OpenAI, model: str = DEFAULT_MODEL) -> dict | None:
    """Makes a synchronous API call to OpenAI and parses JSON output."""
    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except json.JSONDecodeError as e:
        st.error(f"AI response JSON parsing error: {e}")
        st.text_area("Problematic AI Response:", content, height=150)
        return None
    except Exception as e:
        st.error(f"OpenAI API call failed: {e}")
        return None

def generate_email_prompts(company_info, lead_objective_type, lead_objective_url, downloadable_material_context, num_emails):
    prompts = []
    email_objective = "Demand Capture"
    email_destination_url = lead_objective_url
    email_cta_text_suggestion = f"Book a {lead_objective_type}" if lead_objective_type else "Learn More"

    for i in range(num_emails):
        sequence_guidance = ""
        if num_emails > 1:
            sequence_guidance = f"This is email {i+1} of a {num_emails}-email sequence. The messaging should evolve."
            if i == 0: sequence_guidance += " This first email should introduce the core value."
            elif i == num_emails - 1: sequence_guidance += " This last email should be a final engagement attempt."
            else: sequence_guidance += " This email should build on previous messages."

        prompt = f"""
        You are an expert email marketing copywriter for {company_info.get('company_name', 'the company')}.
        Company Info: Tone: {company_info.get('tone_of_voice', 'professional')}, Offerings: {company_info.get('offerings', [])}, USPs: {company_info.get('USPs', [])}.
        Target Audience: {company_info.get('target_audience', 'potential clients')}.
        Email Details: Objective: {email_objective}, Lead Objective: {lead_objective_type}, CTA URL: {email_destination_url}.
        {sequence_guidance}
        Downloadable Material Context (if relevant): {downloadable_material_context if downloadable_material_context else "N/A"}

        Output JSON: {{
          "version_number": {i + 1}, "objective": "{email_objective}",
          "headline": "Captivating email headline/hook (internal title or first impactful sentence).",
          "subject_line": "Compelling email subject line.",
          "body": "Email body (2-3 paragraphs). Embed CTA naturally. {sequence_guidance} Adhere to company tone. Mention downloadable material if relevant.",
          "cta": "Brief CTA description (e.g., 'Click here to book your demo ({email_cta_text_suggestion})')."
        }}
        Provide ONLY the JSON object.
        """
        prompts.append({"type": "email", "prompt": prompt, "version": i + 1, "objective_type": email_objective})
    return prompts

def generate_linkedin_ad_prompts(company_info, lead_objective_type, lead_objective_url, downloadable_material_context, downloadable_material_url, num_pieces):
    prompts = []
    linkedin_objectives = ["Brand Awareness", "Demand Gen", "Demand Capture"]
    base_cta_options = {"Demo Booking": ["Request Demo", "Book Now"], "Sales Meeting": ["Book Meeting", "Schedule Call"]}

    for i in range(num_pieces):
        for objective in linkedin_objectives:
            dest_url = lead_objective_url
            cta_buttons = base_cta_options.get(lead_objective_type, []) + ["Learn More"]
            
            current_downloadable_context = "N/A"
            if downloadable_material_url and objective in ["Demand Gen", "Brand Awareness"]:
                dest_url = downloadable_material_url
                cta_buttons = ["Download", "Learn More"]
                current_downloadable_context = downloadable_material_context if downloadable_material_context else "Available for download."

            prompt = f"""
            Generate a LinkedIn ad for {company_info.get('company_name', 'the company')}.
            Company Info: Tone: {company_info.get('tone_of_voice', 'professional')}, Offerings: {company_info.get('offerings', [])}, USPs: {company_info.get('USPs', [])}.
            Target Audience: {company_info.get('target_audience', 'professionals')}.
            Ad Details: Objective: {objective}, Lead Objective: {lead_objective_type}, Destination URL: {dest_url}.
            Downloadable Material Context: {current_downloadable_context}

            Output JSON: {{
              "version_number": {i + 1},
              "ad_name": "LinkedIn Ad - {objective} - V{i + 1} - [Unique focus/keyword]",
              "objective": "{objective}",
              "introductory_text": "Hook in first 150 chars. Total 200-350 chars (max 500). Use emojis. Align with company tone.",
              "image_copy": "Short text for ad image (max 125 chars).",
              "headline": "Compelling headline (max 70 chars).",
              "destination": "{dest_url}",
              "cta_button": "Choose one from: {', '.join(cta_buttons)}. If 'Download', ensure ad promotes it."
            }}
            Ad name max 255 chars. Provide ONLY the JSON object.
            """
            prompts.append({"type": "linkedin", "prompt": prompt, "version": i + 1, "objective_type": objective})
    return prompts

def generate_facebook_ad_prompts(company_info, lead_objective_type, lead_objective_url, downloadable_material_context, downloadable_material_url, num_pieces):
    prompts = []
    fb_objectives = ["Brand Awareness", "Demand Gen", "Demand Capture"]
    base_cta_options = {"Demo Booking": ["Book Now", "Request Demo"], "Sales Meeting": ["Book Now", "Schedule Call"]}

    for i in range(num_pieces):
        for objective in fb_objectives:
            dest_url = lead_objective_url
            cta_buttons = base_cta_options.get(lead_objective_type, []) + ["Learn More"]

            current_downloadable_context = "N/A"
            if downloadable_material_url and objective in ["Demand Gen", "Brand Awareness"]:
                dest_url = downloadable_material_url
                cta_buttons = ["Download", "Learn More"]
                current_downloadable_context = downloadable_material_context if downloadable_material_context else "Available for download."

            prompt = f"""
            Generate a Facebook ad for {company_info.get('company_name', 'the company')}.
            Company Info: Tone: {company_info.get('tone_of_voice', 'professional')}, Offerings: {company_info.get('offerings', [])}, USPs: {company_info.get('USPs', [])}.
            Target Audience: {company_info.get('target_audience', 'relevant users')}.
            Ad Details: Objective: {objective}, Lead Objective: {lead_objective_type}, Destination URL: {dest_url}.
            Downloadable Material Context: {current_downloadable_context}

            Output JSON: {{
              "version_number": {i + 1},
              "ad_name": "Facebook Ad - {objective} - V{i + 1} - [Unique focus/keyword]",
              "objective": "{objective}",
              "primary_text": "Hook in first 125 chars. Total 200-350 chars (max 500). Use emojis. Align with company tone.",
              "image_copy": "Short text for ad image (max 125 chars).",
              "headline": "Compelling headline (max 27 chars).",
              "link_description": "Link description (max 27 chars).",
              "destination": "{dest_url}",
              "cta_button": "Choose one from: {', '.join(cta_buttons)}. If 'Download', ensure ad promotes it."
            }}
            Ad name max 255 chars. Provide ONLY the JSON object.
            """
            prompts.append({"type": "facebook", "prompt": prompt, "version": i + 1, "objective_type": objective})
    return prompts

def generate_google_search_ad_prompt(company_info):
    prompt = f"""
    Generate Google Search Ad components for {company_info.get('company_name', 'the company')}.
    Company Info: Offerings: {company_info.get('offerings', [])}, USPs: {company_info.get('USPs', [])}, Target Audience: {company_info.get('target_audience', 'search users')}.
    Output JSON: {{
      "headlines": ["Headline 1 (max 30 chars)", /* ...14 more headlines */ ],
      "descriptions": ["Description 1 (max 90 chars)", /* ...3 more descriptions */ ]
    }}
    Provide exactly 15 unique, compelling headlines (max 30 chars each).
    Provide exactly 4 unique, informative descriptions (max 90 chars each).
    Provide ONLY the JSON object.
    """
    return {"type": "google_search", "prompt": prompt}

def generate_google_display_ad_prompt(company_info):
    prompt = f"""
    Generate Google Display Ad components for {company_info.get('company_name', 'the company')}.
    Company Info: Offerings: {company_info.get('offerings', [])}, USPs: {company_info.get('USPs', [])}, Target Audience: {company_info.get('target_audience', 'relevant audience segments')}.
    Output JSON: {{
      "headlines": ["Headline 1 (max 30 chars)", /* ...4 more headlines */ ],
      "descriptions": ["Description 1 (max 90 chars)", /* ...4 more descriptions */ ]
    }}
    Provide exactly 5 unique, compelling headlines (max 30 chars each).
    Provide exactly 5 unique, informative descriptions (max 90 chars each).
    Provide ONLY the JSON object.
    """
    return {"type": "google_display", "prompt": prompt}

def generate_reasoning_prompt(company_info, all_scraped_text, lead_objective_type, downloadable_material_context):
    prompt = f"""
    You are a senior marketing consultant. Based on the provided company information and context, provide a strategic reasoning statement.
    Explain how the company data (name, offerings, USPs, target audience, tone: {company_info.get('tone_of_voice')}), website content, lead objective ({lead_objective_type}),
    and any downloadable material context ({'Provided' if downloadable_material_context else 'Not provided'})
    were (or would be) used to tailor the generated marketing ad content for different platforms.

    Company Information Extracted: {json.dumps(company_info, indent=2)}
    Full Scraped Text Summary (first 1000 chars): {all_scraped_text[:1000]}...
    Downloadable Material Context: {downloadable_material_context if downloadable_material_context else "N/A"}

    Output JSON: {{
      "reasoning_statement": "Your detailed reasoning here. Explain data influence on content strategy."
    }}
    Provide ONLY the JSON object.
    """
    return prompt


def compile_all_prompts(company_info, lead_objective_type, lead_objective_url,
                        downloadable_material_context, downloadable_material_url,
                        num_content_pieces, full_scraped_text_for_reasoning):
    all_prompts_dict = {
        "email": generate_email_prompts(company_info, lead_objective_type, lead_objective_url, downloadable_material_context, num_content_pieces),
        "linkedin": generate_linkedin_ad_prompts(company_info, lead_objective_type, lead_objective_url, downloadable_material_context, downloadable_material_url, num_content_pieces),
        "facebook": generate_facebook_ad_prompts(company_info, lead_objective_type, lead_objective_url, downloadable_material_context, downloadable_material_url, num_content_pieces),
        "google_search": [generate_google_search_ad_prompt(company_info)], # List of one for consistency
        "google_display": [generate_google_display_ad_prompt(company_info)], # List of one
        "reasoning": generate_reasoning_prompt(company_info, full_scraped_text_for_reasoning, lead_objective_type, downloadable_material_context)
    }
    return all_prompts_dict

def generate_all_content(all_prompts_dict, openai_client, progress_bar_updater, status_updater, model=DEFAULT_MODEL):
    results = {"email": [], "linkedin": [], "facebook": [], "google_search": [], "google_display": [], "reasoning": None}
    
    total_api_calls = 0
    for platform, prompts_or_prompt_str in all_prompts_dict.items():
        if platform == "reasoning":
            if prompts_or_prompt_str: total_api_calls +=1
        elif isinstance(prompts_or_prompt_str, list):
            total_api_calls += len(prompts_or_prompt_str)
            
    completed_api_calls = 0

    for platform, prompts_list_or_str in all_prompts_dict.items():
        if platform == "reasoning":
            if prompts_list_or_str: # This is a single prompt string
                status_updater(f"Generating reasoning statement...")
                reasoning_content = _call_openai_api_sync(prompts_list_or_str, openai_client, model)
                if reasoning_content:
                    results["reasoning"] = reasoning_content
                completed_api_calls += 1
                progress_bar_updater(completed_api_calls / total_api_calls if total_api_calls > 0 else 1)
                time.sleep(1) # API rate limit
            continue

        # For other platforms, it's a list of prompt objects
        for prompt_obj in prompts_list_or_str:
            prompt_text = prompt_obj["prompt"]
            version = prompt_obj.get("version", 1)
            objective = prompt_obj.get("objective_type", "N/A")
            
            status_updater(f"Generating content for {platform.capitalize()} ({objective} - V{version})...")
            
            generated_data = _call_openai_api_sync(prompt_text, openai_client, model)
            if generated_data:
                results[platform].append(generated_data)
            else: # Add a placeholder if API call failed for this item
                error_placeholder = {"error": f"Failed to generate content for {platform} V{version} ({objective})"}
                if platform in ["google_search", "google_display"]: # These expect specific structures
                     error_placeholder = {"headlines": [f"Error generating for {platform}"], "descriptions": ["Error"]}
                results[platform].append(error_placeholder)

            completed_api_calls += 1
            progress_bar_updater(completed_api_calls / total_api_calls if total_api_calls > 0 else 1)
            time.sleep(1) # Slight delay

    return results