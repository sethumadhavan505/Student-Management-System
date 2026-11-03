const form = document.getElementById("studentForm");
const tableBody = document.getElementById("studentTable");
const message = document.getElementById("formMessage");
const searchInput = document.getElementById("searchInput");
const idInput = document.getElementById("studentId");
const fields = ["name", "roll_number", "department", "email"];
const localStorageKey = "student-management-system.students.v1";
const usesBrowserStorage = document.body.dataset.storage === "local";
let students = [];

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

  const records = JSON.parse(saved);
  if (!Array.isArray(records)) {
    throw new Error("Saved student records are invalid. Clear this site's browser data to continue.");
  }
  return records;
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
    return records
      .filter((record) =>
        fields.some((field) =>
          String(record[field] || "").toLowerCase().includes(query),
        ),
      )
      .sort((left, right) => Number(right.id) - Number(left.id));
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
  const missing = fields.filter((field) => !String(values[field] || "").trim());
  if (missing.length) {
    throw new Error(`Please provide: ${missing.join(", ")}.`);
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

  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
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

function renderStudents(records) {
  if (!records.length) {
    tableBody.innerHTML =
      '<tr><td colspan="5" class="empty">No student records found. Add your first student.</td></tr>';
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

async function loadStudents() {
  try {
    students = await api(
      `/api/students?q=${encodeURIComponent(searchInput.value.trim())}`,
    );
    renderStudents(students);
    document.getElementById("studentCount").textContent = students.length;
    document.getElementById("departmentCount").textContent = new Set(
      students.map((student) => student.department.toLowerCase()),
    ).size;
  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="5" class="empty">${escapeHtml(error.message)}</td></tr>`;
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
searchInput.addEventListener("input", loadStudents);

loadStudents();
