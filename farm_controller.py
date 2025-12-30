import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import os
import time
import json
import random
import re
import math
from datetime import datetime

# 尝试导入 u2
try:
    import uiautomator2 as u2
    U2_AVAILABLE = True
except ImportError:
    U2_AVAILABLE = False

# ================= 🔧 配置区 =================
CONFIG_FILE = "farm_config.json"
KEYWORDS_FILE = "keywords.txt"
VM_SCRIPT = "/data/local/tmp/vm.sh"
PKG_NAME = "fr.vinted"
BACKUP_ROOT = "/sdcard/MultiApp_Farm" 

# ================= 🔥 Vinted UI ID (基于你的XML精准适配) 🔥 =================

# 1. 搜索与导航
ID_SEARCH_INPUT = "fr.vinted:id/view_input_value"
ID_TAB_HOME = "fr.vinted:id/navigation_tab_discover"

class VintedFarmGUI:
    def __init__(self, root):
        self.root = root
        root.title("Vinted 养号中控台 V7.4 (Bezier Curves + Toast)")
        root.geometry("800x900")
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.keywords = []
        
        # 记录上一次点击的坐标，防止重复点击
        self.last_click_pos = None 
        
        self.load_config()
        self.load_keywords()
        self.setup_ui()
        
        if not U2_AVAILABLE:
            self.log("⚠️ 未检测到 uiautomator2，功能受限。请运行 pip install uiautomator2")

    # ================= Bezier Curve Implementation =================
    
    def bezier_curve(self, p0, p1, p2, p3, num_points=20):
        """
        Generate points along a cubic Bezier curve.
        p0: start point (x, y)
        p1: first control point
        p2: second control point
        p3: end point (x, y)
        """
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            # Cubic Bezier formula
            x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
            y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
            points.append((x, y))
        return points
    
    def human_swipe(self, d, start_x, start_y, end_x, end_y, duration=0.3):
        """
        Perform a human-like swipe using Bezier curve with variable speed.
        """
        # Generate control points with random offset for natural curve
        dx = end_x - start_x
        dy = end_y - start_y
        
        # Control points with random deviation (10-30% of distance)
        deviation1 = random.uniform(0.1, 0.3)
        deviation2 = random.uniform(0.1, 0.3)
        
        # Add perpendicular offset for more natural curve
        perp_offset1 = random.uniform(-50, 50)
        perp_offset2 = random.uniform(-50, 50)
        
        cp1_x = start_x + dx * 0.33 + perp_offset1
        cp1_y = start_y + dy * 0.33
        
        cp2_x = start_x + dx * 0.66 + perp_offset2
        cp2_y = start_y + dy * 0.66
        
        # Generate Bezier points
        num_points = random.randint(15, 25)  # Variable number of points
        points = self.bezier_curve(
            (start_x, start_y),
            (cp1_x, cp1_y),
            (cp2_x, cp2_y),
            (end_x, end_y),
            num_points
        )
        
        # Execute swipe with variable speed
        base_delay = duration / num_points
        
        for i in range(len(points) - 1):
            # Variable speed: slower at start/end, faster in middle
            progress = i / num_points
            if progress < 0.2 or progress > 0.8:
                speed_multiplier = random.uniform(1.2, 1.5)  # Slower
            else:
                speed_multiplier = random.uniform(0.7, 1.0)  # Faster
            
            delay = base_delay * speed_multiplier
            
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            
            try:
                d.swipe(x1, y1, x2, y2, duration=0.01)  # Very short individual swipes
                time.sleep(delay)
            except:
                pass
    
    def smart_scroll(self, d, direction="up", scale=0.7):
        """
        Smart scrolling with Bezier curves.
        direction: "up" or "down"
        scale: how much of the screen to scroll (0.0 to 1.0)
        """
        w, h = d.window_size()
        
        # Define safe scroll area (avoid edges)
        x_center = w * 0.5 + random.uniform(-50, 50)  # Random horizontal offset
        
        if direction == "up":
            start_y = h * (0.7 + random.uniform(-0.1, 0.1))
            end_y = h * (0.3 - scale * 0.5 + random.uniform(-0.05, 0.05))
        else:
            start_y = h * (0.3 + random.uniform(-0.1, 0.1))
            end_y = h * (0.7 + scale * 0.5 + random.uniform(-0.05, 0.05))
        
        duration = random.uniform(0.2, 0.4)
        self.human_swipe(d, x_center, start_y, x_center, end_y, duration)

    def setup_ui(self):
        # === 1. 环境设置 ===
        frame_setup = ttk.LabelFrame(self.root, text=" ⚙️ 环境设置 ", padding=10)
        frame_setup.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(frame_setup, text="ADB 路径:").grid(row=0, column=0, sticky="w")
        self.entry_adb = ttk.Entry(frame_setup, width=50)
        self.entry_adb.insert(0, self.config.get("adb_path", ""))
        self.entry_adb.grid(row=0, column=1, padx=5)
        
        ttk.Label(frame_setup, text="设备 ID:").grid(row=1, column=0, sticky="w")
        self.entry_device = ttk.Entry(frame_setup, width=50)
        self.entry_device.insert(0, self.config.get("device_id", ""))
        self.entry_device.grid(row=1, column=1, padx=5)
        
        ttk.Button(frame_setup, text="保存配置", command=self.save_config).grid(row=0, column=2, rowspan=2, padx=5)

        # === 2. 单号管理 (New/Save/Load) ===
        frame_single = ttk.LabelFrame(self.root, text=" 👤 账号管理 (核心功能) ", padding=10)
        frame_single.pack(fill="x", padx=10, pady=5)
        
        # 线路选择
        ttk.Label(frame_single, text="线路 (New用):").grid(row=0, column=0, sticky="w")
        self.node_var = tk.StringVar(value="UK-01")
        nodes = [f"UK-{i:02d}" for i in range(1, 51)]
        self.node_combo = ttk.Combobox(frame_single, textvariable=self.node_var, values=nodes, width=10)
        self.node_combo.grid(row=0, column=1, padx=5)
        
        # 账号名称
        ttk.Label(frame_single, text="账号名:").grid(row=0, column=2, sticky="w")
        self.acc_name_var = tk.StringVar(value="User_01")
        self.entry_acc_name = ttk.Entry(frame_single, textvariable=self.acc_name_var, width=15)
        self.entry_acc_name.grid(row=0, column=3, padx=5)
        
        # 按钮区
        btn_frame_s = ttk.Frame(frame_single)
        btn_frame_s.grid(row=1, column=0, columnspan=4, pady=10)
        
        ttk.Button(btn_frame_s, text="🆕 创建新环境", command=self.action_new).pack(side="left", padx=5)
        ttk.Button(btn_frame_s, text="💾 保存存档", command=self.action_save).pack(side="left", padx=5)
        ttk.Button(btn_frame_s, text="♻️ 恢复环境", command=self.action_load).pack(side="left", padx=5)

        # === 3. 存档列表 ===
        frame_acc = ttk.LabelFrame(self.root, text=" 📂 存档列表 (自动扫描) ", padding=10)
        frame_acc.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.list_acc = tk.Listbox(frame_acc, height=6, selectmode=tk.MULTIPLE)
        self.list_acc.pack(side="left", fill="both", expand=True)
        
        sb = ttk.Scrollbar(frame_acc, orient="vertical", command=self.list_acc.yview)
        sb.pack(side="right", fill="y")
        self.list_acc.config(yscrollcommand=sb.set)
        
        ttk.Button(frame_acc, text="🔄 刷新列表", command=self.refresh_accounts).pack(side="bottom", fill="x", pady=2)

        # === 4. 自动化挂机 ===
        frame_ctrl = ttk.LabelFrame(self.root, text=" 🤖 自动养号 ", padding=10)
        frame_ctrl.pack(fill="x", padx=10, pady=5)
        
        self.btn_start = ttk.Button(frame_ctrl, text="▶️ 开始挂机 (选中账号)", command=self.start_farming)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_stop = ttk.Button(frame_ctrl, text="⏹️ 停止", command=self.stop_farming, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Button(frame_ctrl, text="📸 抓UI结构", command=self.dump_ui_hierarchy).pack(side="right", padx=5)
        
        # === 5. 日志 ===
        frame_log = ttk.LabelFrame(self.root, text=" 📜 详细日志 ", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.text_log = scrolledtext.ScrolledText(frame_log, height=12, state='disabled', font=('Consolas', 9))
        self.text_log.pack(fill="both", expand=True)

    # ================= 基础功能 =================
    def log(self, msg):
        print(f"[Console] {msg}")
        if hasattr(self, 'text_log'):
            self.text_log.config(state='normal')
            ts = datetime.now().strftime('%H:%M:%S')
            self.text_log.insert(tk.END, f"[{ts}] {msg}\n")
            self.text_log.see(tk.END)
            self.text_log.config(state='disabled')

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config = json.load(f)
            except: self.config = {}
        else: self.config = {}

    def load_keywords(self):
        if os.path.exists(KEYWORDS_FILE):
            try:
                with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
                    self.keywords = [line.strip() for line in f if line.strip()]
                self.log(f"✅ 已加载 {len(self.keywords)} 个关键词")
            except: self.keywords = []
        else: self.keywords = []

    def save_config(self):
        self.config["adb_path"] = self.entry_adb.get()
        self.config["device_id"] = self.entry_device.get()
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f)
        self.log("✅ 配置已保存")

    def get_adb_cmd(self, shell_cmd):
        adb = self.entry_adb.get()
        dev = self.entry_device.get()
        if not adb or not os.path.exists(adb):
            self.log(f"❌ ADB路径错误")
            return None
        cmd = [adb]
        if dev: cmd.extend(["-s", dev])
        if shell_cmd.startswith("ls "): cmd.extend(["shell", shell_cmd])
        else: cmd.extend(["shell", f"su -c '{shell_cmd}'"])
        return cmd

    def run_adb(self, shell_cmd):
        cmd = self.get_adb_cmd(shell_cmd)
        if not cmd: return False
        try:
            subprocess.run(cmd, check=True, creationflags=0x08000000 if os.name == 'nt' else 0)
            return True
        except Exception as e:
            self.log(f"❌ ADB失败: {e}")
            return False

    def refresh_accounts(self):
        self.log(f"📂 扫描存档...")
        adb = self.entry_adb.get()
        dev = self.entry_device.get()
        cmd = [adb]
        if dev: cmd.extend(["-s", dev])
        cmd.extend(["shell", f"ls {BACKUP_ROOT}/*.tar.gz"])
        try:
            result = subprocess.check_output(cmd, encoding='utf-8', stderr=subprocess.STDOUT, creationflags=0x08000000 if os.name == 'nt' else 0)
            files = result.strip().split('\n')
            self.list_acc.delete(0, tk.END)
            for f in files:
                if f.strip() and ".tar.gz" in f and "No such" not in f:
                    name = os.path.basename(f).replace(".tar.gz", "")
                    self.list_acc.insert(tk.END, name)
            self.log(f"✅ 刷新完毕")
        except: self.log("ℹ️ 暂无存档")

    def check_file_exists(self, filename):
        adb = self.entry_adb.get()
        dev = self.entry_device.get()
        cmd = [adb]
        if dev: cmd.extend(["-s", dev])
        cmd.extend(["shell", f"[ -f {filename} ] && echo YES || echo NO"])
        try:
            res = subprocess.check_output(cmd, encoding='utf-8', creationflags=0x08000000 if os.name == 'nt' else 0)
            return "YES" in res
        except: return False

    # ================= 按钮动作 =================
    def action_new(self):
        name = self.acc_name_var.get()
        node = self.node_var.get()
        
        if not name: return
        
        profile_path = f"{BACKUP_ROOT}/Profiles/{name}.conf"
        if self.check_file_exists(profile_path):
            if not messagebox.askyesno("⚠️ 警告", f"账号 [{name}] 已存在！\n是否覆盖？"): return
        
        self.log(f"🆕 创建: {name} | 线路: {node}")
        threading.Thread(target=self.run_vm_task, args=("new", name, node)).start()

    def action_save(self):
        name = self.acc_name_var.get()
        if not name: return
        self.log(f"💾 保存: {name}")
        threading.Thread(target=self.run_vm_task, args=("save", name)).start()

    def action_load(self):
        name = self.acc_name_var.get()
        if not name: return
        self.log(f"♻️ 恢复: {name}")
        threading.Thread(target=self.run_vm_task, args=("load", name)).start()

    def run_vm_task(self, action, name, node=None):
        if action == "new":
            cmd = f"sh {VM_SCRIPT} {action} {name} {node}"
        else:
            cmd = f"sh {VM_SCRIPT} {action} {name}"
        
        if self.run_adb(cmd):
            self.log(f"✅ {action} 成功")
        else:
            self.log(f"❌ {action} 失败")

    # ================= 自动化核心 (深度修复误判与拟人化) =================

    def start_farming(self):
        selected = self.list_acc.curselection()
        if not selected:
            messagebox.showwarning("提示", "请选择账号")
            return
        accounts = [self.list_acc.get(i) for i in selected]
        self.is_running = True
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        threading.Thread(target=self.farm_loop, args=(accounts,)).start()

    def stop_farming(self):
        self.is_running = False
        self.stop_event.set()
        self.log("🛑 正在停止...")

    def farm_loop(self, accounts):
        self.log("🚀 任务开始...")
        while self.is_running:
            for acc in accounts:
                if self.stop_event.is_set(): break
                self.process_account(acc)
                
                if self.stop_event.is_set(): break
                sleep_t = random.randint(20, 40)
                self.log(f"☕ 休息 {sleep_t}s...")
                time.sleep(sleep_t)
            
            if self.stop_event.is_set(): break
            long_sleep = random.randint(300, 600)
            self.log(f"😴 轮次结束，休眠 {long_sleep/60:.1f} 分钟...")
            time.sleep(long_sleep)
        
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.log("🛑 任务结束")

    def process_account(self, account_name):
        self.log(f"▶️ 处理: {account_name}")
        if not self.run_adb(f"sh {VM_SCRIPT} load {account_name}"): return
        
        self.log("⏳ 等待启动 (20s)...")
        time.sleep(20)
        
        if U2_AVAILABLE:
            self.u2_actions()
        else:
            time.sleep(30)
            
        self.log(f"💾 存档: {account_name}")
        self.run_adb(f"sh {VM_SCRIPT} save {account_name}")
        self.log("-" * 30)

    def u2_actions(self):
        try:
            dev_id = self.entry_device.get()
            d = u2.connect(dev_id) if dev_id else u2.connect()
            
            # 启动 Vinted 并等待
            d.app_start(PKG_NAME)
            time.sleep(8)
            
            # 时长控制：每个号随机逛 3-5 分钟
            session_time = random.randint(180, 300)
            start = time.time()
            self.log(f"⏱️ 活跃时长: {int(session_time/60)}分钟")

            while time.time() - start < session_time:
                if self.stop_event.is_set(): return
                
                # 随机动作
                if self.keywords and random.random() < 0.2: # 20% 搜索
                    kw = random.choice(self.keywords)
                    self.action_search(d, kw)
                else: # 80% 浏览首页
                    self.action_browse_feed(d, clicks=random.randint(2, 4))
                
                # 每轮动作后检查并恢复状态
                self.safe_back_to_home(d)
                
        except Exception as e:
            self.log(f"❌ 自动化错: {e}")

    def safe_back_to_home(self, d):
        """
        超级安全的返回首页逻辑 (修复误判问题)
        """
        # 1. 优先检测当前界面是否已经是首页界面
        # 如果能找到 "Home" 标签 或 "搜索框"，说明我们在App里面，安全
        if d(resourceId=ID_TAB_HOME).exists or d(resourceId=ID_SEARCH_INPUT).exists:
            # 已经在首页附近，不需要按返回，或者只需要确保点一下Home
            if d(resourceId=ID_TAB_HOME).exists:
                # 偶尔点一下Home确保刷新
                if random.random() < 0.2: 
                    d(resourceId=ID_TAB_HOME).click()
            return
        
        # 2. 如果没在首页，尝试按一次 Back
        d.press("back")
        time.sleep(2.0) # 稍微多等一下 UI 反应
                
        # 3. 再次检测是否回到了 App 界面 (双重保险)
        if d(resourceId=ID_TAB_HOME).exists or d(resourceId=ID_SEARCH_INPUT).exists:
            return # 安全，不需要重启
                    
        # 4. 只有在确定界面元素不存在，且包名也不对时，才认为"崩了"
        current_app = d.app_current()
        if current_app['package'] != PKG_NAME:
            self.log("⚠️ 确实离开了应用，正在拉回...")
            d.app_start(PKG_NAME)
            time.sleep(5) # 重启多等一会
                    
        # 5. 最后尝试归位到 Home Tab
        if d(resourceId=ID_TAB_HOME).exists:
             d(resourceId=ID_TAB_HOME).click()

    # ================= 🔥 核心功能优化区 🔥 =================

    def action_browse_feed(self, d, clicks):
        """浏览首页并随机点击商品，包含优化后的滑动和防重逻辑"""
        w, h = d.window_size()
        
        for _ in range(clicks):
            if self.stop_event.is_set(): return
            
            # 1. 模拟真人滑动浏览 (使用 Bezier 曲线)
            self.log("   🖐️ 滑动浏览 (人类轨迹)...")
            self.smart_scroll(d, "up", scale=random.uniform(0.6, 0.9))
            time.sleep(random.uniform(2, 4))
            
            # 2. 查找商品 (Vinted item pattern)
            items = d(resourceIdMatches=".*item.*|.*product.*")
            
            if items.count > 0:
                try:
                    # 随机选一个当前屏幕内的商品
                    idx = random.randint(0, items.count - 1)
                    item = items[idx]
                    bounds = item.info['bounds']
                    
                    # 过滤逻辑：避开顶部和底部
                    if bounds['bottom'] > (h * 0.9) or bounds['top'] < (h * 0.1):
                        continue

                    cx = (bounds['left'] + bounds['right']) / 2
                    cy = (bounds['top'] + bounds['bottom']) / 2
                    
                    # === 防重点击逻辑 ===
                    if self.last_click_pos:
                        dist = ((cx - self.last_click_pos[0])**2 + (cy - self.last_click_pos[1])**2)**0.5
                        if dist < 100: 
                            self.log("   ⚠️ 商品位置重复，强制再滑一次...")
                            self.smart_scroll(d, "up", scale=0.5)
                            time.sleep(1)
                            continue
                    
                    self.last_click_pos = (cx, cy)
                    
                    self.log(f"   👉 点击商品")
                    d.click(cx, cy)
                    
                    # === 进入详情页逻辑 ===
                    time.sleep(random.uniform(5, 7)) 
                    
                    # 3. 拟人化浏览图片 (随机步长)
                    self.action_gallery_browse(d)

                    # 4. 简单浏览详情描述
                    if random.random() < 0.6:
                        self.smart_scroll(d, "up", scale=0.4)
                        time.sleep(random.uniform(1, 2))

                    # 5. 执行点赞 (概率降低到 10% 左右)
                    if random.random() < 0.10: 
                        self.try_like_item(d)
                    
                    # 6. 返回首页
                    self.log("   🔙 返回首页")
                    
                    # 直接调用安全返回，不自己乱判断
                    self.safe_back_to_home(d)
                    
                except Exception as e:
                    self.log(f"   ⚠️ 操作异常: {str(e)[:50]}")
            else:
                self.log("   ⚠️ 未找到可见商品，继续滑动...")

    def action_gallery_browse(self, d):
        """
        详情页图片浏览逻辑 - 拟人化增强 (Bezier 曲线)
        区域: 左上(0.13, 0.12) -> 右下(0.93, 0.54)
        """
        w, h = d.window_size()
        
        # 安全区域边界
        area_left = w * 0.13
        area_right = w * 0.93
        area_top = h * 0.12
        area_bottom = h * 0.54
        
        swipes = random.randint(1, 4)
        current_idx = 0
        
        self.log(f"   🖼️ 浏览图片 ({swipes}次)")
        
        for i in range(swipes):
            # 决定方向
            direction = "next"
            if current_idx > 0 and random.random() < 0.3: 
                direction = "prev"
            
            # Y轴基准位置
            y_base = random.uniform(area_top + 50, area_bottom - 50)
            start_y = y_base + random.randint(-20, 20)
            end_y = y_base + random.randint(-20, 20)
            
            # 动态步长
            base_distance = w * random.uniform(0.4, 0.7)
            
            if direction == "next":
                # 从右往左滑
                start_x = random.uniform(area_right - 100, area_right - 10)
                end_x = max(area_left, start_x - base_distance)
                current_idx += 1
            else:
                # 从左往右滑
                start_x = random.uniform(area_left + 10, area_left + 100)
                end_x = min(area_right, start_x + base_distance)
                current_idx -= 1
            
            # 使用 Bezier 曲线滑动
            duration = random.uniform(0.2, 0.45)
            self.human_swipe(d, start_x, start_y, end_x, end_y, duration)
            time.sleep(random.uniform(0.8, 1.5))

    def try_like_item(self, d):
        """精准点赞逻辑 (已适配 favorite_button)"""
        target_id = "favorite_button"
        clicked = False

        # 优先精准匹配
        if d(resourceIdMatches=f".*{target_id}").exists:
            self.log(f"   ❤️ 尝试点赞 (ID: {target_id})")
            try:
                d(resourceIdMatches=f".*{target_id}").click()
                clicked = True
            except: pass
        
        # 兜底：描述匹配
        if not clicked:
            if d(descriptionMatches=".*Favourited by.*").exists:
                 try:
                     d(descriptionMatches=".*Favourited by.*").click()
                     clicked = True
                 except: pass

        if clicked:
            time.sleep(1.5)
        else:
            self.log("   👀 未找到点赞按钮")

    def action_search(self, d, keyword):
        try:
            if d(resourceId=ID_SEARCH_INPUT).exists:
                d(resourceId=ID_SEARCH_INPUT).click()
                time.sleep(1.5)
                d.send_keys(keyword)
                time.sleep(0.5)
                d.press("enter")
                self.log(f"   🔎 搜: {keyword}")
                time.sleep(5)
                self.action_browse_feed(d, clicks=2)
            else:
                d.press("back")
        except: pass

    def dump_ui_hierarchy(self):
        def run():
            try:
                dev_id = self.entry_device.get()
                d = u2.connect(dev_id) if dev_id else u2.connect()
                xml = d.dump_hierarchy()
                with open("ui_dump.xml", "w", encoding="utf-8") as f: f.write(xml)
                self.log("✅ UI已保存")
            except Exception as e: self.log(f"❌ {e}")
        threading.Thread(target=run).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = VintedFarmGUI(root)
    root.mainloop()