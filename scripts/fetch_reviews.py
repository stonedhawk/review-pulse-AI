from core.ingest import GooglePlayIngestor
import traceback

def main():
    print("Starting ReviewPulse AI Ingestion Process...")
    try:
        ingestor = GooglePlayIngestor()
        print(f"Fetching reviews for package: {ingestor.package_name}")
        ingestor.process_and_store_reviews()
        print("Ingestion completed.")
    except ValueError as ve:
        print(f"Configuration Error: {ve}")
        print("Please ensure your .env variables are properly set.")
    except Exception as e:
        print(f"An unexpected error occurred during ingestion:")
        traceback.print_exc()

if __name__ == "__main__":
    main()
