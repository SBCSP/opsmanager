# database/models.py

from .connection import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import BYTEA


class InventoryConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

    date_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<InventoryConfig {self.id} updated on {self.date_updated}>'
    
class HostStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.String(50), nullable=False)
    last_checked = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<HostStatus {self.hostname} {self.status}>'

class AppConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<AppConfig {self.key}={self.value}>'

class Playbooks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    content = db.Column(db.Text, nullable=False)
    sudo_required = db.Column(db.Boolean, default=False, nullable=False)
    results = db.relationship('PlaybookResults', backref='playbook', lazy='dynamic')
    author = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Playbook {self.name}>'

class PlaybookResults(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playbook_id = db.Column(db.Integer, db.ForeignKey('playbooks.id'), nullable=False)
    result_data = db.Column(db.Text, nullable=False)
    date_executed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<PlaybookResults {self.id} for Playbook {self.playbook_id}>'

    
class ContainerImages(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(255), nullable=False)
    image_name = db.Column(db.String(255), nullable=False, unique=True)
    running_apps = db.relationship('RunningApps', backref='container_image', lazy='dynamic')
    dport = db.Column(db.Integer, nullable=True)  # New field for the default port

    def __repr__(self):
        return f'<ContainerImage {self.image_name}>'

class RunningApps(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    container_image_id = db.Column(db.Integer, db.ForeignKey('container_images.id'), nullable=False)
    container_id = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    date_launched = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    port = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f'<RunningApp {self.container_id} using Image {self.container_image_id}>'
    
class Vault(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False, unique=True)
    file_size = db.Column(db.Integer, nullable=False)  # size in bytes
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    password = db.Column(db.String(255), nullable=True)  # Optional password field

    def __repr__(self):
        return f'<Vault {self.filename}>'
    
class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
    profile_pic = db.Column(BYTEA, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Profile {self.email}>'
    

class Dockerfiles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    content = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Dockerfile {self.name}>'
    

class HTTPCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<HTTPCheck {self.url}>'