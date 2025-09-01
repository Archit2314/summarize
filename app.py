import streamlit as st
import pdfplumber
import google.generativeai as genai
import os
from io import BytesIO

# Configure the page
st.set_page_config(
    page_title="AI PDF Summarizer",
    page_icon="📄",
    layout="wide"
)

st.title("📄 AI PDF Summarizer")
st.markdown("Upload a PDF document and get an AI-generated summary!")

# Sidebar for API key configuration
with st.sidebar:
    st.header("🔧 Configuration")
    
    # Try to get API key from secrets first, then from user input
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    
    if not api_key:
        api_key = st.text_input(
            "Google API Key", 
            type="password",
            help="Enter your Google Generative AI API key"
        )
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            st.success("✅ API key configured successfully!")
        except Exception as e:
            st.error(f"❌ Error configuring API: {e}")
            model = None
    else:
        st.info("👆 Please enter your Google API key to use the summarizer")
        model = None

# Function to read PDF content
@st.cache_data
def read_pdf_content(uploaded_file):
    """Extract text from uploaded PDF file"""
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

# Function to chunk text
def chunk_text(text, chunk_size=1000, overlap=100):
    """Split text into chunks for processing"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end > len(text):
            end = len(text)
        if end < len(text):
            # Try to break at word boundary
            while end > start and text[end-1].isalnum():
                end -= 1
            if end == start:
                end = start + chunk_size
                if end < len(text):
                    while end < len(text) and text[end-1].isalnum():
                        end += 1
        chunks.append(text[start:end])
        start = end - overlap if end - overlap > start else end
    return chunks

# Function to summarize text
def summarize_text(text_chunks, model):
    """Generate summaries for text chunks"""
    summaries = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, chunk in enumerate(text_chunks):
        try:
            status_text.text(f"Summarizing chunk {i+1}/{len(text_chunks)}...")
            prompt = f"Summarize the following text in a clear and concise manner:\n{chunk}"
            response = model.generate_content(prompt)
            summaries.append(response.text)
            progress_bar.progress((i + 1) / len(text_chunks))
        except Exception as e:
            st.error(f"Error summarizing chunk {i+1}: {e}")
            summaries.append(f"[Error summarizing chunk {i+1}]")
    
    status_text.empty()
    progress_bar.empty()
    return summaries

# Main interface
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type="pdf",
        help="Upload a PDF document to summarize"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        # Display file info
        file_size = len(uploaded_file.getvalue())
        st.info(f"📊 File size: {file_size / 1024:.1f} KB")

with col2:
    st.header("⚙️ Settings")
    chunk_size = st.slider(
        "Chunk Size (characters)",
        min_value=500,
        max_value=2000,
        value=1000,
        step=100,
        help="Size of text chunks for processing"
    )
    
    overlap = st.slider(
        "Overlap (characters)",
        min_value=0,
        max_value=200,
        value=100,
        step=25,
        help="Overlap between consecutive chunks"
    )

# Processing section
if uploaded_file is not None and model is not None:
    if st.button("🚀 Generate Summary", type="primary"):
        with st.spinner("Extracting text from PDF..."):
            pdf_text = read_pdf_content(uploaded_file)
        
        if pdf_text.strip():
            st.success(f"✅ Extracted {len(pdf_text)} characters from PDF")
            
            # Show text preview
            with st.expander("📄 Text Preview"):
                st.text_area("Extracted Text (first 1000 characters):", 
                            pdf_text[:1000] + "..." if len(pdf_text) > 1000 else pdf_text,
                            height=200)
            
            # Generate summary
            text_chunks = chunk_text(pdf_text, chunk_size, overlap)
            st.info(f"📋 Split text into {len(text_chunks)} chunks")
            
            with st.spinner("Generating summary..."):
                summaries = summarize_text(text_chunks, model)
            
            # Display results
            st.header("📝 Summary")
            
            # Combined summary
            full_summary = "\n\n".join(summaries)
            st.markdown("### Complete Summary")
            st.markdown(full_summary)
            
            # Individual chunk summaries
            with st.expander(f"📋 Individual Chunk Summaries ({len(summaries)} chunks)"):
                for i, summary in enumerate(summaries):
                    st.markdown(f"*Chunk {i+1}:*")
                    st.markdown(summary)
                    if i < len(summaries) - 1:
                        st.divider()
            
            # Download summary
            st.download_button(
                label="💾 Download Summary",
                data=full_summary,
                file_name=f"summary_{uploaded_file.name}.txt",
                mime="text/plain"
            )
        else:
            st.error("❌ Could not extract text from PDF. Please check if the PDF contains readable text.")

elif uploaded_file is not None and model is None:
    st.warning("⚠️ Please configure your Google API key in the sidebar to generate summaries.")

# Footer
st.markdown("---")
st.markdown("💡 *Tip:* Make sure your PDF contains selectable text (not scanned images) for best results.")

# Instructions
with st.expander("📖 How to use"):
    st.markdown("""
    1. *Get a Google API Key:*
       - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
       - Create a new API key
       - Copy and paste it in the sidebar
    
    2. *Upload your PDF:*
       - Click "Browse files" or drag and drop
       - Wait for the file to upload
    
    3. *Adjust settings (optional):*
       - Chunk size: Larger chunks = more context, but may hit API limits
       - Overlap: Prevents losing context at chunk boundaries
    
    4. *Generate summary:*
       - Click "Generate Summary"
       - Wait for processing to complete
       - Download or copy the results
    """)

