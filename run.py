#!/usr/bin/env python3
"""
MiniMax Coding Plan - 流式 Token 压测工具 (终极自动化 HTML 报告版)
"""

import os
import time
import uuid
import json
import threading
import requests
import webbrowser

# ============== 配置 ==============
API_KEY = os.getenv("ANTHROPIC_AUTH_TOKEN", "请替换为你的真实API_KEY")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")
MODEL = os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.5")
QUOTA_API_URL = "https://www.minimaxi.com/v1/api/openplatform/coding_plan/remains"

CONCURRENCY = 3          
# 🔥 恢复极限输出测试，设为最大值 4096
MAX_TOKENS_OUTPUT = 4096 

if "填这里" in API_KEY or "替换" in API_KEY or not API_KEY.startswith("sk-"):
    print("❌ 致命错误：请先设置真实的 API Key！(通常以 sk- 开头)")
    exit(1)

# ============== 额度查询模块 ==============
def fetch_quota_status() -> dict:
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    try:
        resp = requests.get(QUOTA_API_URL, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "model_remains" in data and len(data["model_remains"]) > 0:
                info = data["model_remains"][0]
                total = info.get("current_interval_total_count", 0)
                remains = info.get("current_interval_usage_count", 0) 
                used = total - remains
                return {"success": True, "total": total, "remains": remains, "used": used}
    except Exception:
        pass
    return {"success": False, "total": 1500, "remains": 0, "used": 0}

# ============== 全局状态与分析模块 ==============
class UsageTracker:
    def __init__(self):
        self.active_requests = 0   # 🔥 新增：记录当前正在生成中的活跃请求数
        self.successful_requests = 0
        self.partial_requests = 0  
        self.failed_requests = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.latencies = []  
        self.start_time = time.time()
        self.lock = threading.Lock()
        
    def start_req(self):
        with self.lock: self.active_requests += 1
        
    def end_req(self):
        with self.lock: self.active_requests -= 1

    def add_input(self, tokens: int):
        with self.lock: self.total_input_tokens += tokens

    def add_output(self, tokens: int):
        with self.lock: self.total_output_tokens += tokens

    def add_success(self, latency_s: float):
        with self.lock: 
            self.successful_requests += 1
            self.latencies.append(latency_s)
            
    def add_partial(self, latency_s: float):
        with self.lock:
            self.partial_requests += 1
            self.latencies.append(latency_s)

    def add_failure(self):
        with self.lock: self.failed_requests += 1

    def print_status(self):
        with self.lock:
            elapsed = time.time() - self.start_time
            total_tokens = self.total_input_tokens + self.total_output_tokens
            quota = fetch_quota_status()
            q_str = f"🟢 剩余 {quota['remains']} 次 / 总额 {quota['total']} 次 (已消耗 {quota['used']} 次)" if quota['success'] else "查询失败"
            
            print(f"\n{'='*65}")
            print(f"📊 实时压测状态 ({elapsed:.1f}s)  |  🏃‍♂️ 正在生成中: {self.active_requests} 个")
            print(f"✅ 完整成功: {self.successful_requests} | ⚠️ 中断有效: {self.partial_requests} | ❌ 失败: {self.failed_requests}")
            print(f"📥 In: {self.total_input_tokens} | 📤 Out: {self.total_output_tokens}")
            if elapsed > 0:
                print(f"🚀 Token 吞吐率: {total_tokens/elapsed:.2f} tokens/s")
            print(f"🏦 官方额度: {q_str}")
            print(f"{'='*65}\n")

    def generate_html_report(self):
        """生成并自动打开 HTML 报告"""
        with self.lock:
            elapsed = time.time() - self.start_time
            total_valid_reqs = self.successful_requests + self.partial_requests
            total_tokens = self.total_input_tokens + self.total_output_tokens
            tps = total_tokens / elapsed if elapsed > 0 else 0

            avg_in = self.total_input_tokens / total_valid_reqs if total_valid_reqs > 0 else 0
            avg_out = self.total_output_tokens / total_valid_reqs if total_valid_reqs > 0 else 0

            avg_lat = sum(self.latencies) / len(self.latencies) if self.latencies else 0
            max_lat = max(self.latencies) if self.latencies else 0
            min_lat = min(self.latencies) if self.latencies else 0
            
            success_rate = (total_valid_reqs / (total_valid_reqs + self.failed_requests) * 100) if (total_valid_reqs + self.failed_requests) > 0 else 0

            quota = fetch_quota_status()
            health_pct = (quota['remains'] / quota['total'] * 100) if quota['total'] > 0 else 0

            # HTML 模板注入真实数据
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MiniMax 极限压测分析报告</title>
    <style>
        :root {{
            --bg-color: #f8fafc; --card-bg: rgba(255, 255, 255, 0.7);
            --text-main: #0f172a; --text-muted: #64748b;
            --shadow-sm: 0 4px 6px -1px rgba(0,0,0,0.05);
            --shadow-hover: 0 20px 25px -5px rgba(0,0,0,0.1);
        }}
        body {{
            margin: 0; padding: 3rem 2rem; background-color: var(--bg-color);
            background-image: radial-gradient(circle at 15% 50%, rgba(14, 165, 233, 0.15), transparent 25%),
                              radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.15), transparent 25%);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--text-main); display: flex; justify-content: center;
        }}
        .dashboard {{ max-width: 1200px; width: 100%; display: flex; flex-direction: column; gap: 2.5rem; }}
        .header {{ text-align: center; }}
        .header h1 {{ font-size: 3rem; margin: 0; background: linear-gradient(135deg, #0f172a, #334155); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }}
        .card {{
            background: var(--card-bg); border: 1px solid rgba(255,255,255,0.8); border-radius: 24px;
            padding: 2rem; backdrop-filter: blur(20px); box-shadow: var(--shadow-sm); transition: 0.3s;
        }}
        .card:hover {{ transform: translateY(-5px); box-shadow: var(--shadow-hover); }}
        .card-title {{ font-size: 0.95rem; font-weight: 600; color: var(--text-muted); margin-bottom: 1.2rem; }}
        .card-value {{ font-size: 3rem; font-weight: 800; margin: 0; }}
        .card-subtitle {{ font-size: 0.9rem; color: var(--text-muted); margin-top: 1rem; display: flex; justify-content: space-between; }}
        .text-blue {{ background: linear-gradient(135deg, #0ea5e9, #2563eb); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .text-purple {{ background: linear-gradient(135deg, #a855f7, #6366f1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .text-red {{ background: linear-gradient(135deg, #f43f5e, #e11d48); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .text-green {{ background: linear-gradient(135deg, #10b981, #059669); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .progress-container {{ width: 100%; height: 12px; background: #e2e8f0; border-radius: 10px; margin-top: 1.5rem; overflow: hidden; }}
        .progress-bar {{ height: 100%; background: linear-gradient(90deg, #34d399, #10b981); border-radius: 10px; width: {health_pct}%; }}
        .badge {{ background: rgba(16, 185, 129, 0.1); color: #10b981; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; border: 1px solid rgba(16, 185, 129, 0.2); }}
    </style>
</head>
<body>
    <div class="dashboard">
        <header class="header">
            <h1>MiniMax 数据压测中枢</h1>
            <p>Coding Plan Token 极限并发测试报告</p>
        </header>
        <div class="grid">
            <div class="card">
                <div class="card-title">⏱️ 总运行时间</div>
                <div class="card-value">{elapsed:.2f}<span style="font-size: 1.5rem; color: #64748b;"> s</span></div>
                <div class="card-subtitle"><span>并发设定: {CONCURRENCY} Worker</span></div>
            </div>
            <div class="card">
                <div class="card-title">🚀 平均吞吐率 (TPS)</div>
                <div class="card-value text-blue">{tps:.2f}</div>
                <div class="card-subtitle"><span>Tokens / 秒</span><span>计算包含 Input+Output</span></div>
            </div>
            <div class="card">
                <div class="card-title">💎 总 Token 消耗</div>
                <div class="card-value text-purple">{total_tokens}</div>
                <div class="card-subtitle"><span>输入: {self.total_input_tokens}</span><span>输出: {self.total_output_tokens}</span></div>
            </div>
            <div class="card">
                <div class="card-title">🔄 有效请求率</div>
                <div class="card-value text-red">{success_rate:.1f}<span style="font-size: 1.5rem;"> %</span></div>
                <div class="card-subtitle"><span>完整:{self.successful_requests} / 中断:{self.partial_requests}</span><span>失败: {self.failed_requests}</span></div>
            </div>
            <div class="card">
                <div class="card-title">⏳ 响应延迟分析</div>
                <div class="card-value">{avg_lat:.2f}<span style="font-size: 1.5rem; color: #64748b;"> s</span></div>
                <div class="card-subtitle"><span>最快: {min_lat:.2f}s</span><span>最慢: {max_lat:.2f}s</span></div>
            </div>
            <div class="card">
                <div class="card-title">📦 单次请求均值</div>
                <div class="card-value text-blue" style="font-size: 2.5rem;">~{int(avg_in + avg_out)} <span style="font-size: 1.2rem; color: #64748b;">Tokens</span></div>
                <div class="card-subtitle"><span>Input: ~{int(avg_in)}</span><span>Output: ~{int(avg_out)}</span></div>
            </div>
            <div class="card" style="grid-column: 1 / -1;">
                <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                    <div>
                        <div class="card-title">🏦 官方额度状态 (Coding Plan)</div>
                        <div class="card-value text-green" style="font-size: 3.5rem;">剩余 {quota['remains']} 次</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="badge" style="margin-bottom: 8px; display: inline-block;">健康度: {health_pct:.1f}% 可用</span>
                        <div style="font-weight: 700; font-size: 1.2rem;">总额: {quota['total']} 次</div>
                        <div style="color: #64748b; font-weight: 500;">已消耗: {quota['used']} 次</div>
                    </div>
                </div>
                <div class="progress-container"><div class="progress-bar"></div></div>
                <div class="card-subtitle" style="margin-top: 1.5rem; justify-content: flex-end;">
                    <span>⏳ 动态恢复窗口监控中...</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
            # 保存为 HTML 文件
            report_path = os.path.abspath("minimax_report.html")
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            print(f"\n✨ 压测报告已生成: {report_path}")
            # 自动在浏览器打开
            webbrowser.open(f"file://{report_path}")

# ============== 重型 Prompt 生成器 ==============
def generate_heavy_prompt() -> str:
    run_id = str(uuid.uuid4())[:8]
    prompt = f"// Test Run ID: {run_id}\nclass EnterpriseSystemManager {{\n"
    for i in range(300):
        prompt += f"    public String processModule{i}() {{ return \"\"; }}\n"
    prompt += "}\n\n指令：逐个解释以上方法的业务用途，并写一篇1000字的架构演进史，务必详细写满字数。"
    return prompt

# ============== 流式 API 调用 ==============
def call_api_stream(worker_id: int, tracker: UsageTracker):
    url = f"{BASE_URL}/v1/messages"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    payload = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS_OUTPUT,
        "stream": True,
        "messages": [{"role": "user", "content": generate_heavy_prompt()}]
    }

    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=30) as resp:
            if resp.status_code == 429:
                yield {"status": "rate_limit"}
                return
            if resp.status_code != 200:
                yield {"status": "error", "error": f"HTTP {resp.status_code}: {resp.text[:100]}"}
                return

            chunk_count = 0
            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]": break
                        try:
                            event_data = json.loads(data_str)
                            event_type = event_data.get("type")

                            if event_type == "message_start":
                                in_tokens = event_data.get("message", {}).get("usage", {}).get("input_tokens", 0)
                                tracker.add_input(in_tokens)
                                yield {"status": "start", "input": in_tokens}
                            elif event_type == "content_block_delta":
                                chunk_count += 1
                                if chunk_count % 50 == 0:
                                    print(f"⚡ Worker {worker_id}: 持续输出中 ({chunk_count} 片段)...")
                            elif event_type == "message_delta":
                                out_tokens = event_data.get("usage", {}).get("output_tokens", 0)
                                tracker.add_output(out_tokens)
                                yield {"status": "end", "output": out_tokens}
                        except json.JSONDecodeError:
                            continue
            yield {"status": "success"}
    except requests.exceptions.Timeout:
         yield {"status": "error", "error": "请求超时 (Timeout)"}
    except Exception as e:
        yield {"status": "error", "error": str(e)}

# ============== Worker 逻辑 ==============
def worker(worker_id: int, tracker: UsageTracker, stop_event: threading.Event):
    backoff_time = 5
    while not stop_event.is_set():
        tracker.start_req() # 标记活跃开始
        start_t = time.time()
        is_success, in_t, out_t = False, 0, 0
        
        for event in call_api_stream(worker_id, tracker):
            if stop_event.is_set():
                break  # 收到停止信号，跳出流接收
            
            if event["status"] == "rate_limit":
                time.sleep(backoff_time)
                backoff_time = min(backoff_time * 2, 60)
                break
            elif event["status"] == "error":
                # 🔥 修复点2：确保请求报错能打印到控制台，并正确计入“失败请求”中
                print(f"❌ Worker {worker_id}: 请求出错 - {event['error']}")
                tracker.add_failure()
                time.sleep(2)
                break
            elif event["status"] == "start":
                in_t = event["input"]
            elif event["status"] == "end":
                out_t = event["output"]
            elif event["status"] == "success":
                is_success = True
                backoff_time = 5

        cost_t = time.time() - start_t
        tracker.end_req() # 标记活跃结束
        
        # 判断请求结束状态（完整成功 vs 被强行中断但有数据）
        if is_success:
            tracker.add_success(cost_t)
            print(f"✅ Worker {worker_id}: 完整跑通! In: {in_t} | Out: {out_t} | 耗时: {cost_t:.1f}s")
        elif in_t > 0 and not is_success:
            # 只有没有走 error 或 success 但获取了输入 Token 的才算被中断的有效请求
            tracker.add_partial(cost_t)
            print(f"⚠️ Worker {worker_id}: 请求被中断，但已计入 Token 消耗。")

        if not stop_event.is_set():
            time.sleep(1)

# ============== 主函数 ==============
if __name__ == "__main__":
    print("\n🚀 启动终极压测 (带自动化 HTML 报表)...")
    print("👉 随时按 Ctrl+C 停止，将自动在浏览器弹出演示大屏！")
    
    tracker = UsageTracker()
    stop_event = threading.Event()

    def status_thread():
        while not stop_event.is_set():
            time.sleep(10)
            if not stop_event.is_set():
                tracker.print_status()

    threading.Thread(target=status_thread, daemon=True).start()

    threads = []
    for i in range(CONCURRENCY):
        t = threading.Thread(target=worker, args=(i, tracker, stop_event), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True: 
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号，正在汇总数据并生成 HTML 报告...")
        stop_event.set()
        time.sleep(1.5) # 等待数据刷新
        tracker.generate_html_report()

