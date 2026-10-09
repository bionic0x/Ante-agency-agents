"use strict";
// All user and agent text is inserted with textContent. Never use innerHTML here.

const $ = (id) => document.getElementById(id);
const state = { me: null, csrf: null, after: 0, plan: null };

function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (cls) node.className = cls;
  return node;
}

function showError(message) {
  $("status").textContent = message || "";
}

async function api(method, path, body, retried) {
  const init = { method, credentials: "same-origin", headers: {} };
  if (method === "POST") {
    init.headers["Content-Type"] = "application/json";
    if (state.csrf) init.headers["X-Relay-CSRF"] = state.csrf;
    init.body = JSON.stringify(body || {});
  }
  const res = await fetch(path, init);
  let data = {};
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (res.status === 403 && method === "POST" && !retried && /CSRF/.test(data.error || "")) {
    await refreshCsrf();
    return api(method, path, body, true);
  }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function refreshCsrf() {
  state.csrf = (await api("GET", "/api/csrf")).csrf;
}

async function join() {
  const token = location.hash.slice(1);
  history.replaceState(null, "", "/");
  if (!token) return false;
  try {
    const data = await api("POST", "/api/join", { token });
    state.csrf = data.csrf;
    return true;
  } catch (err) {
    $("join-status").textContent = "This invite link is invalid, used or expired.";
    return false;
  }
}

function renderEntry(entry) {
  const p = entry.payload || {};
  const when = new Date(entry.at).toLocaleString();
  let text;
  switch (entry.kind) {
    case "message": text = `${p.name}: ${p.text}`; break;
    case "run.requested": text = `Run requested for task ${p.task_id} (${p.agent}): ${p.instruction}`; break;
    case "run.started": text = `Run ${p.run_id} admitted by NEXUS; reserved ${p.reserved_cost}`; break;
    case "run.refused": text = `Run ${p.run_id} refused: ${p.reason}`; break;
    case "run.completed": text = `Run ${p.run_id} completed${p.error ? ` with error: ${p.error}` : ""}; cost ${p.actual_cost}`; break;
    case "run.accepted": text = `Run ${p.run_id} accepted: ${p.note}`; break;
    case "run.rejected": text = `Run ${p.run_id} rejected: ${p.note}`; break;
    case "run.declined": text = `Run ${p.run_id} declined: ${p.reason}`; break;
    default: text = entry.kind;
  }
  const li = el("li");
  li.append(el("span", when + " ", "muted"), el("span", text));
  return li;
}

async function pollLog() {
  const data = await api("GET", `/api/log?after=${state.after}`);
  const feed = $("feed");
  const atBottom = feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 8;
  for (const entry of data.entries) {
    state.after = Math.max(state.after, entry.seq);
    if (["message", "run.requested", "run.started", "run.refused", "run.completed",
         "run.accepted", "run.rejected", "run.declined"].includes(entry.kind)) {
      feed.append(renderEntry(entry));
    }
  }
  if (atBottom) feed.scrollTop = feed.scrollHeight;
  return data.entries.length > 0;
}

async function renderPlan() {
  const plan = await api("GET", "/api/plan");
  state.plan = plan;
  $("plan-summary").textContent = `Decision: ${plan.decision_state} · spent ${plan.spent} · uncommitted ${plan.uncommitted_cost}`;
  const rows = $("plan-rows");
  rows.replaceChildren();
  const select = $("request-task");
  const current = select.value;
  select.replaceChildren();
  for (const t of plan.tasks) {
    const tr = el("tr");
    tr.append(el("td", t.task_id), el("td", t.agent), el("td", t.ready ? "ready" : t.status), el("td", t.blockers.join(", ")));
    rows.append(tr);
    const opt = el("option", `${t.task_id} · ${t.agent}`);
    opt.value = t.task_id;
    select.append(opt);
  }
  if (current) select.value = current;
}

function actionButton(label, handler) {
  const b = el("button", label);
  b.type = "button";
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { await handler(); showError(""); await refresh(); } catch (err) { showError(err.message); }
    b.disabled = false;
  });
  return b;
}

function predicatesFor(taskId) {
  // The predicates come from the NEXUS instance; the owner must affirm every one.
  const task = (state.plan && state.plan.tasks.find((t) => t.task_id === taskId)) || null;
  const names = task ? task.acceptance_predicates : [];
  if (!names.length) { showError("This task has no acceptance predicates in the instance."); return null; }
  const ok = confirm(`Accepting records that each of these holds for task ${taskId}:\n\n- ${names.join("\n- ")}\n\nConfirm all?`);
  return ok ? names.slice() : null;
}

