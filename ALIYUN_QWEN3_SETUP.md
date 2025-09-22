# 阿里云百炼千问3配置指南

本指南将详细说明如何在项目中配置和使用阿里云百炼的通义千问3模型。

## 1. 获取阿里云百炼API Key

### 步骤1：注册阿里云账号
1. 访问 [阿里云官网](https://www.aliyun.com)
2. 注册并完成实名认证

### 步骤2：开通百炼服务
1. 登录阿里云控制台
2. 搜索"百炼"或访问 [百炼控制台](https://bailian.console.aliyun.com/)
3. 按照提示开通百炼服务
4. 完成服务开通后，您将获得一定的免费额度

### 步骤3：获取API Key
1. 在百炼控制台，点击右上角的头像
2. 选择"API-KEY管理"
3. 点击"创建API-KEY"
4. 复制生成的API Key（格式类似：sk-xxxxxxxxxxxxxxxx）

## 2. 配置项目环境

### 步骤1：创建环境配置文件
在项目根目录创建 `.env` 文件：

```bash
cp env.example .env
```

### 步骤2：编辑配置文件
编辑 `.env` 文件，添加以下配置：

```env
# 多模型配置
LLM_PROFILES=default,qwen3
LLM_DEFAULT=qwen3

# 阿里云百炼千问3配置
LLM_QWEN3_LABEL=通义千问3
LLM_QWEN3_API_KEY=sk-your-actual-api-key-here
LLM_QWEN3_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_QWEN3_MODEL=qwen-plus
LLM_QWEN3_TEMPERATURE=0.2
LLM_QWEN3_TIMEOUT=60

# 默认模型配置（可选，作为备用）
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

### 步骤3：选择模型版本
阿里云百炼提供多个千问模型版本，您可以根据需求选择：

- `qwen-plus`: 平衡性能和成本，推荐日常使用
- `qwen-max`: 最强性能，适合复杂任务
- `qwen-turbo`: 快速响应，适合简单对话

## 3. 启动应用

### 启动后端服务
```bash
cd backend
conda activate ai-web-mcpmode
uvicorn main:app --reload --host 0.0.0.0 --port 8003
```

### 启动前端服务
```bash
cd frontend
python -m http.server 3000
```

### 访问应用
打开浏览器访问：http://localhost:3000

## 4. 使用千问3模型

### 方法1：通过前端界面切换
1. 打开聊天界面
2. 点击右上角的"模型：默认 ▾"按钮
3. 选择"通义千问3 (qwen-plus)"
4. 开始对话

### 方法2：通过URL参数指定
在WebSocket连接URL中添加model参数：
```
ws://localhost:8003/ws/chat?model=qwen3
```

## 5. 验证配置

### 检查模型列表API
```bash
curl http://localhost:8003/api/models
```

预期返回：
```json
{
  "success": true,
  "data": {
    "models": [
      {
        "id": "qwen3",
        "label": "通义千问3",
        "model": "qwen-plus",
        "is_default": true
      }
    ],
    "default": "qwen3"
  }
}
```

### 测试对话
发送一条测试消息，观察是否使用千问3模型进行回复。

## 6. 常见问题

### Q: 模型切换不生效？
A: 请检查：
1. 环境变量配置是否正确
2. 后端服务是否重启
3. 前端是否正确发送model参数

### Q: API调用失败？
A: 请检查：
1. API Key是否正确
2. 网络是否能访问阿里云服务
3. 账户是否有足够的额度

### Q: 模型响应慢？
A: 可以尝试：
1. 调整TIMEOUT参数
2. 选择更快的模型版本（如qwen-turbo）
3. 检查网络连接

## 7. 成本优化建议

1. **选择合适的模型版本**：
   - 简单对话使用 `qwen-turbo`
   - 复杂任务使用 `qwen-plus`
   - 高要求场景使用 `qwen-max`

2. **调整温度参数**：
   - 创意任务：0.7-1.0
   - 分析任务：0.2-0.5
   - 事实性任务：0.0-0.2

3. **监控使用量**：
   - 定期查看百炼控制台的使用统计
   - 设置使用量告警

## 8. 技术支持

- [阿里云百炼官方文档](https://help.aliyun.com/zh/dashscope/)
- [通义千问模型介绍](https://help.aliyun.com/zh/dashscope/developer-reference/model-introduction)
- [API参考文档](https://help.aliyun.com/zh/dashscope/developer-reference/api-details)
