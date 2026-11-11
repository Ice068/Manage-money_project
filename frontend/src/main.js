import "./style.css";

const API_BASE = "http://127.0.0.1:8000/api";
const statusElement = document.querySelector("#api-status");
const messageElement = document.querySelector("#page-message");
const periodForm = document.querySelector("#period-form");
const settingsForm = document.querySelector("#settings-form");
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
    const detail = typeof body.detail === "string" ? body.detail : "เชื่อมต่อ API ไม่สำเร็จ";
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
  } catch (error) {
    showMessage(error.message, true);
  }
});

async function initialize() {
  await loadSettings();
  await loadDashboard();
}

initialize();
