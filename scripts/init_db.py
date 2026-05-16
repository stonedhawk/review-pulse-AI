from core.database import engine, Base

def init_db():
    print(f"Creating database schema at {engine.url}...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Database schema created successfully.")
    except Exception as e:
        print(f"Failed to create database schema: {e}")

if __name__ == "__main__":
    init_db()
