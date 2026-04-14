# Mr. Helmet 智能翻译功能配置指南

## 功能简介

新增的智能翻译功能允许你：
- 输入中文销售文案
- 自动翻译到目标语言（马来文、英文、泰文等）
- 用翻译后的文本生成音频

翻译由大模型 API 提供（Moonshot、Claude 或 OpenAI），确保高质量翻译。

---

## 本地开发环境配置

### 1. 获取 Moonshot API Key（推荐）

最快的方式，特别是如果你在中国：

1. 访问 https://platform.moonshot.cn/
2. 注册或登录账户
3. 创建 API Key
4. 复制 API Key

### 2. 配置 .env 文件

在项目根目录创建或编辑 `.env` 文件：

```env
LLM_PROVIDER=moonshot
MOONSHOT_API_KEY=sk-proj-YOUR_KEY_HERE
```

将 `YOUR_KEY_HERE` 替换为你的实际 API Key。

### 3. 安装依赖

确保已安装所有依赖：

```bash
pip install -r requirements.txt
```

依赖应该包含：
- edge-tts
- fastapi
- uvicorn[standard]
- jinja2
- python-multipart
- python-dotenv

### 4. 启动应用

```bash
python app.py
```

打开 http://localhost:8000

### 5. 测试翻译功能

1. 输入中文文案（例：`我们的产品质量最好，价格也最优惠`）
2. 勾选"启用自动翻译"
3. 选择源语言：`中文（简体）`
4. 选择目标语言：`马来文`
5. 选择 TTS 引擎和音色
6. 点击"生成音频"

系统会：
- 先用 Moonshot 翻译成马来文
- 再用 Edge TTS 或 ElevenLabs 生成音频
- 返回翻译后的文本和音频

---

## Vercel 部署配置

### 1. 在 Vercel 仪表板添加环境变量

**重要：不要在代码中硬编码 API Key！**

1. 进入 Vercel 项目设置：https://vercel.com/[username]/mr-helmet/settings
2. 找到 `Environment Variables` 部分
3. 添加以下变量：
   - **Name**: `MOONSHOT_API_KEY`
   - **Value**: `sk-proj-xxx` （你的实际 API Key）
   - **Scope**: 选择 `Production`, `Preview`, `Development`

4. 添加另一个变量（可选）：
   - **Name**: `LLM_PROVIDER`
   - **Value**: `moonshot`

5. 点击 `Save`

### 2. 部署

```bash
git add .
git commit -m "Add translation feature with Moonshot API"
git push
```

Vercel 会自动部署。

### 3. 验证部署

部署完成后，在 Vercel 部署的 URL 上测试翻译功能。

---

## 支持的大模型

### Moonshot（默认）✅
- **特点**：中文理解能力强，成本低，访问快（中国境内）
- **成本**：约 ¥0.02 per 1K tokens
- **获取**：https://platform.moonshot.cn/

### Claude（可选）
- **特点**：翻译质量好，支持多语言
- **成本**：约 $0.003 per 1K input tokens
- **配置**：
  ```env
  LLM_PROVIDER=claude
  ANTHROPIC_API_KEY=sk-ant-xxx
  ```

### OpenAI（可选）
- **特点**：稳定可靠，支持 GPT-3.5 和 GPT-4
- **成本**：约 $0.0015 per 1K tokens（GPT-3.5）
- **配置**：
  ```env
  LLM_PROVIDER=openai
  OPENAI_API_KEY=sk-xxx
  ```

---

## 故障排除

### 1. "MOONSHOT_API_KEY not set" 错误

**原因**：环境变量未设置

**解决**：
- 本地：检查 `.env` 文件是否存在且格式正确
- Vercel：检查项目设置中是否添加了环境变量

### 2. "Translation failed" 错误

**原因**：API 调用失败（网络、配额等）

**解决**：
- 检查 API Key 是否有效
- 检查账户是否有足够配额
- 查看浏览器控制台错误信息

### 3. 翻译质量差

**原因**：temperature 设置过高

**解决**：已在代码中设置 temperature=0.3，确保翻译稳定性。如需调整，编辑 `translate.py` 中的 `temperature` 参数。

---

## 成本监控

### Moonshot 成本估算

- 单次翻译（500-1000 字）：< ¥0.02
- 月均 100 次翻译：< ¥2

### 如何降低成本

1. **缓存翻译结果**（如需大量重复翻译）
2. **批量翻译**（多个文案一起翻译）
3. **选择便宜的提供商**（Moonshot 最划算）

---

## API 参考

### POST /api/generate

新增翻译参数：

```json
{
  "text": "中文文案",
  "engine": "edge",
  "language": "ms-MY",
  "gender": "female",
  "translate": true,
  "source_lang": "zh-CN",
  "target_lang": "ms"
}
```

**响应示例**：

```json
{
  "audio_base64": "SUQzBAAAAAAAI1RTUUM...",
  "duration": 15.5,
  "duration_fmt": "0:15",
  "translated": true,
  "original_text": "中文文案",
  "translated_text": "Teks Melayu",
  "llm_provider": "moonshot"
}
```

---

## 常见问题

**Q: 能否保存翻译记录？**
A: 目前没有，但可以通过修改代码添加数据库存储。

**Q: 是否支持实时翻译预览？**
A: 目前是直接翻译后生成，不显示中间步骤。可通过调用 `/api/translate` 端点实现。

**Q: 多语言对翻译有什么影响？**
A: ElevenLabs 支持多语言自动检测，翻译后直接生成对应语言音频。Edge TTS 需要手动选择语言。

---

## 更多帮助

- 项目 GitHub：[链接]
- Moonshot 文档：https://platform.moonshot.cn/docs
- 问题反馈：[创建 Issue]
