from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegistrationForm, MovieForm, RatingForm
from models import db, User, Movie, Rating, Watchlist
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask_wtf.csrf import CSRFProtect


# Configure Cloudinary
cloudinary.config(
    cloud_name="",  # Replace with your Cloudinary cloud name
    api_key="",       # Replace with your Cloudinary API key
    api_secret=""  # Replace with your Cloudinary API secret
)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movieverse.db'
db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    movies = Movie.query.all()
    return render_template('dashboard.html', movies=movies)

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Use the default method 'pbkdf2:sha256' for password hashing
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_movie', methods=['GET', 'POST'])
@login_required
def add_movie():
    # Check if the current user is the admin
    if current_user.email != 'admin@movieverse.com':
        flash('You are not authorized to access add movie page.', 'danger')
        return redirect(url_for('index'))  # Redirect to the home page or any other page of your choice

    form = MovieForm()
    if form.validate_on_submit():
        # Upload the image to Cloudinary if provided
        poster_url = None
        if form.poster.data:
            upload_result = cloudinary.uploader.upload(form.poster.data)
            poster_url = upload_result['secure_url']

        # Add the movie to the database
        movie = Movie(
            title=form.title.data,
            genre=form.genre.data,
            description=form.description.data,
            poster_url=poster_url
        )
        db.session.add(movie)
        db.session.commit()
        flash('Movie added successfully!')
        return redirect(url_for('index'))
    return render_template('add_movie.html', form=form)


@app.route('/movie/<int:movie_id>', methods=['GET', 'POST'])
def movie_detail(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    form = RatingForm()

    if form.validate_on_submit():
        rating = Rating(rating=form.rating.data, movie_id=movie.id, user_id=current_user.id)
        db.session.add(rating)
        db.session.commit()
        flash('Your rating has been submitted!', 'success')
        return redirect(url_for('movie_detail', movie_id=movie.id))

    return render_template('movie_detail.html', movie=movie, form=form)

@app.route('/watchlist')
@login_required
def watchlist():
    movies = current_user.watchlist_movies
    return render_template('watchlist.html', movies=movies)

@app.route('/remove_from_watchlist/<int:movie_id>', methods=['POST'])
@login_required
def remove_from_watchlist(movie_id):
    watchlist_entry = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if watchlist_entry:
        db.session.delete(watchlist_entry)
        db.session.commit()
        flash('Movie removed from watchlist!')
    return redirect(url_for('watchlist'))

@app.route('/add_to_watchlist/<int:movie_id>')
@login_required
def add_to_watchlist(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    if movie not in current_user.watchlist_movies:
        watchlist_entry = Watchlist(user_id=current_user.id, movie_id=movie_id)
        db.session.add(watchlist_entry)
        db.session.commit()
        flash('Movie added to watchlist!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
