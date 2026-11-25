const form = document.getElementById("studentForm");
const tableBody = document.getElementById("studentTable");
const message = document.getElementById("formMessage");
const searchInput = document.getElementById("searchInput");
const departmentFilter = document.getElementById("departmentFilter");
const academicYearFilter = document.getElementById("academicYearFilter");
const idInput = document.getElementById("studentId");
const exportButton = document.getElementById("exportButton");
const directoryStatus = document.getElementById("directoryStatus");
const importFile = document.getElementById("importFile");
const importPreview = document.getElementById("importPreview");
const importSummary = document.getElementById("importSummary");
const importPreviewRows = document.getElementById("importPreviewRows");
const confirmImportButton = document.getElementById("confirmImportButton");
const fields = ["name", "roll_number", "department", "academic_year", "email"];
const searchableFields = ["id", "name", "roll_number", "department", "email"];
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
let pendingImport = [];
let loadSequence = 0;

function showMessage(text, type = "") {
  message.textContent = text;
  message.className = `message ${type}`;
}

function getFormValues() {
  return Object.fromEntries(
    fields.map((field) => [
      field,
      field === "email"
        ? document.getElementById(field).value
        : document.getElementById(field).value.trim(),
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

  const values = options.body ? JSON.parse(options.body) : {};
  const studentPath = requestUrl.pathname.match(/\/api\/students\/(\d+)$/);

  if (
    requestUrl.pathname.endsWith("/api/students/import") &&
    method === "POST"
  ) {
    if (!Array.isArray(values.students) || values.students.length === 0) {
      throw new Error("Select at least one student to import.");
    }
    const errors = [];
    const imported = [];
    values.students.forEach((value, index) => {
      const error = getStudentValidationError(value, [...records, ...imported]);
      if (error) {
        errors.push(`Row ${index + 2}: ${error}`);
      } else {
        imported.push({
          ...Object.fromEntries(fields.map((field) => [field, value[field].trim()])),
          id: records.reduce((maxId, record) => Math.max(maxId, Number(record.id) || 0), 0) + imported.length + 1,
          created_at: new Date().toISOString(),
        });
      }
    });
    if (errors.length) {
      throw new Error(`Import contains invalid rows. ${errors.join(" ")}`);
    }
    saveLocalStudents([...records, ...imported]);
    return { imported: imported.length, students: imported };
  }

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

function getStudentValidationError(values, records, currentId = null) {
  if (!values || typeof values !== "object" || Array.isArray(values)) {
    return "Request body must be a JSON object.";
  }

  if (fields.some((field) => typeof values[field] !== "string")) {
    return "Student fields must be text.";
  }
  const missing = fields.filter((field) => !values[field].trim());
  if (missing.length) {
    const labels = {
      name: "name",
      roll_number: "roll number",
      department: "department",
      academic_year: "academic year",
      email: "email",
    };
    return `Please provide: ${missing.map((field) => labels[field]).join(", ")}.`;
  }

  const item = Object.fromEntries(fields.map((field) => [field, values[field].trim()]));

  if (item.name.length > 100 || item.department.length > 100) {
    return "Name and department must be 100 characters or fewer.";
  }
  if (item.roll_number.length > 30) {
    return "Roll number must be 30 characters or fewer.";
  }
  if (!/^(?:19|20|21)\d{2}$/.test(item.academic_year)) {
    return "Academic year must be a four-digit year.";
  }
  const academicYear = Number(item.academic_year);
  if (academicYear < 2000 || academicYear > 2100) {
    return "Academic year must be between 2000 and 2100.";
  }
  if (values.email !== values.email.trim()) {
    return "Enter a valid email address.";
  }
  const emailPattern = /^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,}$/;
  if (!emailPattern.test(item.email)) {
    return "Enter a valid email address.";
  }

  const duplicate = records.some(
    (record) =>
      Number(record.id) !== currentId &&
      (record.roll_number === item.roll_number ||
        String(record.email).toLowerCase() === item.email.toLowerCase()),
  );
  if (duplicate) {
    return "A student with this roll number or email already exists.";
  }
  return "";
}

function validateLocalStudent(values, records, currentId = null) {
  const error = getStudentValidationError(values, records, currentId);
  if (error) {
    throw new Error(error);
  }
}

async function api(url, options = {}) {
  if (usesBrowserStorage) {
    return localRequest(url, options);
  }

  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const rowErrors = Array.isArray(data.errors)
      ? data.errors.map((item) => `Row ${item.row}: ${item.error}`).join(" ")
      : "";
    throw new Error([data.error || "Request failed.", rowErrors].filter(Boolean).join(" "));
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
  return `"${text.replace(/"/g, '""')}"`;
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
    return;
  }

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
              <button class="mini-btn" data-edit="${escapeHtml(student.id)}" type="button">Edit</button>
              <button class="mini-btn delete" data-delete="${escapeHtml(student.id)}" type="button">Delete</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");
}

function setDirectoryStatus(text, type = "") {
  directoryStatus.textContent = text;
  directoryStatus.className = `directory-status ${type}`;
}

async function loadStudents() {
  const sequence = ++loadSequence;
  setDirectoryStatus("Loading student records...", "loading");
  tableBody.innerHTML = '<tr><td colspan="6" class="empty">Loading student records...</td></tr>';
  try {
    const params = new URLSearchParams();
    if (searchInput.value.trim()) params.set("q", searchInput.value.trim());
    if (departmentFilter.value.trim()) params.set("department", departmentFilter.value.trim());
    if (academicYearFilter.value.trim()) params.set("academic_year", academicYearFilter.value.trim());
    const matchingStudents = await api(`/api/students${params.size ? `?${params}` : ""}`);
    const allStudents = await api("/api/students");
    if (sequence !== loadSequence) {
      return;
    }
    students = matchingStudents;
    renderStudents(students);
    document.getElementById("studentCount").textContent = allStudents.length;
    document.getElementById("departmentCount").textContent = new Set(
      allStudents.map((student) => student.department.toLowerCase()),
    ).size;
    const selectedDepartment = departmentFilter.value;
    departmentFilter.innerHTML = '<option value="">All departments</option>' + [...new Set(
      allStudents.map((student) => student.department).filter(Boolean),
    )]
      .sort((left, right) => left.localeCompare(right))
      .map((department) => {
        const escapedDepartment = escapeHtml(department);
        return `<option value="${escapedDepartment}">${escapedDepartment}</option>`;
      })
      .join("");
    departmentFilter.value = selectedDepartment;
    const years = Object.entries(allStudents.reduce((counts, student) => {
      counts[student.academic_year] = (counts[student.academic_year] || 0) + 1;
      return counts;
    }, {}))
      .filter(([year]) => year)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([year, count]) => `${year}: ${count}`);
    document.getElementById("yearBreakdown").textContent = years.join(" · ") || "No records";
    setDirectoryStatus(
      students.length
        ? `Showing ${students.length} matching student record${students.length === 1 ? "" : "s"}.`
        : "No student records match the selected search and filters.",
      students.length ? "success" : "empty",
    );
  } catch (error) {
    if (sequence !== loadSequence) {
      return;
    }
    tableBody.innerHTML = `<tr><td colspan="6" class="empty">${escapeHtml(error.message)}</td></tr>`;
    setDirectoryStatus(error.message, "error");
  }
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let inQuotes = false;
  let quoteClosed = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (inQuotes) {
      if (character === '"' && text[index + 1] === '"') {
        value += '"';
        index += 1;
      } else if (character === '"') {
        inQuotes = false;
        quoteClosed = true;
      } else {
        value += character;
      }
    } else if (character === '"') {
      if (value !== "" || quoteClosed) {
        throw new Error("CSV contains a quote in an invalid position.");
      }
      inQuotes = true;
    } else if (character === ",") {
      row.push(value);
      value = "";
      quoteClosed = false;
    } else if (character === "\n" || character === "\r") {
      row.push(value);
      if (row.some((cell) => cell.trim())) {
        rows.push(row);
      }
      row = [];
      value = "";
      quoteClosed = false;
      if (character === "\r" && text[index + 1] === "\n") {
        index += 1;
      }
    } else {
      if (quoteClosed && character.trim()) {
        throw new Error("CSV contains characters after a quoted value.");
      }
      if (!quoteClosed) {
        value += character;
      }
    }
  }

  if (inQuotes) {
    throw new Error("CSV contains an unclosed quoted value.");
  }
  row.push(value);
  if (row.some((cell) => cell.trim())) {
    rows.push(row);
  }
  return rows;
}

