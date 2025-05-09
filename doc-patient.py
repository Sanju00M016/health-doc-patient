from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime
import os
import requests

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://doctor:doctor@localhost:5432/doctors'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class DoctorPatient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.String(10), nullable=False)
    patient_id = db.Column(db.String(10), nullable=False)
    assigned_date = db.Column(db.DateTime, default=db.func.now())


PATIENT_SERVICE_URL = "http://127.0.0.1:5001"
DOCTOR_SERVICE_URL = "http://127.0.0.1:5002"

@app.route('/v1/assign', methods=['POST'])
def assign_patient_to_doctor():
    try:
        data = request.json
        doctor_id = data.get('doctor_id')
        patient_id = data.get('patient_id')

        # Validate id with Doctor Service
        doctor_response = requests.get(f"{DOCTOR_SERVICE_URL}/v1/doctors/{doctor_id}")
        if doctor_response.status_code != 200:
            return jsonify({'error': f'Doctor with ID {doctor_id} not found'}), 404

        # Validate id with Patient Service
        patient_response = requests.get(f"{PATIENT_SERVICE_URL}/v1/patients/{patient_id}")
        if patient_response.status_code != 200:
            return jsonify({'error': f'Patient with ID {patient_id} not found'}), 404

        # Create the relationship in the database
        relationship = DoctorPatient.query.filter_by(doctor_id=doctor_id, patient_id=patient_id).first()
        if relationship:
            return jsonify({'message': 'Patient is already assigned to this doctor'}), 409

        new_relationship = DoctorPatient(doctor_id=doctor_id, patient_id=patient_id)
        db.session.add(new_relationship)
        db.session.commit()

        return jsonify({'message': f'Patient {patient_id} assigned to Doctor {doctor_id}'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/v1/doctor/<string:id>/patients', methods=['GET'])
def get_patients_of_doctor(id):
    try:
        # Get all patient IDs assigned to the doctor
        assignments = DoctorPatient.query.filter_by(doctor_id=id).all()
        if not assignments:
            return jsonify({'message': f'No patients found for Doctor {id}'}), 404

        # Collect patient IDs
        patient_ids = [assignment.id for assignment in assignments]

        # Fetch detailed patient information
        patients_data = []
        for id in patient_ids:
            response = requests.get(f"{PATIENT_SERVICE_URL}/v1/patients/{id}")
            if response.status_code == 200:
                patients_data.append(response.json()) 
            else:
                patients_data.append({'patient_id': id, 'error': 'Details not found'})

        return jsonify({'doctor_id': id, 'patients': patients_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

if __name__ == '__main__':
    app.run(debug=True)