# 模型與技術細節
#  ggg
本文件補充 `README.md`〈模型來源一覽〉表格背後的技術原理:每個模型實際上是怎麼運作的、為什麼
選它、資料/技術從哪個國家/機構來。`README.md` 是專案總覽,本文件是給想理解「底層到底在做
什麼」的人看的技術細節。

## 模型總覽表

| 用途 | 模型/技術 | 出品單位(國家) | 授權 |
|---|---|---|---|
| 文字 → 背景圖 | FLUX.1-dev | Black Forest Labs(德國) | 非商用開放權重 |
| 人臉偵測/辨識 | buffalo_l(InsightFace) | InsightFace 專案(國際團隊) | 開源 |
| 人臉置換 | inswapper_128.onnx | **來源不明**,原始發布者匿名,官方已下架 | 不明,本專案唯一已知例外 |
| 文字轉語音克隆(TTS) | Chatterbox Multilingual TTS V3 | Resemble AI(美國) | MIT |
| 聲音轉換(Voice Conversion) | kNN-VC | Stellenbosch University(南非) | MIT |
| 嘴型同步/說話影片生成 | Wav2Lip | IIIT Hyderabad(印度) | 僅限個人/研究/非商業 |
| Wav2Lip 內部用的人臉偵測器 | S3FD | ⚠️ 見下方〈已知血統瑕疵〉 | 隨 Wav2Lip 附帶 |
| 去背合成 | U2-Net(透過 rembg) | University of Alberta(加拿大) | 開源 |
| 對話大腦(LLM) | Llama 3.1-8B-Instruct | Meta(美國) | Llama 3.1 Community License |
| 安全防護(內容審核) | Llama Guard 3-8B | Meta(美國) | Llama 3.1 Community License |
| RAG 嵌入模型 | paraphrase-multilingual-MiniLM-L12-v2 | Sentence-Transformers(德國,基於微軟多語 MiniLM) | Apache 2.0 |
| RAG 向量資料庫 | ChromaDB | Chroma(美國) | Apache 2.0 |
| 語音辨識(ASR) | Whisper(base) | OpenAI(美國) | MIT |
| 語音活動偵測(VAD,自動接話用) | WebRTC VAD(`webrtcvad`) | Google(美國,WebRTC 專案的一部分) | BSD |

---

## 專案目錄結構

```
virtual_vtuber/
├── README.md / MODELS.md      # 專案總覽 / 本文件(技術細節)
├── rea.sh                      # 一鍵啟動/停止/查看整合層服務狀態
│
├── app.py                      # 【子專案1:背景圖+人臉置換】port 7860
├── background_gen.py           #   文字 → 背景圖(FLUX.1-dev)
├── face_swap.py                 #   人臉置換(InsightFace,選填;支援圖片與整段影片逐幀換臉)
├── models/                      #   inswapper_128.onnx(需手動放置,子專案1、5 共用)
├── requirements.txt / .venv/    #   Python 3.8 環境(FLUX 需要的版本)
├── tests/
│
├── chatterbox/                  # 【子專案2:語音克隆(TTS)】port 7861
│   ├── app.py / voice_clone.py  #   文字 → 克隆語音(Chatterbox Multilingual TTS V3)
│   ├── voices(input)/           #   參考語音樣本
│   ├── chatterbox/               #   Chatterbox 原始碼(git clone,不受本 repo 追蹤)
│   ├── pyproject.toml / uv.lock / .venv/  # Python 3.11 環境
│   └── tests/
│
├── talking_head/                 # 【子專案3:照片+語音→說話影片】port 7862
│   ├── app.py / lip_sync.py      #   subprocess 呼叫 Wav2Lip(靜態照片模式,--static True)
│   ├── Wav2Lip/                   #   Wav2Lip 原始碼(git clone,不受本 repo 追蹤)
│   ├── fixtures/ / requirements.txt / .venv/ / tests/
│
├── integration/                  # 【子專案4:整合層,主要入口】port 7863
│   ├── app.py                     #   最終網頁(「文字生成」+「影片換臉換聲」兩個分頁)
│   ├── process_manager.py         #   自動啟動/健康檢查/關閉子專案1、2、3、5
│   ├── orchestrator.py            #   以 HTTP(gradio_client)呼叫其他子專案的服務
│   ├── compositor.py              #   去背(rembg)+ 疊加 + 音軌合併(僅「文字生成」流程用)
│   └── requirements.txt / .venv/ / tests/
│
└── video_talking_head/           # 【子專案5:影片換臉+換聲說話】port 7864
    ├── app.py                     #   本子專案自己的獨立網頁
    ├── lip_sync_video.py          #   subprocess 呼叫 Wav2Lip(影片模式,逐幀,無 --static)
    ├── face_swap_video.py         #   InsightFace 逐幀換臉(獨立重新實作,不 import 根目錄 face_swap.py)
    ├── voice_conversion.py        #   kNN-VC 聲音轉換(直接對音訊波形操作,不經過文字/TTS)
    ├── voice_source.py            #   決定用 voice_conversion(保留原內容)或直接上傳的音檔
    ├── pipeline.py                #   編排:先對嘴型(Wav2Lip)再換臉(InsightFace)
    ├── Wav2Lip/                    #   獨立 git clone(跟子專案3的是兩份獨立副本)
    ├── models/                     #   symlink 至根目錄 models/inswapper_128.onnx
    ├── fixtures/                   #   測試用影片/照片/音檔樣本(含真實小型樣本)
    └── requirements.txt / .venv/ / pytest.ini / tests/
```

