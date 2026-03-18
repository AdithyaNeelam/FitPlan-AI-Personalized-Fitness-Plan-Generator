# import_to_postgresql.py
import json
import os
from app import app, db
from datetime import datetime

print("📥 Importing data to PostgreSQL...")

# Import your models
from app import User, UserProgress, WorkoutSchedule

with open('backup_data.json', 'r') as f:
    data = json.load(f)

with app.app_context():
    # Create tables first
    db.create_all()
    print("✅ Database tables created")
    
    # Import Users
    print("Importing users...")
    for row in data.get('user', []):
        try:
            user = User(
                id=row['id'],
                email=row['email'],
                name=row['name'],
                age=row['age'],
                weight=row['weight'],
                height=row['height'],
                fitness_level=row['fitness_level'],
                created_at=datetime.fromisoformat(row['created_at'].replace('Z', '+00:00'))
            )
            db.session.add(user)
        except Exception as e:
            print(f"Error importing user: {e}")
    
    db.session.commit()
    print(f"✅ Imported {len(data.get('user', []))} users")
    
    # Import other tables as needed...
    
    print("✅ Import complete!")