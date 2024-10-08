import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timezone

app = Flask(__name__)

# Get the absolute path of the directory where the app.py is located
basedir = os.path.abspath(os.path.dirname(__file__))

# Use an absolute path for the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'mydbdata.db')}"
app.config['SECRET_KEY'] = 'your_secret_key'  # For flash messages
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')  # Directory for uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    lastname = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username 

# Define Blog model
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.String(400), nullable=False)
    image = db.Column(db.String(200), nullable=True)  # Field for image filename
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))

    def __repr__(self):
        return '<Blog %r>' % self.title 

@app.route("/")
def index():
    blogs = Blog.query.order_by(Blog.pub_date.desc()).all()
    return render_template("index.html", blogs=blogs)

@app.route("/dashboard")
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    blogs = Blog.query.filter_by(author=user.username).order_by(Blog.pub_date.desc()).all()
    return render_template("dashboard.html", user=user, blogs=blogs)

@app.route("/signup", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        uname = request.form['uname']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        existing_username = User.query.filter_by(username=uname).first()
        if existing_user:
            flash('Email already exists, try a different one.', 'danger')
            return redirect(url_for('register'))
        if existing_username:
            flash('Username already exists, try a different one.', 'danger')
            return redirect(url_for('register'))

        # Hash the password before storing it
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Create a new user and add to the database
        new_user = User(
            firstname=fname, 
            lastname=lname, 
            username=uname, 
            email=email, 
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful!', 'success')
        return redirect(url_for('login'))  
    return render_template("register.html")

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            flash('Login successful!', 'success')
            session['user_id'] = user.id  # Store user session
            session['username'] = user.username
            return redirect(url_for('dashboard')) 
        else:
            flash('Invalid email or password.', 'danger')
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('user_id', None)  # Remove user from session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route("/add_blog", methods=['GET', 'POST'])
def create_blog():
    if 'user_id' not in session:
        flash('Please log in to create a blog post.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        uname = session['username']
        title = request.form['title']
        content = request.form['content']
        image_file = request.files['image']  # Get the uploaded image file

        if not title:
            flash('Title cannot be empty.', 'warning')
            return redirect(url_for('create_blog'))
        if not content:
            flash('Content cannot be empty.', 'warning')
            return redirect(url_for('create_blog'))

        # Handle image upload
        image_filename = None
        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # Create the blog post and save it to the database
        new_blog = Blog(author=uname, title=title, content=content, image=image_filename)
        db.session.add(new_blog)
        db.session.commit()
        flash('Your blog post was submitted successfully.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_blog.html')

@app.route("/details_blog/<int:id>")
def detail_blog(id):
    blog = Blog.query.get(id)
    return render_template('blog_detail.html', blog=blog)

@app.route("/delete_blog/<int:id>")
def delete_blog(id):
    blog = Blog.query.get(id)
    db.session.delete(blog)
    db.session.commit()
    flash('Blog deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route("/edit_blog/<int:id>", methods=['GET', 'POST'])
def edit_blog(id):
    blog = Blog.query.get_or_404(id)
    if request.method == 'POST':
        blog.title = request.form['title']
        blog.content = request.form['content']
        image_file = request.files['image']  # Get the uploaded image file

        if not blog.title:
            flash('Title cannot be empty.', 'warning')
            return redirect(url_for('edit_blog', id=blog.id))
        if not blog.content:
            flash('Content cannot be empty.', 'warning')
            return redirect(url_for('edit_blog', id=blog.id))

        # Handle image upload
        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            blog.image = image_filename  # Update image filename in the blog

        db.session.commit()
        flash('Blog post updated successfully.', 'success')
        return redirect(url_for('dashboard')) 
    return render_template('edit_blog.html', blog=blog)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database and tables
    app.run(debug=True)
