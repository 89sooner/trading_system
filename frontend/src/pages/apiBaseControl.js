import {
  getConfiguredApiBaseUrl,
  setConfiguredApiBaseUrl,
  userMessageForError,
} from "../api/client.js";

export function initApiBaseControl() {
  const input = document.getElementById("api-base-url");
  const button = document.getElementById("save-api-base-url");
  const message = document.getElementById("api-base-message");

  if (!input || !button || !message) {
    return;
  }

  input.value = getConfiguredApiBaseUrl();

  button.addEventListener("click", () => {
    const value = input.value;
    if (!value.trim()) {
      message.textContent = "API Base URL을 입력하세요.";
      message.classList.add("error");
      return;
    }
    try {
      const saved = setConfiguredApiBaseUrl(value);
      message.textContent = `Saved: ${saved}`;
      message.classList.remove("error");
    } catch (error) {
      message.textContent = userMessageForError(error);
      message.classList.add("error");
    }
  });
}
