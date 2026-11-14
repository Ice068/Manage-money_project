import "./style.css";

const API_BASE = "http://127.0.0.1:8000/api";
const statusElement = document.querySelector("#api-status");
const messageElement = document.querySelector("#page-message");
const periodForm = document.querySelector("#period-form");
const settingsForm = document.querySelector("#settings-form");
const goalForm = document.querySelector("#goal-form");
const goalsList = document.querySelector("#savings-goals");
const dateInput = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const today = new Date();
document.querySelector("#period-start").value = dateInput(
  new Date(today.getFullYear(), today.getMonth(), 1),
);
document.querySelector("#period-end").value = dateInput(today);

function formatMoney(satang) {
  return new Intl.NumberFormat("th-TH", {
    style: "currency",
    currency: "THB",
    maximumFractionDigits: 2,
  }).format(satang / 100);
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string"
      ? body.detail
      : Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join("; ")
        : "เชื่อมต่อ API ไม่สำเร็จ";
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

function showMessage(message, isError = false) {
  messageElement.textContent = message;
  messageElement.classList.toggle("error", isError);
}

async function loadDashboard() {
  showMessage("");
  const params = new URLSearchParams({
    start_date: document.querySelector("#period-start").value,
    end_date: document.querySelector("#period-end").value,
  });

  try {
    const data = await request(`/dashboard/summary?${params}`);
    document.querySelector("#current-balance").textContent = formatMoney(data.current_balance_satangs);
    document.querySelector("#income-total").textContent = formatMoney(data.income_satangs);
    document.querySelector("#expense-total").textContent = formatMoney(data.expense_satangs);
    document.querySelector("#net-total").textContent = formatMoney(data.net_satangs);
    document.querySelector("#average-expense").textContent = data.average_daily_expense_satangs === null
      ? "ไม่มีรายจ่ายในช่วงนี้"
      : `เฉลี่ยต่อวัน ${formatMoney(data.average_daily_expense_satangs)}`;
    document.querySelector("#runway-days").textContent = data.runway_days === null
      ? "คำนวณไม่ได้"
      : `${data.runway_days} วัน`;
    document.querySelector("#balance-note").textContent =
      `ตั้งต้น ${formatMoney(data.opening_balance_satangs)} ณ ${data.opening_balance_date}`;
    statusElement.textContent = "เชื่อมต่อแล้ว";
    statusElement.classList.add("connected");
    statusElement.classList.remove("disconnected");
  } catch (error) {
    statusElement.textContent = "เชื่อมต่อ backend ไม่ได้";
    statusElement.classList.add("disconnected");
    statusElement.classList.remove("connected");
    showMessage(error.message, true);
  }
}

async function loadSettings() {
  try {
    const settings = await request("/dashboard/settings");
    document.querySelector("#opening-balance").value = (settings.opening_balance_satangs / 100).toFixed(2);
    document.querySelector("#opening-date").value = settings.opening_balance_date;
    return true;
  } catch (error) {
    showMessage(error.message, true);
    return false;
  }
}

function makeGoalCard(goal) {
  const card = document.createElement("article");
  card.className = "goal-card";

  const header = document.createElement("div");
  header.className = "goal-card-header";
  const title = document.createElement("h3");
  title.textContent = goal.name;
  const badge = document.createElement("span");
  const complete = goal.amount_remaining_satangs === 0;
  badge.className = complete ? "goal-badge complete" : "goal-badge";
  badge.textContent = complete ? "ถึงเป้าหมายแล้ว" : "กำลังเก็บ";
  header.append(title, badge);

  const note = document.createElement("p");
  note.className = "goal-note";
  note.textContent = goal.note || "ไม่มีบันทึกเพิ่มเติม";

  const amounts = document.createElement("div");
  amounts.className = "goal-amounts";
  const saved = document.createElement("span");
  saved.textContent = `${formatMoney(goal.saved_amount_satangs)} จาก ${formatMoney(goal.target_amount_satangs)}`;
  const percent = document.createElement("span");
  percent.textContent = `${Math.round(goal.progress_percent)}%`;
  amounts.append(saved, percent);

  const progress = document.createElement("div");
  progress.className = "progress-track";
  progress.setAttribute("role", "progressbar");
  progress.setAttribute("aria-label", `ความคืบหน้า ${goal.name}`);
  progress.setAttribute("aria-valuemin", "0");
  progress.setAttribute("aria-valuemax", "100");
  progress.setAttribute("aria-valuenow", String(Math.round(goal.progress_percent)));
  const progressBar = document.createElement("span");
  progressBar.style.width = `${Math.max(0, Math.min(100, goal.progress_percent))}%`;
  progress.append(progressBar);

  const remaining = document.createElement("p");
  remaining.className = "goal-remaining";
  remaining.textContent = complete
    ? "เก็บครบตามราคาเป้าหมายแล้ว"
    : `ยังขาด ${formatMoney(goal.amount_remaining_satangs)}`;

  const forecast = document.createElement("p");
  forecast.className = "goal-forecast";
  if (goal.estimated_days === null) {
    forecast.textContent = "ยังประมาณวันไม่ได้ เพราะเงินออมสุทธิเฉลี่ยยังไม่เป็นบวก";
  } else if (goal.estimated_days === 0) {
    forecast.textContent = "ถึงเป้าหมายแล้ว";
  } else {
    const estimatedDate = new Date(`${goal.estimated_date}T00:00:00`);
    const dateText = new Intl.DateTimeFormat("th-TH", { dateStyle: "long" }).format(estimatedDate);
    forecast.textContent = `ประมาณ ${goal.estimated_days} วัน (วันที่ ${dateText}) หากออมได้ใกล้เคียงค่าเฉลี่ยเดิม`;
  }

  const actions = document.createElement("div");
  actions.className = "goal-actions";
  const editButton = document.createElement("button");
  editButton.type = "button";
  editButton.className = "secondary-button";
  editButton.textContent = "แก้ไข";
  editButton.addEventListener("click", () => editGoal(goal));
  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "danger-button";
  deleteButton.textContent = "ลบ";
  deleteButton.addEventListener("click", () => deleteGoal(goal));
  actions.append(editButton, deleteButton);

  card.append(header, note, amounts, progress, remaining, forecast, actions);
  return card;
}

async function loadSavingsGoals() {
  try {
    const goals = await request("/savings-goals");
    goalsList.replaceChildren();
    if (goals.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "ยังไม่มีเป้าหมาย เริ่มเพิ่มของชิ้นแรกที่อยากเก็บเงินซื้อได้เลย";
      goalsList.append(empty);
      return;
    }
    for (const goal of goals) goalsList.append(makeGoalCard(goal));
  } catch (error) {
    showMessage(error.message, true);
  }
}

function editGoal(goal) {
  document.querySelector("#goal-id").value = goal.id;
  document.querySelector("#goal-name").value = goal.name;
  document.querySelector("#goal-target").value = (goal.target_amount_satangs / 100).toFixed(2);
  document.querySelector("#goal-saved").value = (goal.saved_amount_satangs / 100).toFixed(2);
  document.querySelector("#goal-note").value = goal.note || "";
  document.querySelector("#goal-submit").textContent = "บันทึกการแก้ไข";
  document.querySelector("#goal-cancel").hidden = false;
  document.querySelector("#goal-name").focus();
}

function resetGoalForm() {
  goalForm.reset();
  document.querySelector("#goal-id").value = "";
  document.querySelector("#goal-saved").value = "0";
  document.querySelector("#goal-submit").textContent = "เพิ่มเป้าหมาย";
  document.querySelector("#goal-cancel").hidden = true;
}

async function deleteGoal(goal) {
  if (!window.confirm(`ลบเป้าหมาย “${goal.name}” หรือไม่?`)) return;
  try {
    await request(`/savings-goals/${goal.id}`, { method: "DELETE" });
    showMessage("ลบเป้าหมายแล้ว");
    await loadSavingsGoals();
  } catch (error) {
    showMessage(error.message, true);
  }
}

periodForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadDashboard();
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const amountBaht = Number(document.querySelector("#opening-balance").value);
  if (!Number.isFinite(amountBaht) || amountBaht < 0) {
    showMessage("กรุณากรอกเงินตั้งต้นเป็นจำนวนศูนย์หรือมากกว่า", true);
    return;
  }

  try {
    const settings = await request("/dashboard/settings", {
      method: "PUT",
      body: JSON.stringify({
        opening_balance_satangs: Math.round(amountBaht * 100),
        opening_balance_date: document.querySelector("#opening-date").value,
      }),
    });
    document.querySelector("#opening-balance").value =
      (settings.opening_balance_satangs / 100).toFixed(2);
    showMessage("บันทึกเงินตั้งต้นแล้ว");
    await loadDashboard();
    await loadSavingsGoals();
  } catch (error) {
    showMessage(error.message, true);
  }
});

goalForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const targetBaht = Number(document.querySelector("#goal-target").value);
  const savedBaht = Number(document.querySelector("#goal-saved").value);
  if (!Number.isFinite(targetBaht) || targetBaht <= 0 || !Number.isFinite(savedBaht) || savedBaht < 0) {
    showMessage("กรุณาตรวจสอบราคาเป้าหมายและยอดที่เก็บไว้แล้ว", true);
    return;
  }

  const goalId = document.querySelector("#goal-id").value;
  const payload = {
    name: document.querySelector("#goal-name").value,
    target_amount_satangs: Math.round(targetBaht * 100),
    saved_amount_satangs: Math.round(savedBaht * 100),
    note: document.querySelector("#goal-note").value || null,
  };

  try {
    await request(goalId ? `/savings-goals/${goalId}` : "/savings-goals", {
      method: goalId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    resetGoalForm();
    showMessage(goalId ? "บันทึกการแก้ไขเป้าหมายแล้ว" : "เพิ่มเป้าหมายแล้ว");
    await loadSavingsGoals();
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector("#goal-cancel").addEventListener("click", resetGoalForm);

async function initialize() {
  await Promise.all([loadSettings(), loadDashboard(), loadSavingsGoals()]);
}

initialize();
