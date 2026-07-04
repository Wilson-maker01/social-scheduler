from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Post
from ml_model import predict
from datetime import datetime
import pickle

app = Flask(__name__)
app.secret_key = "socialschedulerkey123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
db.init_app(app)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
@login_required
def dashboard():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    total_posts = len(posts)
    scheduled = Post.query.filter_by(user_id=current_user.id, status='scheduled').count()
    published = Post.query.filter_by(user_id=current_user.id, status='published').count()
    total_predicted_engagement = sum(p.predicted_engagement for p in posts)

    platform_stats = {}
    for post in posts:
        if post.platform not in platform_stats:
            platform_stats[post.platform] = {
                'count': 0,
                'engagement': 0
            }
        platform_stats[post.platform]['count'] += 1
        platform_stats[post.platform]['engagement'] += post.predicted_engagement

    return render_template('dashboard.html',
                         posts=posts,
                         total_posts=total_posts,
                         scheduled=scheduled,
                         published=published,
                         total_predicted_engagement=round(total_predicted_engagement),
                         platform_stats=platform_stats)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'danger')
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('User not found!', 'danger')
            return redirect(url_for('login'))

        if bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Wrong password!', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        platform = request.form['platform']
        post_type = request.form['post_type']
        scheduled_time = datetime.strptime(
            request.form['scheduled_time'], '%Y-%m-%dT%H:%M')
        hashtags = int(request.form.get('hashtags', 0))
        mentions = int(request.form.get('mentions', 0))
        has_image = 1 if request.form.get('has_image') else 0
        has_video = 1 if request.form.get('has_video') else 0
        word_count = len(content.split())
        followers = int(request.form.get('followers', 1000))

        prediction = predict(
        platform=platform,
        post_type=post_type,
        hour=scheduled_time.hour,
        day_of_week=scheduled_time.weekday(),
        hashtags=hashtags,
        mentions=mentions,
        has_image=has_image,
        has_video=has_video,
        word_count=word_count,
        followers=followers
        )

        new_post = Post(
            title=title,
            content=content,
            platform=platform,
            post_type=post_type,
            scheduled_time=scheduled_time,
            hashtags=hashtags,
            mentions=mentions,
            has_image=bool(has_image),
            has_video=bool(has_video),
            word_count=word_count,
            predicted_likes=prediction['likes'],
            predicted_shares=prediction['shares'],
            predicted_comments=prediction['comments'],
            predicted_engagement=prediction['engagement'],
            user_id=current_user.id
        )

        db.session.add(new_post)
        db.session.commit()

        flash(f'Post scheduled! Predicted engagement: {prediction["engagement"]}', 'success')
        return redirect(url_for('dashboard'))

    return render_template('schedule.html')

@app.route('/post/<int:post_id>')
@login_required
def post_detail(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    return render_template('post_detail.html', post=post)

@app.route('/post/<int:post_id>/publish', methods=['POST'])
@login_required
def publish_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    post.status = 'published'
    post.actual_likes = float(request.form.get('actual_likes', 0))
    post.actual_shares = float(request.form.get('actual_shares', 0))
    post.actual_comments = float(request.form.get('actual_comments', 0))
    db.session.commit()
    flash('Post marked as published!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/post/<int:post_id>/delete')
@login_required
def delete_post(post_id):
    post = db.session.get(Post, post_id) or abort(404)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/analytics')
@login_required
def analytics():
    posts = Post.query.filter_by(user_id=current_user.id).all()
    platform_data = {}
    for post in posts:
        if post.platform not in platform_data:
            platform_data[post.platform] = {
                'predicted': 0,
                'actual': 0,
                'count': 0
            }
        platform_data[post.platform]['predicted'] += post.predicted_engagement
        platform_data[post.platform]['actual'] += (
            post.actual_likes + post.actual_shares + post.actual_comments)
        platform_data[post.platform]['count'] += 1

    return render_template('analytics.html',
                         posts=posts,
                         platform_data=platform_data)

@app.route('/metrics')
@login_required
def metrics():
    with open('ml_metrics.pkl', 'rb') as f:
        ml_metrics = pickle.load(f)
    return render_template('metrics.html', metrics=ml_metrics)

if __name__ == '__main__':
    app.run(debug=True)