import "./style.css";

const status = document.querySelector("#api-status");

async function checkBackend() {
  try {
    const response = await fetch("http://127.0.0.1:8000/api/hello");
    if (!response.ok) throw new Error(`Backend returned ${response.status}`);
    const data = await response.json();
    status.textContent = data.message;
    status.classList.add("connected");
  } catch {
    status.textContent = "ยังเชื่อมต่อ backend ไม่ได้ — ตรวจว่า FastAPI ทำงานที่พอร์ต 8000";
    status.classList.add("disconnected");
  }
}

checkBackend();