**為什麼每個子專案都有自己獨立的虛擬環境?** 各自依賴的套件版本會衝突(子專案1 需要
Python 3.8 搭配 FLUX 指定版本的 PyTorch;子專案2、3、4、5 都需要 Python 3.11 才裝得到相容
的新版 PyTorch/CUDA)。整合層完全不 `import` 任何子專案的程式碼,只透過 HTTP 呼叫它們已
啟動的 Gradio 服務,依賴問題因此徹底隔離——即使某個子專案的環境壞掉,頂多是那個服務打不通、
回傳錯誤訊息,不會直接讓整合層或其他子專案跟著掛掉。

## 架構:各子專案如何互相運作

整個系統其實是**兩條獨立的產線**,共用同一個整合層入口(port 7863),但彼此互不依賴:

```
                        使用者瀏覽器 → http://localhost:7863(整合層)
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                        │
             分頁一:文字生成                          分頁二:影片換臉換聲
                    │                                        │
                    ▼                                        ▼
      整合層依序呼叫(HTTP,gradio_client):          整合層只呼叫「一個」服務:
                    │                                        │
      1. 子專案1(7860)文字→背景圖                    子專案5(7864)
      2. 子專案2(7861)文字→克隆語音                  ── 內部自己完成全部三件事,
      3. 子專案3(7862)照片+語音→說話影片                不再對外呼叫任何其他子專案:
      4. 整合層自己:去背+疊加+合成(compositor.py)      a. Wav2Lip 對嘴(影片模式)
                    │                                        b. kNN-VC 或直接音檔 → 新聲音
                    ▼                                        c. InsightFace 逐幀換臉
                最終影片                                       │
                                                              ▼
                                                          最終影片
```

**關鍵差異**:分頁一的四個步驟是**跨服務、依序呼叫**的長鏈(任何一站塞車,整條都要等);
分頁二(子專案5)則是**自己包辦到底**的單一服務——這是刻意的設計決策,因為聲音轉換
(kNN-VC)最初曾經考慮做成呼叫子專案2(Chatterbox)的方案,但後來改成直接對音訊波形操作
（見上方〈聲音轉換:kNN-VC〉一節),不再需要文字這個中介、也就不再需要呼叫語音服務,子專案5
因此變得完全自我包含,只在啟動時被整合層的 `process_manager.py` 拉起、健康檢查通過即可,
執行期間不再對其他子專案發出任何請求。

**每個服務暴露的介面**都是同一套慣例:Gradio 應用程式本身就是 HTTP 伺服器,`gradio_client`
呼叫時固定打 `api_name="/handle_generate"` 這個端點,回傳 `(結果檔案路徑或 None, 狀態文字)`
的二元組——呼叫端一律用「回傳 `None`」判斷失敗,而不是靠例外(exception)傳遞錯誤,這樣
就算某個子專案內部出錯,也不會把整條呼叫鏈炸掉,只會沿路把清楚的錯誤訊息往上傳。

---

## 1. 文字 → 背景圖:FLUX.1-dev

**出品**:Black Forest Labs(德國,由前 Stable Diffusion 核心團隊創立)。

**原理**:FLUX.1 是一個 **rectified flow transformer**(整流流匹配 transformer,屬於
diffusion model 的一種變體,參數量約 120 億)。跟傳統 DDPM 系擴散模型「一步步去噪」不同,
rectified flow 學習的是一條從「純噪聲」到「目標圖片」的**直線路徑**(而非彎曲的擴散軌跡),
理論上能用更少的取樣步數達到相近品質。模型本體是一個混合 DiT(Diffusion Transformer)架構,
文字提示先經過 T5/CLIP 文字編碼器轉成 embedding,再透過 cross-attention 引導 transformer
在 latent space 中逐步生成圖片,最後用 VAE decoder 還原成像素。本專案(`background_gen.py`)
只呼叫其文生圖(text-to-image)功能生成場景背景,不涉及圖生圖或 ControlNet 引導。

## 2. 人臉偵測與辨識:buffalo_l(InsightFace)

**出品**:InsightFace 開源專案,國際團隊維護。

**原理**:`buffalo_l` 是一組模型包,包含:
- **人臉偵測**:基於 RetinaFace 系架構,單階段(single-stage)偵測人臉框與 5 個關鍵點
  (雙眼、鼻尖、嘴角)。
