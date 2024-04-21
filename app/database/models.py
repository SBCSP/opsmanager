# database/models.py

from .connection import db
from datetime import datetime


class Playbooks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    content = db.Column(db.Text, nullable=False)
    sudo_required = db.Column(db.Boolean, default=False, nullable=False)
    results = db.relationship('PlaybookResults', backref='playbook', lazy='dynamic')

    def __repr__(self):
        return f'<Playbook {self.name}>'

class PlaybookResults(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playbook_id = db.Column(db.Integer, db.ForeignKey('playbooks.id'), nullable=False)
    result_data = db.Column(db.Text, nullable=False)
    date_executed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<PlaybookResults {self.id} for Playbook {self.playbook_id}>'
    
# New model for container images
class ContainerImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_name = db.Column(db.String(255), nullable=False, unique=True)
    running_apps = db.relationship('RunningApps', backref='container_image', lazy='dynamic')

    def __repr__(self):
        return f'<ContainerImage {self.image_name}>'

# New model for running applications
class RunningApps(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    container_image_id = db.Column(db.Integer, db.ForeignKey('container_images.id'), nullable=False)
    container_id = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    date_launched = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<RunningApp {self.container_id} using Image {self.container_image_id}>'