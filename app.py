from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
import json
from blockchain import Blockchain
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
import os

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///circuLink.db'
app.secret_key = os.urandom(24)  # For session management
db = SQLAlchemy(app)
blockchain = Blockchain()

# Database Models
class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    sustainability_cert = db.Column(db.String(200), nullable=False)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    cert_hash = db.Column(db.String(64), unique=True)

class EnergyData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    energy_consumed_kwh = db.Column(db.Float, nullable=False)
    data_hash = db.Column(db.String(64))

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('circuLink.db')
        c = conn.cursor()
        user = c.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('circuLink.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)',
                     (full_name, email, hashed_password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered', 'error')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/warehouse_locator')
def warehouse_locator():
    return render_template('warehouse_locator.html')

@app.route('/parts_finder')
def parts_finder():
    return render_template('parts_finder.html')

@app.route('/energy_tracking')
def energy_tracking():
    return render_template('energy_tracking.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register_supplier', methods=['GET', 'POST'])
def register_supplier():
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        sustainability_cert = request.form['sustainability_cert']
        
        # Create hash of certification data
        cert_hash = hashlib.sha256(sustainability_cert.encode()).hexdigest()
        
        # Add to blockchain
        blockchain.add_block({
            'type': 'supplier_registration',
            'cert_hash': cert_hash
        })
        
        # Save to database
        supplier = Supplier(
            name=name,
            location=location,
            sustainability_cert=sustainability_cert,
            cert_hash=cert_hash
        )
        db.session.add(supplier)
        db.session.commit()
        
        return redirect(url_for('suppliers'))
    return render_template('register_supplier.html')

@app.route('/suppliers')
def suppliers():
    suppliers = Supplier.query.all()
    return render_template('suppliers.html', suppliers=suppliers)

@app.route('/submit_energy_data', methods=['GET', 'POST'])
def submit_energy_data():
    if request.method == 'POST':
        warehouse_id = request.form['warehouse_id']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        energy_consumed_kwh = float(request.form['energy_consumed_kwh'])
        
        # Create hash of energy data
        data_str = f"{warehouse_id}{date}{energy_consumed_kwh}"
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()
        
        # Add to blockchain
        blockchain.add_block({
            'type': 'energy_data',
            'data_hash': data_hash
        })
        
        # Save to database
        energy_data = EnergyData(
            warehouse_id=warehouse_id,
            date=date,
            energy_consumed_kwh=energy_consumed_kwh,
            data_hash=data_hash
        )
        db.session.add(energy_data)
        db.session.commit()
        
        return redirect(url_for('energy_dashboard'))
    return render_template('submit_energy.html')

@app.route('/energy_dashboard')
def energy_dashboard():
    energy_data = EnergyData.query.order_by(EnergyData.date).all()
    warehouses = db.session.query(EnergyData.warehouse_id).distinct().all()
    return render_template('energy_dashboard.html', 
                         energy_data=energy_data,
                         warehouses=warehouses)

@app.route('/blockchain')
def view_blockchain():
    chain = blockchain.get_chain()
    return render_template('blockchain.html', chain=chain)

@app.route('/documentation')
def documentation():
    return render_template('documentation.html')

# API Endpoints
@app.route('/api/suppliers')
def api_suppliers():
    suppliers = Supplier.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'location': s.location,
        'sustainability_cert': s.sustainability_cert,
        'date_registered': s.date_registered.isoformat(),
        'cert_hash': s.cert_hash
    } for s in suppliers])

@app.route('/api/energy_data')
def api_energy_data():
    energy_data = EnergyData.query.all()
    return jsonify([{
        'id': e.id,
        'warehouse_id': e.warehouse_id,
        'date': e.date.isoformat(),
        'energy_consumed_kwh': e.energy_consumed_kwh,
        'data_hash': e.data_hash
    } for e in energy_data])

@app.route('/api/blockchain')
def api_blockchain():
    return jsonify(blockchain.get_chain())

# Create database tables
with app.app_context():
    db.create_all()

# Initialize database and run app
if __name__ == '__main__':
    app.run(debug=True) 