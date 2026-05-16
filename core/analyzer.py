from core.database import SessionLocal, Review
from core.llm_client import GeminiClient
from core.config import settings

class ReviewAnalyzer:
    def __init__(self):
        self.llm_client = GeminiClient()
        self.target_rating = settings.TARGET_STORE_RATING

    def run_analysis(self):
        db = SessionLocal()
        try:
            # 1. Fetch UNTRIAGED reviews
            untriaged = db.query(Review).filter(Review.status == 'UNTRIAGED').all()
            if not untriaged:
                print("No UNTRIAGED reviews found.")
                return []

            # Prepare data for Gemini
            reviews_data = [
                {
                    "review_id": r.review_id,
                    "review_text": r.review_text,
                    "rating": r.rating,
                    "app_version": r.app_version
                } for r in untriaged
            ]

            print(f"Sending {len(reviews_data)} reviews to Gemini for clustering...")
            # 2. Cluster the reviews via LLM
            # Note: For very large datasets, we should batch this (e.g. 50-100 reviews per prompt). 
            # We'll assume the current ingestion limit of 500 can be processed or we slice it.
            # Let's chunk into 100 max per API call for safety.
            clustered_results = []
            chunk_size = 100
            for i in range(0, len(reviews_data), chunk_size):
                chunk = reviews_data[i:i+chunk_size]
                res = self.llm_client.cluster_reviews_batch(chunk)
                clustered_results.extend(res)

            # Map results by review_id for quick lookup
            cluster_map = {item['review_id']: item for item in clustered_results if 'review_id' in item}

            # 3. Calculate metrics per cluster
            cluster_stats = {}
            for r in untriaged:
                c_info = cluster_map.get(r.review_id)
                if not c_info:
                    continue
                
                c_id = c_info.get('cluster_id', 'UNKNOWN')
                if c_id not in cluster_stats:
                    cluster_stats[c_id] = {'count': 0, 'rating_sum': 0.0, 'name': c_info.get('cluster_name', c_id)}
                
                cluster_stats[c_id]['count'] += 1
                cluster_stats[c_id]['rating_sum'] += r.rating

            # 4. Calculate Priority Score: Cluster Frequency * (Target Store Rating - Average Cluster Rating)
            cluster_priorities = {}
            for c_id, stats in cluster_stats.items():
                avg_rating = stats['rating_sum'] / stats['count']
                priority_score = stats['count'] * (self.target_rating - avg_rating)
                # Keep score from going negative if avg_rating > target
                priority_score = max(0.0, round(priority_score, 2))
                cluster_priorities[c_id] = priority_score
                stats['avg_rating'] = round(avg_rating, 2)
                stats['priority_score'] = priority_score

            # 5. Update Database
            print("Updating database with cluster IDs and priority scores...")
            for r in untriaged:
                c_info = cluster_map.get(r.review_id)
                if c_info:
                    c_id = c_info.get('cluster_id', 'UNKNOWN')
                    r.cluster_id = c_id
                    r.priority_score = cluster_priorities.get(c_id, 0.0)
                    r.status = 'TRIAGED'
            
            db.commit()
            return cluster_stats

        except Exception as e:
            db.rollback()
            print(f"Error during analysis: {e}")
            return {}
        finally:
            db.close()
