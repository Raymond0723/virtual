# 虛擬數位分身(Virtual VTuber)

本地端、純開源模型驅動的「虛擬數位分身」專案:輸入文字,自動生成背景、克隆語音、產生說話人像影片,並合成為最終畫面。全部推論皆在本機 GPU(NVIDIA RTX 3090)上執行,不呼叫任何雲端 API。

## 核心限制:不使用大陸出品的模型/API

本專案在模型選型上明確排除**大陸(中國)機構出品、大陸蒸餾或微調過**的模型與 API,即使那些模型品質更好也一律排除。詳見下方〈模型來源一覽〉。

## 專案架構

整個系統拆成 4 個獨立子專案,各自有自己的 Python 虛擬環境(避免依賴衝突),透過 HTTP(`gradio_client`)互相溝通,由第 4 個子專案(整合層)統一編排:

```
使用者輸入文字(背景描述 + 說話內容)+ 上傳(或錄製)語音、照片
        │
        ▼
[整合層自動拉起下列三個服務]
        │
        ├──→ 子專案 1:文字 → 背景圖(FLUX.1-dev)
        ├──→ 子專案 2:文字 → 克隆語音(Chatterbox V3)
        └──→ 子專案 3:照片 + 語音 → 說話影片(Wav2Lip)
        │
        ▼
[整合層:去背後疊加到背景圖上,合成最終影片(rembg + ffmpeg)]
        │
        ▼
瀏覽器播放最終結果
```

## 檔案結構

```
virtual_vtuber/
├── README.md                 # 子專案 1 自己的設定/執行說明
├── PROJECT_OVERVIEW.md        # 本文件:整體專案概覽
├── rea.sh                     # 一鍵啟動/停止/查看整合層服務狀態的腳本
│
├── app.py                     # 【子專案1:背景圖+人臉置換】Gradio 介面,port 7860
├── background_gen.py          #   文字 → 背景圖(FLUX.1-dev)
├── face_swap.py                #   人臉置換(InsightFace,選填功能)
├── models/                     #   人臉置換權重(inswapper_128.onnx,需手動放置)
├── requirements.txt / .venv/   #   子專案1 自己的 Python 3.8 環境
├── tests/                      #   子專案1 的測試
│
├── tedyu/                      # 【子專案2:語音克隆】Gradio 介面,port 7861
│   ├── app.py
│   ├── voice_clone.py          #   文字 → 克隆語音(Chatterbox Multilingual TTS V3)
│   ├── voices(input)/          #   參考語音樣本
│   ├── chatterbox/              #   Chatterbox 原始碼(git clone,不受本 repo 追蹤)
│   ├── clone_v3.py, test_v3.py #   早期手動實驗雛形,已被正式版取代,保留供參考
│   ├── pyproject.toml / uv.lock / .venv/  # 子專案2 自己的 Python 3.11 環境
│   └── tests/
│
├── talking_head/                # 【子專案3:說話影片生成】Gradio 介面,port 7862
│   ├── app.py
│   ├── lip_sync.py              #   subprocess 呼叫 Wav2Lip 做嘴型同步
│   ├── Wav2Lip/                  #   Wav2Lip 原始碼(git clone,不受本 repo 追蹤)
│   │   └── checkpoints/          #   模型權重(wav2lip_gan.pth,需手動下載)
│   ├── fixtures/                 #   測試用照片/音檔樣本
│   ├── requirements.txt / .venv/ #   子專案3 自己的 Python 3.11 環境
│   └── tests/
│
├── integration/                  # 【子專案4:整合層】Gradio 介面,port 7863(主要入口)
│   ├── app.py                    #   最終網頁介面
│   ├── process_manager.py        #   自動啟動/健康檢查/關閉子專案1、2、3
│   ├── orchestrator.py           #   依序呼叫三個子服務
│   ├── compositor.py             #   去背(rembg)+ 疊加 + 音軌合併(ffmpeg)
│   ├── requirements.txt / .venv/ #   整合層自己的 Python 3.11 環境
│   └── tests/
│
└── docs/lol/                     # 設計文件與實作計畫(spec/plan)
    ├── specs/                    #   每個子專案的設計文件
    └── plans/                    #   每個子專案的實作計畫
```

