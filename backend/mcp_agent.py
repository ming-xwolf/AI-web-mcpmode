"""
MCP智能体封装 - 为Web后端使用
基于 test.py 中的 SimpleMCPAgent，优化为适合WebSocket流式推送的版本
"""

import os
import json
import asyncio
from typing import Dict, List, Any, AsyncGenerator, Optional
from pathlib import Path
from datetime import datetime, timedelta

from dotenv import load_dotenv, find_dotenv
import re
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

# ─────────── 1. MCP配置管理 ───────────
class MCPConfig:
    """MCP配置管理"""

    def __init__(self, config_file: str = "mcp.json"):
        self.config_file = config_file
        self.default_config = {}

    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 配置文件加载失败，使用默认配置: {e}")

        # 创建默认配置文件
        self.save_config(self.default_config)
        return self.default_config

    def save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ 配置文件保存失败: {e}")


# ─────────── 3. Web版MCP智能体 ───────────
class WebMCPAgent:
    """Web版MCP智能体 - 支持流式推送"""

    def __init__(self):
        # 修复：使用backend目录下的配置文件
        config_path = Path(__file__).parent / "mcp.json"
        self.config = MCPConfig(str(config_path))
        self.llm = None
        self.llm_tools = None  # 绑定工具用于判定与工具阶段
        self.llm_stream = None # 不绑定工具，仅用于最终回答的真流式
        self.mcp_client = None
        self.tools = []
        # 新增：按服务器分组的工具存储
        self.tools_by_server = {}
        self.server_configs = {}
        self._used_tool_names = set()
        self._exit_tool_name = "exit_tool_mode"

        # 加载 .env 并设置API环境变量（覆盖已存在的环境变量）
        try:
            load_dotenv(find_dotenv(), override=True)
        except Exception:
            # 忽略 .env 加载错误，继续从系统环境读取
            pass

        # 从环境变量读取配置
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        self.model_name = os.getenv("OPENAI_MODEL", os.getenv("OPENAI_MODEL_NAME", "deepseek-chat")).strip()

        # 数值配置，带默认
        try:
            self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        except Exception:
            self.temperature = 0.2
        try:
            self.timeout = int(os.getenv("OPENAI_TIMEOUT", "60"))
        except Exception:
            self.timeout = 60

        # 将关键配置同步到环境（供底层SDK使用），不覆盖外部已设值
        if self.api_key and not os.getenv("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = self.api_key
        if self.base_url and not os.getenv("OPENAI_BASE_URL"):
            os.environ["OPENAI_BASE_URL"] = self.base_url

    async def initialize(self):
        """初始化智能体"""
        try:
            # 初始化大模型
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("缺少 OPENAI_API_KEY，请在 .env 或系统环境中配置")

            # ChatOpenAI 支持从环境变量读取 base_url
            base_llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                timeout=self.timeout,
                max_retries=3,
            )
            # 主引用向后兼容
            self.llm = base_llm

            # 加载MCP配置并连接
            mcp_config = self.config.load_config()
            self.server_configs = mcp_config.get("servers", {})

            if not self.server_configs:
                print("❌ 没有配置MCP服务器")
                return False

            print("🔗 正在连接MCP服务器...")
            
            # 先测试服务器连接
            import aiohttp
            import asyncio
            
            for server_name, server_config in self.server_configs.items():
                try:
                    url = server_config.get('url')
                    if not url:
                        print(f"⚠️ 服务器 {server_name} 缺少 url 配置，跳过连接测试")
                        continue
                    print(f"🧪 测试连接到 {server_name}: {url}")
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            print(f"✅ {server_name} 连接测试成功 (状态: {response.status})")
                except Exception as test_e:
                    print(f"⚠️ {server_name} 连接测试失败: {test_e}")
            
            # 创建MCP客户端 - 强制清除缓存并禁用HTTP/2
            import httpx

            def http_client_factory(headers=None, timeout=None, auth=None):
                return httpx.AsyncClient(
                    http2=False,  # 禁用HTTP/2
                    headers=headers,
                    timeout=timeout,
                    auth=auth
                )

            # 更新服务器配置以使用自定义的httpx客户端工厂
            for server_name in self.server_configs:
                # 避免污染原配置对象，复制后添加工厂
                server_cfg = dict(self.server_configs[server_name])
                server_cfg['httpx_client_factory'] = http_client_factory
                self.server_configs[server_name] = server_cfg

            self.mcp_client = MultiServerMCPClient(self.server_configs)

            # 改为串行获取工具，避免并发问题
            print("🔧 正在逐个获取服务器工具...")
            for server_name in self.server_configs.keys():
                try:
                    print(f"─── 正在从服务器 '{server_name}' 获取工具 ───")
                    server_tools = await self.mcp_client.get_tools(server_name=server_name)
                    # 对工具名做合法化与去重
                    sanitized_tools = []
                    for tool in server_tools:
                        try:
                            original_name = getattr(tool, 'name', '') or ''
                            sanitized = self._sanitize_and_uniq_tool_name(original_name)
                            if sanitized != original_name:
                                print(f"🧹 规范化工具名: '{original_name}' -> '{sanitized}'")
                                try:
                                    tool.name = sanitized  # 覆盖名称，供后续绑定与匹配
                                except Exception:
                                    pass
                            sanitized_tools.append(tool)
                        except Exception as _e:
                            print(f"⚠️ 工具名规范化失败，跳过: {getattr(tool,'name','<unknown>')} - {_e}")
                            sanitized_tools.append(tool)
                    self.tools.extend(sanitized_tools)
                    self.tools_by_server[server_name] = sanitized_tools
                    print(f"✅ 从 {server_name} 获取到 {len(server_tools)} 个工具")
                except Exception as e:
                    print(f"❌ 从服务器 '{server_name}' 获取工具失败: {e}")
                    self.tools_by_server[server_name] = []
            
            # 注入本地“退出工具模式”工具，供判定阶段显式退出
            try:
                class ExitToolArgs(BaseModel):
                    reason: Optional[str] = Field(default=None, description="简短说明为何退出工具模式")

                def exit_tool_impl(reason: Optional[str] = None) -> Dict[str, Any]:
                    return {"status": "exit", "reason": reason or ""}

                exit_tool = StructuredTool.from_function(
                    func=exit_tool_impl,
                    name=self._exit_tool_name,
                    description="当你决定不再调用任何外部工具、应直接进入回答阶段时，调用此工具通知系统退出工具模式。",
                    args_schema=ExitToolArgs,
                )
                self.tools.append(exit_tool)
                # 分组到本地分组，便于前端展示
                self.tools_by_server.setdefault("__local__", []).append(exit_tool)
                print(f"🧰 已注入本地工具: {self._exit_tool_name}")
            except Exception as e:
                print(f"⚠️ 注入本地退出工具失败: {e}")

            # 验证工具来源，确保只有配置文件中的服务器
            print(f"🔍 配置的服务器: {list(self.server_configs.keys())}")
            print(f"🔍 实际获取到的工具数量: {len(self.tools)}")
            
            # 分组逻辑已在上面的循环中完成，无需额外调用

            print(f"✅ 成功连接，获取到 {len(self.tools)} 个工具")
            print(f"📊 服务器分组情况: {dict((name, len(tools)) for name, tools in self.tools_by_server.items())}")

            # 创建双实例：
            # 1) 带工具实例：用于判定与工具调用（非流式阶段）
            self.llm_tools = base_llm.bind_tools(self.tools)

            # 2) 无工具实例：用于最终回答真流式（避免产生 tool_calls 增量）
            self.llm_stream = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                timeout=self.timeout,
                max_retries=3,
            )

            print("🤖 Web MCP智能助手已启动！")
            return True

        except Exception as e:
            import traceback
            print(f"❌ 初始化失败: {e}")
            print(f"📋 详细错误信息:")
            traceback.print_exc()
            
            # 尝试清理可能的连接
            if hasattr(self, 'mcp_client') and self.mcp_client:
                try:
                    await self.mcp_client.close()
                except:
                    pass
            return False

    def _get_tools_system_prompt(self) -> str:
        """用于工具判定/执行阶段的系统提示词：专注于是否需要调用工具与参数生成，不做正文分析输出。"""
        now = datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
        return (
            f"今天是 {current_date}（{current_weekday}）。你是一个‘工具调度器’。\n"
            "- 你的目标是判断是否需要调用工具，并给出准确的工具名称和参数（JSON）。\n"
            "- 如果需要，请通过 tool_calls 结构体给出函数名与有效的 JSON 参数。\n"
            "- 如果不需要工具，不要输出正文分析内容。\n"
            "- 参数必须是合法 JSON 字典（object），不要输出不完整的片段。\n"
            "- 不要输出面向用户的解释或分析，这个留给后续回答模型。\n"
            f"- 若决定不再调用任何工具，请调用 {self._exit_tool_name}(reason?) 来显式退出工具模式，然后停止继续调用其他工具。\n"
        )

    def _get_stream_system_prompt(self) -> str:
        """用于最终回答阶段的系统提示词：专注于面向用户的分析与生成，不触发工具调用。"""
        now = datetime.now()
        current_date = now.strftime("%Y年%m月%d日")
        current_weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
        return (
            f"今天是 {current_date}（{current_weekday}）。你是一个回答助手。\n"
            "- 专注于清晰、结构化的中文回答与分析。\n"
            "- 不要调用或提及任何工具或函数。\n"
            "- 可以分条说明、给出结论、风险点与后续建议。\n"
        )

    def _sanitize_and_uniq_tool_name(self, name: str) -> str:
        """将工具名规范为 ^[a-zA-Z0-9_-]+$，并避免重名冲突。"""
        if not isinstance(name, str):
            name = str(name or "")
        # 仅保留字母数字下划线和连字符，其余替换为下划线
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
        if not sanitized:
            sanitized = "tool"
        base = sanitized
        # 确保唯一
        index = 1
        while sanitized in self._used_tool_names:
            index += 1
            sanitized = f"{base}_{index}"
        self._used_tool_names.add(sanitized)
        return sanitized

    async def chat_stream(self, user_input: str, history: List[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """流式探测 + 立即中断：
        - 先直接 astream 开流，短暂缓冲并检测 function_call/tool_call；
        - 若检测到工具调用：立即中断本次流式（不下发缓冲），执行工具（非流式），写回 messages 后进入下一轮；
        - 若未检测到工具：将本次流作为最终回答，开始流式推送到结束。
        """
        try:
            print(f"🤖 开始处理用户输入: {user_input[:50]}...")
            yield {"type": "status", "content": "开始生成..."}

            # 1) 构建共享消息历史（不包含系统提示，便于两套系统提示分别注入）
            shared_history: List[Dict[str, Any]] = []
            if history:
                for record in history:
                    shared_history.append({"role": "user", "content": record['user_input']})
                    if record.get('ai_response'):
                        shared_history.append({"role": "assistant", "content": record['ai_response']})
            shared_history.append({"role": "user", "content": user_input})

            max_rounds = 5
            round_index = 0
            while round_index < max_rounds:
                round_index += 1
                print(f"🧠 第 {round_index} 轮推理 (双实例：判定工具 + 纯流式回答)...")

                # 2) 使用带工具的常驻实例做判定（非流式）
                tools_messages = [{"role": "system", "content": self._get_tools_system_prompt()}] + shared_history
                try:
                    resp_check = await self.llm_tools.ainvoke(tools_messages)
                    tool_calls_check = getattr(resp_check, 'tool_calls', None)
                except Exception as e:
                    print(f"⚠️ 工具判定失败，退回纯流式：{e}")
                    tool_calls_check = None

                # 调试：打印带工具判定阶段的LLM原始输出与工具调用建议
                try:
                    content_preview = getattr(resp_check, 'content', None)
                    print("📝 工具判定阶段 LLM 输出(content):")
                    print(content_preview if content_preview else "<empty>")

                    serialized_calls = []
                    if tool_calls_check:
                        for tc in tool_calls_check:
                            try:
                                if isinstance(tc, dict):
                                    fn = tc.get('function') or {}
                                    serialized_calls.append({
                                        "id": tc.get('id'),
                                        "name": fn.get('name') or tc.get('name'),
                                        "args_raw": fn.get('arguments') or tc.get('args'),
                                    })
                                else:
                                    # 兼容对象形式
                                    fn_obj = getattr(tc, 'function', None)
                                    args_raw = getattr(tc, 'args', None)
                                    if args_raw is None and fn_obj is not None:
                                        try:
                                            args_raw = getattr(fn_obj, 'arguments', None)
                                        except Exception:
                                            args_raw = None
                                    serialized_calls.append({
                                        "id": getattr(tc, 'id', None),
                                        "name": getattr(tc, 'name', ''),
                                        "args_raw": args_raw,
                                    })
                            except Exception as _e:
                                serialized_calls.append({"$raw": str(tc)})

                    print("🧩 工具判定阶段 tool_calls (标准化):")
                    try:
                        print(json.dumps(serialized_calls, ensure_ascii=False, indent=2))
                    except Exception:
                        print(str(serialized_calls))
                except Exception as log_e:
                    print(f"⚠️ 打印判定阶段输出失败: {log_e}")

                if tool_calls_check:
                    yield {"type": "tool_plan", "content": f"AI决定调用 {len(tool_calls_check)} 个工具", "tool_count": len(tool_calls_check)}
                    # 写回assistant带tool_calls
                    try:
                        shared_history.append({
                            "role": "assistant",
                            "content": getattr(resp_check, 'content', None) or "",
                            "tool_calls": tool_calls_check
                        })
                    except Exception:
                        shared_history.append({"role": "assistant", "content": getattr(resp_check, 'content', None) or ""})

                    # 执行工具（非流式）
                    exit_to_stream = False
                    for i, tool_call in enumerate(tool_calls_check, 1):
                        if isinstance(tool_call, dict):
                            tool_id = tool_call.get('id') or f"call_{i}"
                            fn = tool_call.get('function') or {}
                            tool_name = fn.get('name') or tool_call.get('name') or ''
                            tool_args_raw = fn.get('arguments') or tool_call.get('args') or {}
                        else:
                            tool_id = getattr(tool_call, 'id', None) or f"call_{i}"
                            tool_name = getattr(tool_call, 'name', '') or ''
                            tool_args_raw = getattr(tool_call, 'args', {}) or {}

                        # 解析参数
                        if isinstance(tool_args_raw, str):
                            try:
                                parsed_args = json.loads(tool_args_raw) if tool_args_raw else {}
                            except Exception:
                                parsed_args = {"$raw": tool_args_raw}
                        elif isinstance(tool_args_raw, dict):
                            parsed_args = tool_args_raw
                        else:
                            parsed_args = {"$raw": str(tool_args_raw)}

                        yield {"type": "tool_start", "tool_id": tool_id, "tool_name": tool_name, "tool_args": parsed_args, "progress": f"{i}/{len(tool_calls_check)}"}

                        try:
                            target_tool = None
                            for tool in self.tools:
                                if tool.name == tool_name:
                                    target_tool = tool
                                    break
                            if target_tool is None:
                                error_msg = f"工具 '{tool_name}' 未找到"
                                print(f"❌ {error_msg}")
                                yield {"type": "tool_error", "tool_id": tool_id, "error": error_msg}
                                tool_result = f"错误: {error_msg}"
                            else:
                                tool_result = await target_tool.ainvoke(parsed_args)
                                yield {"type": "tool_end", "tool_id": tool_id, "tool_name": tool_name, "result": str(tool_result)}
                                # 若为显式退出工具模式的工具，则标记并中断后续工具执行
                                if tool_name == self._exit_tool_name:
                                    exit_to_stream = True
                                    # 将简短reason附加到日志
                                    try:
                                        print(f"🚪 收到退出工具模式指令: {parsed_args.get('reason', '')}")
                                    except Exception:
                                        pass
                        except Exception as e:
                            error_msg = f"工具执行出错: {e}"
                            print(f"❌ {error_msg}")
                            yield {"type": "tool_error", "tool_id": tool_id, "error": error_msg}
                            tool_result = f"错误: {error_msg}"

                        # 始终追加 tool 消息，满足 OpenAI 函数调用协议要求
                        # 对于退出工具模式，内容为简单状态，不影响后续回答质量
                        shared_history.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": str(tool_result)
                        })

                        if exit_to_stream:
                            break

                    if exit_to_stream:
                        # 立即进入最终回答的流式输出
                        buffered_text = ""
                        response_started = False
                        final_text = ""

                        loop = asyncio.get_event_loop()
                        start_t = loop.time()
                        buffer_window_seconds = 0.5
                        min_flush_chars = 60

                        try:
                            stream_messages = [{"role": "system", "content": self._get_stream_system_prompt()}] + shared_history
                            async for event in self.llm_stream.astream_events(stream_messages, version="v1"):
                                ev = event.get("event")
                                if ev != "on_chat_model_stream":
                                    continue
                                data = event.get("data", {})
                                chunk = data.get("chunk")
                                if chunk is None:
                                    continue

                                try:
                                    content = getattr(chunk, 'content', None)
                                except Exception:
                                    content = None
                                if content:
                                    if not response_started:
                                        buffered_text += content
                                        time_elapsed = loop.time() - start_t
                                        if time_elapsed >= buffer_window_seconds or len(buffered_text) >= min_flush_chars:
                                            yield {"type": "ai_response_start", "content": "AI正在回复..."}
                                            yield {"type": "ai_response_chunk", "content": buffered_text}
                                            final_text += buffered_text
                                            buffered_text = ""
                                            response_started = True
                                    else:
                                        final_text += content
                                        yield {"type": "ai_response_chunk", "content": content}
                        except Exception as e:
                            print(f"❌ 大模型流式生成失败: {e}")
                            yield {"type": "error", "content": f"大模型流式生成失败: {str(e)}"}
                            return

                        if not response_started and buffered_text:
                            yield {"type": "ai_response_start", "content": "AI正在回复..."}
                            yield {"type": "ai_response_chunk", "content": buffered_text}
                            final_text += buffered_text

                        yield {"type": "ai_response_end", "content": final_text}
                        return
                    else:
                        # 工具后继续下一轮
                        continue

                # 3) 无工具：用“无工具实例”做纯流式（不会产生 tool_calls 增量 → 无 pydantic 报错）
                #    同时保留短暂缓冲，保证首屏稳定
                # 2) 流式探测阶段（短暂缓冲，避免工具阶段文本下发）
                buffered_text = ""
                response_started = False
                final_text = ""

                # 使用事件循环时间来做短暂缓冲阈值
                loop = asyncio.get_event_loop()
                start_t = loop.time()
                buffer_window_seconds = 0.5  # 500ms 窗口
                min_flush_chars = 60         # 或者文本达到一定长度就开始下发

                try:
                    stream_messages = [{"role": "system", "content": self._get_stream_system_prompt()}] + shared_history
                    async for event in self.llm_stream.astream_events(stream_messages, version="v1"):
                        ev = event.get("event")
                        if ev != "on_chat_model_stream":
                            continue
                        data = event.get("data", {})
                        chunk = data.get("chunk")
                        if chunk is None:
                            continue

                        # 文本处理（缓冲 → 条件刷新 → 直接下发）
                        try:
                            content = getattr(chunk, 'content', None)
                        except Exception:
                            content = None
                        if content:
                            if not response_started:
                                buffered_text += content
                                time_elapsed = loop.time() - start_t
                                if time_elapsed >= buffer_window_seconds or len(buffered_text) >= min_flush_chars:
                                    yield {"type": "ai_response_start", "content": "AI正在回复..."}
                                    yield {"type": "ai_response_chunk", "content": buffered_text}
                                    final_text += buffered_text
                                    buffered_text = ""
                                    response_started = True
                            else:
                                final_text += content
                                yield {"type": "ai_response_chunk", "content": content}
                except Exception as e:
                    print(f"❌ 大模型流式生成失败: {e}")
                    yield {"type": "error", "content": f"大模型流式生成失败: {str(e)}"}
                    return

                # 未检测到工具：如果还没开始下发，说明全程都在缓冲内，统一作为最终回答下发
                if not response_started:
                    if buffered_text:
                        yield {"type": "ai_response_start", "content": "AI正在回复..."}
                        yield {"type": "ai_response_chunk", "content": buffered_text}
                        final_text += buffered_text

                yield {"type": "ai_response_end", "content": final_text}
                return

            # 轮次耗尽：不再报错，回退到最终回答的流式输出
            print(f"⚠️ 达到最大推理轮数({max_rounds})，回退为直接生成最终回答（无工具）")
            try:
                buffered_text = ""
                response_started = False
                final_text = ""

                loop = asyncio.get_event_loop()
                start_t = loop.time()
                buffer_window_seconds = 0.5
                min_flush_chars = 60

                stream_messages = [{"role": "system", "content": self._get_stream_system_prompt()}] + shared_history
                async for event in self.llm_stream.astream_events(stream_messages, version="v1"):
                    ev = event.get("event")
                    if ev != "on_chat_model_stream":
                        continue
                    data = event.get("data", {})
                    chunk = data.get("chunk")
                    if chunk is None:
                        continue

                    try:
                        content = getattr(chunk, 'content', None)
                    except Exception:
                        content = None
                    if content:
                        if not response_started:
                            buffered_text += content
                            time_elapsed = loop.time() - start_t
                            if time_elapsed >= buffer_window_seconds or len(buffered_text) >= min_flush_chars:
                                yield {"type": "ai_response_start", "content": "AI正在回复..."}
                                yield {"type": "ai_response_chunk", "content": buffered_text}
                                final_text += buffered_text
                                buffered_text = ""
                                response_started = True
                        else:
                            final_text += content
                            yield {"type": "ai_response_chunk", "content": content}

                if not response_started and buffered_text:
                    yield {"type": "ai_response_start", "content": "AI正在回复..."}
                    yield {"type": "ai_response_chunk", "content": buffered_text}
                    final_text += buffered_text

                yield {"type": "ai_response_end", "content": final_text}
                return
            except Exception as e:
                print(f"❌ 回退流式输出失败: {e}")
                yield {"type": "error", "content": f"达到最大推理轮数，且回退生成失败: {str(e)}"}
        except Exception as e:
            import traceback
            print(f"❌ chat_stream 异常: {e}")
            print("📋 详细错误信息:")
            traceback.print_exc()
            yield {"type": "error", "content": f"处理请求时出错: {str(e)}"}

    def get_tools_info(self) -> Dict[str, Any]:
        """获取工具信息列表，按MCP服务器分组"""
        if not self.tools_by_server:
            return {"servers": {}, "total_tools": 0, "server_count": 0}
        
        servers_info = {}
        total_tools = 0
        
        # 按服务器分组构建工具信息
        for server_name, server_tools in self.tools_by_server.items():
            tools_info = []
            
            for tool in server_tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {},
                    "required": []
                }
                
                # 获取参数信息 - 优化版本
                try:
                    schema = None
                    
                    # 方法1: 尝试使用args_schema (LangChain工具常用)
                    if hasattr(tool, 'args_schema') and tool.args_schema:
                        if isinstance(tool.args_schema, dict):
                            schema = tool.args_schema
                        elif hasattr(tool.args_schema, 'model_json_schema'):
                            schema = tool.args_schema.model_json_schema()
                    
                    # 方法2: 如果没有args_schema，尝试tool_call_schema
                    if not schema and hasattr(tool, 'tool_call_schema') and tool.tool_call_schema:
                        schema = tool.tool_call_schema
                    
                    # 方法3: 最后尝试input_schema
                    if not schema and hasattr(tool, 'input_schema') and tool.input_schema:
                        if isinstance(tool.input_schema, dict):
                            schema = tool.input_schema
                        elif hasattr(tool.input_schema, 'model_json_schema'):
                            try:
                                schema = tool.input_schema.model_json_schema()
                            except:
                                pass
                    
                    # 解析schema
                    if schema and isinstance(schema, dict):
                        if 'properties' in schema:
                            tool_info["parameters"] = schema['properties']
                            tool_info["required"] = schema.get('required', [])
                        elif 'type' in schema and schema.get('type') == 'object' and 'properties' in schema:
                            tool_info["parameters"] = schema['properties']
                            tool_info["required"] = schema.get('required', [])
                
                except Exception as e:
                    # 如果出错，至少保留工具的基本信息
                    print(f"⚠️ 获取工具 '{tool.name}' 参数信息失败: {e}")
                
                tools_info.append(tool_info)
            
            # 添加服务器信息
            servers_info[server_name] = {
                "name": server_name,
                "tools": tools_info,
                "tool_count": len(tools_info)
            }
            
            total_tools += len(tools_info)
        
        return {
            "servers": servers_info,
            "total_tools": total_tools,
            "server_count": len(servers_info)
        }

    async def close(self):
        """关闭连接"""
        try:
            if self.mcp_client and hasattr(self.mcp_client, 'close'):
                await self.mcp_client.close()
        except:
            pass
