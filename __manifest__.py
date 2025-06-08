{
    'name': 'Hospital Management System',
    'version': '17.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Simple Hospital Management System for Odoo 17',
    'description': '''
        A comprehensive Hospital Management System that includes:
        - Patient Management
        - Doctor Management
        - Appointment Scheduling
        - Medical Records
        - Department Management
    ''',
    'author': 'Your Name',
    'website': 'https://www.yourwebsite.com',
    'depends': ['base', 'mail', 'contacts'],
    'data': [
        'security/hms_security.xml',
        'security/ir.model.access.csv',
        'data/hms_data.xml',
        'views/hms_patient_views.xml',
        'views/hms_doctor_views.xml',
        'views/hms_appointment_views.xml',
        'views/hms_medical_record_views.xml',
        'views/hms_department_views.xml',
        'views/hms_menus.xml',
    ],
    'demo': [
        'demo/hms_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}