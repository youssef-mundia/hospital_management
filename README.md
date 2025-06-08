# Hospital Management System (HMS) for Odoo 17

A comprehensive Hospital Management System module for Odoo 17 that provides essential healthcare management functionality.

## Features

### Patient Management
- Complete patient registration with personal and contact information
- Medical history and allergy tracking
- Emergency contact information
- Blood group and vital statistics
- Age calculation from date of birth

### Doctor Management
- Doctor profiles with specialization and qualifications
- Department assignment
- License number tracking
- Consultation fee management
- Experience tracking

### Appointment Scheduling
- Appointment booking system
- Calendar view for better visualization
- Appointment status tracking (Draft, Confirmed, In Progress, Completed, Cancelled)
- Duration and time slot management

### Medical Records
- Comprehensive medical record keeping
- Vital signs tracking (temperature, blood pressure, heart rate, weight, height)
- Diagnosis and treatment documentation
- Prescription management
- Follow-up scheduling

### Department Management
- Hospital department organization
- Department head assignment
- Doctor assignment to departments

## Installation

1. Copy the module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "Hospital Management System" module

## Security Groups

The module includes three security groups:
- **HMS User**: Basic access to view and create records
- **HMS Doctor**: Doctor-level access with medical record management
- **HMS Manager**: Full administrative access

## Usage

### Getting Started

1. **Setup Departments**: Create hospital departments (Configuration > Departments)
2. **Add Doctors**: Register doctors and assign them to departments
3. **Register Patients**: Add patient information
4. **Schedule Appointments**: Book appointments between patients and doctors
5. **Maintain Records**: Create and manage medical records

### Workflow

1. Patient registration
2. Appointment scheduling
3. Appointment confirmation
4. Medical consultation
5. Medical record creation
6. Follow-up scheduling (if required)

## Technical Details

### Models

- `hms.patient`: Patient information and medical history
- `hms.doctor`: Doctor profiles and professional information
- `hms.appointment`: Appointment scheduling and management
- `hms.medical.record`: Medical records and treatment documentation
- `hms.department`: Hospital department organization

### Key Features

- Automatic sequence generation for patient IDs, doctor IDs, appointments, and medical records
- Age calculation based on date of birth
- Appointment duration and end time calculation
- Mail tracking and activity management
- Comprehensive search and filtering options

## Demo Data

The module includes demo data with:
- Sample departments (Cardiology, Orthopedics)
- Demo doctors
- Sample patients

## Customization

The module is designed to be easily extensible. You can:
- Add new fields to existing models
- Create additional views
- Implement custom business logic
- Add reporting functionality

## Support

For support and customization requests, please contact the module author.

## License

This module is licensed under LGPL-3.