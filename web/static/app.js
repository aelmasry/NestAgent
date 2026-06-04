const readyStatus = document.querySelector("#readyStatus");
const toolsEl = document.querySelector("#tools");
const modelsEl = document.querySelector("#models");
const outputEl = document.querySelector("#output");
const runBtn = document.querySelector("#runBtn");
const requestEl = document.querySelector("#request");
const usePlannerEl = document.querySelector("#usePlanner");

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

async function getJson(path) {
  const response = await fetch(path);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || response.statusText);
  }
  return body;
}

runBtn.addEventListener("click", async () => {
  runBtn.disabled = true;
  outputEl.textContent = "Running...";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request: requestEl.value,
        use_planner: usePlannerEl.checked,
      }),
    });
    const body = await response.json();
    outputEl.textContent = pretty(body);
  } catch (error) {
    outputEl.textContent = error.message;
  } finally {
    runBtn.disabled = false;
  }
});

try {
  const ready = await getJson("/api/ready");
  readyStatus.textContent = ready.ready ? "Ready" : "Not ready";
  readyStatus.className = ready.ready ? "status ok" : "status bad";
} catch (error) {
  readyStatus.textContent = error.message;
  readyStatus.className = "status bad";
}

try {
  toolsEl.textContent = pretty(await getJson("/api/tools"));
} catch (error) {
  toolsEl.textContent = error.message;
}

try {
  modelsEl.textContent = pretty(await getJson("/api/models"));
} catch (error) {
  modelsEl.textContent = error.message;
}
