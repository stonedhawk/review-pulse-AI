import os
import sys

# `streamlit run app/main.py` puts app/ on the path, not the repo root, so `core` would not import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from core.database import Base, SessionLocal, Review, engine
from core.demo import template_draft
from core.llm_client import GeminiClient
from core.ingest import GooglePlayIngestor
from core.jira_client import JiraClient
from sqlalchemy import func, desc

# Set by `python pulse.py ui --demo`: drafts come from templates and nothing is sent anywhere.
DEMO_MODE = os.environ.get("REVIEWPULSE_DEMO") == "1"

st.set_page_config(page_title="ReviewPulse AI", layout="wide", page_icon="📈")

# Idempotent: makes a first run on an empty database show the empty state instead of erroring.
os.makedirs("data", exist_ok=True)
Base.metadata.create_all(bind=engine)

# Clients are created on first use, so the dashboard opens even when a key is missing.
@st.cache_resource
def get_llm_client():
    return GeminiClient()

@st.cache_resource
def get_ingestor():
    return GooglePlayIngestor()

@st.cache_resource
def get_jira_client():
    return JiraClient()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def load_metrics():
    db = next(get_db())
    untriaged_count = db.query(Review).filter(Review.status == 'UNTRIAGED').count()
    triaged_count = db.query(Review).filter(Review.status == 'TRIAGED').count()
    
    # Highest priority cluster
    top_cluster = db.query(Review.cluster_id, Review.priority_score)\
        .filter(Review.cluster_id.isnot(None))\
        .order_by(desc(Review.priority_score))\
        .first()
        
    highest_cluster = top_cluster[0] if top_cluster else "N/A"
    
    return untriaged_count, triaged_count, highest_cluster

def load_top_clusters():
    db = next(get_db())
    # Group by cluster to show top 5 priority clusters
    clusters = db.query(
        Review.cluster_id,
        func.count(Review.review_id).label('review_count'),
        func.max(Review.priority_score).label('priority_score')
    ).filter(Review.status == 'TRIAGED', Review.cluster_id.isnot(None))\
    .group_by(Review.cluster_id)\
    .order_by(desc('priority_score'))\
    .limit(5).all()
    
    return pd.DataFrame(clusters, columns=['Cluster ID', 'Review Count', 'Priority Score'])

def load_reviews_for_cluster(cluster_id):
    db = next(get_db())
    reviews = db.query(Review).filter(Review.cluster_id == cluster_id, Review.status == 'TRIAGED').all()
    return reviews

def reply_and_update(review_id, reply_text):
    success = get_ingestor().reply_to_review(review_id, reply_text)
    if success:
        db = next(get_db())
        review = db.query(Review).filter(Review.review_id == review_id).first()
        if review:
            review.developer_response = reply_text
            review.status = 'SENT'
            db.commit()
        return True
    return False

# Sidebar
st.sidebar.title("ReviewPulse AI")
untriaged, triaged, top_cluster = load_metrics()
st.sidebar.metric("Total Untriaged", untriaged)
st.sidebar.metric("Total Triaged", triaged)
st.sidebar.metric("Highest Priority Cluster", top_cluster)

st.title("Cluster Triage Dashboard")
if DEMO_MODE:
    st.info("Demo mode: mock reviews, template drafts. Sending replies and Jira tickets are turned off.")

# Top 5 Clusters Table
st.subheader("Top 5 Critical Clusters")
top_clusters_df = load_top_clusters()
if not top_clusters_df.empty:
    st.dataframe(top_clusters_df, use_container_width=True)
else:
    st.info("No triaged clusters available. Please run the analysis engine.")

st.divider()

# Main View - Cluster Selection
if not top_clusters_df.empty:
    selected_cluster = st.selectbox("Select a Cluster to Triage", top_clusters_df['Cluster ID'].tolist())
    
    if selected_cluster:
        st.subheader(f"Reviews for '{selected_cluster}'")
        reviews = load_reviews_for_cluster(selected_cluster)
        
        # Check Priority Score for the selected cluster from the dataframe
        cluster_info = top_clusters_df[top_clusters_df['Cluster ID'] == selected_cluster]
        if not cluster_info.empty:
            priority_score = cluster_info.iloc[0]['Priority Score']
            if priority_score > 15:
                st.warning(f"High Priority Cluster! Score: {priority_score}")
                if st.button("Push to Jira", disabled=DEMO_MODE):
                    with st.spinner("Creating Jira Ticket..."):
                        jira_url = get_jira_client().create_bug_ticket(selected_cluster, priority_score, reviews)
                        if jira_url:
                            st.success(f"Ticket created successfully: [View Jira Ticket]({jira_url})")
                        else:
                            st.error("Failed to create Jira ticket. Please check your credentials.")
        
        if not reviews:
            st.success("All reviews in this cluster have been addressed!")
        else:
            for review in reviews:
                with st.expander(f"Review from {review.reviewer_name} ({review.rating} ⭐) - {review.review_date}"):
                    st.write(f"**App Version:** {review.app_version}")
                    st.write(f"**Review:** {review.review_text}")
                    
                    # Session state keys for dynamic UI
                    draft_key = f"draft_{review.review_id}"
                    
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        if st.button("Generate AI Draft", key=f"btn_gen_{review.review_id}"):
                            if DEMO_MODE:
                                st.session_state[draft_key] = template_draft(selected_cluster)
                                st.rerun()
                            try:
                                with st.spinner("Drafting..."):
                                    draft = get_llm_client().draft_review_response(review.review_text, selected_cluster)
                            except ValueError as e:
                                st.error(str(e))
                            else:
                                st.session_state[draft_key] = draft
                                st.rerun()
                    
                    if draft_key in st.session_state:
                        st.markdown("### Edit Draft Response")
                        
                        # Constraint: 350 character limit enforced by text_area
                        edited_draft = st.text_area(
                            "Response (Max 350 chars):", 
                            value=st.session_state[draft_key], 
                            max_chars=350,
                            key=f"text_{review.review_id}"
                        )
                        
                        st.caption(f"Characters remaining: {350 - len(edited_draft)}")
                        
                        if st.button("Approve & Send", type="primary", key=f"btn_send_{review.review_id}", disabled=DEMO_MODE):
                            with st.spinner("Sending to Google Play..."):
                                try:
                                    success = reply_and_update(review.review_id, edited_draft)
                                except ValueError as e:
                                    st.error(str(e))
                                    success = None
                                if success:
                                    st.success("Reply sent successfully!")
                                    del st.session_state[draft_key]
                                    st.rerun()
                                elif success is False:
                                    st.error("Failed to send reply. Check API quotas or credentials.")
