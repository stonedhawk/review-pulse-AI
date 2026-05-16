import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from core.config import settings
from core.database import SessionLocal, Review
from sqlalchemy.dialects.sqlite import insert

class GooglePlayIngestor:
    def __init__(self):
        credentials = settings.get_google_credentials()
        self.service = build('androidpublisher', 'v3', credentials=credentials)
        self.package_name = settings.PLAY_STORE_PACKAGE_NAME

    def fetch_recent_reviews(self, max_results=100, max_pages=5):
        """Fetches the latest reviews from the Google Play Console using pagination."""
        all_reviews = []
        next_page_token = None
        pages_fetched = 0
        
        try:
            while pages_fetched < max_pages:
                request = self.service.reviews().list(
                    packageName=self.package_name,
                    maxResults=max_results,
                    token=next_page_token
                )
                response = request.execute()
                
                reviews = response.get('reviews', [])
                all_reviews.extend(reviews)
                
                next_page_token = response.get('tokenPagination', {}).get('nextPageToken')
                pages_fetched += 1
                
                if not next_page_token:
                    break
            
            return all_reviews
        except Exception as e:
            print(f"Error fetching reviews from Google Play API: {e}")
            return all_reviews

    def parse_review_timestamp(self, timestamp_dict):
        """Parses Google API timestamp format."""
        if not timestamp_dict or 'seconds' not in timestamp_dict:
            return None
        return datetime.datetime.fromtimestamp(int(timestamp_dict['seconds']))

    def process_and_store_reviews(self):
        raw_reviews = self.fetch_recent_reviews()
        if not raw_reviews:
            print("No reviews fetched.")
            return

        db = SessionLocal()
        inserted_count = 0
        updated_count = 0

        try:
            for raw in raw_reviews:
                review_id = raw.get('reviewId')
                comments = raw.get('comments', [])
                if not comments:
                    continue

                user_comment = comments[0].get('userComment', {})
                dev_comment = comments[1].get('developerComment', {}) if len(comments) > 1 else {}
                
                # Using SQLite's UPSERT equivalent
                stmt = insert(Review).values(
                    review_id=review_id,
                    reviewer_name=raw.get('authorName', 'Anonymous'),
                    rating=user_comment.get('starRating', 0),
                    review_text=user_comment.get('text', ''),
                    review_date=self.parse_review_timestamp(user_comment.get('lastModified')),
                    app_version=user_comment.get('appVersionName', 'Unknown'),
                    developer_response=dev_comment.get('text', None)
                )
                
                # If there's a conflict on review_id, update fields that might change
                on_conflict_stmt = stmt.on_conflict_do_update(
                    index_elements=['review_id'],
                    set_={
                        'reviewer_name': stmt.excluded.reviewer_name,
                        'rating': stmt.excluded.rating,
                        'review_text': stmt.excluded.review_text,
                        'review_date': stmt.excluded.review_date,
                        'app_version': stmt.excluded.app_version,
                        'developer_response': stmt.excluded.developer_response
                    }
                )
                
                result = db.execute(on_conflict_stmt)
                
                # A rudimentary way to guess if it was insert or update, 
                # though SQLite driver rowcount behavior varies.
                if result.rowcount > 0:
                    inserted_count += 1
            
            db.commit()
            print(f"Processed {len(raw_reviews)} reviews. DB operations successful.")
        except Exception as e:
            db.rollback()
            print(f"Error storing reviews in DB: {e}")
        finally:
            db.close()

    def reply_to_review(self, review_id: str, reply_text: str) -> bool:
        """
        Replies to a user review via the Google Play Developer API.
        """
        try:
            request = self.service.reviews().reply(
                packageName=self.package_name,
                reviewId=review_id,
                body={'replyText': reply_text}
            )
            request.execute()
            print(f"Successfully replied to review {review_id}.")
            return True
        except HttpError as e:
            print(f"Google Play API HttpError replying to {review_id}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error replying to {review_id}: {e}")
            return False
