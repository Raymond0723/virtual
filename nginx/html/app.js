import { CommandBudget } from "./core.js";

const budget = new CommandBudget(5);
const realSide = "left"; // Shell A 為真實 VM
let currentPrompt = "ubuntu@ubuntu:~$ ";

function cleanOutput(value) {
  return value.replace(/\x1B(?:[@-_][0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1B\\))/g, "");
}

function updateBudgetUI(side) {
  const countVal = budget.remaining(side);
  document.querySelector(`#${side}-count`).textContent = countVal;
  
  const dots = document.querySelectorAll(`[data-budget="${side}"] li`);
  dots.forEach((slot, index) => {
    slot.classList.toggle("used", index >= countVal);
  });

  if (side === "right" && countVal === 0) {
    const form = document.querySelector('[data-command-form="right"]');
    form.querySelector("input").disabled = true;
    form.querySelector("button").disabled = true;
  }
}

// 隱藏 ttyd 捲軸
const ttyIframe = document.getElementById('tty-iframe');
if (ttyIframe) {
  ttyIframe.addEventListener('load', () => {
    try {
      const style = document.createElement('style');
      style.textContent = `::-webkit-scrollbar { display: none !important; } * { scrollbar-width: none !important; }`;
      ttyIframe.contentDocument.head.appendChild(style);
    } catch (e) {}
  });
}

// 表單提交事件處理
const rightForm = document.querySelector('[data-command-form="right"]');
if (rightForm) {
  rightForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    const input = rightForm.elements.command;
    const command = input.value.trim();
    if (!command) return;

    if (!budget.use("right")) {
      document.querySelector('#right-error').textContent = "這側的五次指令已用完";
      return;
    }
    
    updateBudgetUI("right");
    document.querySelector('#right-error').textContent = "";

    const outputEl = document.querySelector('#right-output');
    outputEl.textContent += `${currentPrompt}${command}\n`;
    input.value = '';

    try {
      const res = await fetch('/api/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: command })
      });
      const data = await res.json();

      if (command === 'clear') {
        outputEl.textContent = '';
      } else if (data.output) {
        outputEl.textContent += `${cleanOutput(data.output)}\n`;
      }

      if (data.prompt) {
        currentPrompt = data.prompt + " ";
      }
    } catch (err) {
      if (command === 'clear') {
        outputEl.textContent = '';
      } else {
        outputEl.textContent += `bash: ${command.split(' ')[0]}: command not found\n`;
      }
    }

    outputEl.scrollTop = outputEl.scrollHeight;
  });
}

// 投票事件處理
const dialog = document.querySelector("#result-dialog");
document.querySelectorAll("[data-vote]").forEach((button) => {
  button.addEventListener("click", () => {
    const choice = button.dataset.vote;
    const isCorrect = (choice === realSide);

    document.querySelectorAll("[data-vote]").forEach((btn) => (btn.disabled = true));

    document.querySelector("#result-label").textContent = `真實環境：Shell A`;
    document.querySelector("#result-title").textContent = isCorrect ? "判斷正確！" : "你被 Honeypot 騙過了";
    document.querySelector("#result-copy").textContent = isCorrect
      ? "你成功辨認出真實的 Linux Shell。"
      : "這次的互動已記錄為 LLM-assisted Honeypot Shell 成功欺敵。";
    
    dialog.showModal();
  });
});

document.querySelector("#restart")?.addEventListener("click", () => {
  location.reload();
});