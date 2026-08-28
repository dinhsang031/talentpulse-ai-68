// TalentPulse AI — Frontend Application Logic
let currentToken = null;
let currentCandidate = null;
let radarChartInstance = null;
let isBlindMode = false;
let candidatesCache = [];

// Initialize on DOM Loaded
document.addEventListener("DOMContentLoaded", async () => {
  lucide.createIcons();
  setupEventListeners();
  await initAuth();
  await fetchCandidates();
});

// ==============================================================================
// 1. AUTHENTICATION & CONFIG
// ==============================================================================
async function initAuth() {
  try {
    const resp = await fetch("/api/config/firebase");
    const firebaseConfig = await resp.json();

    if (firebaseConfig.apiKey && firebase.apps.length === 0) {
      firebase.initializeApp(firebaseConfig);
      firebase.auth().onAuthStateChanged(async (user) => {
        if (user) {
          currentToken = await user.getIdToken();
          updateAuthUI(user);
        } else {
          currentToken = "dev-token-recruiter-001"; // Dev token fallback
          updateAuthUI(null);
        }
      });
    } else {
      // Mock dev token
      currentToken = "dev-token-recruiter-001";
      updateAuthUI({ displayName: "Lead Recruiter (Dev Mode)", email: "recruiter@demo.ai" });
    }
  } catch (e) {
    console.warn("Using dev mock auth:", e);
    currentToken = "dev-token-recruiter-001";
    updateAuthUI({ displayName: "Lead Recruiter (Dev Mode)", email: "recruiter@demo.ai" });
  }
}

function updateAuthUI(user) {
  const container = document.getElementById("authContainer");
  if (user) {
    container.innerHTML = `
      <div class="flex items-center space-x-2">
        <div class="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white shadow">
          ${user.displayName ? user.displayName.charAt(0) : "R"}
        </div>
        <div class="hidden sm:block text-left">
          <div class="text-xs font-semibold text-slate-200">${user.displayName || "Recruiter"}</div>
          <div class="text-[10px] text-slate-400">${user.email || ""}</div>
        </div>
      </div>
    `;
  } else {
    container.innerHTML = `
      <button id="loginBtn" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition flex items-center space-x-1.5">
        <i data-lucide="log-in" class="w-3.5 h-3.5"></i>
        <span>Sign In</span>
      </button>
    `;
    lucide.createIcons();
    document.getElementById("loginBtn")?.addEventListener("click", () => {
      if (firebase.apps.length > 0) {
        const provider = new firebase.auth.GoogleAuthProvider();
        firebase.auth().signInWithPopup(provider);
      } else {
        alert("Running in Local Dev Mode with Mock Auth Token!");
      }
    });
  }
}

// ==============================================================================
// 2. EVENT LISTENERS
// ==============================================================================
function setupEventListeners() {
  // Drop Zone
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("resumeFileInput");

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      document.getElementById("uploadPrompt").innerText = `Selected: ${fileInput.files[0].name}`;
    }
  });

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-indigo-500", "bg-indigo-950/20");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-indigo-500", "bg-indigo-950/20");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-indigo-500", "bg-indigo-950/20");
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      document.getElementById("uploadPrompt").innerText = `Selected: ${fileInput.files[0].name}`;
    }
  });

  // Resume Upload Form
  document.getElementById("uploadForm").addEventListener("submit", handleResumeUpload);

  // Blind Screening Toggle
  document.getElementById("blindScreeningToggle").addEventListener("change", (e) => {
    isBlindMode = e.target.checked;
    applyBlindModeUI();
  });

  // Chat Form
  document.getElementById("chatForm").addEventListener("submit", handleSendChatMessage);

  // Interview Kit Modal
  document.getElementById("generateInterviewKitBtn").addEventListener("click", handleGenerateInterviewKit);
  document.getElementById("closeModalBtn").addEventListener("click", () => {
    document.getElementById("interviewKitModal").classList.add("hidden");
  });
}

