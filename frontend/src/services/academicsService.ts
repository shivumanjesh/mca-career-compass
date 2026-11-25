import { apiClient } from "./apiClient";
import { ensureCsrfCookie } from "./authService";
import type { PaginatedResponse } from "../types/api";
import type {
  AcademicYearRecord,
  ActiveStatus,
  AssignmentType,
  CohortRecord,
  FacultyCohortAssignment,
  FacultyRecord,
  ProgrammeRecord,
  StudentRecord,
} from "../types/academics";

// Programmes
export async function listProgrammes(params?: {
  page?: number;
  search?: string;
  status?: string;
}): Promise<PaginatedResponse<ProgrammeRecord>> {
  const res = await apiClient.get<PaginatedResponse<ProgrammeRecord>>("/academics/programmes/", { params });
  return res.data;
}

export async function createProgramme(payload: {
  code: string;
  name: string;
  level: string;
  status: ActiveStatus;
}): Promise<ProgrammeRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<ProgrammeRecord>("/academics/programmes/", payload);
  return res.data;
}

export async function updateProgramme(
  id: string,
  payload: Partial<{ code: string; name: string; level: string; status: ActiveStatus }>,
): Promise<ProgrammeRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<ProgrammeRecord>(`/academics/programmes/${id}/`, payload);
  return res.data;
}

// Academic Years
export async function listAcademicYears(params?: {
  page?: number;
  status?: string;
}): Promise<PaginatedResponse<AcademicYearRecord>> {
  const res = await apiClient.get<PaginatedResponse<AcademicYearRecord>>("/academics/academic-years/", { params });
  return res.data;
}

export async function createAcademicYear(payload: {
  name: string;
  start_date: string;
  end_date: string;
  status: ActiveStatus;
}): Promise<AcademicYearRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<AcademicYearRecord>("/academics/academic-years/", payload);
  return res.data;
}

export async function updateAcademicYear(
  id: string,
  payload: Partial<{ name: string; start_date: string; end_date: string; status: ActiveStatus }>,
): Promise<AcademicYearRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<AcademicYearRecord>(`/academics/academic-years/${id}/`, payload);
  return res.data;
}

// Cohorts
export async function listCohorts(params?: {
  page?: number;
  search?: string;
  programme_id?: string;
  status?: string;
}): Promise<PaginatedResponse<CohortRecord>> {
  const res = await apiClient.get<PaginatedResponse<CohortRecord>>("/academics/cohorts/", { params });
  return res.data;
}

export async function createCohort(payload: {
  programme_id: string;
  academic_year_id: string;
  batch_name: string;
  semester: number;
  section: string;
  status: ActiveStatus;
}): Promise<CohortRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<CohortRecord>("/academics/cohorts/", payload);
  return res.data;
}

export async function updateCohort(
  id: string,
  payload: Partial<{
    programme_id: string;
    academic_year_id: string;
    batch_name: string;
    semester: number;
    section: string;
    status: ActiveStatus;
  }>,
): Promise<CohortRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<CohortRecord>(`/academics/cohorts/${id}/`, payload);
  return res.data;
}

// Students
export async function listStudents(params?: {
  page?: number;
  search?: string;
  cohort_id?: string;
  status?: string;
}): Promise<PaginatedResponse<StudentRecord>> {
  const res = await apiClient.get<PaginatedResponse<StudentRecord>>("/students/", { params });
  return res.data;
}

export async function createStudent(payload: {
  email: string;
  first_name: string;
  last_name?: string;
  registration_no: string;
  cohort_id?: string | null;
  admission_year?: number | null;
  phone?: string;
  status?: ActiveStatus;
}): Promise<StudentRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<StudentRecord>("/students/", payload);
  return res.data;
}

export async function updateStudent(
  id: string,
  payload: Partial<{
    first_name: string;
    last_name: string;
    registration_no: string;
    cohort_id: string | null;
    admission_year: number | null;
    phone: string;
    status: ActiveStatus;
  }>,
): Promise<StudentRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<StudentRecord>(`/students/${id}/`, payload);
  return res.data;
}

// Faculty
export async function listFaculty(params?: {
  page?: number;
  search?: string;
  department?: string;
  status?: string;
}): Promise<PaginatedResponse<FacultyRecord>> {
  const res = await apiClient.get<PaginatedResponse<FacultyRecord>>("/faculty/", { params });
  return res.data;
}

export async function createFaculty(payload: {
  email: string;
  first_name: string;
  last_name?: string;
  employee_code?: string | null;
  department?: string;
  designation?: string;
  status?: ActiveStatus;
}): Promise<FacultyRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.post<FacultyRecord>("/faculty/", payload);
  return res.data;
}

export async function updateFaculty(
  id: string,
  payload: Partial<{
    first_name: string;
    last_name: string;
    employee_code: string | null;
    department: string;
    designation: string;
    status: ActiveStatus;
  }>,
): Promise<FacultyRecord> {
  await ensureCsrfCookie();
  const res = await apiClient.patch<FacultyRecord>(`/faculty/${id}/`, payload);
  return res.data;
}

export async function assignFacultyCohort(
  facultyId: string,
  cohortId: string,
  assignmentType: AssignmentType,
): Promise<FacultyCohortAssignment> {
  await ensureCsrfCookie();
  const res = await apiClient.post<FacultyCohortAssignment>(`/faculty/${facultyId}/cohorts/`, {
    cohort_id: cohortId,
    assignment_type: assignmentType,
  });
  return res.data;
}

export async function removeFacultyCohort(facultyId: string, assignmentId: string): Promise<void> {
  await ensureCsrfCookie();
  await apiClient.delete(`/faculty/${facultyId}/cohorts/${assignmentId}/`);
}

