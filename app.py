"""Streamlit dashboard for interactive test selection and gap analysis."""

import json
from pathlib import Path
from typing import Optional

import streamlit as st
import numpy as np

from src.embedder import create_embedder
from src.diff_parser import parse_diff
from src.planner import TestPlanner


# Page configuration
st.set_page_config(
    page_title="E5 Diff-to-Test Planner",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚗 E5 Diff-to-Test Planner")
st.markdown(
    "AI-powered Risk-Based Test Selection & Automated Jira Xray Gap Synthesis for Automotive HMI"
)


# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

embedder_choice = st.sidebar.radio(
    "Embedding Mode",
    options=["Mock (Fast)", "E5 Multilingual (Accurate)"],
    help="Mock mode uses deterministic hashing; E5 uses transformer model"
)

use_mock = embedder_choice == "Mock (Fast)"

full_suite_time = st.sidebar.slider(
    "Full Test Suite Duration (hours)",
    min_value=1,
    max_value=12,
    value=8,
    help="Total runtime for running all 4000+ tests"
)
full_suite_time_seconds = full_suite_time * 3600

risk_threshold_high = st.sidebar.slider(
    "HIGH Risk Threshold (cosine similarity)",
    min_value=0.5,
    max_value=1.0,
    value=0.78,
    step=0.01
)

risk_threshold_medium = st.sidebar.slider(
    "MEDIUM Risk Threshold",
    min_value=0.5,
    max_value=0.99,
    value=0.65,
    step=0.01
)

gap_threshold = st.sidebar.slider(
    "Gap Detection Threshold (max allowed)",
    min_value=0.4,
    max_value=0.8,
    value=0.62,
    step=0.01,
    help="When max test similarity < this, a coverage gap is detected"
)


# Load test catalog
@st.cache_resource
def load_catalog(catalog_path="data/sample_test_catalog.json"):
    with open(catalog_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@st.cache_resource
def initialize_planner():
    embedder = create_embedder(mock=use_mock)
    planner = TestPlanner(embedder)
    catalog = load_catalog()
    planner.test_catalog = catalog
    
    # Pre-compute embeddings
    for test in catalog:
        test_desc = f"{test['title']} {test['domain']} {' '.join(test.get('steps', []))} {test.get('expected_result', '')}"
        planner.embeddings_cache[test['id']] = embedder.embed_passage(test_desc)
    
    # Update thresholds
    planner.HIGH_RISK_THRESHOLD = risk_threshold_high
    planner.MEDIUM_RISK_THRESHOLD = risk_threshold_medium
    planner.GAP_DETECTION_THRESHOLD = gap_threshold
    
    return planner


# Main content tabs
tab1, tab2, tab3 = st.tabs(["📋 Analyze", "📊 Results", "🔧 Advanced"])

with tab1:
    st.header("Input Analysis")
    
    col_diff, col_defect = st.columns(2)
    
    with col_diff:
        st.subheader("Git Diff")
        diff_input = st.text_area(
            "Paste your unified diff (or use sample)",
            height=200,
            key="diff_input",
            help="Supports full unified format (diff --git ...)"
        )
        
        if st.button("Load Sample Diff"):
            with open("data/sample_pr_diff.patch", 'r') as f:
                st.session_state.diff_input = f.read()
            st.rerun()
    
    with col_defect:
        st.subheader("Jira Defect (Optional)")
        defect_input = st.text_area(
            "Paste Jira defect JSON or description",
            height=200,
            key="defect_input"
        )
        
        if st.button("Load Sample Defect"):
            with open("data/sample_jira_defect.json", 'r') as f:
                defect_data = json.load(f)
                st.session_state.defect_input = json.dumps(defect_data, indent=2)
            st.rerun()
    
    # Analyze button
    if st.button("🔍 Analyze", key="analyze_btn", use_container_width=True):
        with st.spinner("Analyzing..."):
            try:
                # Parse diff
                diff_summary = parse_diff(diff_input)
                
                # Extract defect text
                defect_text = ""
                if defect_input:
                    try:
                        defect_data = json.loads(defect_input)
                        defect_text = f"{defect_data.get('summary', '')} {defect_data.get('description', '')}"
                    except json.JSONDecodeError:
                        defect_text = defect_input
                
                # Run planning
                planner = initialize_planner()
                result = planner.plan(
                    diff_summary,
                    defect_description=defect_text,
                    full_suite_time_seconds=full_suite_time_seconds
                )
                
                # Store in session
                st.session_state.result = result
                st.session_state.diff_summary = diff_summary
                
                st.success("✓ Analysis complete!")
                st.info("Switch to Results tab to view findings")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


with tab2:
    if 'result' in st.session_state:
        result = st.session_state.result
        diff_summary = st.session_state.diff_summary
        
        st.header("Analysis Results")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Tests Selected", f"{result.test_count}/{result.full_suite_count}")
        
        with col2:
            st.metric("Time Saved", f"{result.hil_time_saved_seconds/3600:.1f}h", 
                     delta=f"{int(100*result.hil_time_saved_seconds/result.full_suite_time_seconds)}%")
        
        with col3:
            st.metric("HIGH Risk", len(result.high_risk_tests))
        
        with col4:
            st.metric("Coverage Gaps", len(result.gap_tickets))
        
        # Execution summary
        st.subheader("Execution Summary")
        st.info(result.execution_summary)
        
        # Ranked tests table
        st.subheader("Selected Tests (Ranked by Risk)")
        
        risk_filter = st.multiselect(
            "Filter by risk level",
            ["HIGH", "MEDIUM"],
            default=["HIGH", "MEDIUM"]
        )
        
        filtered_tests = []
        for test in result.ranked_tests:
            if test.similarity_score >= 0.78 and "HIGH" in risk_filter:
                filtered_tests.append(test)
            elif test.similarity_score >= 0.65 and "MEDIUM" in risk_filter:
                filtered_tests.append(test)
        
        # Display as table
        test_table_data = []
        for test in filtered_tests[:50]:
            risk_level = "🔴 HIGH" if test.similarity_score >= 0.78 else "🟡 MEDIUM"
            test_table_data.append({
                "ID": test.test_id,
                "Risk": risk_level,
                "Similarity": f"{test.similarity_score:.3f}",
                "Title": test.title[:50] + ("..." if len(test.title) > 50 else ""),
                "Duration (s)": test.estimated_duration_seconds,
                "Domain": test.domain,
            })
        
        st.dataframe(test_table_data, use_container_width=True)
        
        # Coverage gaps
        if result.gap_tickets:
            st.subheader("⚠️ Coverage Gaps (Auto-Detected)")
            
            for gap in result.gap_tickets[:10]:
                with st.expander(f"🔗 {gap.suggested_id}: {gap.title}"):
                    st.write(f"**Domain:** {gap.domain}")
                    st.write(f"**Preconditions:** {gap.preconditions}")
                    st.write(f"**Test Steps:**")
                    for i, step in enumerate(gap.test_steps, 1):
                        st.write(f"  {i}. {step}")
                    st.write(f"**Expected Result:** {gap.expected_result}")
                    st.write(f"**HIL Tags:** {', '.join(gap.hil_bench_tags)}")
                    st.write(f"**Gap Reason:** {gap.gap_reason}")
                    
                    # Jira template
                    with st.expander("📌 Jira Description Template"):
                        st.code(gap.to_jira_description(), language="markdown")
        
        # Export options
        st.subheader("📥 Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            json_report = json.dumps(result.to_dict(), indent=2)
            st.download_button(
                label="Download JSON Report",
                data=json_report,
                file_name="e5_test_plan.json",
                mime="application/json"
            )
        
        with col2:
            # Generate CSV export
            csv_lines = ["Test ID,Risk Level,Similarity Score,Title,Domain,Duration (s)"]
            for test in result.ranked_tests:
                risk = "HIGH" if test.similarity_score >= 0.78 else "MEDIUM"
                csv_lines.append(
                    f'{test.test_id},{risk},{test.similarity_score:.3f},"{test.title}",{test.domain},{test.estimated_duration_seconds}'
                )
            csv_data = "\n".join(csv_lines)
            
            st.download_button(
                label="Download CSV (Tests)",
                data=csv_data,
                file_name="e5_tests.csv",
                mime="text/csv"
            )
    else:
        st.info("👈 Use the Analyze tab to run analysis")


with tab3:
    st.header("Advanced Settings & Catalog Info")
    
    # Catalog statistics
    catalog = load_catalog()
    
    st.subheader("Test Catalog Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Tests", len(catalog))
    
    with col2:
        total_duration = sum(t.get('estimated_duration_seconds', 60) for t in catalog)
        st.metric("Total Suite Time", f"{total_duration/3600:.1f}h")
    
    with col3:
        domains = set(t.get('domain', 'Unknown') for t in catalog)
        st.metric("Domains", len(domains))
    
    # Domain breakdown
    st.subheader("Domain Breakdown")
    
    domain_counts = {}
    for test in catalog:
        domain = test.get('domain', 'Unknown')
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    domain_df_data = [
        {"Domain": domain, "Test Count": count}
        for domain, count in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    
    st.dataframe(domain_df_data, use_container_width=True)
    
    # Embedder info
    st.subheader("Embedding Engine")
    
    if use_mock:
        st.info("""
        **Mock Embedder (Deterministic Hash-Based)**
        
        - No external dependencies
        - Instant inference
        - Deterministic results for unit tests
        - Less accuracy than transformer models
        """)
    else:
        st.info("""
        **E5 Multilingual Embedder**
        
        - Model: `intfloat/multilingual-e5-base`
        - Supports: 100+ languages
        - Requires: sentence-transformers, torch
        - First run downloads ~1.1GB model weights
        - Superior semantic understanding
        """)
    
    # Risk thresholds info
    st.subheader("Risk Classification")
    
    st.markdown(f"""
    | Risk Level | Threshold | Interpretation |
    |-----------|-----------|-----------------|
    | 🔴 HIGH   | ≥ {risk_threshold_high:.2f} | Strong semantic match, run this test |
    | 🟡 MEDIUM | {risk_threshold_medium:.2f} - {risk_threshold_high:.2f} | Potential relevance, consider running |
    | 🟢 LOW    | < {risk_threshold_medium:.2f} | Weak match, skip unless full regression |
    | ⚠️ GAP    | < {gap_threshold:.2f} | Coverage gap detected, suggest new test |
    """)


# Footer
st.sidebar.divider()
st.sidebar.markdown("""
---
**e5-diff-to-test-planner v1.0.0**

Automotive HMI · Risk-Based Selection
""")
