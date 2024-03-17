import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

# Load environment variables
load_dotenv()


class Game(Base):
    __tablename__ = 'igdb_games'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    cover = Column(BigInteger, nullable=True)  # Assuming cover IDs are large integers
    first_release_date = Column(DateTime, nullable=True)  # Corrected to DateTime
    slug = Column(String, nullable=True)
    summary = Column(String, nullable=True)
    url = Column(String, nullable=True)


DATABASE_URL = os.getenv("GABS_DATABASE_URL")
print("DATABASE URL MODELS: {0}".format(DATABASE_URL))
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)


def load_initial_data(session, data):
    for row in data:
        # Convert Unix timestamp to datetime object
        first_release_date = row.get('first_release_date')
        if first_release_date is not None:
            first_release_date = datetime.datetime.utcfromtimestamp(first_release_date)

        game = Game(
            name=row.get('name', 'Unknown'),
            cover=row.get('cover'),
            first_release_date=first_release_date,  # Now correctly a datetime object or None
            slug=row.get('slug', 'no-slug'),
            summary=row.get('summary', ''),
            url=row.get('url', '')
        )
        session.add(game)
    session.commit()