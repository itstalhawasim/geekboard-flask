#----------------------------------------------------------------------------#
# Name        : GeekBoard - Job board for developers!
# Description : GeekBoard is a Flask based web application, it was a Minor 
#               Project I did in my 3rd Semester of B.Tech CSE
# Author      : Talha Wasim (@itstalhawasim)
#
# This work is licensed under the terms of the MIT license.  
# For a copy, see <https://opensource.org/licenses/MIT>.
#----------------------------------------------------------------------------#

# Imports
from flask import Flask, render_template, url_for, flash, redirect, request, session, logging
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from wtforms import Form, StringField, TextAreaField, PasswordField, SelectField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import datetime

mail = Mail()
app = Flask(__name__)

mail_from_address = "" #Default email address for sending emails.

# App Configurations
app.secret_key = "o83mvrcbqwj0l0gt2bpf25zklqbzfo" #Change this to something else.
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "geekboard"
app.config["MYSQL_UNIX_SOCKET"] = "/opt/lampp/var/mysql/mysql.sock"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USE_SSL"] = True
app.config["MAIL_USERNAME"] = '' #SMTP Username
app.config["MAIL_PASSWORD"] = '' #SMTP Password
app.config["MAIL_DEFAULT_SENDER"] = mail_from_address

mysql = MySQL(app)
mail.init_app(app)

# Home Page
@app.route("/")
def home():
	cur = mysql.connection.cursor()

	results = cur.execute("SELECT * FROM job_details")
	jobs_posted = cur.rowcount
	jobs = cur.fetchall()

	applications_result = cur.execute("SELECT * FROM job_applications")
	applications_received = cur.rowcount

	hired_result = cur.execute("SELECT * FROM job_applications WHERE status='Hired'")
	people_hired = cur.rowcount

	title = 'Job board for developers!'

	if results > 0:
		return render_template('home.html', 
			jobs=jobs, 
			jobs_posted=jobs_posted, 
			applications_received=applications_received, 
			people_hired=people_hired, 
			title=title
		)
	else:
		msg = 'No jobs found, please check back later!'
		return render_template('home.html', 
			msg=msg, 
			title=title
		)

def check_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Please login first!', 'danger')
			return redirect(url_for('login'))
	return wrap
	
# Registration Page
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=100)])
	email = StringField('Email', [validators.Length(min=6, max=100), validators.Email()])
	password = StringField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

