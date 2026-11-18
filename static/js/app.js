const form = document.getElementById("studentForm");
const tableBody = document.getElementById("studentTable");
const message = document.getElementById("formMessage");
const resultsStatus = document.getElementById("resultsStatus");
const searchInput = document.getElementById("searchInput");
const departmentFilter = document.getElementById("departmentFilter");
const academicYearFilter = document.getElementById("academicYearFilter");
const idInput = document.getElementById("studentId");
const exportButton = document.getElementById("exportButton");
const fields = ["name", "roll_number", "department", "academic_year", "email"];
// Keep search fields aligned with SEARCHABLE_FIELDS in app.py.
const searchableFields = ["name", "roll_number", "department", "email"];
const maxNameLength = 100;
const maxDepartmentLength = 100;
const maxRollNumberLength = 30;
const minAcademicYear = 2000;
const maxAcademicYear = 2100;
const emailPattern = /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$/;
const csvColumns = [
  ["id", "ID"],
  ["name", "Name"],
  ["roll_number", "Roll Number"],
  ["department", "Department"],
  ["academic_year", "Academic Year"],
  ["email", "Email"],
  ["created_at", "Created At"],
];
const localStorageKey = "student-management-system.students.v1";
const usesBrowserStorage = document.body.dataset.storage === "local";
let students = [];
let latestLoadRequest = 0;
let searchTimer;

function showMessage(text, type = "") {
  message.textContent = text;
  message.className = `message ${type}`;
}

function getFormValues() {
  return Object.fromEntries(
    fields.map((field) => [
      field,
      document.getElementById(field).value.trim(),
    ]),
  );
}

function resetForm() {
  form.reset();
  idInput.value = "";
  document.getElementById("formTitle").textContent = "Add a student";
  document.getElementById("saveButton").textContent = "Add student";
  document.getElementById("cancelButton").classList.add("hidden");
  showMessage("");
}

function readLocalStudents() {
  const saved = localStorage.getItem(localStorageKey);
  if (!saved) {
    return [];
  }
  try {
    const records = JSON.parse(saved);
    if (!Array.isArray(records)) {
      throw new Error("Saved student records are invalid.");
    }
    return records;
  } catch {
    throw new Error("Saved student records are invalid. Clear this site's browser data to continue.");
  }
}

function saveLocalStudents(records) {
  localStorage.setItem(localStorageKey, JSON.stringify(records));
}

function localRequest(url, options) {
  const requestUrl = new URL(url, window.location.href);
  const method = options.method || "GET";
  const records = readLocalStudents();

  if (requestUrl.pathname.endsWith("/api/students") && method === "GET") {
    const query = requestUrl.searchParams.get("q")?.trim().toLowerCase() || "";
    const department = requestUrl.searchParams.get("department")?.trim().toLowerCase() || "";
    const academicYear = requestUrl.searchParams.get("academic_year")?.trim() || "";
    return records
      .filter((record) =>
        searchableFields.some((field) =>
          String(record[field] || "").toLowerCase().includes(query),
        ) &&
        (!department || String(record.department || "").toLowerCase() === department) &&
        (!academicYear || String(record.academic_year || "") === academicYear),
      )
      .sort((left, right) => Number(right.id) - Number(left.id));
  }

  if (requestUrl.pathname.endsWith("/api/students/summary") && method === "GET") {
    const departments = [...new Set(
      records.map((record) => record.department).filter(Boolean),
    )].sort((left, right) => left.localeCompare(right));
    return {
      total_students: records.length,
      department_count: new Set(
        records
          .map((record) => String(record.department || "").toLowerCase())
          .filter(Boolean),
      ).size,
      departments,
    };
  }

  const values = options.body ? JSON.parse(options.body) : {};
  const studentPath = requestUrl.pathname.match(/\/api\/students\/(\d+)$/);

  if (
    requestUrl.pathname.endsWith("/api/students") &&
    method === "POST"
  ) {
    validateLocalStudent(values, records);
    const student = {
      ...values,
      id: records.reduce((maxId, record) => Math.max(maxId, Number(record.id) || 0), 0) + 1,
      created_at: new Date().toISOString(),
    };
    saveLocalStudents([...records, student]);
    return student;
  }

  if (studentPath && method === "PUT") {
    const studentId = Number(studentPath[1]);
    const index = records.findIndex((record) => Number(record.id) === studentId);
    if (index < 0) {
      throw new Error("Student not found.");
    }
    validateLocalStudent(values, records, studentId);
    records[index] = { ...records[index], ...values };
    saveLocalStudents(records);
    return records[index];
  }

  if (studentPath && method === "DELETE") {
    const studentId = Number(studentPath[1]);
    const remaining = records.filter((record) => Number(record.id) !== studentId);
    if (remaining.length === records.length) {
      throw new Error("Student not found.");
    }
    saveLocalStudents(remaining);
    return { message: "Student deleted successfully." };
  }

  throw new Error("This action is not supported by browser storage.");
}

