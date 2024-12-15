from sqlalchemy import create_engine

DATABASE_URL = "postgresql://postgres:postgres@localhost/tsoha_db"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        result = connection.execute("SELECT 1;")
        print(result.fetchone())
    print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")