@app.route("/register", methods=['GET' , 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		password = sha256_crypt.encrypt(str(form.password.data))
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO auth_users(full_name, email, password) VALUES(%s, %s, %s)", [name, email, password])
		mysql.connection.commit()
		cur.close()
		flash('You are registered, please login now.', 'success')
		return redirect(url_for('login'))
	return render_template('register.html', form=form, title='Register')

# Login Page
@app.route("/login", methods=['GET' , 'POST'])
def login():
	if request.method == 'POST':
		email = request.form['email']
		password_given = request.form['password']
		cur = mysql.connection.cursor()
		result = cur.execute("SELECT * FROM auth_users WHERE email = %s", [email])
		if result > 0:
			data = cur.fetchone()
			password = data['password']
			full_name = data['full_name']
			if sha256_crypt.verify(password_given, password):
				session['logged_in'] = True
				session['email'] = email
				session['full_name'] = full_name
				return redirect(url_for('home'))
			else:
				flash('Email or password is incorrect.', 'danger')
				return redirect(url_for('login'))
			cur.close()
		else: 
			flash('Email or password is incorrect.', 'danger')
			return redirect(url_for('login'))
	return render_template('login.html', title='Login')

# Logout
@app.route("/logout")
@check_logged_in
def logout():
	session.clear()
	flash('You have successfully logged out.', 'success')
	return redirect(url_for('login'))

# Add Job Page
class JobForm(Form):
	title = StringField('Job Title', [validators.Length(min=1, max=200)])
	company = StringField('Company', [validators.Length(min=1, max=200)])
	details = TextAreaField('Job Description', [validators.Length(min=50)])
	coding_task = TextAreaField('Coding Task', [validators.Length(min=50)])
	location = StringField('Job Location', [validators.Length(min=1, max=200)])

@app.route("/add_job", methods=['GET' , 'POST'])
@check_logged_in
def add_job():
	form = JobForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		company = form.company.data
		details = form.details.data
		coding_task = form.coding_task.data
		location = form.location.data
		posted_by = session['email']
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO job_details(title, details, company, coding_task, location, posted_by) VALUES(%s, %s, %s, %s, %s, %s)", [title, details, company, coding_task, location, posted_by])
		mysql.connection.commit()
		cur.close()
		flash('Job was successfully posted.', 'success')
		return redirect(url_for('manage_jobs'))
	return render_template('add_job.html', form=form, title='Add Job')

# Edit Job Page
@app.route("/edit_job/<string:id>", methods=['GET' , 'POST'])
@check_logged_in
def edit_job(id):
	cur = mysql.connection.cursor()
	cur.execute("SELECT * FROM job_details WHERE id=%s", [id])
	job = cur.fetchone()
	form = JobForm(request.form)
	form.title.data = job['title']
	form.company.data = job['company']
	form.details.data = job['details']
	form.coding_task.data = job['coding_task']
	form.location.data = job['location']
	if request.method == 'POST' and form.validate():
		title = request.form['title']
		company = request.form['company']
		details = request.form['details']
		coding_task = request.form['coding_task']
		location = request.form['location']
		posted_by = session['email']
		cur1 = mysql.connection.cursor()
		cur1.execute("UPDATE job_details SET title=%s, company=%s, details=%s, location=%s, coding_task=%s WHERE id=%s AND posted_by=%s", [title, company, details, location, coding_task, id, posted_by])
		mysql.connection.commit()
		cur1.close()
		flash('Job was successfully edited.', 'success')
		return redirect(url_for('manage_jobs'))
	return render_template('edit_job.html', form=form, title='Edit Job')

# Delete Job
@app.route("/delete_job/<string:id>", methods=['POST'])
@check_logged_in
def delete_job(id):
	if request.method == 'POST':
		posted_by = session['email']
		cur = mysql.connection.cursor()
		cur.execute("DELETE FROM job_details WHERE id=%s AND posted_by=%s", [id, posted_by])
		mysql.connection.commit()
		cur.close()
		flash('Job was successfully deleted.', 'success')
		return redirect(url_for('manage_jobs'))
	return render_template('manage_jobs.html', title='Manage Job')

# Manage Jobs Page
@app.route("/manage_jobs")
@check_logged_in
def manage_jobs():
	cur = mysql.connection.cursor()
	results = cur.execute("SELECT * FROM job_details WHERE posted_by=%s", [session['email']])
	jobs = cur.fetchall()
	if results > 0:
		return render_template('manage_jobs.html', jobs=jobs, title='Manage Jobs')
	else:
		return render_template('manage_jobs.html', title='Manage Jobs')

# Manage Applications Page
@app.route("/manage_applications")
@check_logged_in
def manage_applications():
	cur = mysql.connection.cursor()
	results = cur.execute("SELECT job_applications.id, job_applications.job_id, job_details.title, job_applications.applied_on, job_applications.full_name, job_applications.email, job_applications.phone, job_applications.coding_task_solution, job_applications.cover_letter, job_applications.status FROM job_applications INNER JOIN job_details ON job_details.id=job_applications.job_id WHERE posted_by=%s", [session['email']])
	applications = cur.fetchall()
	if results > 0:
		return render_template('manage_applications.html', applications=applications, title='Manage Applications')
	else:
		return render_template('manage_applications.html', title='Manage Jobs')

class ProceedForm(Form):
	application_status = SelectField(u'Application Status', [validators.Optional()], choices=[
		('Rejected', 'Rejected'), 
		('Applied', 'Applied'), 
		('Screening', 'Screening'), 
		('Interview', 'Interview'), 
		('Hired', 'Hired')
	])
	message = TextAreaField(u'Message', [validators.Optional()])

# Application Details Page
@app.route("/applications/<string:id>", methods=['GET' , 'POST'])
@check_logged_in
def applications(id):
	cur = mysql.connection.cursor()
	results = cur.execute("SELECT * FROM job_applications WHERE id=%s", [id])
	if results <= 0:
		msg = 'Application not found'
		return render_template('applications.html', form=False, application=False, job_title=False, title=msg)
	application = cur.fetchone()
	cur1 = mysql.connection.cursor()
	results1 = cur1.execute("SELECT * FROM job_details WHERE id=%s", [application['job_id']])
	job = cur1.fetchone()
	job_title = job['title']
	msg = application['full_name'].title() + "'s Application"
	form = ProceedForm(request.form)
	form.application_status.data = application['status']
	form.message.data = application['message']
	if request.method == 'POST' and form.validate():
		application_status = request.form['application_status']
		message = request.form['message']
		cur1 = mysql.connection.cursor()
		cur1.execute("UPDATE job_applications SET status=%s, message=%s WHERE id=%s", [application_status, message,id])
		mysql.connection.commit()
		cur1.close()
		msg = Message("Update on your application for " + job['title'] + " at " + job['company'],
                  recipients = [application['email']])
		msg.html = message + " <br><hr><center><p>Powered by GeekBoard, a project by Talha Wasim.</p></center></br>"
		mail.send(msg)
		return redirect(url_for('manage_applications'))
	return render_template('applications.html', form=form, application=application, job_title=job_title, title=msg)

# Job Details Page
class ApplicationForm(Form):
	full_name = StringField('Full Name', [validators.Length(min=1, max=200)])
	email = StringField('Email Address', [validators.Length(min=1, max=200), validators.Email()])
	phone = StringField('Phone Number', [validators.Length(min=10, max=30)])
	cover_letter = TextAreaField('Cover Letter', [validators.Length(min=50)])
	coding_task_solution = TextAreaField('Coding Task Solution', [validators.Length(min=10)])

@app.route("/jobs/<string:id>", methods=['GET' , 'POST'])
def job(id):
	form = ApplicationForm(request.form)
	if request.method == 'POST' and form.validate():
		full_name = form.full_name.data
		email = form.email.data
		phone = form.phone.data
		coding_task_solution = form.coding_task_solution.data
		cover_letter = form.cover_letter.data
		job_id = request.form['job_id']
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO job_applications(job_id, full_name, email, phone, coding_task_solution, cover_letter, status) VALUES(%s, %s, %s, %s, %s, %s, 'Applied')", [job_id, full_name, email, phone, coding_task_solution, cover_letter])
		mysql.connection.commit()
		cur.close()
		flash('Your application was successfully submitted.', 'success')
		return redirect('/jobs/'+job_id)
	cur = mysql.connection.cursor()
	results = cur.execute("SELECT * FROM job_details WHERE id=%s",[id])
	job = cur.fetchone()
	if results > 0:
		msg = job['title'] + " at " + job['company']
	else:
		msg = 'Job not found'
	return render_template('job.html', form=form, job=job, title=msg)

# Delete Application
@app.route("/delete_application/<string:id>", methods=['POST'])
@check_logged_in
def delete_application(id):
	if request.method == 'POST':
		cur = mysql.connection.cursor()
		cur.execute("DELETE FROM job_applications WHERE id=%s", [id])
		mysql.connection.commit()
		cur.close()
		flash('Application was successfully deleted.', 'success')
		return redirect(url_for('manage_applications'))
	return render_template('manage_applications.html', title='Manage Applications')

# About us Page
@app.route("/about")
def about():
    return render_template('about.html', title='About Us')

# Contact us Page
@app.route("/contact", methods=['GET' , 'POST'])
def contact():
	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		query = request.form['query']
		msg = Message("Message from " + name + " (" + email  + ")",
                  recipients=[mail_from_address])
		msg.body = query
		mail.send(msg)
	return render_template('contact.html', title='Contact Us')

if __name__ == '__main__':
	app.run(debug=True)