- **人臉辨識/嵌入**:採用 **ArcFace**(Additive Angular Margin Loss)訓練的 ResNet 骨幹,
  把每張人臉編碼成一個 512 維的身分向量(embedding)。這個向量的特性是「同一人的不同照片,
  向量夾角(cosine 距離)很近;不同人則遠」,是後續人臉置換的身分依據。

本專案在 `face_swap.py`(子專案1)與 `face_swap_video.py`(子專案5)中都用它來:
(a) 找出畫面中「最大的」人臉框、(b) 抽取目標人臉照片的身分向量。

## 3. 人臉置換:inswapper_128.onnx

**出品**:來源不明。原始發布者身分不明,官方管道已下架,現存版本全數來自非官方鏡像流通。
這是本專案「排除大陸出品模型」原則下**唯一的例外**,詳見 `README.md`〈已知例外〉段落——
沒有品質足夠、血統清楚、且「單張照片免訓練」的替代方案。

**原理**(one-shot face swap,免訓練):
1. 用 buffalo_l 從**目標人臉照片**抽出 512 維身分向量(見上一節)。
2. 用同一個偵測器找出**場景畫面**(或影片每一幀)中要被置換的那張臉,取得其對齊後的臉部
   crop。
3. 把場景臉部影像丟進一個 **GAN 生成器**(inswapper 的核心),生成器同時接收「場景臉的
   姿態/表情/光線資訊」與「目標身分向量」兩路輸入——身分向量通常透過類似 AdaIN
   (Adaptive Instance Normalization)的機制注入生成器中間層,讓輸出影像**保留原場景的
   姿勢、表情、光線**,但五官特徵換成目標身分。這跟 SimSwap、FaceShifter 這類論文提出的
   「身分注入(identity injection)」概念是同一個技術路線。
4. 生成的 128×128 臉部影像,依照偵測到的臉部框幾何關係做仿射變換(affine warp)貼回
   原畫面對應位置(paste-back),邊緣做羽化混合避免明顯接縫。

本專案的**逐幀影片換臉**(`swap_face_video()` / `swap_face_frames()`)就是把上述流程對
影片的每一幀各自跑一次,偵測不到臉的幀直接跳過、保留原畫面(不會讓整段影片失敗)。

## 4. 文字轉語音克隆(TTS):Chatterbox Multilingual TTS V3

**出品**:Resemble AI(美國)。MIT 授權。

**原理**(從實際原始碼確認,`chatterbox/chatterbox/src/chatterbox/`):
- **T3(Text-to-Token)模組**:骨幹是一個 **520M 參數的 LLaMA 風格 transformer**
  (`llama_config_name = "Llama_520M"`),把輸入文字 token 化後,以自迴歸方式生成一串
  「語音 token」(speech token),生成過程會用**參考語音抽出的說話人特徵**做條件約束
  (conditioning),這就是「零樣本聲音克隆」的關鍵——不需要針對某人重新訓練,只要幾秒鐘
  參考音檔就能抽出足以代表其音色的向量。
- **VoiceEncoder**:負責從參考音檔抽取說話人嵌入向量(speaker embedding),原理與人臉辨識
  的 embedding 概念類似,只是換成聲音領域。
- **S3Gen 模組**:把 T3 產生的語音 token 轉回實際波形,內部結合 **flow matching**(整流
  流匹配,跟 FLUX 用的是同一大類生成技術,只是應用在聲音上)產生聲學特徵,再用
  **HiFiGAN** 聲碼器(vocoder)把聲學特徵轉成最終音訊波形。另外還有一個 **x-vector**
  模組進一步強化說話人音色的穩定性。
- **Perth 浮水印**:Chatterbox 官方在每一段生成的音訊裡都嵌入 Resemble AI 自家的
  **Perth(Perceptual Threshold)神經網路浮水印**——人耳聽不出來,但即使音檔被壓縮成
  MP3、剪輯過,仍可用官方工具偵測出「這是 AI 生成的」,是負責任 AI 的實踐(本專案未主動
  停用這個機制,所有透過 Chatterbox 生成的音檔皆帶有此浮水印)。

支援 23 種語言(含中文),本專案呼叫時語言參數固定傳 `"zh"`。

## 5. 聲音轉換(Voice Conversion):kNN-VC

**出品**:Baas、van Niekerk、Kamper,Stellenbosch University(南非),論文發表於
Interspeech 2023《Voice Conversion With Just Nearest Neighbors》。MIT 授權。

**這跟第 4 點的「聲音克隆」是完全不同的技術**,用途也不同:

