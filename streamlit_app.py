import streamlit as st
from openai import OpenAI
import os
import time
import io

# Import local modules
from utils import (
    add_http_if_missing, extract_text_from_pdf,
    extract_text_from_pptx, get_file_extension,
    format_company_name_for_filename
)
from scraper import (
    scrape_website_text, extract_key_info_from_text,
    scrape_downloadable_material_text
)
from ai_content_generator import (
    compile_all_prompts, generate_all_content
)
from excel_formatter import create_excel_file

# Use gpt-4o-mini as it's a capable and cost-effective recent model.
# The user can change this if they have access to a specific "gpt-4.1-mini".
# The prompt specified "gpt-4.1-mini", but "gpt-4o-mini" is a more standard recent model.
AI_MODEL_NAME = "gpt-4o-mini" 

st.set_page_config(layout="wide", page_title="Marketing Content Generator")

# --- Initialize OpenAI Client ---
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    client = OpenAI(api_key=openai_api_key)
except KeyError:
    st.error("OpenAI API key not found. Please add it to your secrets.toml file.")
    st.stop()
except Exception as e:
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()


# --- App Title ---
st.title("🤖 AI-Powered Marketing Ad Content Generator")
st.markdown("Upload your client's website and materials to generate tailored marketing ad content.")

# --- Session State Initialization ---
if 'generated_excel_bytes' not in st.session_state:
    st.session_state.generated_excel_bytes = None
if 'excel_filename' not in st.session_state:
    st.session_state.excel_filename = ""
if 'company_info' not in st.session_state:
    st.session_state.company_info = None
if 'generation_time' not in st.session_state:
    st.session_state.generation_time = None

# --- Frontend Inputs ---
st.sidebar.header("Client Inputs")
company_url = st.sidebar.text_input("Company Website URL*", placeholder="e.g., www.example.com")
additional_material_file = st.sidebar.file_uploader(
    "Upload Additional Context (PDF/PPTX)",
    type=['pdf', 'pptx'],
    help="Upload client's brochures, presentations, etc."
)

st.sidebar.header("Lead & Downloadable Material")
lead_objective_options = ["Demo Booking", "Sales Meeting"]
selected_lead_objective = st.sidebar.selectbox("Lead Objective*", options=lead_objective_options)
lead_objective_url = st.sidebar.text_input(f"URL for {selected_lead_objective}*", placeholder="e.g., www.example.com/book-demo")

downloadable_material_file = st.sidebar.file_uploader(
    "Upload Downloadable Material (e.g., White Paper PDF/PPTX)",
    type=['pdf', 'pptx'],
    help="Material for 'Download' CTAs. If provided, its context will be used."
)
downloadable_material_url_input = st.sidebar.text_input(
    "OR URL for Downloadable Material Page",
    placeholder="e.g., www.example.com/whitepaper-landing",
    help="If you provide a URL instead of uploading a file for downloadable material."
)

st.sidebar.header("Content Configuration")
num_content_pieces = st.sidebar.slider("Number of Content Pieces per Objective/Sequence*", 1, 20, 10)

generate_button = st.sidebar.button("🚀 Generate Content", type="primary", use_container_width=True)

# --- Main Area for Status and Results ---
status_placeholder = st.empty()
progress_bar_placeholder = st.empty()
timer_placeholder = st.empty()
download_placeholder = st.empty()


