# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database initialization
def init_db():
    conn = sqlite3.connect('students.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                grade REAL NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id))''')
    
    conn.commit()
    conn.close()

init_db()

class Student:
    def __init__(self, student_id, name, roll_number):
        self.id = student_id
        self.name = name
        self.roll_number = roll_number
        self.grades = {}
    
    def add_grade(self, subject, grade):
        self.grades[subject] = grade
    
    def calculate_average(self):
        if not self.grades:
            return 0
        return sum(self.grades.values()) / len(self.grades)
    
    def get_details(self):
        return {
            'id': self.id,
            'name': self.name,
            'roll_number': self.roll_number,
            'grades': self.grades,
            'average': round(self.calculate_average(), 2)
        }

class StudentTracker:
    @staticmethod
    def add_student(name, roll_number):
        try:
            conn = sqlite3.connect('students.db')
            c = conn.cursor()
            c.execute("INSERT INTO students (name, roll_number) VALUES (?, ?)", 
                     (name, roll_number))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("Roll number must be unique")
        finally:
            conn.close()
    
    @staticmethod
    def add_grade(student_id, subject, grade):
        if not (0 <= grade <= 100):
            raise ValueError("Grade must be between 0 and 100")
        
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        
        # Update or insert grade
        c.execute('''INSERT OR REPLACE INTO grades (student_id, subject, grade)
                    VALUES (?, ?, ?)''', (student_id, subject, grade))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_student(student_id):
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        
        # Get student info
        c.execute("SELECT id, name, roll_number FROM students WHERE id = ?", (student_id,))
        student_data = c.fetchone()
        if not student_data:
            return None
        
        student = Student(*student_data)
        
        # Get grades
        c.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
        for subject, grade in c.fetchall():
            student.add_grade(subject, grade)
        
        conn.close()
        return student
    
    @staticmethod
    def get_all_students():
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        
        c.execute("SELECT id FROM students")
        student_ids = [row[0] for row in c.fetchall()]
        students = [StudentTracker.get_student(sid) for sid in student_ids]
        
        conn.close()
        return students
    
    @staticmethod
    def get_subject_topper(subject):
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        
        c.execute('''SELECT s.id, s.name, MAX(g.grade) as top_grade
                     FROM students s
                     JOIN grades g ON s.id = g.student_id
                     WHERE g.subject = ?
                     GROUP BY s.id
                     ORDER BY top_grade DESC
                     LIMIT 1''', (subject,))
        result = c.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def get_class_average(subject):
        conn = sqlite3.connect('students.db')
        c = conn.cursor()
        
        c.execute("SELECT AVG(grade) FROM grades WHERE subject = ?", (subject,))
        result = c.fetchone()[0]
        conn.close()
        return round(result, 2) if result else 0
    
    @staticmethod
    def export_to_file():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            students = StudentTracker.get_all_students()
            for student in students:
                f.write(f"ID: {student.id}\n")
                f.write(f"Name: {student.name}\n")
                f.write(f"Roll Number: {student.roll_number}\n")
                f.write("Grades:\n")
                for subject, grade in student.grades.items():
                    f.write(f"  {subject}: {grade}\n")
                f.write(f"Average: {student.calculate_average():.2f}\n")
                f.write("\n")
        return filename

# Web Routes
@app.route('/')
def index():
    students = StudentTracker.get_all_students()
    return render_template('index.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        
        try:
            StudentTracker.add_student(name, roll_number)
            flash('Student added successfully!', 'success')
            return redirect(url_for('index'))
        except ValueError as e:
            flash(str(e), 'error')
    
    return render_template('add_student.html')

@app.route('/add_grade', methods=['GET', 'POST'])
def add_grade():
    students = StudentTracker.get_all_students()
    
    if request.method == 'POST':
        student_id = int(request.form['student_id'])
        subject = request.form['subject']
        try:
            grade = float(request.form['grade'])
            StudentTracker.add_grade(student_id, subject, grade)
            flash('Grade added successfully!', 'success')
            return redirect(url_for('view_student', student_id=student_id))
        except ValueError as e:
            flash(str(e), 'error')
    
    return render_template('add_grade.html', students=students)

@app.route('/student/<int:student_id>')
def view_student(student_id):
    student = StudentTracker.get_student(student_id)
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('index'))
    return render_template('student.html', student=student.get_details())

@app.route('/averages')
def show_averages():
    students = StudentTracker.get_all_students()
    return render_template('averages.html', students=students)

@app.route('/subject_topper', methods=['GET', 'POST'])
def subject_topper():
    subjects = ['Math', 'Science', 'English']
    topper = None
    
    if request.method == 'POST':
        subject = request.form['subject']
        topper = StudentTracker.get_subject_topper(subject)
    
    return render_template('subject_topper.html', 
                          subjects=subjects, 
                          topper=topper)

@app.route('/class_average', methods=['GET', 'POST'])
def class_average():
    subjects = ['Math', 'Science', 'English']
    average = None
    
    if request.method == 'POST':
        subject = request.form['subject']
        average = StudentTracker.get_class_average(subject)
    
    return render_template('class_average.html', 
                          subjects=subjects, 
                          average=average)

@app.route('/export')
def export_data():
    try:
        filename = StudentTracker.export_to_file()
        flash(f'Data exported to {filename}', 'success')
    except Exception as e:
        flash(f'Error exporting data: {str(e)}', 'error')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)