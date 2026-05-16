import json
from google import genai
from google.genai import types
from core.config import settings

class GeminiClient:
    def __init__(self):
        # We assume the library will automatically pick up GEMINI_API_KEY from environment, 
        # but we can explicitly pass it if needed.
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = 'gemini-2.5-flash' # Good default for fast batch processing

    def cluster_reviews_batch(self, reviews_data: list[dict]) -> list[dict]:
        """
        Sends a batch of reviews to Gemini and returns a structured JSON mapping of 
        clusters and justifications.
        """
        if not reviews_data:
            return []

        prompt = f"""
You are an expert Game Developer triage assistant.
Analyze the following batch of Google Play reviews.
Identify 5-8 distinct, recurring technical or gameplay issues (e.g., 'Login Timeout', 'Level 42 Crash', 'Gacha Rates Too Low').
Map each review to one of these clusters. If a review is generic praise or unhelpful, assign it to a 'Generic' or 'Unhelpful' cluster.

Here are the reviews:
{json.dumps(reviews_data, indent=2)}

Return a strict JSON array where each element matches this structure:
{{
  "review_id": "<the string ID>",
  "cluster_id": "<short, unique string representing the issue category, e.g., 'LOGIN_CRASH'>",
  "cluster_name": "<human readable cluster name>",
  "justification": "<brief reason why this review fits this cluster>"
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            # The response text should be a JSON array due to response_mime_type
            result_json = response.text
            return json.loads(result_json)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini JSON output: {e}")
            return []
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return []

    def draft_review_response(self, review_text: str, cluster_issue: str) -> str:
        """
        Drafts a developer response for a review, adhering to a strict 350-character limit.
        """
        prompt = f"""
You are an expert customer support representative for a mobile game developer.
A user left the following review, which we have categorized under the issue: '{cluster_issue}'
Review text: "{review_text}"

Draft a professional, empathetic reply from the development team addressing this review.
CRITICAL CONSTRAINT: Your response MUST be under 350 characters total. Do not use filler words. Be concise, polite, and assure the user we are looking into the '{cluster_issue}'.
Respond ONLY with the drafted text. Do not include quotes or surrounding conversational text.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            draft = response.text.strip()
            # Failsafe enforce character limit in code just in case
            if len(draft) > 350:
                draft = draft[:347] + "..."
            return draft
        except Exception as e:
            print(f"Error calling Gemini API for drafting: {e}")
            return "Thank you for your feedback. Our team is looking into this."
