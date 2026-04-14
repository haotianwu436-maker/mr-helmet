# 快速开始：翻译功能

## 🚀 30 秒快速设置

### 1. 获取 API Key
访问 https://platform.moonshot.cn/ 获取免费 API Key

### 2. 配置环境
编辑 `.env` 文件：
```env
MOONSHOT_API_KEY=sk-proj-你的KEY
LLM_PROVIDER=moonshot
```

### 3. 启动应用
```bash
python app.py
```

### 4. 打开浏览器
访问 http://localhost:8000

---

## ✨ 测试翻译功能

1. **输入文案**
   ```
   我们的产品质量最好，价格也最优惠。立即购买享受50%折扣！
   ```

2. **勾选翻译**
   ✓ 启用自动翻译

3. **设置语言**
   - 原文语言：中文（简体）
   - 目标语言：马来文

4. **生成音频**
   点击"生成音频"

5. **查看结果**
   - 系统会自动翻译成马来文
   - 用 Edge TTS 生成马来文语音
   - 显示翻译成功信息

---

## 🔧 常见设置

### 只翻译，不生成音频
```bash
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "我们的产品质量最好",
    "source_lang": "zh-CN",
    "target_lang": "ms"
  }'
```

### 翻译成英文
界面选择：
- 源语言：中文（简体）
- 目标语言：英文

### 使用 ElevenLabs 引擎
1. 勾选"ElevenLabs"
2. 输入 ElevenLabs API Key
3. 选择音色
4. 勾选翻译
5. 生成

---

## 📊 支持的语言对

| 源语言 | 目标语言 | 说明 |
|--------|---------|------|
| 中文 | 马来文 | ✅ 推荐 |
| 中文 | 英文 | ✅ 推荐 |
| 中文 | 泰文 | ✅ 推荐 |
| 中文 | 越南文 | ✅ |
| 中文 | 日文 | ✅ |
| 中文 | 韩文 | ✅ |
| 中文 | 印尼文 | ✅ |
| 自动检测 | 任何 | ✅ |

---

## 💡 提示

- **保存 API Key**：前端会自动保存 ElevenLabs Key 到浏览器，Moonshot Key 在服务器端保管
- **成本**：每次翻译成本不到 ¥0.02，非常划算
- **速度**：翻译 + 生成通常 2-5 秒完成
- **无配额限制**：使用企业账户可获得更高额度

---

## 🐛 如果出错

### 错误：MOONSHOT_API_KEY not set
→ 检查 `.env` 文件是否存在，内容是否正确

### 错误：Translation failed
→ 检查 API Key 是否有效（复制粘贴时留意空格）

### 错误：Network timeout
→ 网络问题，重试一次

---

## 📝 下一步

1. **在 Vercel 部署**
   - 在 Vercel 仪表板添加 `MOONSHOT_API_KEY` 环境变量
   - Push 代码自动部署

2. **集成到销售流程**
   - 为每个目标市场预设语言
   - 批量生成多语言销售音频

3. **监控成本**
   - 记录每月翻译次数
   - 必要时升级 Moonshot 账户

---

## 📞 支持

遇到问题？参考 `TRANSLATION_SETUP.md` 的完整故障排除指南。
