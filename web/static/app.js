const readyStatus = document.querySelector("#readyStatus");
const runBtn = document.querySelector("#runBtn");
const requestEl = document.querySelector("#request");

const currentStatusEl = document.querySelector("#currentStatus");
const goalTextEl = document.querySelector("#goalText");
const progressTextEl = document.querySelector("#progressText");
const elapsedTimeEl = document.querySelector("#elapsedTime");
const progressBarEl = document.querySelector("#progressBar");
const activityFeedEl = document.querySelector("#activityFeed");
const activityCountEl = document.querySelector("#activityCount");
const finalAnswerEl = document.querySelector("#finalAnswer");
const totalRuntimeEl = document.querySelector("#totalRuntime");
const timelineListEl = document.querySelector("#timelineList");
const evidenceListEl = document.querySelector("#evidenceList");
const evidenceCountEl = document.querySelector("#evidenceCount");

const plannerOutputEl = document.querySelector("#plannerOutput");
const selectedCapabilitiesEl = document.querySelector("#selectedCapabilities");
const evidenceGeneratedEl = document.querySelector("#evidenceGenerated");
const validationDecisionsEl = document.querySelector("#validationDecisions");

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function getJson(path) {
  const response = await fetch(path);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.error || response.statusText);
  }
  return body;
}

function setStatus(text, className = "") {
  currentStatusEl.textContent = text;
  currentStatusEl.className = className;
}

function eventKind(event) {
  return event.event || event.type || "activity";
}

function eventTitle(event) {
  return event.title || eventKind(event).replaceAll("_", " ");
}

function eventDetail(event) {
  return event.details || event.detail || "";
}

function appendActivityEvent(event) {
  const item = document.createElement("li");
  const kind = eventKind(event);
  item.className = `activity-item ${kind}`;
  item.innerHTML = `
    <div class="activity-icon">${escapeHtml(kind.replaceAll("_", " "))}</div>
    <div class="activity-body">
      <div class="activity-title">
        <strong>${escapeHtml(eventTitle(event))}</strong>
        <span>${escapeHtml(event.status)}</span>
      </div>
      <p>${escapeHtml(eventDetail(event))}</p>
      <small>${escapeHtml(event.duration_ms ?? 0)}ms · ${escapeHtml(event.timestamp ?? "live")}</small>
    </div>
  `;
  activityFeedEl.append(item);
  activityCountEl.textContent = `${activityFeedEl.children.length} actions`;
}

function renderUserView(payload) {
  const view = payload.user_view;
  goalTextEl.textContent = view.goal;
  setStatus(view.current_status, view.current_status);
  progressTextEl.textContent = view.progress;
  elapsedTimeEl.textContent = `${view.elapsed_time_ms}ms`;

  const [done, total] = view.progress.split("/").map((part) => Number.parseInt(part, 10));
  const percent = total ? Math.round((done / total) * 100) : 0;
  progressBarEl.style.width = `${percent}%`;
}

function renderActivityFeed(events) {
  activityFeedEl.innerHTML = "";
  activityCountEl.textContent = `${events.length} actions`;
  for (const event of events) {
    appendActivityEvent(event);
  }
}

function renderTimeline(timeline) {
  timelineListEl.innerHTML = "";
  totalRuntimeEl.textContent = `${timeline.total_runtime_ms}ms total`;
  for (const step of timeline.steps) {
    const item = document.createElement("li");
    item.className = "timeline-step";
    item.innerHTML = `
      <span>${escapeHtml(step.name)}</span>
      <strong>${escapeHtml(step.status)}</strong>
      <small>${escapeHtml(step.duration_ms)}ms</small>
    `;
    if (step.name === timeline.current_step) {
      item.classList.add("current");
    }
    timelineListEl.append(item);
  }
}

function evidenceTitle(item) {
  return item.title || item.name || item.id || "Evidence item";
}

function evidencePrimaryValue(item) {
  if (item.price !== undefined && item.currency) {
    return `${item.price} ${item.currency}`;
  }
  if (item.value !== undefined) {
    return item.value;
  }
  return "n/a";
}

function evidenceSignal(item) {
  if (item.metro_distance === null) {
    return "metro distance unknown";
  }
  if (item.metro_distance !== undefined) {
    return `${item.metro_distance}m signal`;
  }
  return item.status || "observed";
}