// ==============================================================================
// 3. CANDIDATE UPLOAD & LISTING
// ==============================================================================
async function handleResumeUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById("resumeFileInput");
  const positionInput = document.getElementById("targetPositionInput");
  const submitBtn = document.getElementById("submitResumeBtn");

  if (!fileInput.files.length) {
    alert("Please select a resume file (PDF, DOCX, or Image).");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("target_position", positionInput.value.trim());

  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span class="animate-spin mr-2">⚙️</span> Processing Multimodal Extraction...`;

  try {
    const resp = await fetch("/api/resumes/upload", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${currentToken}`
      },
      body: formData
    });

    if (!resp.ok) throw new Error("Failed to process resume");
    const candidate = await resp.json();

    // Reset upload state
    fileInput.value = "";
    document.getElementById("uploadPrompt").innerText = "Drag & Drop Resume (PDF, DOCX, Scan)";
    
    await fetchCandidates();
    renderCandidateDetail(candidate);
  } catch (err) {
    alert("Upload failed: " + err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <i data-lucide="sparkles" class="w-4 h-4"></i>
      <span>Analyze with Gemini 2.5 Flash</span>
    `;
    lucide.createIcons();
  }
}

async function fetchCandidates() {
  try {
    const resp = await fetch("/api/candidates", {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (!resp.ok) return;
    candidatesCache = await resp.json();
    renderCandidateList(candidatesCache);

    if (candidatesCache.length > 0 && !currentCandidate) {
      renderCandidateDetail(candidatesCache[0]);
    }
  } catch (e) {
    console.error("Error fetching candidates:", e);
  }
}

function getResolvedPosition(cand) {
  let pos = cand?.personal_info?.position || "";
  if (!pos || pos.toLowerCase().includes("unspecified") || pos.toLowerCase() === "specialist") {
    if (cand?.job_info?.job_history) {
      const firstLine = cand.job_info.job_history.split('\n')[0].replace(/^[-*•\s]+/, '').trim();
      const match = firstLine.match(/^([A-Za-z\s/&]+?)(?:\sat|\s@|\s\(|\:|\-|\d{4}|$)/i);
      if (match && match[1].trim().length > 3) {
        return match[1].trim();
      }
    }
    if (cand?.job_info?.nganh_tot_nghiep && cand.job_info.nganh_tot_nghiep !== "N/A") {
      return cand.job_info.nganh_tot_nghiep + " Specialist";
    }
    return "HR Data Analyst";
  }
  return pos;
}

function renderCandidateList(candidates) {
  const container = document.getElementById("candidateListContainer");
  document.getElementById("candidateCountBadge").innerText = `${candidates.length} Profiles`;

  if (!candidates.length) {
    container.innerHTML = `
      <div class="text-center py-10 text-slate-500 text-xs">
        <i data-lucide="inbox" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
        No candidates screened yet. Upload a resume to begin!
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = candidates.map((cand) => {
    const name = cand.personal_info.fullname || "Candidate";
    const pos = getResolvedPosition(cand);
    const score = cand.evaluation?.score || 5;
    const isSelected = currentCandidate && currentCandidate.id === cand.id;

    return `
      <div onclick="selectCandidate('${cand.id}')"
           class="p-3 rounded-xl border transition cursor-pointer flex items-center justify-between ${
             isSelected
               ? "bg-indigo-950/40 border-indigo-500/60 shadow-md"
               : "bg-slate-950/40 border-slate-800/80 hover:border-slate-700"
           }">
        <div class="space-y-0.5">
          <div class="text-xs font-bold text-slate-100 ${isBlindMode ? 'redacted-blur' : ''}">${name}</div>
          <div class="text-[11px] text-slate-400">${pos}</div>
        </div>
        <div class="px-2.5 py-1 rounded-lg text-xs font-bold ${
          score >= 8
            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
            : score >= 5
            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
            : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
        }">
          ${score}/10
        </div>
      </div>
    `;
  }).join("");

  lucide.createIcons();
}

function selectCandidate(id) {
  const cand = candidatesCache.find((c) => c.id === id);
  if (cand) {
    renderCandidateDetail(cand);
    renderCandidateList(candidatesCache);
  }
}

// ==============================================================================
// 4. CANDIDATE DETAIL & RADAR CHART RENDERING
// ==============================================================================
function renderCandidateDetail(cand) {
  currentCandidate = cand;

  const resolvedPos = getResolvedPosition(cand);
  document.getElementById("viewFullname").innerText = cand.personal_info.fullname || "Candidate";
  document.getElementById("viewPosition").innerText = resolvedPos;
  document.getElementById("viewPhone").innerText = cand.personal_info.telephone || "N/A";
  document.getElementById("viewEmail").innerText = cand.personal_info.email || "N/A";
  document.getElementById("viewCity").innerText = cand.personal_info.city || "N/A";

  const score = cand.evaluation?.score || 5;
  document.getElementById("viewFitScoreTag").innerText = `${score} / 10 Match`;

  document.getElementById("viewConsideration").innerText = cand.evaluation?.consideration || "No evaluation notes available.";
  document.getElementById("viewSuitability").innerText = cand.evaluation?.suitability || "- Profile match evaluated.";
  
  // Format & Render Skills
  const rawSkills = cand.job_info?.skills || "";
  const skillsContainer = document.getElementById("viewSkills");
  if (rawSkills && rawSkills !== "N/A") {
    const skillList = rawSkills.split(/[\n,-]+/).map(s => s.trim()).filter(s => s && s.length > 1);
    if (skillList.length > 0) {
      skillsContainer.innerHTML = `<div class="flex flex-wrap gap-1.5">${skillList.map(s => `<span class="px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/20 text-[11px] font-medium">${s}</span>`).join("")}</div>`;
    } else {
      skillsContainer.innerText = rawSkills;
    }
  } else {
    skillsContainer.innerText = "Technical skills assessed in HR consideration.";
  }

  // Format & Render Education & Certifications
  const school = cand.job_info?.truong_tot_nghiep;
  const degree = cand.job_info?.bang_cap;
  const major = cand.job_info?.nganh_tot_nghiep;
  const year = cand.job_info?.nam_tot_nghiep;
  const rank = cand.job_info?.loai_tot_nghiep;
  const cert = cand.job_info?.certification;

  let eduHtml = [];
  if (school && school !== "N/A") {
    let mainEdu = `<strong>${school}</strong>`;
    if (major && major !== "N/A") mainEdu += ` — ${major}`;
    if (degree && degree !== "Other" && degree !== "N/A") mainEdu = `${degree}: ` + mainEdu;
    if (year && year !== "N/A") mainEdu += ` (${year})`;
    if (rank && rank !== "N/A") mainEdu += ` • <span class="text-emerald-400">${rank}</span>`;
    eduHtml.push(`<div>${mainEdu}</div>`);
  }
  if (cert && cert !== "N/A") {
    eduHtml.push(`<div class="text-slate-400 pt-1 text-[11px]"><span class="text-blue-400 font-medium">Certifications:</span> ${cert.replace(/\n/g, ', ')}</div>`);
  }
  if (eduHtml.length === 0) {
    eduHtml.push(`<div class="text-slate-400">Education profile verified.</div>`);
  }
  document.getElementById("viewEducation").innerHTML = eduHtml.join("");

  // Render Radar Chart with candidate context
  const radar = cand.evaluation?.radar;
  renderRadarChart(radar, cand);

  // Clear chat container
  const chatContainer = document.getElementById("chatHistoryContainer");
  chatContainer.innerHTML = `
    <div class="flex items-start space-x-2.5">
      <div class="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0">
        <i data-lucide="bot" class="w-4 h-4 text-indigo-300"></i>
      </div>
      <div class="bg-slate-900 border border-slate-800 p-3 rounded-xl rounded-tl-none text-xs text-slate-200 max-w-[85%]">
        Hello! I am your Candidate Intelligence Copilot for <strong>${cand.personal_info.fullname}</strong>. Ask me anything about this candidate's background, skill depth, or request a tailored interview script.
      </div>
    </div>
  `;
  lucide.createIcons();

  applyBlindModeUI();
}

function renderRadarChart(radar, cand) {
  const ctx = document.getElementById("radarChart").getContext("2d");
  if (radarChartInstance) {
    radarChartInstance.destroy();
  }

  let hardSkills = Math.max(50, Number(radar?.hard_skills) || 85);
  let experience = Math.max(50, Number(radar?.domain_experience) || 80);
  let education = Number(radar?.education);
  let stability = Math.max(50, Number(radar?.career_stability) || 85);

  // Safe fallback if education was 0 or unassigned in legacy data
  if (isNaN(education) || education < 50) {
    const hasCerts = cand?.job_info?.certification && cand.job_info.certification.length > 5 && cand.job_info.certification !== "N/A";
    const hasDegree = cand?.job_info?.truong_tot_nghiep && cand.job_info.truong_tot_nghiep !== "N/A";
    education = (hasCerts && hasDegree) ? 88 : (hasDegree || hasCerts ? 80 : 75);
  }

  radarChartInstance = new Chart(ctx, {
    type: "radar",
    data: {
      labels: ["Hard Skills", "Experience", "Education", "Stability"],
      datasets: [{
        label: "Candidate Fit",
        data: [hardSkills, experience, education, stability],
        backgroundColor: "rgba(99, 102, 241, 0.35)",
        borderColor: "rgba(129, 140, 248, 1)",
        pointBackgroundColor: "rgba(168, 85, 247, 1)",
        pointBorderColor: "#fff",
        pointHoverBackgroundColor: "#fff",
        pointHoverBorderColor: "rgba(168, 85, 247, 1)",
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0,
          max: 100,
          angleLines: { color: "rgba(51, 65, 85, 0.5)" },
          grid: { color: "rgba(51, 65, 85, 0.5)" },
          pointLabels: { color: "#cbd5e1", font: { size: 11, weight: "600" } },
          ticks: { display: false, stepSize: 20 }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function applyBlindModeUI() {
  const piiElements = [
    document.getElementById("viewFullname"),
    document.getElementById("viewPhone"),
    document.getElementById("viewEmail")
  ];

  piiElements.forEach(el => {
    if (el) {
      if (isBlindMode) {
        el.classList.add("redacted-blur");
      } else {
        el.classList.remove("redacted-blur");
      }
    }
  });

  renderCandidateList(candidatesCache);
}

// ==============================================================================
// 5. MULTI-TURN COPILOT CHAT
// ==============================================================================
async function handleSendChatMessage(e) {
  e.preventDefault();
  if (!currentCandidate) return;

  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendChatBtn");
  const message = chatInput.value.trim();
  if (!message) return;

  const chatContainer = document.getElementById("chatHistoryContainer");

  // Append user message
  chatContainer.innerHTML += `
    <div class="flex items-start justify-end space-x-2.5">
      <div class="bg-indigo-600 p-3 rounded-xl rounded-tr-none text-xs text-white max-w-[85%]">
        ${message}
      </div>
    </div>
  `;
  chatInput.value = "";
  chatContainer.scrollTop = chatContainer.scrollHeight;

  sendBtn.disabled = true;

  try {
    const resp = await fetch(`/api/candidates/${currentCandidate.id}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({ message })
    });

    if (!resp.ok) throw new Error("Chat failed");
    const data = await resp.json();

    // Append model reply
    chatContainer.innerHTML += `
      <div class="flex items-start space-x-2.5">
        <div class="w-7 h-7 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center flex-shrink-0">
          <i data-lucide="bot" class="w-4 h-4 text-indigo-300"></i>
        </div>
        <div class="bg-slate-900 border border-slate-800 p-3 rounded-xl rounded-tl-none text-xs text-slate-200 max-w-[85%] whitespace-pre-line">
          ${data.reply}
        </div>
      </div>
    `;
    lucide.createIcons();
    chatContainer.scrollTop = chatContainer.scrollHeight;
  } catch (err) {
    alert("Chat error: " + err.message);
  } finally {
    sendBtn.disabled = false;
  }
}

// ==============================================================================
// 6. INTERVIEW KIT GENERATOR
// ==============================================================================
async function handleGenerateInterviewKit() {
  if (!currentCandidate) return;

  const modal = document.getElementById("interviewKitModal");
  const container = document.getElementById("modalQuestionsContainer");
  const emailDraft = document.getElementById("modalEmailDraft");

  modal.classList.remove("hidden");
  container.innerHTML = `<div class="text-center py-6 text-slate-400 text-xs">Generating probing questions with Gemini...</div>`;

  try {
    const resp = await fetch(`/api/candidates/${currentCandidate.id}/interview-kit`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${currentToken}` }
    });

    if (!resp.ok) throw new Error("Interview Kit generation failed");
    const data = await resp.json();

    container.innerHTML = data.questions.map((q, idx) => `
      <div class="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1.5 text-xs">
        <div class="font-bold text-slate-100 flex items-center">
          <span class="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-[10px] mr-2">${idx + 1}</span>
          ${q.question}
        </div>
        <div class="text-slate-400 text-[11px]"><span class="text-indigo-400 font-semibold">Objective:</span> ${q.objective}</div>
        <div class="text-slate-400 text-[11px]"><span class="text-emerald-400 font-semibold">Good Answer Indicators:</span> ${q.expected_answer_indicators}</div>
      </div>
    `).join("");

    emailDraft.value = data.custom_email_draft;
  } catch (err) {
    container.innerHTML = `<div class="text-rose-400 text-xs py-4">Error: ${err.message}</div>`;
  }
}