| | Chatterbox(TTS 聲音克隆) | kNN-VC(聲音轉換) |
|---|---|---|
| 輸入 | 一段**文字** + 參考音色 | 一段**現成音訊**(要被轉換的原始語音) + 參考音色 |
| 輸出內容 | 照文字**重新生成**一段全新語音 | **原始語音**的內容原封不動,只換音色 |
| 用在哪 | 整合層「文字生成」分頁(講稿是使用者打的字) | 子專案5「影片換臉換聲」的聲音克隆模式(保留影片原本講的話) |

**原理**(免訓練,zero-shot,不經過文字這個中介):
1. 用預訓練的 **WavLM-Large**(3.15 億參數的自監督語音表徵模型,微軟研究院發表的通用語音
   基礎模型架構——本專案使用的是 kNN-VC 作者釋出、基於 WavLM 微調過的權重)把來源語音的
   每一小段(frame)編碼成高維特徵向量,這些向量帶有「語音內容/音素資訊」但相對不那麼綁定
   特定說話人音色。
2. 同樣用 WavLM 把參考語音(要模仿的音色)編碼成一組特徵向量,當作「比對資料庫」
   (matching set)。
3. 對來源語音的**每一個**特徵向量,在參考語音的比對資料庫中做 **k 近鄰(k-Nearest
   Neighbors,預設 k=4)搜尋**,找出最相似的幾個參考特徵、取平均,直接**替換**掉來源的
   特徵向量——這一步完全是非參數化的向量比對,沒有任何神經網路需要「訓練」或「微調」,
   這正是這個方法叫 kNN-VC 的原因,也是它能做到單一（或少量）參考樣本就有效轉換的關鍵。
4. 把替換後的特徵序列丟進 **HiFiGAN 聲碼器**(跟 Chatterbox 用的是同一類技術,但是
   kNN-VC 自己訓練的權重)還原成音訊波形。

因為內容/語音時長完全來自步驟 1 抽取的原始特徵序列(只是把「音色」相關的成分替換掉),輸出
音檔的**長度、停頓、語氣起伏幾乎跟原始語音一致**——這正是子專案5 用它取代「文字轉語音」的
原因:使用者要的是「內容不變、只換音色」,而不是「重新讀一段新台詞」。

本專案在 `video_talking_head/voice_conversion.py` 中的做法:先用 ffmpeg 把來源(可能是
整段影片)跟參考音檔都正規化成 16kHz 單聲道 wav,再呼叫上述流程。

## 6. 嘴型同步/說話影片生成:Wav2Lip

**出品**:IIIT Hyderabad(印度理工學院海得拉巴分校),論文《A Lip Sync Expert Is All You
Need for Speech to Lip Generation In the Wild》,ACM Multimedia 2020。**僅限個人/研究/
非商業用途**。

**原理**(GAN + 一個關鍵的「專家判別器」):
- **生成器(Generator)**:一個 encoder-decoder 架構。臉部影像 encoder 把輸入人臉(遮住
  下半臉,只留上半臉當作身分/姿態參考)編碼成特徵;音訊 encoder 把對應的 mel-spectrogram
  (梅爾頻譜,聲音的時頻表示)編碼成特徵;兩路特徵在 decoder 中融合,只重繪臉部**下半部**
  (嘴巴周圍區域),上半臉與背景維持原樣直接沿用,這也是為什麼 Wav2Lip 對「換臉之外的其他
  部分」失真風險很低。
- **這篇論文最核心的貢獻是「SyncNet 專家判別器」**:一個**事先單獨訓練好、凍結權重**的
  判別網路,專門評估「這段嘴型動作」跟「這段聲音」是否同步吻合(輸出一個同步分數)。訓練
  Wav2Lip 生成器時,除了一般的 GAN 判別器(評估畫面像不像真的)之外,額外用這個 SyncNet
  的同步分數當作**強力的監督訊號**,逼生成器把嘴型對得準,而不只是畫面好看——這正是論文
  標題「A Lip Sync Expert Is All You Need」的意思。
- 推論時是**逐幀**進行:把整段音訊切成跟影格對應的 mel-spectrogram 片段,搭配對應畫面
  逐幀跑生成器。

**本專案的兩種呼叫模式**:
- 子專案3(`talking_head/`):`--static True`,只用**一張固定照片**重複貼滿所有影格,
  相當於「照片 + 語音 → 說話影片」。
- 子專案5(`video_talking_head/`):**不加** `--static`,對**整段來源影片的每一幀**分別
  做人臉偵測與嘴型合成,這樣影片中人物原本的頭部動作、背景都會保留,只有嘴型跟著新語音變。

**本專案對官方程式碼做的兩處必要修補**(詳細記錄在 `video_talking_head/README.md`,只影響
子專案5 自己 clone 的 `Wav2Lip/`,因為該目錄不受 git 追蹤,重新部署需要重新套用):
1. `load_model()`:部分流通的 `wav2lip_gan.pth` 鏡像是用 `torch.jit.save` 存的,新版
   `torch.load()` 會誤判成 TorchScript 模組而回傳錯誤型別,已修補成同時相容兩種格式。
