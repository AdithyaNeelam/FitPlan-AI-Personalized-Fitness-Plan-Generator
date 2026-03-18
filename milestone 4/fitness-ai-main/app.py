from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import random
import requests
import json
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fitnessappsecretkey2026')

# Database configuration with SSL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///fitness.db')

# Add SSL mode for PostgreSQL connections
if database_url and 'postgresql' in database_url:
    # Ensure SSL is enabled
    if '?' not in database_url:
        database_url += '?sslmode=require'
    else:
        database_url += '&sslmode=require'

if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

db=SQLAlchemy(app)

# Mail configuration for OTP
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')
mail = Mail(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    fitness_level = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    current_weight = db.Column(db.Float)
    date = db.Column(db.Date)
    notes = db.Column(db.Text)

class WorkoutSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    schedule_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Add these with your other database models (User, UserProgress, etc.)

class UserProfile(db.Model):
    """Extended user profile"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    profile_pic = db.Column(db.String(200), default='default.jpg')
    bio = db.Column(db.Text)
    fitness_goal = db.Column(db.String(100))
    target_weight = db.Column(db.Float)
    target_date = db.Column(db.Date)
    experience_level = db.Column(db.String(50))
    workout_preferences = db.Column(db.Text)  # JSON stored
    
    # Social
    friends = db.Column(db.Text)  # JSON list of friend IDs
    achievements = db.Column(db.Text)  # JSON list of badges
    
    # Settings
    dark_mode = db.Column(db.Boolean, default=False)
    email_notifications = db.Column(db.Boolean, default=True)


class WorkoutLog(db.Model):
    """Track daily workouts"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date())
    workout_name = db.Column(db.String(200))
    duration = db.Column(db.Integer)  # minutes
    calories_burned = db.Column(db.Integer)
    exercises = db.Column(db.Text)  # JSON of exercises



class NutritionLog(db.Model):
    """Track daily nutrition"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date)
    meal_type = db.Column(db.String(50))  # breakfast, lunch, etc.
    food_items = db.Column(db.Text)  # JSON
    calories = db.Column(db.Integer)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fats = db.Column(db.Float)
    water_intake = db.Column(db.Float)  # in liters


# ===== AFTER YOUR EXISTING MODELS (WorkoutLog, Achievement etc) =====

class MealLog(db.Model):
    """Track daily meals"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date())
    meal_type = db.Column(db.String(50))  # breakfast, lunch, dinner, snack
    food_name = db.Column(db.String(200))
    calories = db.Column(db.Integer)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fats = db.Column(db.Float)
    image_url = db.Column(db.String(500))  # Food image

class UserSettings(db.Model):
    """User preferences and settings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notification_enabled = db.Column(db.Boolean, default=True)
    dark_mode = db.Column(db.Boolean, default=False)
    measurement_unit = db.Column(db.String(10), default='metric')  # metric/imperial
    workout_reminder_time = db.Column(db.String(5), default='08:00')
    meal_reminder_time = db.Column(db.String(5), default='12:00')
    water_goal = db.Column(db.Float, default=2.5)  # liters
    daily_calorie_goal = db.Column(db.Integer, default=2000)



class Friend(db.Model):
    """Friend connections"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    friend_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FriendRequest(db.Model):
    """Friend requests"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Post(db.Model):
    """Community posts"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    type = db.Column(db.String(50))  # workout, meal, achievement
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user=db.relationship('User',backref='posts')


class Challenge(db.Model):
    """User challenges"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    goal_type = db.Column(db.String(50))  # 'workouts', 'water', 'calories', 'custom'
    goal_value = db.Column(db.Integer)
    current_value = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(20))
    start_date = db.Column(db.Date, default=datetime.utcnow().date())
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # 'active', 'completed', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Goal(db.Model):
    """User goals tracking"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    goal_type = db.Column(db.String(50))  # 'weight', 'workout', 'strength', 'custom'
    current_value = db.Column(db.Float, default=0)
    target_value = db.Column(db.Float)
    unit = db.Column(db.String(20))  # 'kg', 'workouts', 'reps', 'minutes', 'km'
    start_date = db.Column(db.Date, default=datetime.utcnow().date())
    deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # 'active', 'completed', 'expired'
    progress_percent = db.Column(db.Float, default=0)
    completed_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Achievement(db.Model):
    """User achievements"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    badge_name = db.Column(db.String(100))
    badge_icon = db.Column(db.String(50))
    date_earned = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)




# Create tables
with app.app_context():
    db.create_all()

# Store OTP temporarily
otp_storage = {}

# Routes
@app.route('/')
def index():
    return render_template('index.html')




import sendgrid
from sendgrid.helpers.mail import Mail
import os

@app.route('/send-otp', methods=['POST'])
def send_otp():
    try:
        email = request.json.get('email')
        otp = str(random.randint(100000, 999999))
        otp_storage[email] = otp
        
        # Get SendGrid API key
        sg_api_key = os.getenv('SENDGRID_API_KEY')
        if not sg_api_key:
            print("❌ SendGrid API key not found")
            return jsonify({'success': False, 'message': 'Email service not configured'})
        
        # Create email message
        message = Mail(
            from_email=os.getenv('EMAIL_USER', 'noreply@fitness-ai.com'),
            to_emails=email,
            subject='FitAI - Your Verification Code',
            plain_text_content=f'''Welcome to FitAI!

Your verification code is: {otp}

This code will expire in 10 minutes.

Thanks,
FitAI Team'''
        )
        
        # Send via SendGrid
        sg = sendgrid.SendGridAPIClient(api_key=sg_api_key)
        response = sg.send(message)
        
        if response.status_code == 202:
            print(f"✅ OTP sent via SendGrid to {email}: {otp}")
            return jsonify({'success': True, 'message': 'OTP sent successfully'})
        else:
            print(f"❌ SendGrid error: {response.status_code}")
            return jsonify({'success': False, 'message': 'Failed to send OTP'})
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


        


            








@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    email = request.json.get('email')
    otp = request.json.get('otp')
    
    if email in otp_storage and otp_storage[email] == otp:
        session['email'] = email
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            session['user_id'] = user.id
            return jsonify({'success': True, 'new_user': False})
        else:
            return jsonify({'success': True, 'new_user': True})
    
    return jsonify({'success': False, 'message': 'Invalid OTP'})

@app.route('/direct-signup', methods=['POST'])
def direct_signup():
    data = request.json
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'success': False, 'error': 'Email already registered'})
    
    # Create new user directly
    user = User(
        email=data['email'],
        name=data['name'],
        age=data['age'],
        weight=data['weight'],
        height=data['height'],
        fitness_level=data['fitness_level']
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Set session
    session['email'] = data['email']
    session['user_id'] = user.id
    
    return jsonify({'success': True})

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)



            
import requests
import os
import json

@app.route('/generate-schedule', methods=['POST'])
def generate_schedule():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Get user inputs
        goal = data.get('goal', 'strength')
        level = data.get('level', 'beginner')
        equipment = data.get('equipment', 'bodyweight')
        
        # Create a VERY specific prompt to ensure AI generation
        prompt = f"""Generate a COMPLETE 5-day workout schedule for {user.name}.

USER DETAILS:
- Name: {user.name}
- Age: {user.age}
- Goal: {goal}
- Level: {level}
- Equipment: {equipment}

IMPORTANT: Generate ALL 5 days. Each day must have 5 exercises.
Do NOT use templates. Be creative.

Format EXACTLY like this:

DAY 1: [Focus Area]
1. [Exercise] - [sets] sets x [reps] reps
2. [Exercise] - [sets] sets x [reps] reps
3. [Exercise] - [sets] sets x [reps] reps
4. [Exercise] - [sets] sets x [reps] reps
5. [Exercise] - [sets] sets x [reps] reps

DAY 2: [Different Focus Area]
...continue for DAYS 3, 4, and 5

Make every day different and unique."""
        
        # Try Groq API first
        groq_key = os.getenv('GROQ_API_KEY')
        if not groq_key:
            return jsonify({'success': False, 'error': 'GROQ_API_KEY not found'})
        
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        
        # Try multiple models in sequence
        models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it"
        ]
        
        schedule = None
        
        for model in models:
            try:
                print(f"🔄 Trying Groq model: {model}")
                
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a professional fitness trainer. Create complete, detailed 5-day workout plans."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.8,
                        "max_tokens": 1200
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    schedule = result['choices'][0]['message']['content']
                    
                    # Verify we got all 5 days
                    if schedule and len(schedule) > 200 and "DAY 5" in schedule:
                        print(f"✅ Success with {model}")
                        break
                    else:
                        print(f"⚠️ {model} response incomplete, trying next...")
                        schedule = None
                else:
                    print(f"❌ {model} failed: {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ Error with {model}: {str(e)}")
                continue
        
        # If all Groq models fail, try OpenRouter as backup
        if not schedule:
            print("🔄 Trying OpenRouter backup...")
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": "Bearer sk-or-v1-64e1068c3d61c5b8b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.8
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    schedule = result['choices'][0]['message']['content']
                    print("✅ OpenRouter success!")
            except Exception as e:
                print(f"❌ OpenRouter failed: {str(e)}")
        
        # If ALL AI fails, use a clean template (but still personalized)
        if not schedule:
            print("⚠️ All AI failed, using clean template")
            
            # Set sets/reps based on level
            if level == 'beginner':
                sets = 3
                reps = "10-12"
            elif level == 'intermediate':
                sets = 4
                reps = "8-10"
            else:
                sets = 4
                reps = "6-8"
            
            # Equipment-specific exercises
            if 'pullup' in equipment:
                exercises = {
                    'upper': ['Pull-ups', 'Chin-ups', 'Inverted Rows', 'Pull-up Holds', 'Negative Pull-ups'],
                    'lower': ['Squats', 'Lunges', 'Glute Bridges', 'Calf Raises', 'Step-ups'],
                    'core': ['Hanging Knee Raises', 'L-sits', 'Planks', 'Leg Raises', 'Russian Twists']
                }
            else:
                exercises = {
                    'upper': ['Push-ups', 'Dips', 'Rows', 'Pike Push-ups', 'Archer Push-ups'],
                    'lower': ['Squats', 'Lunges', 'Glute Bridges', 'Calf Raises', 'Step-ups'],
                    'core': ['Planks', 'Crunches', 'Leg Raises', 'Mountain Climbers', 'Russian Twists']
                }
            
            schedule = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 YOUR 5-DAY WORKOUT PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 For: {user.name} | Goal: {goal} | Level: {level} | Equipment: {equipment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 DAY 1: Upper Body Focus
───────────────────────────────
1. {exercises['upper'][0]} - {sets} x {reps}
2. {exercises['upper'][1]} - {sets} x {reps}
3. {exercises['upper'][2]} - {sets} x {reps}
4. {exercises['upper'][3]} - {sets} x {reps}
5. {exercises['upper'][4]} - {sets} x {reps}

📅 DAY 2: Lower Body Focus
───────────────────────────────
1. {exercises['lower'][0]} - {sets} x {reps}
2. {exercises['lower'][1]} - {sets} x {reps}
3. {exercises['lower'][2]} - {sets} x {reps}
4. {exercises['lower'][3]} - {sets} x {reps}
5. {exercises['lower'][4]} - {sets} x {reps}

📅 DAY 3: Core & Conditioning
───────────────────────────────
1. {exercises['core'][0]} - 3 x 45 sec
2. {exercises['core'][1]} - 3 x 15
3. {exercises['core'][2]} - 3 x 12
4. {exercises['core'][3]} - 3 x 30 sec
5. {exercises['core'][4]} - 3 x 12

📅 DAY 4: Full Body Power
───────────────────────────────
1. {exercises['upper'][0]} - {sets} x {reps}
2. {exercises['lower'][0]} - {sets} x {reps}
3. {exercises['upper'][2]} - {sets} x {reps}
4. {exercises['lower'][2]} - {sets} x {reps}
5. Burpees - 3 x 8

📅 DAY 5: Active Recovery
───────────────────────────────
1. Light cardio - 20 min
2. Full body stretching - 15 min
3. Foam rolling - 10 min
4. Deep breathing - 5 min
5. Mobility work - 10 min

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💪 PRO TIP: Stay consistent and track your progress!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        # Save schedule
        workout_schedule = WorkoutSchedule(
            user_id=user.id,
            schedule_data=schedule
        )
        db.session.add(workout_schedule)
        db.session.commit()
        
        return jsonify({'success': True, 'schedule': schedule})
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})
      
                
 


        


        

    
    
        
    
    

@app.route('/update-progress', methods=['POST'])
def update_progress():
    data = request.json
    progress = UserProgress(
        user_id=session['user_id'],
        current_weight=data['current_weight'],
        date=datetime.now().date(),
        notes=data.get('notes', '')
    )
    
    db.session.add(progress)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/schedule')
def schedule():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user=User.query.get(session['user_id'])
    return render_template('schedule.html',user=user)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    print(f"Loading profile for user: {user.name if user else 'None'}")
    return render_template('profile.html', user=user)

@app.route('/upload-profile-pic', methods=['POST'])
def upload_profile_pic():
    if 'user_id' not in session:
        return jsonify({'success': False})
    
    file = request.files['profile_pic']
    if file:
        filename = f"user_{session['user_id']}_{file.filename}"
        file.save(f'static/uploads/{filename}')
        
        # Update user profile
        user = User.query.get(session['user_id'])
        # You'd need to add profile_pic field to User model
        db.session.commit()
        
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/api/quote')
def get_quote():
    quotes = [
        "The only bad workout is the one that didn't happen.",
        "Your body can stand almost anything. It's your mind you need to convince.",
        "Strength doesn't come from what you can do. It comes from overcoming the things you once thought you couldn't.",
        "The difference between try and triumph is a little umph!",
        "Success starts with self-discipline."
    ]
    return jsonify({
        'quote': random.choice(quotes),
        'author': 'FitAI'
    })



@app.route('/nutrition')
def nutrition():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('nutrition.html')

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('index'))
    
    return render_template('analytics.html', user=user)




@app.route('/community')
def community():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user_id = session['user_id']
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('index'))
    
    # Get friend requests (pending requests sent to current user)
    friend_requests = db.session.query(FriendRequest, User).join(
        User, FriendRequest.sender_id == User.id
    ).filter(
        FriendRequest.receiver_id == user_id,
        FriendRequest.status == 'pending'
    ).all()
    
    # Get friends list
    friends = db.session.query(User).join(
        Friend,
        ((Friend.user_id == user_id) & (Friend.friend_id == User.id)) |
        ((Friend.friend_id == user_id) & (Friend.user_id == User.id))
    ).filter(Friend.status == 'accepted').all()
    
    # Get posts with user info
    posts = db.session.query(Post, User).join(
        User, Post.user_id == User.id
    ).order_by(Post.created_at.desc()).limit(20).all()
    
    # Get leaderboard
    from sqlalchemy import func
    leaderboard = db.session.query(
        User, 
        func.count(WorkoutLog.id).label('workout_count'),
        func.sum(WorkoutLog.calories_burned).label('total_calories')
    ).outerjoin(WorkoutLog, User.id == WorkoutLog.user_id).group_by(User.id).order_by(func.count(WorkoutLog.id).desc()).limit(10).all()
    
    return render_template('community.html', 
                         user=user,
                         friend_requests=friend_requests,
                         friends=friends,
                         posts=posts,
                         leaderboard=leaderboard)



    



    
@app.route('/send-friend-request', methods=['POST'])
def send_friend_request():
    try:
        data = request.json
        receiver_email = data.get('email')
        
        # Find user by email
        receiver = User.query.filter_by(email=receiver_email).first()
        if not receiver:
            return jsonify({'success': False, 'error': 'User not found'})
        
        # Check if trying to add self
        if receiver.id == session['user_id']:
            return jsonify({'success': False, 'error': 'You cannot add yourself as friend'})
        
        # Check if already friends
        existing_friend = Friend.query.filter(
            ((Friend.user_id == session['user_id']) & (Friend.friend_id == receiver.id)) |
            ((Friend.friend_id == session['user_id']) & (Friend.user_id == receiver.id))
        ).first()
        
        if existing_friend:
            return jsonify({'success': False, 'error': 'Already friends'})
        
        # Check if request already sent
        existing_request = FriendRequest.query.filter_by(
            sender_id=session['user_id'],
            receiver_id=receiver.id,
            status='pending'
        ).first()
        
        if existing_request:
            return jsonify({'success': False, 'error': 'Friend request already sent'})
        
        # Create friend request
        friend_request = FriendRequest(
            sender_id=session['user_id'],
            receiver_id=receiver.id,
            status='pending'
        )
        db.session.add(friend_request)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Friend request sent!'})
        
    except Exception as e:
        print(f"Error sending friend request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/accept-friend-request', methods=['POST'])
def accept_friend_request():
    try:
        data = request.json
        request_id = data.get('request_id')
        
        # Get the friend request
        friend_request = FriendRequest.query.get(request_id)
        if not friend_request:
            return jsonify({'success': False, 'error': 'Request not found'})
        
        # Update request status
        friend_request.status = 'accepted'
        
        # Create friendship
        friend = Friend(
            user_id=friend_request.sender_id,
            friend_id=friend_request.receiver_id,
            status='accepted'
        )
        db.session.add(friend)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error accepting friend request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/decline-friend-request', methods=['POST'])
def decline_friend_request():
    try:
        data = request.json
        request_id = data.get('request_id')
        
        friend_request = FriendRequest.query.get(request_id)
        if friend_request:
            friend_request.status = 'declined'
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error declining friend request: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/create-post', methods=['POST'])
def create_post():
    try:
        data = request.json
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Not logged in'})
        
        post = Post(
            user_id=session['user_id'],
            content=data.get('content'),
            type=data.get('type', 'update'),
            likes=0
        )
        db.session.add(post)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})



@app.route('/like-post', methods=['POST'])
def like_post():
    try:
        data = request.json
        post = Post.query.get(data.get('post_id'))
        if post:
            post.likes += 1
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Error liking post: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})



    
@app.route('/log-workout', methods=['POST'])
def log_workout():
    try:
        data = request.json
        workout = WorkoutLog(
            user_id=session['user_id'],
            date=datetime.now().date(),
            workout_name=data['type'],
            duration=data['duration'],
            calories_burned=data['calories'],
            exercises=data.get('exercises','')
        )
        db.session.add(workout)
        db.session.commit()
        print(f"✅ Workout saved: {workout.workout_name}, {workout.calories_burned} calories")  # Debug
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving workout: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/log-meal', methods=['POST'])
def log_meal():
    data = request.json
    meal = MealLog(
        user_id=session['user_id'],
        meal_type=data['meal_type'],
        food_name=data['food_name'],
        calories=data['calories'],
        protein=data.get('protein', 0),
        carbs=data.get('carbs', 0),
        fats=data.get('fats', 0),
        image_url=data.get('image_url', '')
    )
    db.session.add(meal)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/get-recent-meals')
def get_recent_meals():
    meals = MealLog.query.filter_by(user_id=session['user_id'])\
        .order_by(MealLog.date.desc()).limit(5).all()
    return jsonify([{
        'meal_type': m.meal_type,
        'food_name': m.food_name,
        'calories': m.calories,
        'image_url': m.image_url
    } for m in meals])

@app.route('/get-recent-workouts')
def get_recent_workouts():
    workouts = WorkoutLog.query.filter_by(user_id=session['user_id'])\
        .order_by(WorkoutLog.date.desc()).limit(5).all()
    return jsonify([{
        'workout_name': w.workout_name,
        'duration': w.duration,
        'calories_burned': w.calories_burned,
        'date': w.date.strftime('%Y-%m-%d')
    } for w in workouts])

@app.route('/save-settings', methods=['POST'])
def save_settings():
    try:
        data = request.json
        settings = UserSettings.query.filter_by(user_id=session['user_id']).first()
        if not settings:
            settings = UserSettings(user_id=session['user_id'])
    
        settings.notification_enabled = data.get('notification_enabled', True)
        settings.dark_mode = data.get('dark_mode', False)
        settings.measurement_unit = data.get('measurement_unit', 'metric')
        settings.workout_reminder_time = data.get('workout_reminder_time', '08:00')
        settings.meal_reminder_time = data.get('meal_reminder_time', '12:00')
        settings.water_goal = data.get('water_goal', 2.5)
        settings.daily_calorie_goal = data.get('daily_calorie_goal', 2000)
    
        db.session.add(settings)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-weather')
def get_weather():
    try:
        import requests
        city = request.args.get('city', 'Chennai')
        api_key = os.getenv('WEATHER_API_KEY')
        
        if not api_key:
            # Return mock data if no API key
            return jsonify({
                'temp': 32,
                'condition': 'Sunny',
                'humidity': 65,
                'icon': '☀️'
            })
        
        # OpenWeatherMap API
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'temp': round(data['main']['temp']),
                'condition': data['weather'][0]['main'],
                'humidity': data['main']['humidity'],
                'icon': get_weather_icon(data['weather'][0]['main'])
            })
        else:
            # Fallback to mock data
            return jsonify({
                'temp': 32,
                'condition': 'Sunny',
                'humidity': 65,
                'icon': '☀️'
            })
    except Exception as e:
        print(f"Weather API error: {str(e)}")
        return jsonify({
            'temp': 32,
            'condition': 'Sunny',
            'humidity': 65,
            'icon': '☀️'
        })

def get_weather_icon(condition):
    icons = {
        'Clear': '☀️',
        'Clouds': '☁️',
        'Rain': '🌧️',
        'Drizzle': '🌦️',
        'Thunderstorm': '⛈️',
        'Snow': '❄️',
        'Mist': '🌫️',
        'Smoke': '🌫️',
        'Haze': '🌫️',
        'Fog': '🌫️'
    }
    return icons.get(condition, '☀️')

@app.route('/get-nutrition-tip')
def get_nutrition_tip():
    tips = [
        {"tip": "Drink 2-3 liters of water daily for optimal metabolism", "icon": "💧"},
        {"tip": "Include protein in every meal to support muscle growth", "icon": "🥩"},
        {"tip": "Eat colorful vegetables for essential vitamins", "icon": "🥗"},
        {"tip": "Don't skip breakfast - it kickstarts your metabolism", "icon": "🍳"},
        {"tip": "Healthy fats like avocado and nuts are essential", "icon": "🥑"},
        {"tip": "Complex carbs provide sustained energy for workouts", "icon": "🍠"},
        {"tip": "Meal prep on Sundays to stay on track", "icon": "📅"},
        {"tip": "Listen to your body's hunger cues", "icon": "👂"},
    ]
    import random
    return jsonify(random.choice(tips))



@app.route('/get-achievements')
def get_achievements():
    user_id = session['user_id']
    
    # Get user data
    user = User.query.get(user_id)
    workouts = WorkoutLog.query.filter_by(user_id=user_id).order_by(WorkoutLog.date).all()
    meals = MealLog.query.filter_by(user_id=user_id).order_by(MealLog.date).all()
    
    # Calculate workout stats
    workout_count = len(workouts)
    
    # Calculate total weight lifted (if you track this)
    total_weight_lifted = 0  # You'd need to add this to your workout model
    
    # Calculate total distance run (if you track this)
    total_distance = 0  # You'd need to add this to your workout model
    
    # Count morning workouts (before 12 PM)
    morning_workouts = 0
    for w in workouts:
        # You'd need time field in workout model
        pass
    
    # Calculate streak
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    # Get unique workout dates
    workout_dates = sorted(list(set([w.date for w in workouts])), reverse=True)
    
    # Calculate current streak
    streak = 0
    if workout_dates:
        streak = 1
        for i in range(1, len(workout_dates)):
            if (workout_dates[i-1] - workout_dates[i]).days == 1:
                streak += 1
            else:
                break
    
    # Calculate level and XP
    total_xp = workout_count * 10 + len(meals) * 5
    level = total_xp // 100
    current_level_xp = total_xp % 100
    xp_to_next=100-current_level_xp
    
    # Determine earned badges based on REAL data
    achievements = []
    
    # First Workout
    if workout_count >= 1:
        first_workout_date = workouts[0].date.strftime('%b %d, %Y') if workouts else 'Today'
        achievements.append({
            'name': 'First Workout',
            'icon': '🎯',
            'description': 'Completed your first workout',
            'date': first_workout_date,
            'earned': True
        })
    
    # 10 Workouts
    if workout_count >= 10:
        achievements.append({
            'name': 'Getting Stronger',
            'icon': '💪',
            'description': 'Completed 10 workouts',
            'date': 'Recent',
            'earned': True
        })
    
    # 7-Day Streak
    if streak >= 7:
        achievements.append({
            'name': '7-Day Streak',
            'icon': '🔥',
            'description': 'Worked out 7 days in a row',
            'date': 'Current',
            'earned': True
        })
    else:
        achievements.append({
            'name': '7-Day Streak',
            'icon': '🔥',
            'description': 'Work out 7 days in a row',
            'date': f'{7-streak} days to go',
            'earned': False
        })
    
    # 30-Day Streak
    if streak >= 30:
        achievements.append({
            'name': '30-Day Streak',
            'icon': '⚡',
            'description': 'Worked out 30 days straight',
            'date': 'Champion!',
            'earned': True
        })
    else:
        achievements.append({
            'name': '30-Day Streak',
            'icon': '⚡',
            'description': 'Work out 30 days straight',
            'date': f'{30-streak} days to go',
            'earned': False
        })
    
    # Healthy Eater
    if len(meals) >= 5:
        achievements.append({
            'name': 'Healthy Eater',
            'icon': '🥗',
            'description': 'Logged 5 meals',
            'date': 'Recent',
            'earned': True
        })
    
    # Weight Lifter (if you track this)
    if total_weight_lifted >= 1000:
        achievements.append({
            'name': 'Weight Lifter',
            'icon': '🏋️',
            'description': 'Lifted 1000kg total',
            'date': 'Achieved',
            'earned': True
        })
    
    # Marathon Ready (if you track distance)
    if total_distance >= 42:
        achievements.append({
            'name': 'Marathon Ready',
            'icon': '🏃',
            'description': 'Ran 42km total',
            'date': 'Achieved',
            'earned': True
        })
    
    # Early Bird (if you track workout times)
    if morning_workouts >= 5:
        achievements.append({
            'name': 'Early Bird',
            'icon': '🌅',
            'description': '5 morning workouts',
            'date': 'Achieved',
            'earned': True
        })
    
    return jsonify({
        'level': level,
        'current_xp': current_level_xp,
        'total_xp': total_xp,
        'xp_to_next': 100 - current_level_xp,
        'workout_count': workout_count,
        'badge_count': len([a for a in achievements if a.get('earned')]),
        'streak': streak,
        'challenge_count': Challenge.query.filter_by(user_id=user_id, status='active').count(),
        'achievements': achievements
    })
    
    
    
   
    
    



@app.route('/create-challenge', methods=['POST'])
def create_challenge():
    data = request.json
    challenge = Challenge(
        user_id=session['user_id'],
        name=data['name'],
        description=data['description'],
        goal_type=data['goal_type'],
        goal_value=data['goal_value'],
        unit=data['unit'],
        end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date()
    )
    db.session.add(challenge)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/update-challenge', methods=['POST'])
def update_challenge():
    data = request.json
    challenge = Challenge.query.get(data['challenge_id'])
    if challenge and challenge.user_id == session['user_id']:
        challenge.current_value = data['current_value']
        if challenge.current_value >= challenge.goal_value:
            challenge.status = 'completed'
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/get-challenges')
def get_challenges():
    user_id = session['user_id']
    active_challenges = Challenge.query.filter_by(
        user_id=user_id, 
        status='active'
    ).all()
    
    completed_challenges = Challenge.query.filter_by(
        user_id=user_id, 
        status='completed'
    ).order_by(Challenge.end_date.desc()).limit(5).all()
    
    return jsonify({
        'active': [{
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'goal_value': c.goal_value,
            'current_value': c.current_value,
            'unit': c.unit,
            'end_date': c.end_date.strftime('%b %d, %Y')
        } for c in active_challenges],
        'completed': [{
            'name': c.name,
            'end_date': c.end_date.strftime('%b %d, %Y')
        } for c in completed_challenges]
    })



@app.route('/log-workout-page')
def log_workout_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('log_workout.html', now=datetime.now())

@app.route('/log-meal-page')
def log_meal_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('log_meal.html', now=datetime.now())

@app.route('/progress')
def progress_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('progress.html')





 
       
        
@app.route('/get-progress-data')
def get_progress_data():
    try:
        user_id = session['user_id']
        
        # Get workouts
        workouts = WorkoutLog.query.filter_by(user_id=user_id).order_by(WorkoutLog.date).all()
        
        # Calculate stats
        totalWorkouts = len(workouts)
        totalCaloriesBurned = sum(w.calories_burned for w in workouts)
        totalMinutes = sum(w.duration for w in workouts)
        
        # Calculate streak
        from datetime import datetime, timedelta
        today = datetime.now().date()
        streak = 0
        
        # Get unique workout dates
        workout_dates = sorted(list(set([w.date for w in workouts])), reverse=True)
        if workout_dates:
            streak = 1
            for i in range(1, len(workout_dates)):
                if (workout_dates[i-1] - workout_dates[i]).days == 1:
                    streak += 1
                else:
                    break
        
        # Weekly data
        weekLabels = []
        weeklyWorkouts = []
        weeklyCalories = []
        
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            weekLabels.append(day.strftime('%a'))
            day_workouts = [w for w in workouts if w.date == day]
            weeklyWorkouts.append(len(day_workouts))
            weeklyCalories.append(sum(w.calories_burned for w in day_workouts))
        
        # Recent activity
        recent = []
        workout_types = {}
        
        for w in sorted(workouts, key=lambda x: x.date, reverse=True)[:10]:
            recent.append({
                'icon': 'fa-dumbbell',
                'date': w.date.strftime('%b %d'),
                'title': w.workout_name,
                'calories': w.calories_burned,
                'duration': w.duration
            })
            # Count workout types for distribution
            workout_types[w.workout_name] = workout_types.get(w.workout_name, 0) + 1
        
        return jsonify({
            'success': True,
            'totalWorkouts': totalWorkouts,
            'totalCaloriesBurned': totalCaloriesBurned,
            'totalMinutes': totalMinutes,
            'streak': streak,
            'weekLabels': weekLabels,
            'weeklyWorkouts': weeklyWorkouts,
            'weeklyCalories': weeklyCalories,
            'recentActivity': recent,
            'workoutDistribution': {
                'labels': list(workout_types.keys()),
                'values': list(workout_types.values())
            }
        })
        
    except Exception as e:
        print(f"Error in get-progress-data: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

        
        

    

   
      
    
       

@app.route('/get-daily-totals')
def get_daily_totals():
    user_id = session['user_id']
    today = datetime.now().date()
    
    meals = MealLog.query.filter_by(user_id=user_id, date=today).all()
    total_calories = sum(m.calories for m in meals)
    total_protein = sum(m.protein for m in meals)
    
    return jsonify({
        'calories': total_calories,
        'protein': total_protein
    })


@app.route('/get-settings')
def get_settings():
    try:
        user_id = session['user_id']
        settings = UserSettings.query.filter_by(user_id=user_id).first()
        
        if settings:
            return jsonify({
                'success': True,
                'notification_enabled': settings.notification_enabled,
                'dark_mode': settings.dark_mode,
                'measurement_unit': settings.measurement_unit,
                'workout_reminder_time': settings.workout_reminder_time,
                'meal_reminder_time': settings.meal_reminder_time,
                'water_goal': settings.water_goal,
                'daily_calorie_goal': settings.daily_calorie_goal,
                'profile_visibility': 'public'  # Default value
            })
        else:
            return jsonify({
                'success': True,
                'notification_enabled': True,
                'dark_mode': False,
                'measurement_unit': 'metric',
                'workout_reminder_time': '08:00',
                'meal_reminder_time': '12:00',
                'water_goal': 2.5,
                'daily_calorie_goal': 2000,
                'profile_visibility': 'public'
            })
            
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})





@app.route('/achievements')
def achievements():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('achievements.html',user=User.query.get(session['user_id']))


@app.route('/goals')
def goals():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('goals.html',user=User.query.get(session['user_id']))


@app.route('/create-goal', methods=['POST'])
def create_goal():
    try:
        data = request.json
        goal = Goal(
            user_id=session['user_id'],
            name=data['name'],
            description=data.get('description', ''),
            goal_type=data['goal_type'],
            current_value=0,
            target_value=data['target_value'],
            unit=data['unit'],
            deadline=datetime.strptime(data['deadline'], '%Y-%m-%d').date()
        )
        db.session.add(goal)
        db.session.commit()
        return jsonify({'success': True, 'goal_id': goal.id})
    except Exception as e:
        print(f"Error creating goal: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/update-goal', methods=['POST'])
def update_goal():
    try:
        data = request.json
        goal = Goal.query.get(data['goal_id'])
        
        if not goal or goal.user_id != session['user_id']:
            return jsonify({'success': False, 'error': 'Goal not found'})
        
        goal.current_value = data['current_value']
        goal.progress_percent = (goal.current_value / goal.target_value) * 100
        
        if goal.current_value >= goal.target_value:
            goal.status = 'completed'
            goal.completed_date = datetime.now().date()
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating goal: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/complete-goal', methods=['POST'])
def complete_goal():
    try:
        data = request.json
        goal = Goal.query.get(data['goal_id'])
        
        if not goal or goal.user_id != session['user_id']:
            return jsonify({'success': False, 'error': 'Goal not found'})
        
        goal.status = 'completed'
        goal.completed_date = datetime.now().date()
        goal.progress_percent = 100
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error completing goal: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete-goal', methods=['POST'])
def delete_goal():
    try:
        data = request.json
        goal = Goal.query.get(data['goal_id'])
        
        if not goal or goal.user_id != session['user_id']:
            return jsonify({'success': False, 'error': 'Goal not found'})
        
        db.session.delete(goal)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting goal: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get-goals')
def get_goals():
    try:
        user_id = session['user_id']
        
        # Get active goals
        active_goals = Goal.query.filter_by(
            user_id=user_id, 
            status='active'
        ).order_by(Goal.deadline).all()
        
        # Get completed goals
        completed_goals = Goal.query.filter_by(
            user_id=user_id, 
            status='completed'
        ).order_by(Goal.completed_date.desc()).all()
        
        return jsonify({
            'active': [{
                'id': g.id,
                'name': g.name,
                'description': g.description,
                'goal_type': g.goal_type,
                'current_value': g.current_value,
                'target_value': g.target_value,
                'unit': g.unit,
                'progress': g.progress_percent,
                'deadline': g.deadline.strftime('%b %d, %Y'),
                'days_left': (g.deadline - datetime.now().date()).days
            } for g in active_goals],
            'completed': [{
                'id': g.id,
                'name': g.name,
                'completed_date': g.completed_date.strftime('%b %d, %Y')
            } for g in completed_goals]
        })
    except Exception as e:
        print(f"Error getting goals: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/calendar')
def calendar():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('calendar.html',user=User.query.get(session['user_id']))

@app.route('/music')
def music():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('music.html',user=User.query.get(session['user_id']))



@app.route('/get-analytics-data')
def get_analytics_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    range_type = request.args.get('range', 'week')  # week, month, year, all
    
    from datetime import datetime, timedelta
    import random
    today = datetime.now().date()
    
    # Get the user first - THIS WAS MISSING!
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Set date range based on selection
    if range_type == 'week':
        start_date = today - timedelta(days=7)
    elif range_type == 'month':
        start_date = today - timedelta(days=30)
    elif range_type == 'year':
        start_date = today - timedelta(days=365)
    else:  # all time
        start_date = None
    
    # Get workouts within date range
    workouts_query = WorkoutLog.query.filter_by(user_id=user_id)
    if start_date:
        workouts_query = workouts_query.filter(WorkoutLog.date >= start_date)
    workouts = workouts_query.order_by(WorkoutLog.date).all()
    
    # Get meals within date range
    meals_query = MealLog.query.filter_by(user_id=user_id)
    if start_date:
        meals_query = meals_query.filter(MealLog.date >= start_date)
    meals = meals_query.order_by(MealLog.date).all()
    
    # Get user progress
    progress = UserProgress.query.filter_by(user_id=user_id).order_by(UserProgress.date).all()
    
    # Calculate stats
    total_workouts = len(workouts)
    total_minutes = sum(w.duration for w in workouts)
    total_calories_burned = sum(w.calories_burned for w in workouts)
    total_meals = len(meals)
    total_calories_consumed = sum(m.calories for m in meals)
    
    # Calculate current streak
    streak = 0
    workout_dates = sorted(list(set([w.date for w in workouts])), reverse=True)
    if workout_dates:
        streak = 1
        for i in range(1, len(workout_dates)):
            if (workout_dates[i-1] - workout_dates[i]).days == 1:
                streak += 1
            else:
                break
    
    # Calculate best streak
    best_streak = 0
    current_streak = 0
    for i in range(len(workout_dates)):
        if i == 0:
            current_streak = 1
        elif (workout_dates[i-1] - workout_dates[i]).days == 1:
            current_streak += 1
        else:
            current_streak = 1
        best_streak = max(best_streak, current_streak)
    
    # Weekly data for charts
    week_labels = []
    weekly_workouts = []
    weekly_calories = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        week_labels.append(day.strftime('%a'))
        day_workouts = [w for w in workouts if w.date == day]
        weekly_workouts.append(len(day_workouts))
        weekly_calories.append(sum(w.calories_burned for w in day_workouts))
    
    # Workout type distribution
    workout_types = {}
    for w in workouts:
        workout_types[w.workout_name] = workout_types.get(w.workout_name, 0) + 1
    
    # Time of day distribution (mock data)
    time_distribution = {
        'Morning': random.randint(30, 50),
        'Afternoon': random.randint(20, 40),
        'Evening': random.randint(20, 40)
    }
    
    # Weight progress
    weight_start = user.weight if user.weight else 70
    weight_current = progress[-1].current_weight if progress else user.weight
    weight_goal = 60  # Default goal
    
    # Calculate weight progress percentage
    if weight_start > weight_goal:  # Weight loss goal
        weight_progress = ((weight_start - weight_current) / (weight_start - weight_goal)) * 100
    else:  # Weight gain goal
        weight_progress = ((weight_current - weight_start) / (weight_goal - weight_start)) * 100
    weight_progress = max(0, min(100, weight_progress))
    
    # Strength PRs
    strength_prs = {
        'bench': 80,
        'squat': 100,
        'deadlift': 120
    }
    
    # Nutrition averages
    if meals:
        avg_calories = sum(m.calories for m in meals) // len(meals)
        avg_protein = sum(m.protein for m in meals) // len(meals)
        avg_carbs = sum(m.carbs for m in meals) // len(meals)
        avg_fats = sum(m.fats for m in meals) // len(meals)
    else:
        avg_calories = avg_protein = avg_carbs = avg_fats = 0
    
    # Generate insights
    insights = []
    
    if total_workouts > 0:
        insights.append({
            'icon': '💪',
            'title': 'Workout Consistency',
            'text': f"You've completed {total_workouts} workouts in this period."
        })
    
    if streak > 0:
        insights.append({
            'icon': '🔥',
            'title': 'Current Streak',
            'text': f"You're on a {streak}-day streak!"
        })
    
    if weight_progress > 0:
        insights.append({
            'icon': '🎯',
            'title': 'Goal Progress',
            'text': f"You're {weight_progress:.1f}% towards your weight goal."
        })
    
    return jsonify({
        'stats': {
            'totalWorkouts': total_workouts,
            'totalMinutes': total_minutes,
            'totalCaloriesBurned': total_calories_burned,
            'bestStreak': best_streak,
            'currentStreak': streak
        },
        'progress': {
            'weightStart': weight_start,
            'weightCurrent': weight_current,
            'weightGoal': weight_goal,
            'weightProgress': weight_progress,
            'strengthPRs': strength_prs,
            'workoutGoal': 50,
            'workoutProgress': (total_workouts / 50) * 100 if total_workouts > 0 else 0
        },
        'charts': {
            'weekLabels': week_labels,
            'weeklyWorkouts': weekly_workouts,
            'weeklyCalories': weekly_calories,
            'distribution': list(workout_types.values()),
            'distributionLabels': list(workout_types.keys()),
            'timeDistribution': time_distribution,
            'nutrition': {
                'caloriesConsumed': [random.randint(1800, 2500) for _ in range(7)],
                'caloriesBurned': weekly_calories
            },
            'macros': {
                'protein': avg_protein,
                'carbs': avg_carbs,
                'fats': avg_fats
            }
        },
        'insights': insights
    })
    
    
    
@app.route('/get-user-level')
def get_user_level():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    user_id = session['user_id']
    
    # Get user data
    workouts = WorkoutLog.query.filter_by(user_id=user_id).all()
    meals = MealLog.query.filter_by(user_id=user_id).all()
    
    # Calculate XP (10 per workout, 5 per meal)
    total_xp = len(workouts) * 10 + len(meals) * 5
    
    # Calculate level (every 100 XP = 1 level)
    level = (total_xp // 100) + 1  # Start at level 1
    current_level_xp = total_xp % 100
    next_level_xp = 100 - current_level_xp
    
    # Calculate level progress percentage
    progress_percent = (current_level_xp / 100) * 100
    
    return jsonify({
        'level': level,
        'current_xp': current_level_xp,
        'next_level_xp': next_level_xp,
        'progress': progress_percent,
        'total_xp': total_xp,
        'workouts': len(workouts),
        'meals': len(meals)
    })


@app.route('/debug-workouts')
def debug_workouts():
    if 'user_id' not in session:
        return "Login first"
    
    user_id = session['user_id']
    workouts = WorkoutLog.query.filter_by(user_id=user_id).all()
    
    result = "<h2>Workouts in Database:</h2>"
    for w in workouts:
        result += f"<p>ID: {w.id}, Date: {w.date}, Name: {w.workout_name}, Calories: {w.calories_burned}, Duration: {w.duration}</p>"
    
    result += f"<h3>Total: {len(workouts)} workouts</h3>"
    return result


# ===== ADD THIS AT THE VERY BOTTOM, BEFORE if __name__ =====

# Add this function to initialize database
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Database tables created/verified!")


# Add this with your other routes (around line 300-400)

@app.route('/check-email', methods=['POST'])
def check_email():
    data = request.json
    email = data.get('email')
    
    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})


    

# Your existing code at the bottom should look like this:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


    


