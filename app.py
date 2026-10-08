# ats-resume-checker
import streamlit as st
import google.generativeai as genai
import PyPDF2
import io
import re

# ---------------------- CONFIGURATION ----------------------
st.set_page_config(
    page_title="ATS Resume Checker",
    page_icon="📄",
    layout="wide"
)

# Get API key from Streamlit secrets or user input
API_KEY = None
if "GOOGLE_API_KEY" in st.secrets:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    API_KEY = st.sidebar.text_input("🔑 Enter your Google Gemini API Key", type="password")
    st.sidebar.info("Get your free API key from https://aistudio.google.com/")

if not API_KEY:
    st.warning("⚠️ Please enter your Gemini API key to continue.")
    st.stop()

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-flash-expansion")

# ---------------------- TEXT EXTRACTION ----------------------
def extract_text_from_pdf(uploaded_file):
    """Extract text from uploaded PDF resume"""
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if not text.strip():
            return None, "❌ Could not extract text. Try a different PDF or plain text resume."
        return text, None
    except Exception as e:
        return None, f"Error reading PDF: {str(e)}"

# ---------------------- ATS SCORING PROMPT ----------------------
def analyze_resume_with_gemini(resume_text):
    prompt = f"""You are an expert ATS (Applicant Tracking System) analyzer and career coach.

Analyze this resume and return a structured assessment:

--- RESUME START ---
{resume_text}
--- RESUME END ---

Return your response in this EXACT format:

SCORE: [0-100]

CATEGORY BREAKDOWN:
- Formatting & Structure: [score]/30
- Keyword & Content Quality: [score]/40
- Completeness & Clarity: [score]/30

STRENGTHS:
- [bullet points of what's done well]

IMPROVEMENTS:
- [specific, actionable suggestions]

KEYWORDS FOUND:
[list important skills/keywords found]

MISSING KEYWORDS / SUGGESTED ADDITIONS:
[list relevant keywords to consider adding]

FORMAT ISSUES:
- [list any formatting problems found, or "None detected"]

DETAILED FEEDBACK:
[2-3 sentences summary]

Keep it professional, encouraging, and specific.
"""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return None, f"AI Analysis Error: {str(e)}"

# ---------------------- PARSING RESULTS ----------------------
def parse_analysis_result(result_text):
    """Parse the AI response into structured data"""
    data = {
        "score": 0,
        "breakdown": {},
        "strengths": [],
        "improvements": [],
        "keywords_found": [],
        "missing_keywords": [],
        "format_issues": [],
        "summary": ""
    }

    try:
        score_match = re.search(r"SCORE:\s*(\d+)", result_text)
        if score_match:
            data["score"] = int(score_match.group(1))

        # Category breakdown
        fmt_match = re.search(r"Formatting & Structure:\s*(\d+)/30", result_text)
        kw_match = re.search(r"Keyword & Content Quality:\s*(\d+)/40", result_text)
        comp_match = re.search(r"Completeness & Clarity:\s*(\d+)/30", result_text)
        
        if fmt_match: data["breakdown"]["Formatting & Structure"] = int(fmt_match.group(1))
        if kw_match: data["breakdown"]["Keyword & Content Quality"] = int(kw_match.group(1))
        if comp_match: data["breakdown"]["Completeness & Clarity"] = int(comp_match.group(1))

        # Extract sections
        sections = {
            "strengths": r"STRENGTHS:\n(.*?)(?=\n[A-Z ]+:|$)",
            "improvements": r"IMPROVEMENTS:\n(.*?)(?=\n[A-Z ]+:|$)",
            "keywords_found": r"KEYWORDS FOUND:\n(.*?)(?=\n[A-Z ]+:|$)",
            "missing_keywords": r"MISSING KEYWORDS / SUGGESTED ADDITIONS:\n(.*?)(?=\n[A-Z ]+:|$)",
            "format_issues": r"FORMAT ISSUES:\n(.*?)(?=\n[A-Z ]+:|$)",
            "summary": r"DETAILED FEEDBACK:\n(.*?)$"
        }

        for key, pattern in sections.items():
            match = re.search(pattern, result_text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                if key == "summary":
                    data[key] = content
                else:
                    items = [i.strip().lstrip("-•").strip() for i in content.split("\n") if i.strip()]
                    data[key] = items

    except Exception:
        pass

    return data, result_text

# ---------------------- UI ----------------------
st.title("📄 ATS Resume Checker & AI Improver")
st.markdown("Upload your resume — get an ATS score + personalized improvement tips powered by Gemini Flash.")

uploaded_file = st.file_uploader("Upload your Resume (PDF only)", type=["pdf"])

if uploaded_file:
    with st.spinner("Reading resume..."):
        resume_text, error = extract_text_from_pdf(uploaded_file)
    
    if error:
        st.error(error)
    elif resume_text:
        st.success("✅ Resume text extracted successfully!")
        
        with st.spinner("🤖 Analyzing with Gemini Flash..."):
            raw_result = analyze_resume_with_gemini(resume_text)
            
            if isinstance(raw_result, tuple) and len(raw_result) == 2:
                st.error(raw_result[1])
            elif raw_result:
                data, full_text = parse_analysis_result(raw_result)
                
                # Score display
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.subheader("ATS Score")
                    score = data["score"]
                    if score >= 80:
                        st.success(f"### {score}/100")
                    elif score >= 60:
                        st.warning(f"### {score}/100")
                    else:
                        st.error(f"### {score}/100")
                    
                    # Score gauge
                    st.progress(min(score/100, 1.0))
                    
                    if score >= 80:
                        st.success("✅ Excellent ATS readiness!")
                    elif score >= 60:
                        st.info("⚠️ Good start — some improvements recommended")
                    else:
                        st.error("🔴 Needs significant work to pass ATS filters")
                
                with col2:
                    st.subheader("Score Breakdown")
                    for cat, pts in data["breakdown"].items():
                        st.metric(cat, f"{pts}/{30 if 'Formatting' in cat or 'Completeness' in cat else 40}")
                
                # Tabs for detailed results
                tab1, tab2, tab3, tab4 = st.tabs(["💡 Improvements", "✅ Strengths", "🔑 Keywords", "📋 Full Report"])
                
                with tab1:
                    st.subheader("Actionable Improvements")
                    if data["improvements"]:
                        for item in data["improvements"]:
                            st.write(f"- {item}")
                    else:
                        st.info("No specific improvements detected.")
                    
                    if data["format_issues"] and data["format_issues"] != ["None detected"]:
                        st.subheader("⚠️ Formatting Issues")
                        for issue in data["format_issues"]:
                            st.write(f"- {issue}")
                
                with tab2:
                    st.subheader("Your Strengths")
                    for item in data["strengths"]:
                        st.write(f"✅ {item}")
                
                with tab3:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.subheader("Keywords Found")
                        for kw in data["keywords_found"]:
                            st.write(f"✓ {kw}")
                    with c2:
                        st.subheader("Suggested Keywords to Add")
                        for kw in data["missing_keywords"]:
                            st.write(f"+ {kw}")
                
                with tab4:
                    st.subheader("Complete Analysis Report")
                    st.text(full_text)
                
                st.divider()
                st.info("💡 **Tip:** For best results, export your PDF directly from Word or Google Docs — avoid image-based PDFs and fancy multi-column layouts.")

# Footer
st.markdown("---")
st.markdown("Built with Streamlit + Google Gemini Flash")
