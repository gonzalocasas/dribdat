# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import (Blueprint, request, render_template, flash, url_for,
                   redirect, session, current_app, jsonify)
from flask_login import login_required, current_user

from dribdat.user.models import User, Event, Project, Activity
from dribdat.public.forms import LoginForm, UserForm
from dribdat.database import db
from dribdat.extensions import cache
from dribdat.aggregation import GetEventUsers
from dribdat.user import getProjectStages, isUserActive

from datetime import datetime

blueprint = Blueprint('public', __name__, static_folder="../static")


def current_event(): return Event.current()


# Renders a static dashboard
@blueprint.route("/dashboard/")
def dashboard():
    event = current_event()
    if not event:
        return 'No current event'
    wall = 'twitter.com' in event.community_url
    return render_template("public/dashboard.html", current_event=event, with_social_wall=wall)

# Outputs JSON-LD about the current event (see also api.py/info_event_hackathon_json)


@blueprint.route('/hackathon.json')
def info_current_hackathon_json():
    event = Event.query.filter_by(is_current=True).first(
    ) or Event.query.order_by(Event.id.desc()).first()
    return jsonify(event.get_schema(request.host_url))

# Renders a simple about page


@blueprint.route("/about/")
def about():
    return render_template("public/about.html", current_event=current_event())

# Favicon just points to a file


@blueprint.route("/favicon.ico")
def favicon():
    return redirect(url_for('static', filename='img/favicon.ico'))

# Home page


@blueprint.route("/")
def home():
    cur_event = current_event()
    if cur_event is not None:
        events = Event.query.filter(Event.id != cur_event.id)
    else:
        events = Event.query
    events = events.filter(Event.is_hidden.isnot(True))
    timed_events = events.filter(Event.lock_resources.isnot(True))
    today = datetime.utcnow()
    events_next = timed_events.filter(Event.starts_at > today)
    events_past = timed_events.filter(Event.ends_at < today)
    resource_events = events.filter(Event.lock_resources)
    return render_template(
        "public/home.html",
        events_next=events_next.order_by(Event.starts_at.asc()).all(),
        events_past=events_past.order_by(Event.starts_at.desc()).all(),
        events_tips=resource_events.order_by(Event.name.asc()).all(),
        current_event=cur_event
    )


@blueprint.route('/user/<username>', methods=['GET'])
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    if not isUserActive(user):
        # return "User deactivated. Please contact an event organizer."
        flash('This user account is under review. Please contact the organizing team if you have any questions.', 'warning')
    event = current_event()
    cert_path = user.get_cert_path(event)
    submissions = user.posted_challenges()
    projects = user.joined_projects(False)
    posts = user.latest_posts()
    return render_template("public/userprofile.html", active="profile",
                           current_event=event, event=event, user=user, cert_path=cert_path,
                           projects=projects, submissions=submissions, posts=posts)


@blueprint.route("/event/<int:event_id>")
def event(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    projects = Project.query.filter_by(event_id=event_id, is_hidden=False)
    if request.args.get('embed'):
        return render_template("public/embed.html", current_event=event, projects=projects)
    summaries = [p.data for p in projects]
    # Sort projects by reverse score, then name
    summaries.sort(key=lambda x: (
        -x['score'] if isinstance(x['score'], int) else 0,
        x['name'].lower()))
    project_count = projects.count()
    return render_template("public/event.html", current_event=event,
                           projects=summaries, project_count=project_count, active="projects")


@blueprint.route("/event/<int:event_id>/participants")
def event_participants(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    users = GetEventUsers(event)
    usercount = len(users) if users else 0
    return render_template("public/eventusers.html",
                           current_event=event, participants=users, usercount=usercount, active="participants")


@blueprint.route("/event/<int:event_id>/stages")
def event_stages(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    steps = getProjectStages()
    return render_template("public/stages.html",
                           current_event=event, steps=steps, active="stages")


@blueprint.route("/event/<int:event_id>/instruction")
def event_instruction(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    steps = getProjectStages()
    for s in steps:
        s['projects'] = []  # Reset the index
    resource_events = Event.query.filter_by(lock_resources=True).all()
    for e in resource_events:
        projects = Project.query.filter_by(event_id=e.id, is_hidden=False)
        for s in steps:
            if not 'projects' in s:
                s['projects'] = []
            project_list = [p.data for p in projects.filter_by(
                progress=s['id']).all()]
            s['projects'].extend(project_list)
    return render_template("public/instruction.html",
                           current_event=event, steps=steps, active="instruction")


@blueprint.route('/event/<int:event_id>/print')
def event_print(event_id):
    now = datetime.utcnow().strftime("%d.%m.%Y %H:%M")
    event = Event.query.filter_by(id=event_id).first_or_404()
    projects = Project.query.filter_by(event_id=event_id, is_hidden=False)
    projects = projects.filter(Project.progress >= 0).order_by(Project.name)
    return render_template('public/eventprint.html',
                           current_event=event, projects=projects, curdate=now, active='print')


@blueprint.route("/dribs")
def dribs():
    """ Shows the latest logged posts """
    page = request.args.get('page') or 1
    per_page = request.args.get('limit') or 10
    dribs = Activity.query.filter(Activity.action == "post")
    dribs = dribs.order_by(Activity.id.desc())
    dribs = dribs.paginate(int(page), int(per_page))
    return render_template("public/dribs.html",
                           endpoint='public.dribs', active='dribs',
                           current_event=current_event(), data=dribs)