async function renderRuns() {
  const { runs } = await api("GET", "/api/runs");
  const list = $("runs");
  list.replaceChildren();
  const owner = state.me.role === "owner";
  for (const r of runs) {
    const li = el("li");
    li.append(el("div", `${r.id} · task ${r.task_id} · ${r.state}${r.actual_cost !== null ? ` · cost ${r.actual_cost}` : ""}`));
    li.append(el("div", r.instruction, "muted"));
    if (r.error) li.append(el("div", r.error, "error"));
    if (r.control_changes && r.control_changes.length) {
      li.append(el("div", `Changed files that steer future agent runs: ${r.control_changes.join(", ")}`, "error"));
    }
    const actions = el("div", null, "actions");
    if (["completed", "accepted", "rejected", "running"].includes(r.state)) {
      actions.append(actionButton("Output", async () => {
        const { output } = await api("GET", `/api/run-output?run_id=${encodeURIComponent(r.id)}`);
        const pre = $("output");
        pre.hidden = false;
        pre.textContent = output || "(no output yet)";
      }));
    }
    if (owner && r.state === "requested") {
      actions.append(actionButton("Approve", () => api("POST", "/api/runs/approve", { run_id: r.id })));
      actions.append(actionButton("Decline", async () => {
        const reason = prompt("Reason for declining:");
        if (reason) await api("POST", "/api/runs/decline", { run_id: r.id, reason });
      }));
    }
    if (owner && r.state === "running") {
      actions.append(actionButton("Stop", () => api("POST", "/api/runs/cancel", { run_id: r.id })));
    }
    if (owner && r.state === "completed") {
      actions.append(actionButton("Accept", async () => {
        const confirmed = predicatesFor(r.task_id);
        if (confirmed === null) return;
        const changes = r.control_changes || [];
        if (changes.length && !confirm(`This run changed files that steer future agent runs:\n\n- ${changes.join("\n- ")}\n\nOpen the workspace and review them first. Accept anyway?`)) return;
        const note = prompt("Review note:");
        if (note) await api("POST", "/api/runs/review", { run_id: r.id, accepted: true, confirmed_predicates: confirmed, note,
                                                         acknowledged_control_changes: changes });
      }));
      actions.append(actionButton("Reject", async () => {
        const note = prompt("Why is this result rejected?");
        if (note) await api("POST", "/api/runs/review", { run_id: r.id, accepted: false, confirmed_predicates: [], note });
      }));
    }
    li.append(actions);
    list.append(li);
  }
}

async function renderMembers() {
  if (state.me.role !== "owner") return;
  $("members-panel").hidden = false;
  const { members } = await api("GET", "/api/members");
  const list = $("members");
  list.replaceChildren();
  for (const m of members) {
    const li = el("li", `${m.name} · ${m.role}${m.disabled_at ? " · disabled" : ""} `);
    if (m.role !== "owner" && !m.disabled_at) {
      li.append(actionButton("New link", async () => {
        const { token } = await api("POST", "/api/members/reinvite", { member_id: m.id });
        $("invite-link").textContent = `${location.origin}/join#${token}`;
      }));
      li.append(actionButton("Disable", () => api("POST", "/api/members/disable", { member_id: m.id })));
    }
    list.append(li);
  }
}

async function refresh() {
  await Promise.all([renderPlan(), renderRuns(), renderMembers()]);
}

async function boot() {
  if (location.pathname === "/join" || location.hash.length > 1) await join();
  try {
    state.me = (await api("GET", "/api/me")).member;
  } catch (_) {
    $("signed-out").hidden = false;
    return;
  }
  await refreshCsrf();
  $("room").hidden = false;
  $("logout").hidden = false;
  $("who").textContent = `${state.me.name} · ${state.me.role}`;
  $("request-form").hidden = state.me.role === "viewer";
  $("message-form").hidden = false;

  $("message-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = $("message-text").value.trim();
    if (!text) return;
    try { await api("POST", "/api/messages", { text }); $("message-text").value = ""; await pollLog(); }
    catch (err) { showError(err.message); }
  });
  $("request-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      await api("POST", "/api/runs/request", { task_id: $("request-task").value, instruction: $("request-instruction").value });
      $("request-instruction").value = "";
      await refresh();
    } catch (err) { showError(err.message); }
  });
  $("invite-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      const { token } = await api("POST", "/api/members/invite", { name: $("invite-name").value, role: $("invite-role").value });
      $("invite-link").textContent = `${location.origin}/join#${token}`;
      $("invite-name").value = "";
      await renderMembers();
    } catch (err) { showError(err.message); }
  });
  $("logout").addEventListener("click", async () => {
    try { await api("POST", "/api/logout"); } finally { location.replace("/"); }
  });

  await refresh();
  await pollLog();
  setInterval(async () => {
    try { if (await pollLog()) await refresh(); } catch (err) { showError(err.message); }
  }, 2500);
}

boot();
