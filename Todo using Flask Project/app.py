from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///todo_new.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-secret-key-here'  # Required for flash messages
db = SQLAlchemy(app)

class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    desc = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High
    status = db.Column(db.String(20), default='Pending')   # Pending, In Progress, Completed
    category = db.Column(db.String(50), nullable=True)

    def __repr__(self) -> str:
        return f"{self.sno} - {self.title}"

    def to_dict(self):
        return {
            'sno': self.sno,
            'title': self.title,
            'desc': self.desc,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'due_date': self.due_date.strftime('%Y-%m-%d %H:%M:%S') if self.due_date else None,
            'priority': self.priority,
            'status': self.status,
            'category': self.category
        }

@app.route('/', methods=['GET', 'POST'])
def hello():
    if request.method == 'POST':
        title = request.form['titles']
        desc = request.form['descriptions']
        due_date = request.form.get('due_date')
        priority = request.form.get('priority', 'Medium')
        category = request.form.get('category')
        
        todo = Todo(
            title=title,
            desc=desc,
            priority=priority,
            category=category
        )
        
        if due_date:
            todo.due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')

        db.session.add(todo)
        db.session.commit()
        flash('Todo added successfully!', 'success')
        return redirect(url_for('hello'))

    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')
    category_filter = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'created_at')
    search_query = request.args.get('search', '')

    # Base query
    query = Todo.query

    # Apply filters
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    if search_query:
        query = query.filter(Todo.title.ilike(f'%{search_query}%') | Todo.desc.ilike(f'%{search_query}%'))

    # Apply sorting
    if sort_by == 'due_date':
        query = query.order_by(Todo.due_date.asc())
    elif sort_by == 'priority':
        priority_order = {'High': 1, 'Medium': 2, 'Low': 3}
        query = query.order_by(Todo.priority.asc())
    else:  # default sort by created_at
        query = query.order_by(Todo.created_at.desc())

    AllTodoData = query.all()
    
    # Get unique categories for filter dropdown
    categories = db.session.query(Todo.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]  # Remove None values

    return render_template('home.html', 
                         AllTodo=AllTodoData,
                         categories=categories,
                         current_status=status_filter,
                         current_priority=priority_filter,
                         current_category=category_filter,
                         current_sort=sort_by,
                         search_query=search_query)

@app.route('/update/<int:sno>', methods=['GET', 'POST'])
def update(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    
    if request.method == 'POST':
        todo.title = request.form['title_changed']
        todo.desc = request.form['description_changed']
        todo.priority = request.form.get('priority', 'Medium')
        todo.status = request.form.get('status', 'Pending')
        todo.category = request.form.get('category')
        
        due_date = request.form.get('due_date')
        if due_date:
            todo.due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
        else:
            todo.due_date = None

        db.session.commit()
        flash('Todo updated successfully!', 'success')
        return redirect(url_for('hello'))

    return render_template('update.html', 
                         todo=todo,
                         categories=db.session.query(Todo.category).distinct().all())

@app.route('/delete/<int:sno>')
def delete(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    db.session.delete(todo)
    db.session.commit()
    flash('Todo deleted successfully!', 'success')
    return redirect(url_for('hello'))

@app.route('/update_status/<int:sno>', methods=['POST'])
def update_status(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    new_status = request.json.get('status')
    if new_status in ['Pending', 'In Progress', 'Completed']:
        todo.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/get_stats')
def get_stats():
    total = Todo.query.count()
    completed = Todo.query.filter_by(status='Completed').count()
    pending = Todo.query.filter_by(status='Pending').count()
    in_progress = Todo.query.filter_by(status='In Progress').count()
    
    return jsonify({
        'total': total,
        'completed': completed,
        'pending': pending,
        'in_progress': in_progress
    })

if __name__ == '__main__':
    with app.app_context():
        # Check if database exists
        db_exists = os.path.exists('instance/todo.db')
        
        # Create all tables
        db.create_all()
        
        # If database didn't exist before, add some sample data
        if not db_exists:
            sample_todos = [
                Todo(
                    title="Welcome to Todo App",
                    desc="This is a sample todo. You can edit or delete it.",
                    priority="Medium",
                    status="Pending",
                    category="General"
                ),
                Todo(
                    title="Learn Flask",
                    desc="Study Flask framework and its features",
                    priority="High",
                    status="In Progress",
                    category="Learning"
                )
            ]
            db.session.add_all(sample_todos)
            db.session.commit()
    
    app.run(debug=True)