2. `face_detect()`:原始程式碼只要「任何一幀」偵測不到臉就讓整段影片失敗——對真實世界素材
   (例如電視新聞剪輯,畫面常被跑馬燈/圖卡佔滿完全沒有臉)太嚴格。已修補成偵測不到臉的幀
   沿用最近一次偵測到的臉部位置,只有整段影片從頭到尾都沒有一幀偵測到臉才會真的報錯。

## 7. ⚠️ 已知血統瑕疵:S3FD(Wav2Lip 內部用的人臉偵測器)

Wav2Lip 本身在做嘴型同步前,需要先在每一幀裡找到臉的位置,用的是 **S3FD**
(Single Shot Scale-invariant Face Detector)。查證後這篇論文的作者單位包含**中國科學院**
(Chinese Academy of Sciences)——這是專案審查模型來源時**先前沒有特別標註**的一個環節,
在此誠實補上:這是**隨 Wav2Lip 官方推薦設定一起附帶安裝**的子元件(權重下載連結本來就寫在
`talking_head/README.md` 與 `video_talking_head/README.md` 的建置步驟裡),只做「畫面中
有沒有臉、臉在哪裡」的偵測用途,不涉及身分辨識或內容生成,風險程度遠低於 inswapper_128
這種直接決定輸出內容身分的模型——但基於本專案一貫「如實記錄、不隱瞞」的原則,仍在此明確
記錄這個既有的技術依賴。

## 8. 去背合成:U2-Net(透過 rembg)

**出品**:University of Alberta(加拿大)。

**原理**:U²-Net(U-squared-Net)是一個「巢狀 U 型」(nested U-shape)的顯著物件偵測
(salient object detection)網路,設計目的就是精準框出畫面中的「主要物件」並產生前景/
背景的像素級遮罩(mask),不需要額外的邊界框標註。整合層(`integration/compositor.py`)
用它把「文字生成」分頁產生的說話人像影片去背,疊加到 FLUX 生成的背景圖上合成最終畫面。

`rembg` 套件在某次版本更新後,預設模型一度悄悄換成 BRIA RMBG-2.0(血統可能沾到大陸、授權
也偏非商用限制),開發過程中發現後已修正為在程式碼中**明確指定** U2-Net,不依賴套件預設值。

## 9. 對話大腦(LLM):Llama 3.1-8B-Instruct

**出品**:Meta(美國)。透過 **Ollama**(本機推論伺服器,美國開源專案)在本機載入 GGUF
量化權重(Q4_K_M,約 4.9GB)執行,不呼叫任何雲端 API。

**原理**:標準的 decoder-only transformer(自迴歸語言模型),80 億參數,經過指令微調
(instruction-tuned)使其擅長遵循系統提示詞、多輪對話。子專案6(`digital_human/`)把
「虛擬人的個性設定 + RAG 檢索到的相關記憶」組成系統提示詞,再把使用者的訊息當作 user
turn 送進去,模型輸出的文字就是虛擬人的回覆。

## 10. 安全防護:Llama Guard 3-8B

**出品**:Meta(美國),跟 Llama 3.1 同家族。

**原理**:本身也是一個 LLM,但經過專門微調成「內容安全分類器」——輸入一段文字,輸出
`safe` 或 `unsafe` 加上違反的分類代碼(S1~S14,涵蓋暴力、仇恨言論、大規模殺傷性武器等
14 種類別)。子專案6 在使用者的訊息**進入主要 LLM 之前**先過這一關,分類為 `unsafe` 就
直接擋下,不會讓內容碰到主要對話模型或觸發 RAG 檢索。

## 11. RAG 嵌入模型:paraphrase-multilingual-MiniLM-L12-v2

**出品**:Sentence-Transformers 專案(德國 UKP Lab 維護),模型骨幹基於微軟研究院的多語
MiniLM。

**原理**:把一段文字(不論中文、英文或其他語言)編碼成一個固定維度的向量,語意相近的句子
向量距離也相近——原理上跟前面 ArcFace 做人臉嵌入、VoiceEncoder 做聲音嵌入是同一套「把
內容映射到向量空間、用距離衡量相似度」的概念,只是這次映射的是文字語意。子專案6 用它把
虛擬人的每一則私人記憶都編碼成向量存進 ChromaDB,使用者每講一句話,也編碼成向量,去資料庫
裡找語意最相近的幾則記憶,餵給 LLM 當作上下文——這就是 RAG(檢索增強生成)。

**踩過的坑**:一開始選用英文專用的 `all-MiniLM-L6-v2`,實測對中文語句的語意檢索完全不準
(問「你養什麼寵物」檢索不到「我養了一隻貓」的記憶,反而抓到不相關的內容),換成這顆真正
支援多語言的模型後才正確運作——這是本專案完全中文情境下,選嵌入模型必須特別注意的地方。

## 12. RAG 向量資料庫:ChromaDB