function validateLocalStudent(values, records, currentId = null) {
  // Mirror the server rules because the Pages demo has no Flask API.
  const missing = fields.filter((field) => !String(values[field] || "").trim());
  if (missing.length) {
    throw new Error(`Please provide: ${missing.join(", ")}.`);
  }

  if (
    String(values.name).length > maxNameLength ||
    String(values.department).length > maxDepartmentLength
  ) {
    throw new Error("Name and department must be 100 characters or fewer.");
  }
  if (String(values.roll_number).length > maxRollNumberLength) {
    throw new Error("Roll number must be 30 characters or fewer.");
  }
  if (!/^(?:19|20|21)\d{2}$/.test(String(values.academic_year))) {
    throw new Error("Academic year must be a four-digit year.");
  }
  const academicYear = Number(values.academic_year);
  if (academicYear < minAcademicYear || academicYear > maxAcademicYear) {
    throw new Error("Academic year must be between 2000 and 2100.");
  }
  if (!emailPattern.test(String(values.email))) {
    throw new Error("Enter a valid email address.");
  }

  const duplicate = records.some(
    (record) =>
      Number(record.id) !== currentId &&
      (record.roll_number === values.roll_number ||
        String(record.email).toLowerCase() === values.email.toLowerCase()),
  );
  if (duplicate) {
    throw new Error("A student with this roll number or email already exists.");
  }
}

async function api(url, options = {}) {
  if (usesBrowserStorage) {
    return localRequest(url, options);
  }

  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (["POST", "PUT", "PATCH", "DELETE"].includes((options.method || "GET").toUpperCase())) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(url, {
    ...options,
    headers,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[character]);
}

function escapeCsvValue(value) {
  const text = value == null ? "" : String(value);
  const safeText = /^[\u0000-\u0020\uFEFF]*[=+\-@]/.test(text)
    ? `'${text}`
    : text;
  return `"${safeText.replace(/"/g, '""')}"`;
}

function exportStudentsToCsv() {
  const header = csvColumns.map(([, label]) => escapeCsvValue(label)).join(",");
  const rows = students.map((student) =>
    csvColumns
      .map(([field]) => escapeCsvValue(student[field]))
      .join(","),
  );
  const csv = `\uFEFF${[header, ...rows].join("\r\n")}`;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "students.csv";
  link.hidden = true;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);

  if (students.length === 0) {
    showMessage("No matching student records; exported an empty CSV.");
  } else {
    showMessage(`Exported ${students.length} student record${students.length === 1 ? "" : "s"} to CSV.`, "success");
  }
}

