{
    'name': 'HMS',
    'version': '1.0',
    'summary': 'Hospital Management System',
    'description': """
        A comprehensive module to manage hospital operations including patient records,
        doctor schedules, appointments, and medical history.
    """,
    'author': 'Youssef Mundia',
    'website': 'https://www.example.com',
    'category': 'Services/Healthcare',
    'depends': ['base', 'mail', 'contacts'], # contacts pour res.partner (compagnies d'assurance)
    'data': [
        'security/hms_security.xml',
        'security/ir.model.access.csv',
        'data/hms_data.xml',
        'data/hms_day_of_week_data.xml', # Ajoutez cette ligne
        'views/hms_patient_views.xml',
        'views/hms_doctor_views.xml',
        'views/hms_appointment_views.xml',
        'views/hms_medical_record_views.xml',
        'views/hms_department_views.xml',
        'views/hms_patient_insurance_views.xml',
        'views/hms_menus.xml',
        'demo/hms_demo.xml',
    ],
    'demo': [
        # Les données de démo sont déjà listées dans 'data' si vous les chargez toujours.
        # Sinon, déplacez 'demo/hms_demo.xml' ici.
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}