**出品**:Chroma(美國)。純本機運作(`PersistentClient`,資料存在本機資料夾),不需要
另外架設資料庫伺服器,單機互動式應用最簡單的選擇。

---

## 影片換臉換聲完整流程(子專案5)

這是本專案最新加入的功能,把上面第 3、5(或 4)、6 點的模型串成一條管線,順序經過特別設計:

```
上傳:來源影片(某人講話)+ 目標人臉照片 + 參考聲音(或直接上傳音檔)
        │
        ▼
[Step 1] Wav2Lip(影片模式,§6)
  先把來源影片的嘴型對上「新語音」——
  新語音來自 kNN-VC 聲音轉換(§5,保留原內容只換音色)或直接上傳的音檔
  → 產出:嘴型已對好新語音,但臉孔身分還是原影片的人
        │
        ▼
[Step 2] InsightFace 逐幀換臉(§2 + §3)
  對 Step 1 輸出的每一幀,偵測最大人臉 → 換成目標人臉照片的身分
  → 產出:目標人臉身分,講出新內容(或維持原內容但音色不同),嘴型正確
        │
        ▼
最終輸出影片(音軌從 Step 1 的輸出接續,確保帶有新聲音)
```

**為什麼是「先對嘴、再換臉」而不是相反**:inswapper 這類換臉模型是逐幀貼合當下表情做身分
置換的技術。如果換臉在前,Wav2Lip 之後再對「已經換過臉」的畫面做人臉偵測與嘴型合成,穩定性
會變差(換臉模型偶爾產生的細微畸變可能讓臉部偵測器誤判);先對嘴可以確保換臉步驟拿到的每
一幀都已經是正確的嘴型表情,置換後嘴型自然被保留到最終結果。

---

## 即時虛擬人對話完整流程(子專案6)

**目前這是整個專案唯一實際在跑的路徑**——整合層(7863,及其自動拉起的子專案1/5,port
7860/7864)目前刻意不啟動,`rea.sh` 只管理子專案6 自己需要的四個服務:chatterbox
(7861)、talking_head(7862)、Ollama(11434)、digital_human 本身(7865)。子專案1-5
的程式碼都還在,沒有被刪除,之後要恢復整合層只要把 `rea.sh` 的 `start_services()` 換回
呼叫 `integration/app.py` 即可。

跟前面幾個「批次生成」的子專案不同,這是一個**半雙工、自動接話的連續對話**系統——使用者
講完話,系統自動偵測、自動生成回覆,不用手動按送出;虛擬人講話時麥克風靜音,播完自動恢復
聆聽。每一輪對話串接以下模型:

```
使用者對麥克風持續講話(串流)
        │
        ▼
[Step 0] WebRTC VAD(語音活動偵測)持續監看串流音訊
        │  偵測到「已經開始講話 + 之後靜音達 900ms」→ 判定這一輪講完了
        ▼
[Step 1] Whisper(base)→ 把這一輪錄到的音訊轉成文字
        │
        ▼
[Step 2] Llama Guard 3(§10)→ 安全檢查
        │  不安全 → 直接擋下,不進入後面任何步驟
        ▼
[Step 3] 多語嵌入模型(§11)把使用者訊息編碼 → 向量資料庫(§12)找出最相關的私人記憶
        │
        ▼
[Step 4] Llama 3.1-8B(§9)結合「虛擬人設定 + 檢索到的記憶」生成回覆文字
        │
        ▼
[Step 5] Chatterbox(§4,沿用子專案2 現有服務)把回覆文字用參考聲音克隆唸出來
        │
        ▼
[Step 6] Wav2Lip(§6,常駐引擎,見下方〈這次工作紀錄〉)把虛擬人照片對嘴合成
        │
        ▼
輸出:影片自動播放;播完後 Step 0 的 VAD 自動恢復監聽,不需要任何按鈕
```

**跟其他子專案在架構上的差異**:子專案1-5 都是「使用者提供全部素材 → 跑一次生成 → 拿到
結果」的批次模式;子專案6 是**多輪、自動接話的對話**,每一輪都要重新跑完整條鏈,而且刻意
把「安全檢查」放在最前面、獨立於主要 LLM 之外——這樣即使之後 RAG 檢索到的記憶內容或 LLM
本身被誘導,使用者輸入的內容本身也已經先被篩過一次。

**實測延遲**(RTX 3090,2026-09-14 對嘴引擎改成常駐 + Ollama 顯存修正之後量到的真實數字,
細節見下方〈這次工作紀錄〉):

| 階段 | 實測 |
|---|---|
| 安全檢查(Llama Guard) | ~2.5-3 秒(刻意設計成每輪都卸載重載,見下方說明) |
| RAG 檢索 | ~0.01 秒(常駐,已預熱) |
| LLM 生成回覆 | ~0.5-0.8 秒(常駐,已預熱) |
| 語音克隆(TTS) | ~3-4 秒(視回覆長度而定) |
| 對嘴影片生成 | ~1-3 秒(常駐引擎,比舊版 subprocess 方式快 6-7 倍,視回覆長度而定) |
| **全流程總計** | **約 8-13 秒**,視回覆長短而定 |

