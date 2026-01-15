CREATE TABLE IF NOT EXISTS claim_rules (
    id INTEGER PRIMARY KEY,
    claim_type TEXT NOT NULL UNIQUE,
    required_fields TEXT NOT NULL,
    min_amount REAL,
    description TEXT
);

INSERT OR IGNORE INTO claim_rules (claim_type, required_fields, min_amount, description) VALUES 
('medical', '["patient_name", "diagnosis_code", "hospital_name"]', 50.00, 'Standard hospital admission form. Must contain patient details and diagnosis.'),
('dental', '["patient_name", "dentist_name", "procedure_code"]', 20.00, 'Dental procedure claim form.'),
('vision', '["patient_name", "optometrist_name", "prescription_date"]', 30.00, 'Vision care and glasses prescription form.');
