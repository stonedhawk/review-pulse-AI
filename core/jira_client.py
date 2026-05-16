from jira import JIRA
from core.config import settings

class JiraClient:
    def __init__(self):
        self.is_configured = all([settings.JIRA_URL, settings.JIRA_EMAIL, settings.JIRA_API_TOKEN])
        if self.is_configured:
            try:
                self.jira = JIRA(
                    server=settings.JIRA_URL,
                    basic_auth=(settings.JIRA_EMAIL, settings.JIRA_API_TOKEN)
                )
            except Exception as e:
                print(f"Failed to authenticate with Jira: {e}")
                self.is_configured = false

    def create_bug_ticket(self, cluster_name: str, priority_score: float, reviews: list) -> str | None:
        if not self.is_configured:
            print("Jira is not fully configured in environment variables.")
            return None

        # Build description with the Rating Drag priority score injected at the top
        description = f"*ReviewPulse AI Automated Triage*\n"
        description += f"*Calculated Priority Score (Rating Drag):* {priority_score}\n\n"
        description += "*Top Associated Reviews:*\n"
        
        for idx, review in enumerate(reviews[:5]):
            description += f"{idx+1}. ({review.rating} ⭐) {review.reviewer_name}: {review.review_text}\n"

        issue_dict = {
            'project': {'key': settings.JIRA_PROJECT_KEY},
            'summary': f"[Review Triage] {cluster_name}",
            'description': description,
            'issuetype': {'name': 'Bug'},
        }

        try:
            new_issue = self.jira.create_issue(fields=issue_dict)
            return new_issue.permalink()
        except Exception as e:
            print(f"Error creating Jira ticket: {e}")
            return None
