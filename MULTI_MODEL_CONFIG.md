# 多模型配置说明

本项目支持配置多个AI模型，用户可以在前端界面中动态切换不同的模型进行对话。

## 配置方式

### 1. 环境变量配置

在项目根目录创建 `.env` 文件（或复制 `env.example` 为 `.env`），配置多模型参数：

```env
# 多模型配置
# 指定可用的模型档位，用逗号分隔
LLM_PROFILES=default,qwen3,deepseek

# 默认使用的模型档位
LLM_DEFAULT=default

# 阿里云百炼千问3模型配置
LLM_QWEN3_LABEL=通义千问3
LLM_QWEN3_API_KEY=your_aliyun_dashscope_api_key_here
LLM_QWEN3_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_QWEN3_MODEL=qwen-plus
LLM_QWEN3_TEMPERATURE=0.2
LLM_QWEN3_TIMEOUT=60

# DeepSeek模型配置（示例）
LLM_DEEPSEEK_LABEL=DeepSeek
LLM_DEEPSEEK_API_KEY=your_deepseek_api_key_here
LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
LLM_DEEPSEEK_MODEL=deepseek-chat
LLM_DEEPSEEK_TEMPERATURE=0.2
LLM_DEEPSEEK_TIMEOUT=60
```

### 2. 配置参数说明

每个模型档位需要配置以下参数：

- `LLM_<ID>_LABEL`: 模型显示名称（前端界面显示）
- `LLM_<ID>_API_KEY`: API密钥
- `LLM_<ID>_BASE_URL`: API基础URL
- `LLM_<ID>_MODEL`: 模型名称
- `LLM_<ID>_TEMPERATURE`: 温度参数（可选，默认0.2）
- `LLM_<ID>_TIMEOUT`: 超时时间（可选，默认60秒）

### 3. 支持的模型提供商

#### 阿里云百炼（通义千问）
- **API Key获取**: 登录阿里云控制台 → 百炼服务 → API-KEY管理
- **Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **模型名称**: `qwen-plus`, `qwen-max`, `qwen-turbo` 等

#### DeepSeek
- **API Key获取**: 访问 [DeepSeek官网](https://platform.deepseek.com/)
- **Base URL**: `https://api.deepseek.com/v1`
- **模型名称**: `deepseek-chat`, `deepseek-coder` 等

#### OpenAI
- **API Key获取**: 访问 [OpenAI官网](https://platform.openai.com/)
- **Base URL**: `https://api.openai.com/v1`
- **模型名称**: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo` 等

#### 其他兼容OpenAI接口的模型
- 任何兼容OpenAI API格式的模型都可以通过配置相应的 `BASE_URL` 和 `MODEL` 来使用

## 使用方式

### 1. 前端界面切换

用户可以在聊天界面的模型选择下拉框中切换不同的模型：

1. 打开聊天界面
2. 点击模型选择下拉框
3. 选择想要使用的模型
4. 开始对话

### 2. WebSocket参数切换

也可以通过WebSocket连接参数指定模型：

```javascript
const ws = new WebSocket('ws://localhost:8003/ws/chat?model=qwen3');
```

### 3. API接口获取模型列表

```bash
curl http://localhost:8003/api/models
```

返回格式：
```json
{
  "success": true,
  "data": {
    "models": [
      {
        "id": "default",
        "label": "Default",
        "model": "gpt-4o",
        "is_default": true
      },
      {
        "id": "qwen3",
        "label": "通义千问3",
        "model": "qwen-plus",
        "is_default": false
      }
    ],
    "default": "default"
  }
}
```

## 注意事项

1. **API Key安全**: 请妥善保管您的API密钥，不要将其提交到版本控制系统中
2. **模型兼容性**: 不同模型的输入输出格式可能略有差异，建议测试后再使用
3. **成本控制**: 不同模型的调用成本不同，请根据实际需求选择合适的模型
4. **网络连接**: 确保服务器能够访问相应的API端点

## 故障排除

### 1. 模型初始化失败
- 检查API Key是否正确
- 检查Base URL是否可访问
- 检查模型名称是否正确

### 2. 模型切换不生效
- 检查环境变量配置是否正确
- 重启后端服务
- 检查前端是否正确发送模型参数

### 3. 模型调用超时
- 检查网络连接
- 调整TIMEOUT参数
- 检查API服务状态