function renderEvidence(evidence) {
  evidenceListEl.innerHTML = "";
  evidenceCountEl.textContent = `${evidence.length} items`;
  if (!evidence.length) {
    evidenceListEl.textContent = "No evidence collected.";
    return;
  }

  for (const item of evidence) {
    const card = document.createElement("article");
    card.className = "evidence-card";
    card.innerHTML = `
      <div>
        <strong>${escapeHtml(evidenceTitle(item))}</strong>
        <span>${escapeHtml(evidencePrimaryValue(item))}</span>
      </div>
      <p>${escapeHtml(evidenceSignal(item))}</p>
      <small>${escapeHtml(item.source || "no source")} · confidence ${escapeHtml(item.confidence ?? "n/a")}</small>
    `;
    evidenceListEl.append(card);
  }
}

function renderDeveloperView(payload) {
  plannerOutputEl.textContent = pretty(payload.developer_view.planner_output);
  selectedCapabilitiesEl.textContent = pretty({
    required: payload.capability_manager.required_capabilities,
    available: payload.capability_manager.available_capabilities,
    missing: payload.capability_manager.missing_capabilities,
  });
  evidenceGeneratedEl.textContent = pretty(payload.developer_view.evidence_generated);
  validationDecisionsEl.textContent = pretty(payload.developer_view.validation_decisions);
}

function renderWorkspace(payload) {
  renderUserView(payload);
  renderActivityFeed(payload.agent_activity_feed);
  renderTimeline(payload.timeline_view);
  renderEvidence(payload.evidence_store.evidence);
  finalAnswerEl.textContent = payload.response_composer.final_answer;
  renderDeveloperView(payload);
}

function renderRunningState(request) {
  goalTextEl.textContent = request;
  setStatus("running", "running");
  progressTextEl.textContent = "0/7 steps complete";
  elapsedTimeEl.textContent = "running...";
  progressBarEl.style.width = "12%";
  activityCountEl.textContent = "0 actions";
  activityFeedEl.innerHTML = "";
  timelineListEl.innerHTML = `<li class="timeline-step current"><span>Waiting for events</span><strong>running</strong><small>live</small></li>`;
  totalRuntimeEl.textContent = "running";
  evidenceListEl.textContent = "Waiting for evidence...";
  evidenceCountEl.textContent = "0 items";
  finalAnswerEl.textContent = "Agent is working...";
}

runBtn.addEventListener("click", async () => {
  const request = requestEl.value.trim();
  if (!request) {
    finalAnswerEl.textContent = "Please enter a request.";
    return;
  }

  runBtn.disabled = true;
  renderRunningState(request);
  const stream = new EventSource(`/api/dashboard/stream?request=${encodeURIComponent(request)}`);

  stream.addEventListener("activity", (message) => {
    const event = JSON.parse(message.data);
    appendActivityEvent(event);
    setStatus(event.status, event.status);
    elapsedTimeEl.textContent = `${event.duration_ms ?? 0}ms`;
    progressTextEl.textContent = `${activityFeedEl.children.length} events received`;
    progressBarEl.style.width = `${Math.min(activityFeedEl.children.length * 10, 90)}%`;
  });

  stream.addEventListener("final", (message) => {
    const payload = JSON.parse(message.data);
    renderWorkspace(payload);
    stream.close();
    runBtn.disabled = false;
  });

  stream.onerror = (error) => {
    stream.close();
    setStatus("error", "error");
    finalAnswerEl.textContent = "Live event stream failed.";
    activityFeedEl.insertAdjacentHTML(
      "beforeend",
      `<li class="activity-item error">
        <div class="activity-icon">error</div>
        <div class="activity-body">
          <div class="activity-title"><strong>Workflow error</strong><span>failed</span></div>
          <p>${escapeHtml(error.message || "EventSource connection failed.")}</p>
        </div>
      </li>`,
    );
    runBtn.disabled = false;
  };
});

try {
  const ready = await getJson("/api/ready");
  readyStatus.textContent = ready.ready ? "Ready" : "Not ready";
  readyStatus.className = ready.ready ? "status-pill ok" : "status-pill bad";
} catch (error) {
  readyStatus.textContent = error.message;
  readyStatus.className = "status-pill bad";
}
