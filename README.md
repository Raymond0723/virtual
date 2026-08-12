# 🐚 Shellusion - LLM-assisted Honeypot Blind Test

> **五次指令，辨認真實。**  
> 一個基於 FastAPI、ttyd 與 OpenAI GPT-4o-mini 的雙生 Linux 終端機盲測系統。設計靈感源自 NCKU HITCON Honeypot 展覽測試項目。

---

## 💡 專案簡介

```text
shellusion/
├── .env.example            # 提供環境變數範本 (不含實體 Key)
├── docker-compose.yml      # Docker 容器編排檔
├── README.md               # 專案說明文件
├── nginx/
│   ├── nginx.conf          # Nginx 反向代理設定
│   └── html/               # 前端靜態網頁與腳本
│       ├── index.html
│       ├── styles.css
│       ├── app.js
│       └── core.js
└── api/                    
    ├── Dockerfile
    ├── requirements.txt
    ├── server.py
    ├── shell.py
    ├── llm.py
    ├── config.py
    └── config.toml
```


**Shellusion** 是一個雙側 CLI 盲測與誘捕系統 (Honeypot Challenge)。使用者將面對兩個看似完全相同的 Linux 終端機介面：
* **Shell A (Session A)**：真實運作中的 Ubuntu Linux VM（透過 `ttyd` 連線）。
* **Shell B (Session B)**：由 OpenAI GPT-4o-mini 與 FastAPI 模擬的虛擬 Shell (LLM Honeypot)。

每位測試者在每側僅有 **5 次指令輸入額度**，必須透過觀察指令回應（如系統檔案、錯誤訊息、執行延遲等），判斷哪一側才是真實的 Linux 環境。

---

## 🏗️ 系統架構

系統透過 Docker Compose 進行多容器整合，所有流量統一由 Nginx (Port 80) 進行派發：

```text
[ Client Browser ]
       │
       ▼ (Port 80)
┌───────────────────────────────────────────┐
│               Nginx Server                │
└──────┬─────────────────────────────┬──────┘
       │                              │
       ├─► /ttyd/                     ├─► /api/
       ▼ (Port 7681)                  ▼ (Port 8000)
┌─────────────────────────┐  ┌─────────────────────────┐
│   Session A (Real VM)   │  │ Session B (LLM Engine)  │
│      ttyd + bash        │  │ FastAPI + GPT-4o-mini   │
└─────────────────────────┘  └─────────────────────────┘
```

---

## 🚀 快速開始 (Deployment)

### 前置需求
* [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)
* OpenAI API Key

### 安裝步驟

1. **複製專案庫 (Clone Repository)**
   ```bash
   git clone [https://github.com/your-username/shellusion-honeypot.git](https://github.com/your-username/shellusion-honeypot.git)
   cd shellusion-honeypot
   ```

2. **設定環境變數**
   將 `.env.example` 複製為 `.env` 並填入你的 OpenAI API Key：
   ```bash
   cp .env.example .env
   nano .env
   ```

3. **啟動 Docker 服務**
   ```bash
   docker compose up -d --build
   ```

---

## ⚙️ 客製化設定

### 修改 LLM 預設行為與黑名單
可透過編輯 `api/config.toml` 設定 LLM 的 Shell 身分及提示字元格式：

```toml
[shell]
hostname = "ubuntu"
username = "ubuntu"
home = "/home/ubuntu"
prompt = "{username}@{hostname}:{cwd}$ "

[llm]
enabled = true
model = "gpt-4o-mini"
```

若需新增或修改被拒絕執行的指令（如 `vim`, `ssh` 等），請於 `api/config.py` 中的 `DEFAULT_DENY_COMMANDS` 進行調整。

---