**為什麼每個子專案都有自己獨立的虛擬環境?** 因為各自依賴的套件版本衝突(例如子專案1 用 Python 3.8、FLUX 需要特定版 PyTorch;子專案2、3 需要 Python 3.11 才能裝到相容的新版 PyTorch)。整合層(子專案4)不 import 任何子專案的程式碼,只透過 HTTP 呼叫它們已啟動的 Gradio 服務,藉此完全隔離依賴問題。

## 模型來源一覽(標註是否為大陸出品)

| 功能 | 採用模型 | 出品單位/來源 | 是否大陸出品 |
|---|---|---|---|
| 文字→背景圖 | FLUX.1-dev | Black Forest Labs(德國) | 否 |
| 人臉偵測(子專案1) | buffalo_l(InsightFace) | InsightFace 專案(國際團隊) | 否 |
| 人臉置換(子專案1,選填功能) | inswapper_128.onnx | **來源不明**,原始發布者匿名,官方已下架,現存版本皆為非官方鏡像流通 | ⚠️ **無法確認,血統不乾淨**——這是本專案唯一的例外,屬於已知、已記錄的取捨(見下方說明) |
| 文字→語音克隆 | Chatterbox Multilingual TTS V3 | Resemble AI(美國) | 否 |
| 照片+語音→說話影片 | Wav2Lip | IIIT Hyderabad(印度) | 否 |
| 去背合成(整合層) | U2-Net(透過 rembg) | University of Alberta(加拿大) | 否 |

### 曾經評估但因為是大陸出品而排除的選項

- **Talking-Head 模型**:SadTalker、MuseTalk、Hallo、AniPortrait、LivePortrait —— 目前這個領域最先進的開源模型幾乎都出自大陸研究機構(騰訊、阿里、快手、螞蟻等),品質明顯優於 Wav2Lip,但因為出品單位問題全數排除,改用畫質較舊但血統乾淨的 Wav2Lip。
- **人臉修復/超解析**:GFPGAN、CodeFormer、Real-ESRGAN —— 同樣幾乎都是大陸機構出品,因此整合層的合成流程刻意不搭配這類模型做畫質後製。
- **去背模型的一次誤用事件**:`rembg` 套件在某次版本更新後,預設模型悄悄換成 BRIA RMBG-2.0(血統可能沾到大陸,授權也是非商用限制),開發過程中發現後已修正為明確指定 U2-Net,不依賴套件預設值。

### 已知例外:`inswapper_128.onnx`

這是本專案在「不用大陸模型」這條原則上**唯一的妥協**。原因:目前沒有品質足夠、血統完全乾淨、且「單張圖免訓練」的即時換臉替代方案(唯一乾淨的替代品 DeepFaceLab 需要針對單一身分訓練數小時到數天,不適合互動式流程)。這個檔案不會自動下載,需要使用者自行從信任的來源取得,並放置於 `models/inswapper_128.onnx`。人臉置換是**選填功能**,不放這個檔案的話,子專案1 的純背景圖生成功能完全不受影響。

## 各子專案的環境建置與已知前置需求

詳細建置步驟請參考各子專案自己的 `README.md`(根目錄、`tedyu/README.md`、`talking_head/README.md`、`integration/README.md`)。整體上線前還需要:

1. Hugging Face 帳號授權(FLUX.1-dev 是 gated model)
2. 手動下載 `models/inswapper_128.onnx`(選填,人臉置換功能才需要)
3. 手動下載 `talking_head/Wav2Lip/checkpoints/wav2lip_gan.pth`(Google Drive,無法腳本化下載)
4. 系統安裝 `ffmpeg`(`sudo apt install -y ffmpeg`)

## 快速啟動

```bash
./rea.sh          # 清掉舊行程、啟動整合層(自動拉起全部四個服務)
./rea.sh status   # 查看服務狀態
./rea.sh stop     # 全部停止
```

啟動後,從您自己的電腦建立 SSH 本地端口轉發:

```bash
ssh -L 7863:localhost:7863 <your-ssh-alias>
```

瀏覽器開啟 `http://localhost:7863`。所有服務皆僅監聽 `127.0.0.1`,不會對外網路開放。
