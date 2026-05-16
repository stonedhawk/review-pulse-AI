# Security Policy

ReviewPulse AI handles sensitive community feedback, authentication keys, and corporate Jira backlogs. We take security seriously.

## Supported Versions

Currently, only the `main` branch of this repository receives security updates. We do not support legacy forks or decoupled feature branches at this time.

## Reporting a Vulnerability

**DO NOT** open public GitHub issues or discussions to report security vulnerabilities. This exposes zero-day flaws to malicious actors before a patch can be deployed.

If you discover a vulnerability, please email our security triage team directly at:
**[security@yourstudio.com]**

We will acknowledge your report within 48 hours and work with you to patch the issue safely.

---

## Security Architecture & Defense Layers

ReviewPulse AI is architected with three core defense layers to minimize attack surfaces, especially concerning LLM prompt injection and API abuse:

1. **Zero-File Credential Loading:** 
   We do not use physical `.json` files for Google Cloud Authentication, avoiding accidental commits of sensitive keys. The `GOOGLE_APPLICATION_CREDENTIALS_JSON` environment variable injects service account keys directly into memory upon initialization.

2. **Local Data Persistence:** 
   By utilizing a localized SQLite database configured with Write-Ahead Logging (WAL), ReviewPulse guarantees that your Triaged reviews and proprietary Rating Drag logic never leave your host machine (or Docker container volume) unless explicitly pushed to Jira or the Play Store. There is no unauthorized cloud sync.

3. **API Failsafes & Hardcaps:** 
   To prevent denial-of-wallet attacks and API quotas from being drained, the Ingestion Engine features hardcoded pagination caps (fetching a strict maximum of 500 reviews per run). Furthermore, the Human-in-the-Loop (HITL) dashboard state-machine enforces that no automated drafts can be pushed to the Google Play Store without explicit user approval.

## LLM Privacy Boundary (Google Gemini)

When drafting AI responses and clustering issues, the raw review texts *are* securely transmitted to the Google Gemini API. 

However, we enforce a strict privacy boundary:
- **No Internal Metadata:** Your `Target Store Rating`, internal priority weighting metrics, Jira configurations, and any studio-specific credentials are strictly stripped from the LLM context window. 
- **Anonymization:** Only the raw review body and star rating are evaluated by Gemini for semantic clustering.
