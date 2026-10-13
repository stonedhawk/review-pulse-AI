# Security Policy

ReviewPulse AI handles player feedback, API keys, and access to your Jira backlog. This page covers how to report a problem and what the code does with your data.

## Supported Versions

Security fixes land on the `main` branch. Forks and older feature branches are not maintained.

## Reporting a Vulnerability

Please don't report security vulnerabilities in public GitHub issues or discussions, because that exposes the flaw before a fix ships.

Instead, use GitHub's private vulnerability reporting: open the repository's **Security** tab and click **Report a vulnerability**, or go straight to [the new advisory form](https://github.com/stonedhawk/review-pulse-AI/security/advisories/new). The report is visible only to you and the maintainer.

---

## How the Code Handles Keys and Data

1. **Credentials in `.env`:**
   Keys are read from `.env`, which is gitignored. The Google service account JSON is pasted into `.env` as `GOOGLE_APPLICATION_CREDENTIALS_JSON` and parsed in memory, so there is no separate `.json` key file in the project folder to commit by accident.

2. **Local Data Persistence:**
   Reviews, clusters and priority scores are stored in a local SQLite database with Write-Ahead Logging (WAL). ReviewPulse has no cloud sync. Data leaves your machine in three cases:
   - **Gemini:** review fields for clustering and drafting (see the LLM Privacy Boundary below).
   - **Google Play:** a reply, when you click Approve & Send.
   - **Jira:** when you click Push to Jira, the cluster name, priority score, and the star rating and text of up to five of its reviews.

   Reviewer names never leave your machine. They are stored in the local database and shown in the dashboard, but are not sent to Gemini, Google Play or Jira. `tests/test_jira.py` checks the Jira payload for them.

3. **Fetch Caps and Human Approval:**
   Each `fetch` run reads at most 5 pages of 100 reviews (500 in total). `process` sends every untriaged review to Gemini in batches of 100, so reviews from several fetches all go in a single run. Replies are posted to Google Play only when someone clicks Approve & Send in the dashboard; no code path posts a reply on its own.

4. **Dashboard Access:**
   The dashboard has no login and binds to localhost only (set in `.streamlit/config.toml`). Don't run it on a shared server or expose its port.

## LLM Privacy Boundary (Google Gemini)

Clustering and drafting send review text to the Google Gemini API.

- **Fields sent:** For clustering, Gemini receives the review ID, review text, star rating and app version. For drafting, it receives the review text and cluster name. Reviewer names are not sent.
- **Not sent:** Your target store rating, priority scores, Jira settings and API keys are not included in prompts.
- **Review text is sent as written.** Players can type personal details into a review, such as names, emails or account IDs, and those go to Gemini with the rest of the text. ReviewPulse does not remove them.
- **Free vs. paid keys:** On the free tier, Google can use your prompts to improve its products, and human reviewers may read them. For real player reviews, use a key from a Google Cloud project with billing enabled. See the [Gemini API terms](https://ai.google.dev/gemini-api/terms).
- **Prompt injection:** Review text is placed into prompts unescaped. Reviews are clustered 100 per prompt, so one review can try to steer the whole batch, mislabelling other reviews or skewing priority scores. Drafts are shown to you for editing before anything is posted; cluster assignments are not reviewed, so check a cluster's reviews and score before pushing it to Jira.