function normalizeCsvHeader(value) {
  return value
    .replace(/^\uFEFF/, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
}

function renderImportPreview(rows, errors, messageText = "") {
  pendingImport = errors.length ? [] : rows.map((row) => row.student);
  importSummary.textContent = messageText || (
    errors.length
      ? `${errors.length} row${errors.length === 1 ? "" : "s"} need correction. No records will be imported.`
      : `${rows.length} student record${rows.length === 1 ? "" : "s"} validated. Review the preview before importing.`
  );
  importSummary.className = `import-summary ${errors.length || messageText ? "error" : "success"}`;
  importPreviewRows.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.rowNumber}</td>
      <td>${escapeHtml(row.student.name || "")}</td>
      <td>${escapeHtml(row.student.roll_number || "")}</td>
      <td>${escapeHtml(row.student.department || "")}</td>
      <td>${escapeHtml(row.student.academic_year || "")}</td>
      <td>${escapeHtml(row.student.email || "")}</td>
      <td class="${row.error ? "validation-error" : "validation-ok"}">${escapeHtml(row.error || "Ready")}</td>
    </tr>
  `).join("");
  confirmImportButton.disabled = errors.length > 0 || rows.length === 0;
  importPreview.classList.remove("hidden");
}

async function previewCsvImport(file) {
  try {
    const parsedRows = parseCsv(await file.text());
    if (parsedRows.length < 2) {
      throw new Error("CSV must include a header and at least one student row.");
    }
    const headerNames = parsedRows[0].map(normalizeCsvHeader);
    if (new Set(headerNames).size !== headerNames.length) {
      throw new Error("CSV contains duplicate column headers.");
    }
    const indexes = Object.fromEntries(headerNames.map((name, index) => [name, index]));
    const missing = fields.filter((field) => indexes[field] === undefined);
    if (missing.length) {
      throw new Error(`CSV is missing required columns: ${missing.join(", ")}.`);
    }

    const existing = await api("/api/students");
    const accepted = [];
    const rows = parsedRows.slice(1).map((cells, index) => {
      const candidate = Object.fromEntries(fields.map((field) => [
        field,
        field === "email"
          ? String(cells[indexes[field]] || "")
          : String(cells[indexes[field]] || "").trim(),
      ]));
      const error = cells.length !== headerNames.length
        ? "Row has a different number of values than the header."
        : getStudentValidationError(candidate, [...existing, ...accepted]);
      if (!error) {
        accepted.push(candidate);
      }
      return { rowNumber: index + 2, student: candidate, error };
    });
    const errors = rows.filter((row) => row.error);
    renderImportPreview(rows, errors);
  } catch (error) {
    pendingImport = [];
    renderImportPreview([], [error], error.message);
  }
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
importFile.addEventListener("change", () => {
  const [file] = importFile.files;
  if (file) {
    previewCsvImport(file);
  }
});
document.getElementById("cancelImportButton").addEventListener("click", () => {
  pendingImport = [];
  importFile.value = "";
  importPreview.classList.add("hidden");
});
confirmImportButton.addEventListener("click", async () => {
  confirmImportButton.disabled = true;
  try {
    const result = await api("/api/students/import", {
      method: "POST",
      body: JSON.stringify({ students: pendingImport }),
    });
    pendingImport = [];
    importFile.value = "";
    importPreview.classList.add("hidden");
    showMessage(`Imported ${result.imported} student record${result.imported === 1 ? "" : "s"}.`, "success");
    await loadStudents();
  } catch (error) {
    importSummary.textContent = error.message;
    importSummary.className = "import-summary error";
    confirmImportButton.disabled = false;
  }
});
searchInput.addEventListener("input", loadStudents);
departmentFilter.addEventListener("change", loadStudents);
academicYearFilter.addEventListener("input", loadStudents);

loadStudents();