仍未達到「5 秒內回應」的目標——這次的工作把「會不會 OOM 崩潰」跟「要不要手動按按鈕」兩個
問題解決了,但沒有進一步壓縮生成本身的時間,詳見下方〈這次工作紀錄〉的說明。

---

## 這次工作紀錄(2026-09-14):效能修正 + 自動連續對話

這次的工作分成兩個獨立子專案(各有自己的 spec/plan 文件,見
`docs/superpowers/specs/` 與 `docs/superpowers/plans/`),外加後續一輪真實除錯跟前端調整。

### 子專案 A:對嘴影片效能重構 + Ollama 顯存修正

**問題**:`talking_head/lip_sync.py` 原本每次生成都開一個全新的 subprocess 重跑
`Wav2Lip/inference.py`,連同人臉偵測模型(SFD)跟 Wav2Lip GAN 模型的權重都要重新讀進
GPU——即使同一個服務行程,也完全沒有重複利用,穩定狀態下對嘴這一步要 5.6-6.6 秒。同時,
`digital_human` 在同一輪對話裡背靠背呼叫兩個 Ollama 模型(先 Llama Guard 安全檢查、再
Llama 3.1 主要 LLM),兩個各吃約 8.6GB 顯存,加上 chatterbox 常駐的 ~4.3GB,曾經真實撞過
`CUDA out of memory`。

**修法**:
- 新增 `talking_head/wav2lip_engine.py`,把 Wav2Lip 靜態照片模式的推論邏輯重新實作成一個
  常駐模組——人臉偵測器跟 Wav2Lip 模型都是**延遲載入的單例**,只在第一次呼叫時載入 GPU,
  之後每次生成都重複利用同一份已載入的模型,不再每次都重新 subprocess + 重新讀權重。順便
  把最後合成音軌那步從 `shell=True` 組字串改成 `subprocess.run` 的列表參數形式,徹底避免
  shell 注入風險。效果:對嘴生成從 5.6-6.6 秒降到 **0.9-2.4 秒**(視回覆音訊長度而定),
  快了 6-7 倍。
- `digital_human/safety.py` 呼叫 Ollama 時帶上 `"keep_alive": 0`,讓 Llama Guard **一用
  完就立刻卸載**,不等閒置逾時;`llm.py`(主要 LLM)刻意**不**加這個設定,讓它照 Ollama
  預設行為留在顯存裡(每輪對話都會用到,若也讓它卸載重載,回覆生成會從穩定狀態的
  ~0.5-0.8 秒退化成每輪都要冷啟動)。這是刻意的取捨:Guard 的安全檢查從熱啟動
  ~0.1-0.3 秒變成每輪都要冷啟動 ~2.5-3 秒,換來的是**再也不會因為兩個 8.6GB 模型同時
  常駐而 OOM**。

### 子專案 B:半雙工自動連續對話

**目標**:把「打字/錄音 → 按送出 → 等結果」的回合制,改成「講完話自動偵測、自動回覆,
虛擬人講話時麥克風靜音,播完自動恢復聆聽」,全程不用按任何按鈕。

**架構**:新增 `digital_human/vad.py` 的 `TurnDetector` 類別,用 **WebRTC VAD**(Google
釋出的輕量語音/靜音分類器,純 CPU、不需要 GPU)持續判斷串流進來的麥克風音訊——講話開始後
偵測到 900ms 連續靜音就判定「這一輪講完了」,短於 300ms 的講話視為雜訊誤觸發、忽略。
`app.py` 用一個 `gr.State` 存放每個對話 session 自己的 `TurnDetector` 實例與「現在是否
在聆聽」的旗標。

**開發過程中踩到、而且花了不少力氣才抓出來的兩個 Gradio 坑**,如實記錄:

1. **`gr.State` 每次存取都會 `deepcopy`,但 `webrtcvad.Vad` 包著一個不能被 deepcopy 的
   C 物件(PyCapsule)**——一放進 `gr.State` 就整個 crash
   (`TypeError: cannot pickle 'PyCapsule' object`)。純 mock 的單元測試測不出來(mock 掉
   的 Vad 不是真的 C 物件),是直接對正在跑的真實服務打 API 才發現的。修法:給
   `TurnDetector` 加一個自訂的 `__deepcopy__`——遇到要複製時重建一個新的 `Vad` 物件(它
   本身沒有值得保留的內部狀態),其他欄位正常複製。
