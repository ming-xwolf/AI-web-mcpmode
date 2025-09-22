// config.js - 配置管理器
class ConfigManager {
    constructor() {
        this.config = null;
        this.isLoaded = false;
        this.loadPromise = null;
    }
    
    async loadConfig() {
        // 如果已经在加载中，返回相同的Promise
        if (this.loadPromise) {
            return this.loadPromise;
        }
        
        this.loadPromise = this._doLoadConfig();
        return this.loadPromise;
    }
    
    async _doLoadConfig() {
        try {
            console.log('📋 Starting to load config file...');
            const maxAttempts = 3;
            const baseUrlCandidates = [
                () => `./config.json?t=${Date.now()}`,
                () => `/config.json?t=${Date.now()}`
            ];
            let lastError = null;
            let rawConfig = null;
            
            for (let attempt = 1; attempt <= maxAttempts && rawConfig === null; attempt++) {
                for (const urlBuilder of baseUrlCandidates) {
                    const url = urlBuilder();
                    try {
                        const response = await fetch(url, { cache: 'no-store' });
                        if (!response.ok) {
                            lastError = new Error(`HTTP ${response.status} ${response.statusText}`);
                            continue;
                        }
                        rawConfig = await response.json();
                        break;
                    } catch (err) {
                        lastError = err;
                        // 网络失败则继续尝试下一个候选或下一次重试
                    }
                }
                if (rawConfig === null && attempt < maxAttempts) {
                    const backoffMs = 200 * attempt;
                    await new Promise(res => setTimeout(res, backoffMs));
                }
            }
            
            if (rawConfig === null) {
                throw new Error(`Config file load failed after ${maxAttempts} attempts: ${lastError ? lastError.message : 'unknown error'}`);
            }
            
            // 允许通过 window.__RUNTIME_CONFIG__ 在运行时做增量覆盖
            const runtimeOverlay = (typeof window !== 'undefined' && window.__RUNTIME_CONFIG__) ? window.__RUNTIME_CONFIG__ : null;
            this.config = runtimeOverlay ? this._deepMerge(rawConfig, runtimeOverlay) : rawConfig;
            this.isLoaded = true;
            
            // 验证配置完整性
            this._validateConfig();
            
            console.log('✅ Config file loaded successfully:', this.config);
            return this.config;
        } catch (error) {
            this.config = null;
            this.isLoaded = false;
            console.error('❌ Config file load failed:', error);
            
            // Show user-friendly error message
            this._showConfigError(error.message);
            throw new Error(`Config load failed: ${error.message}`);
        }
    }
    
    _validateConfig() {
        if (!this.config) {
            throw new Error('Config object is empty');
        }
        
        if (!this.config.backend) {
            throw new Error('Config file missing backend configuration');
        }
        
        const { host, port, protocol, wsProtocol } = this.config.backend;
        
        if (!host) {
            throw new Error('Config file missing backend.host');
        }
        
        if (!port) {
            throw new Error('Config file missing backend.port');
        }
        
        if (!protocol) {
            throw new Error('Config file missing backend.protocol');
        }
        
        if (!wsProtocol) {
            throw new Error('Config file missing backend.wsProtocol');
        }
        
        console.log('✅ Config file validation passed');
    }
    
    // 简单的深合并（仅处理对象与基本值，数组以覆盖为准）
    _deepMerge(target, source) {
        if (target === source) return target;
        if (!source || typeof source !== 'object') return target;
        const result = Array.isArray(target) ? target.slice() : { ...target };
        for (const key of Object.keys(source)) {
            const srcVal = source[key];
            const tgtVal = result[key];
            if (srcVal && typeof srcVal === 'object' && !Array.isArray(srcVal)) {
                result[key] = this._deepMerge(tgtVal && typeof tgtVal === 'object' && !Array.isArray(tgtVal) ? tgtVal : {}, srcVal);
            } else {
                result[key] = srcVal;
            }
        }
        return result;
    }

