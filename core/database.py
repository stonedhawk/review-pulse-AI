from sqlalchemy import Column, String, Integer, DateTime, Float, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from core.config import settings

Base = declarative_base()

class Review(Base):
    __tablename__ = 'reviews'

    review_id = Column(String, primary_key=True)
    reviewer_name = Column(String)
    rating = Column(Integer)
    review_text = Column(String)
    review_date = Column(DateTime)
    app_version = Column(String)
    developer_response = Column(String, nullable=True)
    cluster_id = Column(String, nullable=True)
    priority_score = Column(Float, default=0.0)
    status = Column(String, default='UNTRIAGED') # Constrained logically (UNTRIAGED, DRAFTED, APPROVED, REJECTED, SENT)

engine = create_engine(settings.DATABASE_URL)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