2. **Gradio 的串流輸入事件(`gr.Audio(streaming=True)` 的 `stream` 事件)預設
   `trigger_mode="always_last"`**,持續觸發的串流事件會讓「還在執行、還沒跑完」的舊呼叫
   被新進來的呼叫排擠/取代。一開始把「偵測講完話」跟「呼叫 LLM/TTS/對嘴生成回覆」寫在同一個
   跟串流事件綁定的 generator 函式裡,結果真實測試時發現:偵測到「講完話」的那一刻的 log
   有印出來,但後面耗時 10+ 秒的生成邏輯永遠不會真的執行——GPU 沒有任何負載、沒有任何網路
   連線,而且無論等多久都不會有進展,除非使用者主動停止錄音(讓新的串流事件不再持續進來,
   卡住的那個呼叫才終於輪到執行)。修法:把「偵測」(快,留在串流事件上)跟「處理」(慢,
   呼叫 LLM/TTS/對嘴)拆成兩個獨立函式,「處理」改用一個完全獨立的 `gr.Timer(0.5)`
   `.tick()` 事件每 0.5 秒輪詢一次「有沒有講完話在等處理」的旗標——`gr.Timer` 的觸發跟
   麥克風串流完全脫鉤,不會被同一套 `trigger_mode` 邏輯卡住。

**前端**:拿掉打字輸入框(語音自動偵測已經夠用),待機時顯示虛擬人的靜態照片(不是空白
畫面),虛擬人真的在講話時才切換顯示生成好的影片,播完自動切回待機照片;版面用 CSS 重新
排版成置中卡片、加了一個顯示目前狀態(聆聽中/生成中)的提示文字。

### 啟動流程:模型預熱 + GPU 清理

- `chatterbox/app.py`、`talking_head/app.py`、`digital_human/app.py` 現在都在
  `launch()` 開 port **之前**,先把自己會用到的模型(TTS、Wav2Lip+人臉偵測器、
  Whisper、Ollama 的 LLM+安全防護)載入一次——`rea.sh` 原本「等 port 起來」的邏輯完全
  不用改,因為 port 本來就是模型載完之後才開,「等 port 就緒」自然等於「等預熱完成」。
  代價是 `./rea.sh start` 本身變慢(全部模型冷啟動約 30 秒),換來的是使用者第一次真正
  講話時就是熱的,不用再等冷啟動。
- 已實測驗證 `./rea.sh stop` 會完整釋放 GPU:關掉 `ollama serve` 這個主行程,它底下
  實際佔用顯存的 `llama-server` 子行程也會一起被清掉(用 `nvidia-smi` 前後比對確認過),
  不會有孤兒行程繼續佔用 GPU。
- `rea.sh` 目前只管理子專案6 需要的四個服務(chatterbox 7861、talking_head 7862、
  Ollama 11434、digital_human 7865)——整合層(7863)跟它自動拉起的子專案1、5
  (7860、7864)刻意不啟動,程式碼都還在,之後要恢復只要把 `rea.sh` 的
  `start_services()` 換回呼叫 `integration/app.py` 即可。

---

## 其他技術細節

- **服務間溝通**:5 個子專案完全獨立(各自的 Python 虛擬環境,避免版本衝突),彼此之間只
  透過 HTTP(`gradio_client`)呼叫對方已啟動的 Gradio 服務,整合層不 `import` 任何子專案
  的程式碼——即使某個子專案的依賴壞掉,也不會直接讓整合層的程式碼掛掉(頂多是呼叫失敗回傳
  錯誤訊息)。
- **輸出影片編碼**:换脸/合成後的最終影片統一轉成 **H.264**(`libx264`)——`cv2.VideoWriter`
  預設寫出的 `mp4v`(MPEG-4 Part 2)編碼多數瀏覽器無法直接播放,若不重新轉碼,網頁上的
  播放器會顯示空白。
- **輸入檔名的安全處理**:使用者上傳的檔案在餵給 Wav2Lip 前,會先複製到暫存目錄並改成固定
  檔名(只保留副檔名,且副檔名本身也會做白名單檢查,只允許英數字元)——因為 Wav2Lip 自己
  的 `inference.py` 最後一步是用 `subprocess.call(..., shell=True)` 呼叫 ffmpeg,若直接
  把使用者原始檔名(可能含特殊符號)傳進去,理論上有 shell injection 風險,已在本專案端
  先行過濾。
- **人臉偵測失敗的容錯策略**:換臉步驟(InsightFace)與對嘴步驟(Wav2Lip,見上方修補說明)
  現在都採用「這一幀沒偵測到臉就跳過/沿用前一幀位置」而非讓整段影片直接失敗的策略,盡量
  讓真實世界(不一定乾淨的)素材也能跑得完整個流程。
- **GPU 記憶體隔離**:每個子專案的模型(InsightFace、Wav2Lip、kNN-VC 的 WavLM/HiFiGAN、
  Chatterbox)都在各自獨立的 Python 進程中載入,運作期間會一直佔用顯存直到該進程結束——
  這也是為什麼 `rea.sh` 提供 `stop` 指令,確保測試/開發過程中不會有殘留行程長期佔用 GPU。
