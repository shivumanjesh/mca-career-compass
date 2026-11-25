export type ActiveStatus = "active" | "inactive";
export type AssignmentType = "mentor" | "hod" | "faculty" | "coordinator";

export interface ProgrammeRecord {
  id: string;
  code: string;
  name: string;
  level: string;
  status: ActiveStatus;
  created_at: string;
  updated_at: string;
}

export interface AcademicYearRecord {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: ActiveStatus;
  created_at: string;
  updated_at: string;
}

export interface CohortRecord {
  id: string;
  programme_id: string;
  programme_code: string;
  programme_name: string;
  academic_year_id: string;
  academic_year_name: string;
  batch_name: string;
  semester: number;
  section: string;
  status: ActiveStatus;
  student_count: number;
  created_at: string;
  updated_at: string;
}

export interface StudentRecord {
  id: string;
  membership_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  registration_no: string;
  cohort_id: string | null;
  cohort_label: string | null;
  programme_code: string | null;
  batch_name: string | null;
  semester: number | null;
  section: string | null;
  admission_year: number | null;
  phone: string;
  status: ActiveStatus;
  created_at: string;
  updated_at: string;
  onboarding_reset_path?: string;
}

export interface FacultyCohortAssignment {
  id: string;
  cohort_id: string;
  cohort_label: string;
  programme_code: string;
  batch_name: string;
  semester: number;
  section: string;
  assignment_type: AssignmentType;
  created_at: string;
}

export interface FacultyRecord {
  id: string;
  membership_id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  employee_code: string | null;
  department: string;
  designation: string;
  status: ActiveStatus;
  cohort_assignments: FacultyCohortAssignment[];
  created_at: string;
  updated_at: string;
  onboarding_reset_path?: string;
}