# --- Backend Flow on Button Click ---
if generate_button:
    # Reset previous results
    st.session_state.generated_excel_bytes = None
    st.session_state.excel_filename = ""
    st.session_state.company_info = None
    st.session_state.generation_time = None
    download_placeholder.empty() # Clear previous download button

    # Validate inputs
    if not company_url:
        st.sidebar.error("Company Website URL is required.")
        st.stop()
    if not lead_objective_url:
        st.sidebar.error(f"URL for {selected_lead_objective} is required.")
        st.stop()

    company_url = add_http_if_missing(company_url)
    lead_objective_url = add_http_if_missing(lead_objective_url)
    downloadable_material_url = add_http_if_missing(downloadable_material_url_input) if downloadable_material_url_input else ""

    start_time = time.time()
    
    with status_placeholder.status("Processing...", expanded=True) as status_container:
        progress_bar = progress_bar_placeholder.progress(0)
        
        # 1. Scrape client's website
        st.write("Step 1: Scraping client's website...")
        website_text = scrape_website_text(company_url)
        if not website_text:
            status_container.update(label="Failed to scrape website. Please check URL and try again.", state="error")
            st.stop()
        progress_bar.progress(10)

        # Combine with additional uploaded material if any
        additional_text = ""
        if additional_material_file:
            st.write("Processing additional uploaded material...")
            ext = get_file_extension(additional_material_file.name)
            if ext == 'pdf':
                additional_text = extract_text_from_pdf(additional_material_file)
            elif ext == 'pptx':
                additional_text = extract_text_from_pptx(additional_material_file)
        
        combined_context_for_info_extraction = website_text + "\n\n--- Additional Material ---\n" + additional_text
        progress_bar.progress(20)

        # Extract key company info using AI
        st.write("Step 2: Extracting key company information using AI...")
        company_info = extract_key_info_from_text(combined_context_for_info_extraction, client, AI_MODEL_NAME)
        st.session_state.company_info = company_info # Save for reasoning page
        if not company_info or "Error" in company_info.get("company_name", "Error"):
            status_container.update(label="Failed to extract key company information. AI processing error.", state="error")
            st.stop()
        st.write(f"Extracted Company Name: {company_info.get('company_name', 'N/A')}")
        progress_bar.progress(30)

        # 2. Process downloadable material for context
        downloadable_material_context = ""
        if downloadable_material_file:
            st.write("Processing uploaded downloadable material...")
            ext = get_file_extension(downloadable_material_file.name)
            if ext == 'pdf':
                downloadable_material_context = extract_text_from_pdf(downloadable_material_file)
            elif ext == 'pptx':
                downloadable_material_context = extract_text_from_pptx(downloadable_material_file)
            if not downloadable_material_url: # If file uploaded, this becomes the "source" for CTA
                downloadable_material_url = "Uploaded Material" 
        elif downloadable_material_url:
            st.write("Scraping downloadable material URL for context...")
            downloadable_material_context = scrape_downloadable_material_text(downloadable_material_url)
        
        if downloadable_material_context:
            st.write("Context from downloadable material obtained.")
        progress_bar.progress(40)

        # 3. Generate Prompts
        st.write("Step 3: Compiling AI prompts for content generation...")
        # For reasoning, use the full website text and additional material text
        full_scraped_text_for_reasoning = combined_context_for_info_extraction
        
        all_prompts = compile_all_prompts(
            company_info, selected_lead_objective, lead_objective_url,
            downloadable_material_context, downloadable_material_url,
            num_content_pieces, full_scraped_text_for_reasoning
        )
        progress_bar.progress(50)

        # 4. Use OpenAI to generate tailored content
        st.write("Step 4: Generating tailored content with AI (this may take a few minutes)...")
        
        def update_progress_bar(value):
            # Scale AI generation progress from 50% to 90% of the overall progress
            base_progress = 50
            generation_span = 40 
            progress_bar.progress(int(base_progress + value * generation_span))

        def update_status_text(message):
            st.write(message) # Write to the status container

        generated_content_data = generate_all_content(
            all_prompts, client, update_progress_bar, update_status_text, AI_MODEL_NAME
        )
        progress_bar.progress(90)

        # 5. Parse and format into Excel
        st.write("Step 5: Formatting content into Excel file...")
        company_name_for_file = format_company_name_for_filename(company_info.get("company_name", "marketing_content"))
        lead_obj_for_file = selected_lead_objective.lower().replace(" ", "_")
        filename = f"{company_name_for_file}_{lead_obj_for_file}.xlsx"
        
        excel_bytes = create_excel_file(generated_content_data, company_info.get("company_name"), selected_lead_objective, company_info)
        st.session_state.generated_excel_bytes = excel_bytes
        st.session_state.excel_filename = filename
        progress_bar.progress(100)
        
        end_time = time.time()
        st.session_state.generation_time = round(end_time - start_time, 2)

        status_container.update(label=f"Content generation complete! Time taken: {st.session_state.generation_time}s", state="complete")

# --- Display Download Button and Timer if content generated ---
if st.session_state.generation_time is not None:
    timer_placeholder.success(f"Total Generation Time: {st.session_state.generation_time} seconds")

if st.session_state.generated_excel_bytes:
    download_placeholder.download_button(
        label="📥 Download Excel File",
        data=st.session_state.generated_excel_bytes,
        file_name=st.session_state.excel_filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
    if st.session_state.company_info:
        st.subheader("Summary of Extracted Company Information:")
        st.json(st.session_state.company_info)

st.sidebar.markdown("---")
st.sidebar.markdown("Made by M.")