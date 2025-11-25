"""
Personal Budget Tracker - Clean & Concise Version
A comprehensive financial management application with user authentication,
transaction tracking, analytics, and data export capabilities.
"""

import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    """Application factory pattern."""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///budget_tracker.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'

    # Create database tables
    with app.app_context():
        db.create_all()
        setup_relationships()
        seed_default_data()

    # Register routes
    register_routes(app)
    
    # Global template variables
    @app.context_processor
    def inject_globals():
        return {
            'current_year': datetime.now().year,
            'app_name': 'TrackMyCash',
            'timedelta': __import__('datetime').timedelta
        }
    
    @app.before_request
    def load_globals():
        g.today = date.today()
    
    return app


# Database Models
class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username


class Category(db.Model):
    """Category model for transaction categorization."""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    color = db.Column(db.String(7), default='#6c757d')
    icon = db.Column(db.String(50), default='bi-tag')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='category', lazy=True)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('name', 'type', 'user_id', name='uq_category_name_type_user'),
    )


class Transaction(db.Model):
    """Transaction model for income and expense tracking."""
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'income' or 'expense'
    description = db.Column(db.String(255), nullable=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Loan(db.Model):
    """Loan/EMI model for tracking loans and EMIs."""
    __tablename__ = 'loans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Loan name/description
    loan_type = db.Column(db.String(50), nullable=False)  # 'home', 'car', 'personal', 'education', 'other'
    principal_amount = db.Column(db.Float, nullable=False)  # Original loan amount
    remaining_amount = db.Column(db.Float, nullable=False)  # Remaining amount to pay
    interest_rate = db.Column(db.Float, nullable=False)  # Annual interest rate
    emi_amount = db.Column(db.Float, nullable=False)  # Monthly EMI amount
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    next_payment_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_emi_paid_amount(self):
        """Calculate total EMI amount paid so far."""
        from datetime import datetime
        months_paid = 0
        current_date = datetime.now().date()
        
        if current_date >= self.start_date:
            if current_date >= self.end_date:
                # Loan completed
                months_paid = (self.end_date.year - self.start_date.year) * 12 + (self.end_date.month - self.start_date.month)
            else:
                # Loan ongoing
                months_paid = (current_date.year - self.start_date.year) * 12 + (current_date.month - self.start_date.month)
        
        return months_paid * self.emi_amount
    
    @property
    def total_emi_paid(self):
        """Get total EMI amount paid."""
        return self.calculate_emi_paid_amount()
    
    @property
    def progress_percentage(self):
        """Calculate loan repayment progress percentage."""
        if self.principal_amount == 0:
            return 0
        paid_amount = self.principal_amount - self.remaining_amount
        return (paid_amount / self.principal_amount) * 100


class Insurance(db.Model):
    """Insurance model for tracking life and health insurance."""
    __tablename__ = 'insurances'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Insurance policy name
    insurance_type = db.Column(db.String(50), nullable=False)  # 'life', 'health', 'motor', 'home', 'other'
    policy_number = db.Column(db.String(100), nullable=True)
    insurance_company = db.Column(db.String(100), nullable=False)
    premium_amount = db.Column(db.Float, nullable=False)  # Premium amount
    premium_frequency = db.Column(db.String(20), nullable=False)  # 'monthly', 'quarterly', 'yearly'
    sum_assured = db.Column(db.Float, nullable=True)  # Coverage amount
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    next_premium_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def premium_per_month(self):
        """Calculate monthly premium equivalent."""
        if self.premium_frequency == 'monthly':
            return self.premium_amount
        elif self.premium_frequency == 'quarterly':
            return self.premium_amount / 3
        elif self.premium_frequency == 'yearly':
            return self.premium_amount / 12
        return self.premium_amount
    
    @property
    def days_to_next_premium(self):
        """Calculate days until next premium payment."""
        from datetime import datetime
        today = datetime.now().date()
        if self.next_premium_date >= today:
            return (self.next_premium_date - today).days
        return 0


# Add relationships after all models are defined
def setup_relationships():
    """Setup model relationships after all models are defined."""
    User.loans = db.relationship('Loan', backref='user', lazy=True, cascade='all, delete-orphan')
    User.insurances = db.relationship('Insurance', backref='user', lazy=True, cascade='all, delete-orphan')


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login."""
    return User.query.get(int(user_id))


def seed_default_data():
    """Seed default categories."""
    defaults = {
        'expense': [
            {"name": "Bills", "color": "#dc3545", "icon": "bi-receipt"},
            {"name": "Transport", "color": "#fd7e14", "icon": "bi-car-front"},
            {"name": "Food", "color": "#20c997", "icon": "bi-egg-fried"},
            {"name": "Entertainment", "color": "#6f42c1", "icon": "bi-film"},
            {"name": "Shopping", "color": "#e83e8c", "icon": "bi-bag"},
            {"name": "Healthcare", "color": "#198754", "icon": "bi-heart-pulse"},
            {"name": "Education", "color": "#0d6efd", "icon": "bi-book"},
            {"name": "Other", "color": "#6c757d", "icon": "bi-three-dots"}
        ],
        'income': [
            {"name": "Salary", "color": "#198754", "icon": "bi-briefcase"},
            {"name": "Investments", "color": "#0d6efd", "icon": "bi-graph-up"},
            {"name": "Freelance", "color": "#fd7e14", "icon": "bi-laptop"},
            {"name": "Business", "color": "#6f42c1", "icon": "bi-building"},
            {"name": "Crypto", "color": "#ffc107", "icon": "bi-currency-bitcoin"},
            {"name": "Real Estate", "color": "#20c997", "icon": "bi-house"},
            {"name": "Other", "color": "#6c757d", "icon": "bi-three-dots"}
        ]
    }
    
    for type_, categories in defaults.items():
        for cat_data in categories:
            exists = Category.query.filter_by(
                name=cat_data["name"], 
                type=type_, 
                user_id=None
            ).first()
            if not exists:
                category = Category(
                    name=cat_data["name"],
                    type=type_,
                    color=cat_data["color"],
                    icon=cat_data["icon"],
                    user_id=None
                )
                db.session.add(category)
    
    db.session.commit()


def register_routes(app):
    """Register all application routes."""
    
    @app.route('/')
    def index():
        """Home page - redirect to dashboard if authenticated, otherwise to login."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration."""
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm = request.form.get('confirm', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()

            # Validation
            if not username or not email or not password:
                flash('Username, email, and password are required.', 'danger')
                return render_template('register.html')
            
            if password != confirm:
                flash('Passwords do not match.', 'danger')
                return render_template('register.html')
            
            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash('Username or email already in use.', 'danger')
                return render_template('register.html')
            
            # Create user
            user = User(
                username=username, 
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login."""
        if request.method == 'POST':
            username_or_email = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            
            user = User.query.filter(
                (User.username == username_or_email) | 
                (User.email == username_or_email.lower())
            ).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash('Logged in successfully.', 'success')
                return redirect(url_for('dashboard'))
            
            flash('Invalid credentials.', 'danger')
        
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        """User logout."""
        logout_user()
        flash('Logged out successfully.', 'success')
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard with financial overview."""
        # Get current month transactions
        month_start = date(g.today.year, g.today.month, 1)
        next_month = date(month_start.year + (month_start.month // 12), 
                         ((month_start.month % 12) + 1), 1)
        
        monthly_txns = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.date >= month_start,
            Transaction.date < next_month
        ).all()
        
        # Calculate totals
        total_income = sum(t.amount for t in monthly_txns if t.type == 'income')
        total_expense = sum(t.amount for t in monthly_txns if t.type == 'expense')
        balance = total_income - total_expense
        
        # Get recent transactions
        recent_txns = Transaction.query.filter_by(user_id=current_user.id)\
            .order_by(Transaction.date.desc(), Transaction.created_at.desc())\
            .limit(10).all()
        
        # Get category breakdown
        categories = get_user_categories(current_user.id)
        
        # Get active loans
        active_loans = Loan.query.filter_by(user_id=current_user.id, is_active=True).all()
        total_emi_amount = sum(loan.emi_amount for loan in active_loans)
        
        # Get active insurances
        active_insurances = Insurance.query.filter_by(user_id=current_user.id, is_active=True).all()
        total_premium_per_month = sum(insurance.premium_per_month for insurance in active_insurances)
        
        return render_template('dashboard.html',
                               total_income=round(total_income, 2),
                               total_expense=round(total_expense, 2),
                               balance=round(balance, 2),
                               recent_transactions=recent_txns,
                               categories=categories,
                               active_loans=active_loans,
                               total_emi_amount=round(total_emi_amount, 2),
                               active_insurances=active_insurances,
                               total_premium_per_month=round(total_premium_per_month, 2))
    
    @app.route('/transactions')
    @login_required
    def transactions_list():
        """List all transactions with filtering."""
        filter_type = request.args.get('type')
        period = request.args.get('period')

        query = Transaction.query.filter_by(user_id=current_user.id)

        # Apply period filter
        if period in ('current', 'last'):
            base = g.today
            if period == 'last':
                prev_month = base.month - 1 or 12
                prev_year = base.year - 1 if base.month == 1 else base.year
                month_start = date(prev_year, prev_month, 1)
            else:
                month_start = date(base.year, base.month, 1)
            next_month = date(month_start.year + (month_start.month // 12), 
                             ((month_start.month % 12) + 1), 1)
            query = query.filter(Transaction.date >= month_start)\
                .filter(Transaction.date < next_month)

        # Apply type filter
        if filter_type in ('income', 'expense'):
            query = query.filter_by(type=filter_type)

        transactions = query.order_by(Transaction.date.desc(), 
                                     Transaction.created_at.desc()).all()

        categories = get_user_categories(current_user.id)
        return render_template('transactions/list.html', 
                               transactions=transactions,
                               categories=categories,
                               active_type=filter_type,
                               active_period=period)

    @app.route('/transactions/add', methods=['GET', 'POST'])
    @login_required
    def transactions_add():
        """Add new transaction."""
        categories = get_user_categories(current_user.id)
        
        if request.method == 'POST':
            type_ = request.form.get('type')
            category_id = request.form.get('category_id')
            amount = request.form.get('amount')
            description = request.form.get('description', '').strip()
            date_str = request.form.get('date')
            
            # Validation
            try:
                amount_val = float(amount)
            except (TypeError, ValueError):
                flash('Invalid amount.', 'danger')
                return render_template('transactions/form.html', 
                                       categories=categories,
                                       form_action=url_for('transactions_add'))
            
            if type_ not in ('income', 'expense'):
                flash('Invalid type.', 'danger')
                return render_template('transactions/form.html',
                                       categories=categories,
                                       form_action=url_for('transactions_add'))
            
            try:
                date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return render_template('transactions/form.html',
                                       categories=categories,
                                       form_action=url_for('transactions_add'))
            
            # Create transaction
            category = Category.query.filter_by(id=category_id).first() if category_id else None
            transaction = Transaction(
                user_id=current_user.id,
                amount=amount_val,
                type=type_,
                description=description,
                date=date_val,
                category=category
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            flash('Transaction added successfully.', 'success')
            return redirect(url_for('transactions_list'))
        
        return render_template('transactions/form.html',
                               categories=categories,
                               form_action=url_for('transactions_add'))

    @app.route('/transactions/<int:txn_id>/edit', methods=['GET', 'POST'])
    @login_required
    def transactions_edit(txn_id):
        """Edit existing transaction."""
        transaction = Transaction.query.filter_by(
            id=txn_id, user_id=current_user.id
        ).first_or_404()
        
        categories = get_user_categories(current_user.id)
        
        if request.method == 'POST':
            type_ = request.form.get('type')
            category_id = request.form.get('category_id')
            amount = request.form.get('amount')
            description = request.form.get('description', '').strip()
            date_str = request.form.get('date')
            
            # Validation
            try:
                transaction.amount = float(amount)
            except (TypeError, ValueError):
                flash('Invalid amount.', 'danger')
                return render_template('transactions/form.html',
                                       categories=categories,
                                       transaction=transaction,
                                       form_action=url_for('transactions_edit', txn_id=transaction.id))
            
            if type_ not in ('income', 'expense'):
                flash('Invalid type.', 'danger')
                return render_template('transactions/form.html',
                                       categories=categories,
                                       transaction=transaction,
                                       form_action=url_for('transactions_edit', txn_id=transaction.id))
            
            try:
                transaction.date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return render_template('transactions/form.html',
                                       categories=categories,
                                       transaction=transaction,
                                       form_action=url_for('transactions_edit', txn_id=transaction.id))
            
            # Update transaction
            transaction.type = type_
            transaction.description = description
            transaction.category = Category.query.filter_by(id=category_id).first() if category_id else None
            
            db.session.commit()
            
            flash('Transaction updated successfully.', 'success')
            return redirect(url_for('transactions_list'))
        
        return render_template('transactions/form.html',
                               categories=categories,
                               transaction=transaction,
                               form_action=url_for('transactions_edit', txn_id=transaction.id))
    
    @app.route('/transactions/<int:txn_id>/delete', methods=['POST'])
    @login_required
    def transactions_delete(txn_id):
        """Delete transaction."""
        transaction = Transaction.query.filter_by(
            id=txn_id, user_id=current_user.id
        ).first_or_404()
        
        db.session.delete(transaction)
        db.session.commit()
        
        flash('Transaction deleted successfully.', 'success')
        return redirect(url_for('transactions_list'))

    @app.route('/categories', methods=['POST'])
    @login_required
    def create_category():
        """Create new category."""
        name = request.form.get('name', '').strip()
        type_ = request.form.get('type', '').strip()
        
        if not name or type_ not in ('income', 'expense'):
            return jsonify({'error': 'Invalid data'}), 400
        
        # Check if category already exists
        exists = Category.query.filter_by(
            name=name, type=type_, user_id=current_user.id
        ).first()
        
        if exists:
            return jsonify({'error': 'Category already exists'}), 409
        
        # Create category
        category = Category(name=name, type=type_, user_id=current_user.id)
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'id': category.id,
            'name': category.name,
            'type': category.type
        }), 201
    
    @app.route('/api/categories')
    @login_required
    def api_categories():
        """API endpoint for categories."""
        type_ = request.args.get('type')
        query = Category.query
        
        if type_ in ('income', 'expense'):
            query = query.filter_by(type=type_)
        
        categories = query.filter(
            (Category.user_id == None) | (Category.user_id == current_user.id)
        ).order_by(Category.type.asc(), Category.name.asc()).all()
        
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'type': c.type,
            'color': c.color,
            'icon': c.icon
        } for c in categories])
    
    # Loan/EMI Routes
    @app.route('/loans')
    @login_required
    def loans_list():
        """List all loans."""
        loans = Loan.query.filter_by(user_id=current_user.id, is_active=True)\
            .order_by(Loan.next_payment_date.asc()).all()
        return render_template('loans/list.html', loans=loans)
    
    @app.route('/loans/add', methods=['GET', 'POST'])
    @login_required
    def loans_add():
        """Add new loan."""
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            loan_type = request.form.get('loan_type', '').strip()
            principal_amount = request.form.get('principal_amount')
            interest_rate = request.form.get('interest_rate')
            emi_amount = request.form.get('emi_amount')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            # Validation
            try:
                principal_val = float(principal_amount)
                interest_val = float(interest_rate)
                emi_val = float(emi_amount)
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                flash('Invalid data provided.', 'danger')
                return render_template('loans/form.html', form_action=url_for('loans_add'))
            
            if not name or not loan_type:
                flash('Name and loan type are required.', 'danger')
                return render_template('loans/form.html', form_action=url_for('loans_add'))
            
            # Create loan
            loan = Loan(
                user_id=current_user.id,
                name=name,
                loan_type=loan_type,
                principal_amount=principal_val,
                remaining_amount=principal_val,
                interest_rate=interest_val,
                emi_amount=emi_val,
                start_date=start_date,
                end_date=end_date,
                next_payment_date=start_date
            )
            
            db.session.add(loan)
            db.session.commit()
            
            flash('Loan added successfully.', 'success')
            return redirect(url_for('loans_list'))
        
        return render_template('loans/form.html', form_action=url_for('loans_add'))
    
    @app.route('/loans/<int:loan_id>/edit', methods=['GET', 'POST'])
    @login_required
    def loans_edit(loan_id):
        """Edit existing loan."""
        loan = Loan.query.filter_by(id=loan_id, user_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            loan.name = request.form.get('name', '').strip()
            loan.loan_type = request.form.get('loan_type', '').strip()
            loan.interest_rate = float(request.form.get('interest_rate'))
            loan.emi_amount = float(request.form.get('emi_amount'))
            loan.remaining_amount = float(request.form.get('remaining_amount'))
            loan.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            loan.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            db.session.commit()
            flash('Loan updated successfully.', 'success')
            return redirect(url_for('loans_list'))
        
        return render_template('loans/form.html', loan=loan, form_action=url_for('loans_edit', loan_id=loan.id))
    
    @app.route('/loans/<int:loan_id>/delete', methods=['POST'])
    @login_required
    def loans_delete(loan_id):
        """Delete loan."""
        loan = Loan.query.filter_by(id=loan_id, user_id=current_user.id).first_or_404()
        loan.is_active = False
        db.session.commit()
        flash('Loan deleted successfully.', 'success')
        return redirect(url_for('loans_list'))
    
    @app.route('/loans/<int:loan_id>/pay_emi', methods=['POST'])
    @login_required
    def loans_pay_emi(loan_id):
        """Process EMI payment and create transaction."""
        loan = Loan.query.filter_by(id=loan_id, user_id=current_user.id).first_or_404()
        
        # Create transaction for EMI payment
        emi_transaction = Transaction(
            user_id=current_user.id,
            amount=loan.emi_amount,
            type='expense',
            description=f'EMI Payment - {loan.name} ({loan.loan_type.title()})',
            date=date.today()
        )
        
        # Update loan details
        loan.remaining_amount = max(0, loan.remaining_amount - loan.emi_amount)
        
        # Update next payment date (add 1 month)
        from dateutil.relativedelta import relativedelta
        loan.next_payment_date = loan.next_payment_date + relativedelta(months=1)
        
        # If loan is fully paid, mark as inactive
        if loan.remaining_amount <= 0:
            loan.is_active = False
            loan.remaining_amount = 0
        
        db.session.add(emi_transaction)
        db.session.commit()
        
        flash(f'EMI payment of ₹{loan.emi_amount:.2f} processed successfully!', 'success')
        return redirect(url_for('loans_list'))
    
    # Insurance Routes
    @app.route('/insurances')
    @login_required
    def insurances_list():
        """List all insurances."""
        insurances = Insurance.query.filter_by(user_id=current_user.id, is_active=True)\
            .order_by(Insurance.next_premium_date.asc()).all()
        return render_template('insurances/list.html', insurances=insurances)
    
    @app.route('/insurances/add', methods=['GET', 'POST'])
    @login_required
    def insurances_add():
        """Add new insurance."""
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            insurance_type = request.form.get('insurance_type', '').strip()
            policy_number = request.form.get('policy_number', '').strip()
            insurance_company = request.form.get('insurance_company', '').strip()
            premium_amount = request.form.get('premium_amount')
            premium_frequency = request.form.get('premium_frequency', '').strip()
            sum_assured = request.form.get('sum_assured')
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            # Validation
            try:
                premium_val = float(premium_amount)
                sum_assured_val = float(sum_assured) if sum_assured else None
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                flash('Invalid data provided.', 'danger')
                return render_template('insurances/form.html', form_action=url_for('insurances_add'))
            
            if not name or not insurance_type or not insurance_company:
                flash('Name, type, and company are required.', 'danger')
                return render_template('insurances/form.html', form_action=url_for('insurances_add'))
            
            # Create insurance
            insurance = Insurance(
                user_id=current_user.id,
                name=name,
                insurance_type=insurance_type,
                policy_number=policy_number,
                insurance_company=insurance_company,
                premium_amount=premium_val,
                premium_frequency=premium_frequency,
                sum_assured=sum_assured_val,
                start_date=start_date,
                end_date=end_date,
                next_premium_date=start_date
            )
            
            db.session.add(insurance)
            db.session.commit()
            
            flash('Insurance added successfully.', 'success')
            return redirect(url_for('insurances_list'))
        
        return render_template('insurances/form.html', form_action=url_for('insurances_add'))
    
    @app.route('/insurances/<int:insurance_id>/edit', methods=['GET', 'POST'])
    @login_required
    def insurances_edit(insurance_id):
        """Edit existing insurance."""
        insurance = Insurance.query.filter_by(id=insurance_id, user_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            insurance.name = request.form.get('name', '').strip()
            insurance.insurance_type = request.form.get('insurance_type', '').strip()
            insurance.policy_number = request.form.get('policy_number', '').strip()
            insurance.insurance_company = request.form.get('insurance_company', '').strip()
            insurance.premium_amount = float(request.form.get('premium_amount'))
            insurance.premium_frequency = request.form.get('premium_frequency', '').strip()
            insurance.sum_assured = float(request.form.get('sum_assured')) if request.form.get('sum_assured') else None
            insurance.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            insurance.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            db.session.commit()
            flash('Insurance updated successfully.', 'success')
            return redirect(url_for('insurances_list'))
        
        return render_template('insurances/form.html', insurance=insurance, form_action=url_for('insurances_edit', insurance_id=insurance.id))
    
    @app.route('/insurances/<int:insurance_id>/delete', methods=['POST'])
    @login_required
    def insurances_delete(insurance_id):
        """Delete insurance."""
        insurance = Insurance.query.filter_by(id=insurance_id, user_id=current_user.id).first_or_404()
        insurance.is_active = False
        db.session.commit()
        flash('Insurance deleted successfully.', 'success')
        return redirect(url_for('insurances_list'))
    
    @app.route('/insurances/<int:insurance_id>/pay_premium', methods=['POST'])
    @login_required
    def insurances_pay_premium(insurance_id):
        """Process insurance premium payment and create transaction."""
        insurance = Insurance.query.filter_by(id=insurance_id, user_id=current_user.id).first_or_404()
        
        # Create transaction for premium payment
        premium_transaction = Transaction(
            user_id=current_user.id,
            amount=insurance.premium_amount,
            type='expense',
            description=f'Insurance Premium - {insurance.name} ({insurance.insurance_type.title()}) - {insurance.insurance_company}',
            date=date.today()
        )
        
        # Update next premium date based on frequency
        from dateutil.relativedelta import relativedelta
        if insurance.premium_frequency == 'monthly':
            insurance.next_premium_date = insurance.next_premium_date + relativedelta(months=1)
        elif insurance.premium_frequency == 'quarterly':
            insurance.next_premium_date = insurance.next_premium_date + relativedelta(months=3)
        elif insurance.premium_frequency == 'yearly':
            insurance.next_premium_date = insurance.next_premium_date + relativedelta(years=1)
        
        # Check if insurance policy has expired
        if insurance.next_premium_date > insurance.end_date:
            insurance.is_active = False
        
        db.session.add(premium_transaction)
        db.session.commit()
        
        flash(f'Premium payment of ₹{insurance.premium_amount:.2f} processed successfully!', 'success')
        return redirect(url_for('insurances_list'))


def get_user_categories(user_id):
    """Get categories for a user, including global ones."""
    global_categories = Category.query.filter_by(user_id=None).all()
    user_categories = Category.query.filter_by(user_id=user_id).all()
    return global_categories + user_categories


# Create the application
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
