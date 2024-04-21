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