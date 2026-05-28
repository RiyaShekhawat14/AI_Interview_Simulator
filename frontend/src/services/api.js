import axios from "axios";

const LOCAL_BACKEND_URL = "http://localhost:8000";
const DEPLOYED_BACKEND_URL = "https://ai-interview-simulator-iu72.onrender.com";

function resolveDefaultBaseUrl() {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return LOCAL_BACKEND_URL;
    }
  }

  return DEPLOYED_BACKEND_URL;
}

export const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  resolveDefaultBaseUrl();

export function getBackendOriginLabel() {
  try {
    return new URL(BASE_URL).origin;
  } catch {
    return BASE_URL;
  }
}

const AUTH_STORAGE_KEY = "ai_interview_auth";

export function getStoredAuth() {
  try {
    return JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

export function setStoredAuth(auth) {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
}

export function clearStoredAuth() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function isAuthenticated() {
  const auth = getStoredAuth();
  return Boolean(auth?.access_token);
}

function buildHeaders(extraHeaders = {}) {
  const auth = getStoredAuth();
  return {
    ...(auth?.access_token ? { Authorization: `Bearer ${auth.access_token}` } : {}),
    ...extraHeaders,
  };
}

const apiClient = axios.create({
  baseURL: BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  config.headers = {
    ...(config.headers || {}),
    ...buildHeaders(),
  };
  return config;
});

export async function fetchJson(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: buildHeaders(options.headers || {}),
  });
  return response.json();
}

export const registerUser = async (payload) => {
  const res = await apiClient.post("/auth/register", payload);
  setStoredAuth(res.data);
  return res.data;
};

export const loginUser = async (payload) => {
  const res = await apiClient.post("/auth/login", payload);
  setStoredAuth(res.data);
  return res.data;
};

export const getCurrentUser = async () => {
  const res = await apiClient.get("/auth/me");
  return res.data;
};

export const logoutUser = () => {
  clearStoredAuth();
};

export const checkBackend = async () => fetchJson("/");

export const checkHealth = async () => fetchJson("/health");

export const getQuestion = async (
  role,
  company,
  answer = "",
  asked = [],
  category = "general",
  resumeText = ""
) => {
  const res = await apiClient.post("/question", null, {
    params: {
      role,
      company,
      answer,
      asked: asked.join("||"),
      category,
      resume_text: resumeText,
    },
  });
  return res.data;
};

export const startInterviewSession = async (role, company, resumeText = "") => {
  const formData = new FormData();
  formData.append("role", role);
  formData.append("company", company);
  formData.append("resume_text", resumeText);

  const res = await apiClient.post("/interview/start", formData);
  return res.data;
};

export const getNextInterviewQuestion = async (
  sessionId,
  lastAnswer = "",
  emotion = "Normal",
  emotionConfidence = 0
) => {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("last_answer", lastAnswer);
  formData.append("emotion", emotion);
  formData.append("emotion_confidence", String(emotionConfidence));

  const res = await apiClient.post("/interview/next", formData);
  return res.data;
};

export const submitCodeAnswer = async (
  sessionId,
  code,
  language,
  emotion = "Normal",
  emotionConfidence = 0
) => {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("code", code);
  formData.append("language", language);
  formData.append("emotion", emotion);
  formData.append("emotion_confidence", String(emotionConfidence));

  const res = await apiClient.post("/interview/submit-code", formData);
  return res.data;
};

export const getInterviewReport = async (sessionId) => {
  const formData = new FormData();
  formData.append("session_id", sessionId);

  const res = await apiClient.post("/interview/report", formData);
  localStorage.setItem("report", JSON.stringify(res.data));
  return res.data;
};

export const speechToText = async (audioFile) => {
  const contentType = audioFile?.type || "audio/webm";
  const extension = contentType.includes("wav")
    ? "wav"
    : contentType.includes("ogg")
      ? "ogg"
      : "webm";
  const formData = new FormData();
  formData.append("file", audioFile, `speech-input.${extension}`);

  const res = await apiClient.post("/speech-to-text", formData);
  return res.data;
};

export const evaluateCode = async (question, code, language) => {
  const res = await apiClient.post("/evaluate-code", {
    question,
    code,
    language,
  });
  return res.data;
};

export const detectEmotion = async (imageFile) => {
  const formData = new FormData();
  formData.append("file", imageFile, "frame.jpg");

  const res = await apiClient.post("/detect-emotion", formData);
  return res.data;
};

export const uploadResume = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await apiClient.post("/upload-resume", formData);
  return res.data;
};

export const getFinalReport = async (payload) => {
  const res = await apiClient.post("/report", payload);
  localStorage.setItem("report", JSON.stringify(res.data));
  return res.data;
};

export const getSavedReports = async (limit = 10) => {
  const res = await apiClient.get("/reports/history", {
    params: { limit },
  });
  return res.data;
};

export const getLatestReport = async () => {
  const res = await apiClient.get("/reports/latest");
  return res.data;
};

export const getReportById = async (reportId) => {
  const res = await apiClient.get(`/reports/${reportId}`);
  return res.data;
};

export const getMetrics = async () => {
  const res = await apiClient.get("/metrics");
  return res.data;
};