function renderStudents(records) {
  if (!records.length) {
    tableBody.innerHTML =
      '<tr><td colspan="6" class="empty">No students match the selected search and filters.</td></tr>';
    resultsStatus.textContent = "No students match the selected search and filters.";
    return;
  }

  resultsStatus.textContent = `${records.length} student record${records.length === 1 ? "" : "s"} found.`;
  tableBody.innerHTML = records
    .map(
      (student) => `
        <tr>
          <td>
            ${escapeHtml(student.name)}
            <span class="student-sub">Student ID: ${escapeHtml(student.id)}</span>
          </td>
          <td>${escapeHtml(student.roll_number)}</td>
          <td>${escapeHtml(student.department)}</td>
          <td>${escapeHtml(student.academic_year)}</td>
          <td>${escapeHtml(student.email)}</td>
          <td>
            <div class="actions">
              <button class="mini-btn" data-edit="${escapeHtml(student.id)}" aria-label="Edit ${escapeHtml(student.name)}" type="button">Edit</button>
              <button class="mini-btn delete" data-delete="${escapeHtml(student.id)}" aria-label="Delete ${escapeHtml(student.name)}" type="button">Delete</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

async function loadStudents() {
  window.clearTimeout(searchTimer);
  const requestId = ++latestLoadRequest;
  try {
    const params = new URLSearchParams();
    if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
    if (departmentFilter.value.trim()) params.set("department", departmentFilter.value.trim());
    if (academicYearFilter.value.trim()) params.set("academic_year", academicYearFilter.value.trim());
    const [filteredStudents, summary] = await Promise.all([
      api(`/api/students${params.size ? `?${params}` : ""}`),
      api("/api/students/summary"),
    ]);
    if (requestId !== latestLoadRequest) {
      return;
    }
    students = filteredStudents;
    renderStudents(students);
    document.getElementById("studentCount").textContent = summary.total_students;
    document.getElementById("departmentCount").textContent = summary.department_count;
    document.getElementById("departmentOptions").innerHTML = summary.departments
      .map((department) => `<option value="${escapeHtml(department)}"></option>`)
      .join("");
  } catch (error) {
    if (requestId !== latestLoadRequest) {
      return;
    }
    tableBody.innerHTML = `<tr><td colspan="6" class="empty">${escapeHtml(error.message)}</td></tr>`;
    resultsStatus.textContent = `Unable to load student records: ${error.message}`;
  }
}

function scheduleStudentLoad() {
  window.clearTimeout(searchTimer);
  latestLoadRequest += 1;
  searchTimer = window.setTimeout(loadStudents, 250);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const studentId = idInput.value;

  try {
    await api(
      studentId ? `/api/students/${studentId}` : "/api/students",
      {
        method: studentId ? "PUT" : "POST",
        body: JSON.stringify(getFormValues()),
      },
    );
    resetForm();
    showMessage(
      studentId ? "Student updated successfully." : "Student added successfully.",
      "success",
    );
    await loadStudents();
  } catch (error) {
    showMessage(error.message, "error");
  }
});

tableBody.addEventListener("click", async (event) => {
  const editId = event.target.dataset.edit;
  const deleteId = event.target.dataset.delete;

  if (editId) {
    const student = students.find((record) => Number(record.id) === Number(editId));
    if (!student) {
      return;
    }

    idInput.value = student.id;
    fields.forEach((field) => {
      document.getElementById(field).value = student[field];
    });
    document.getElementById("formTitle").textContent = "Update student";
    document.getElementById("saveButton").textContent = "Save changes";
    document.getElementById("cancelButton").classList.remove("hidden");
    showMessage("Editing selected student.");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (deleteId && window.confirm("Delete this student record? This cannot be undone.")) {
    try {
      await api(`/api/students/${deleteId}`, { method: "DELETE" });
      await loadStudents();
      showMessage("Student deleted successfully.", "success");
    } catch (error) {
      showMessage(error.message, "error");
    }
  }
});

document.getElementById("cancelButton").addEventListener("click", resetForm);
document.getElementById("refreshButton").addEventListener("click", loadStudents);
document.getElementById("clearFiltersButton").addEventListener("click", () => {
  searchInput.value = "";
  departmentFilter.value = "";
  academicYearFilter.value = "";
  loadStudents();
});
exportButton.addEventListener("click", exportStudentsToCsv);
searchInput.addEventListener("input", scheduleStudentLoad);
departmentFilter.addEventListener("input", scheduleStudentLoad);
academicYearFilter.addEventListener("input", scheduleStudentLoad);

loadStudents();