    _showConfigError(message) {
        // 创建错误提示界面
        const errorHtml = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                color: white;
                font-family: Arial, sans-serif;
            ">
                <div style="
                    background: #f56565;
                    padding: 30px;
                    border-radius: 10px;
                    max-width: 500px;
                    text-align: center;
                ">
                    <h2>⚠️ 配置文件加载失败</h2>
                    <p>无法加载配置文件 <code>config.json</code>。请检查：</p>
                    <ul>
                        <li>确保前端目录中存在 <code>config.json</code> 文件</li>
                        <li>检查文件格式是否为正确的JSON</li>
                        <li>验证后端服务是否正在运行</li>
                        <li>检查网络连接</li>
                    </ul>
                    <p><strong>错误详情：</strong> ${message}</p>
                    <p>请修复上述问题后刷新页面。</p>
                    <button onclick="window.location.reload()" style="
                        background: white;
                        color: #f56565;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        font-weight: bold;
                        margin-top: 15px;
                    ">Reload</button>
                </div>
            </div>
        `;
        
        // 添加到页面
        const errorDiv = document.createElement('div');
        errorDiv.innerHTML = errorHtml;
        document.body.appendChild(errorDiv);
    }
    
    // 确保配置已加载的检查方法
    _ensureConfigLoaded() {
        if (!this.isLoaded || !this.config) {
            throw new Error('Config file not loaded, please call loadConfig() method first');
        }
    }
    
    getApiBaseUrl() {
        this._ensureConfigLoaded();
        // 生产/线上：使用同源，不主动拼接端口，兼容反向代理与TLS
        if (!this.isLocalDeployment()) {
            return window.location.origin;
        }
        // 本地：优先使用 config.api.baseUrl；否则使用 backend 三元组
        if (this.config.api && this.config.api.baseUrl) {
            return this.config.api.baseUrl;
        }
        const { protocol, host, port } = this.config.backend;
        return `${protocol}://${host}:${port}`;
    }
    
    getWebSocketUrl() {
        this._ensureConfigLoaded();
        
        // 优先使用 api.wsUrl，否则构建地址
        if (this.config.api && this.config.api.wsUrl) {
            return this.config.api.wsUrl;
        }
        
        const { wsProtocol, host, port } = this.config.backend;
        return `${wsProtocol}://${host}:${port}`;
    }
    
    getFullApiUrl(endpoint) {
        const baseUrl = this.getApiBaseUrl();
        return `${baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    }
    
    getFullWebSocketUrl(endpoint) {
        const wsUrl = this.getWebSocketUrl();
        return `${wsUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`;
    }
    
    // 检查当前页面host是否与配置host一致
    isLocalDeployment() {
        this._ensureConfigLoaded();
        
        const currentHost = window.location.hostname;
        const configHost = this.config.backend.host;
        
        // 如果配置的host是localhost或127.0.0.1，且当前也是，认为是本地部署
        const localhostAliases = ['localhost', '127.0.0.1', '::1'];
        const currentIsLocal = localhostAliases.includes(currentHost);
        const configIsLocal = localhostAliases.includes(configHost);
        
        return currentIsLocal && configIsLocal;
    }
    
    // 智能获取WebSocket URL（考虑跨域情况）
    getSmartWebSocketUrl(endpoint = '/ws/chat') {
        this._ensureConfigLoaded();
        
        // 本地：使用配置地址
        if (this.isLocalDeployment()) {
            return this.getFullWebSocketUrl(endpoint);
        }
        
        // 线上/生产：同源 + 自适应端口（window.location.host 已包含端口）
        const currentProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const currentHostWithPort = window.location.host;
        return `${currentProtocol}://${currentHostWithPort}${endpoint}`;
    }
}

// 创建全局配置管理器实例
window.configManager = new ConfigManager();

// 立即开始加载配置
window.configManager.loadConfig().catch(error => {
    console.error('❌ 配置加载失败，应用无法正常工作:', error);
});