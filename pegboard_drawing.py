import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
from PIL import Image, ImageDraw
import math
import json
import os
import ctypes
from ctypes import wintypes

def set_taskbar_icon():
    """设置任务栏图标"""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Pegboard.Drawing.App')
    except:
        pass

class PegboardDrawingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("洞洞板画图")
        
        # 设置窗口图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "works", "3iw5x-p77cc-001.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"无法加载图标: {e}")
        
        # 默认设置
        self.rows = 8
        self.cols = 8
        self.grid_size = 50  # 点间距
        self.point_radius = 5  # 点的半径
        self.label_distance = 20  # 行号列号距离点阵的距离
        
        # 数据存储
        self.lines = []  # 存储连线：[(start_pos, end_pos, color, selected)]
        self.components = []  # 存储元器件：[(start_pos, end_pos, text, color, selected)]
        self.squares = []  # 存储方形：[(p1, p2, p3, p4, selected)]
        
        # 状态
        self.draw_mode = "line"  # 绘制模式：line（连线）、square（方形）、component（元器件）
        self.first_point = None  # 第一个点击的点
        self.square_points = []  # 方形绘制中的点：[p1, p2]
        self.selected_item = None  # 当前选中的项 ('line', index)、('component', index) 或 ('square', index)
        self.line_color_mode = "red"  # 线条颜色模式：red 或 blue
        
        # 按键状态跟踪（更可靠的方法）
        self.shift_key_pressed = False  # Shift 键是否被按下
        self.alt_key_pressed = False  # Alt 键是否被按下
        
        # 缩放和平移状态
        self.zoom_scale = 1.0  # 缩放比例，1.0 表示原始大小
        self.pan_offset_x = 0  # 水平平移偏移量
        self.pan_offset_y = 0  # 垂直平移偏移量
        self.panning = False  # 是否正在平移
        self.pan_start_x = 0  # 平移起始X坐标
        self.pan_start_y = 0  # 平移起始Y坐标
        self.pan_start_offset_x = 0  # 平移起始时的偏移X
        self.pan_start_offset_y = 0  # 平移起始时的偏移Y
        
        # 撤销历史栈
        self.undo_stack = []  # 存储历史状态以便撤销
        self.max_undo_steps = 50  # 最大撤销步数
        
        # 默认保存路径
        self.save_path = os.path.expanduser(r"~\Documents")
        
        # 当前打开的存档文件路径(用于自动保存)
        self.current_archive_file = None
        
        # 加载设置
        self.load_settings()
        
        # 创建界面
        self.create_widgets()
        
        # 绑定事件
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.root.bind("<Tab>", self.on_tab_press)
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-Z>", self.undo)  # 处理大写Z
        
        # 绑定按键事件来跟踪 Shift 和 Alt 键的状态
        self.root.bind("<Shift_L>", lambda e: setattr(self, 'shift_key_pressed', True))
        self.root.bind("<Shift_R>", lambda e: setattr(self, 'shift_key_pressed', True))
        self.root.bind("<KeyRelease-Shift_L>", lambda e: setattr(self, 'shift_key_pressed', False))
        self.root.bind("<KeyRelease-Shift_R>", lambda e: setattr(self, 'shift_key_pressed', False))
        
        self.root.bind("<Alt_L>", lambda e: setattr(self, 'alt_key_pressed', True))
        self.root.bind("<Alt_R>", lambda e: setattr(self, 'alt_key_pressed', True))
        self.root.bind("<KeyRelease-Alt_L>", lambda e: setattr(self, 'alt_key_pressed', False))
        self.root.bind("<KeyRelease-Alt_R>", lambda e: setattr(self, 'alt_key_pressed', False))
        
        # 绑定 ESC 键用于退出方形模式
        self.root.bind("<Escape>", self.on_escape_press)
        
        # 绑定滚轮缩放事件（Windows 使用 MouseWheel，Linux 使用 Button-4/Button-5）
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux 向上滚
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux 向下滚
        
        # 绑定中键平移事件
        self.canvas.bind("<Button-2>", self.on_middle_button_press)
        self.canvas.bind("<ButtonRelease-2>", self.on_middle_button_release)
        self.canvas.bind("<B2-Motion>", self.on_middle_button_drag)
        
        # 初始绘制
        self.draw_board()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_widgets(self):
        # 顶部控制面板
        control_frame = tk.Frame(self.root, pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # 行数设置
        tk.Label(control_frame, text="行数:").pack(side=tk.LEFT, padx=5)
        self.rows_entry = tk.Entry(control_frame, width=5)
        self.rows_entry.insert(0, str(self.rows))
        self.rows_entry.pack(side=tk.LEFT, padx=5)
        
        # 列数设置
        tk.Label(control_frame, text="列数:").pack(side=tk.LEFT, padx=5)
        self.cols_entry = tk.Entry(control_frame, width=5)
        self.cols_entry.insert(0, str(self.cols))
        self.cols_entry.pack(side=tk.LEFT, padx=5)
        
        # 应用按钮
        apply_btn = tk.Button(control_frame, text="应用", command=self.apply_settings)
        apply_btn.pack(side=tk.LEFT, padx=10)
        
        # 设置按钮
        settings_btn = tk.Button(control_frame, text="设置", command=self.open_settings)
        settings_btn.pack(side=tk.LEFT, padx=10)
        
        # 保存图片按钮
        save_btn = tk.Button(control_frame, text="保存图片", command=self.save_image)
        save_btn.pack(side=tk.LEFT, padx=10)
        
        # 保存存档按钮
        save_archive_btn = tk.Button(control_frame, text="保存存档", command=self.save_archive)
        save_archive_btn.pack(side=tk.LEFT, padx=10)
        
        # 加载存档按钮
        load_archive_btn = tk.Button(control_frame, text="加载存档", command=self.load_archive)
        load_archive_btn.pack(side=tk.LEFT, padx=10)
        
        # 删除按钮
        delete_btn = tk.Button(control_frame, text="删除选中", command=self.delete_selected)
        delete_btn.pack(side=tk.LEFT, padx=10)
        
        # 清空按钮
        clear_btn = tk.Button(control_frame, text="清空", command=self.clear_all)
        clear_btn.pack(side=tk.LEFT, padx=10)
        
        # 当前颜色模式显示
        self.color_label = tk.Label(control_frame, text="当前颜色: 红色", fg="red", font=("Arial", 10, "bold"))
        self.color_label.pack(side=tk.LEFT, padx=20)
        
        # 当前绘制模式显示
        self.mode_label = tk.Label(control_frame, text="当前模式: 连线", fg="black", font=("Arial", 10, "bold"))
        self.mode_label.pack(side=tk.LEFT, padx=20)
        
        # 画布
        self.canvas = tk.Canvas(self.root, bg="white")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.pack_propagate(False)  # 防止画布大小随窗口变化
    
    def apply_settings(self):
        try:
            new_rows = int(self.rows_entry.get())
            new_cols = int(self.cols_entry.get())
            if new_rows < 2 or new_cols < 2:
                messagebox.showerror("错误", "行数和列数至少为2")
                return
            
            # 检查现有内容是否会被新的网格范围截断
            def is_valid_position(pos):
                x, y = pos
                col = int(round((x - self.grid_size) / self.grid_size))
                row = int(round((y - self.grid_size) / self.grid_size))
                return 0 <= row < new_rows and 0 <= col < new_cols
            
            # 检查所有连线
            for start, end, _, _ in self.lines:
                if not (is_valid_position(start) and is_valid_position(end)):
                    messagebox.showwarning("警告", "应用新设置会导致部分连线超出网格范围，请先删除超出范围的内容或选择清空所有内容")
                    return
            
            # 检查所有元器件
            for start, end, _, _, _ in self.components:
                if not (is_valid_position(start) and is_valid_position(end)):
                    messagebox.showwarning("警告", "应用新设置会导致部分元器件超出网格范围，请先删除超出范围的内容或选择清空所有内容")
                    return
            
            # 检查所有方形
            for square_data in self.squares:
                p1, p2, p3, p4, _ = square_data[:5]
                if not (is_valid_position(p1) and is_valid_position(p2) and is_valid_position(p3) and is_valid_position(p4)):
                    messagebox.showwarning("警告", "应用新设置会导致部分方形超出网格范围，请先删除超出范围的内容或选择清空所有内容")
                    return
            
            # 确认是否应用新设置
            result = messagebox.askyesnocancel("确认", "应用新设置时是否清空所有绘制内容？\n\n点击'是'清空内容，点击'否'保留内容")
            if result is not None:
                # 应用新设置
                self.rows = new_rows
                self.cols = new_cols
                self.save_state()
                if result:
                    self.clear_all()
                self.auto_save_archive()
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def clear_all(self):
        # 清空前保存状态
        self.save_state()
        self.lines = []
        self.components = []
        self.squares = []
        self.first_point = None
        self.square_points = []
        self.selected_item = None
        # 不重置颜色模式和绘制模式，保留用户当前选择
        if self.line_color_mode == "red":
            self.color_label.config(text="当前颜色: 红色", fg="red")
        else:
            self.color_label.config(text="当前颜色: 蓝色", fg="blue")
        self.update_mode_label()
        self.draw_board()
        self.auto_save_archive()
    
    def draw_board(self):
        self.canvas.delete("all")
        
        # 固定画布大小，只在第一次初始化
        if not hasattr(self, 'canvas_fixed_width'):
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width < 100:
                canvas_width = 800
                canvas_height = 600
            self.canvas_fixed_width = canvas_width
            self.canvas_fixed_height = canvas_height
            self.canvas.config(width=canvas_width, height=canvas_height)
        
        # 计算所有点的坐标（世界坐标）
        self.points = {}
        for i in range(self.rows):
            for j in range(self.cols):
                x = j * self.grid_size + self.grid_size
                y = i * self.grid_size + self.grid_size
                self.points[(i, j)] = (x, y)
        
        # 先绘制方形（不透明淡绿色，无边框，在最底层）
        for idx, square_data in enumerate(self.squares):
            p1, p2, p3, p4, selected = square_data[:5]
            no_expand = square_data[5] if len(square_data) > 5 else False
            
            if no_expand:
                # 不扩展，直接使用四个顶点
                p1_screen = self.world_to_screen(p1[0], p1[1])
                p2_screen = self.world_to_screen(p2[0], p2[1])
                p3_screen = self.world_to_screen(p3[0], p3[1])
                p4_screen = self.world_to_screen(p4[0], p4[1])
            else:
                # 计算方形中心
                center_x = (p1[0] + p2[0] + p3[0] + p4[0]) / 4
                center_y = (p1[1] + p2[1] + p3[1] + p4[1]) / 4
                
                # 每个顶点向外扩展40像素
                expand = 40
                
                def expand_point(px, py):
                    dx = px - center_x
                    dy = py - center_y
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 0:
                        return (px + dx / dist * expand, py + dy / dist * expand)
                    return (px, py)
                
                p1_exp = expand_point(p1[0], p1[1])
                p2_exp = expand_point(p2[0], p2[1])
                p3_exp = expand_point(p3[0], p3[1])
                p4_exp = expand_point(p4[0], p4[1])
                
                p1_screen = self.world_to_screen(p1_exp[0], p1_exp[1])
                p2_screen = self.world_to_screen(p2_exp[0], p2_exp[1])
                p3_screen = self.world_to_screen(p3_exp[0], p3_exp[1])
                p4_screen = self.world_to_screen(p4_exp[0], p4_exp[1])
            self.canvas.create_polygon(p1_screen, p2_screen, p3_screen, p4_screen, fill="#90EE90", outline="", width=0, tags=f"square_{idx}")
        
        # 再绘制连线（在方块之上）
        for idx, (start, end, color_mode, selected) in enumerate(self.lines):
            # 转换坐标
            start_screen = self.world_to_screen(start[0], start[1])
            end_screen = self.world_to_screen(end[0], end[1])
            if color_mode == "red":
                color = "#ff6666" if selected else "red"
            else:
                color = "#6666ff" if selected else "blue"
            width = int((6 if selected else 4) * self.zoom_scale)
            self.canvas.create_line(
                start_screen[0], start_screen[1], end_screen[0], end_screen[1],
                fill=color, width=width, tags=f"line_{idx}"
            )
        
        # 再绘制元器件（在方块之上）
        for idx, (start, end, text, color_mode, selected) in enumerate(self.components):
            self.draw_component(start, end, text, color_mode, selected, idx)
        
        # 最后绘制点阵（确保第一个点显示在最上层）
        for i in range(self.rows):
            for j in range(self.cols):
                x_world, y_world = self.points[(i, j)]
                x_screen, y_screen = self.world_to_screen(x_world, y_world)
                radius = self.point_radius * self.zoom_scale
                
                # 检查是否是第一个点（连线模式）
                if self.draw_mode == "line" and self.first_point == (i, j):
                    # 第一个点：黄色，大小两倍
                    self.canvas.create_oval(
                        x_screen - radius * 2, y_screen - radius * 2,
                        x_screen + radius * 2, y_screen + radius * 2,
                        fill="yellow"
                    )
                elif self.draw_mode == "square" and (i, j) in self.square_points:
                    # 方形模式中已选择的点：橙色，大小两倍
                    self.canvas.create_oval(
                        x_screen - radius * 2, y_screen - radius * 2,
                        x_screen + radius * 2, y_screen + radius * 2,
                        fill="orange"
                    )
                elif self.draw_mode == "component" and self.first_point == (i, j):
                    # 元器件模式中第一个点：黄色，大小两倍
                    self.canvas.create_oval(
                        x_screen - radius * 2, y_screen - radius * 2,
                        x_screen + radius * 2, y_screen + radius * 2,
                        fill="yellow"
                    )
                else:
                    # 普通点：黑色，正常大小
                    self.canvas.create_oval(
                        x_screen - radius, y_screen - radius,
                        x_screen + radius, y_screen + radius,
                        fill="black"
                    )
        
        # 绘制顶部列号：从右往左显示 1 到 n
        for j in range(self.cols):
            # 从右往左编号，所以右边的列是1
            col_num = self.cols - j  # 从右往左：最右边是1，最左边是n
            # 获取该列最上方点的位置
            x_world, y_world = self.points[(0, j)]
            x_screen, y_screen = self.world_to_screen(x_world, y_world)
            # 列号显示在点上方，距离可调整
            font_size = int(25 * self.zoom_scale)
            self.canvas.create_text(
                x_screen, y_screen - self.label_distance * self.zoom_scale,
                text=str(col_num), fill="#333333",
                font=("Imprint MT Shadow", font_size, "bold")
            )
        
        # 绘制左侧行号：从下到上显示 A 到 Z，超过 Z 后循环
        for i in range(self.rows):
            # 从下往上编号，使用字母 A-Z
            # 超过 Z 后循环：0->A, 1->B, ..., 25->Z, 26->A, 27->B, ...
            row_letter = chr(ord('A') + ((self.rows - 1 - i) % 26))
            #for i in range(self.rows)从上到下
            # 获取该行最左边点的位置
            x_world, y_world = self.points[(i, 0)]
            x_screen, y_screen = self.world_to_screen(x_world, y_world)
            # 行号显示在点左侧，距离可调整
            font_size = int(25 * self.zoom_scale)
            self.canvas.create_text(
                x_screen - self.label_distance * self.zoom_scale, y_screen,
                text=row_letter, fill="#333333",
                font=("Imprint MT Shadow", font_size, "bold")
            )
    
    def draw_component(self, start, end, text, color_mode, selected, idx):
        # 转换坐标
        start_screen = self.world_to_screen(start[0], start[1])
        end_screen = self.world_to_screen(end[0], end[1])
        
        # 计算中点（屏幕坐标）
        mid_x = (start_screen[0] + end_screen[0]) / 2
        mid_y = (start_screen[1] + end_screen[1]) / 2
        
        # 计算角度
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        
        # 方块尺寸（应用缩放）
        box_width = 40 * self.zoom_scale
        box_height = 20 * self.zoom_scale
        
        # 方块四个角（相对于中点）
        corners = [
            (-box_width/2, -box_height/2),
            (box_width/2, -box_height/2),
            (box_width/2, box_height/2),
            (-box_width/2, box_height/2)
        ]
        
        # 旋转方块
        rotated_corners = []
        for cx, cy in corners:
            rx = cx * math.cos(angle) - cy * math.sin(angle)
            ry = cx * math.sin(angle) + cy * math.cos(angle)
            rotated_corners.append((mid_x + rx, mid_y + ry))
        
        # 绘制连接线
        if color_mode == "red":
            line_color = "#ff6666" if selected else "red"
            outline_color = "red"
        else:
            line_color = "#6666ff" if selected else "blue"
            outline_color = "blue"
        line_width = int((6 if selected else 4) * self.zoom_scale)
        self.canvas.create_line(
            start_screen[0], start_screen[1], rotated_corners[0][0], rotated_corners[0][1],
            fill=line_color, width=line_width, tags=f"component_{idx}"
        )
        self.canvas.create_line(
            end_screen[0], end_screen[1], rotated_corners[2][0], rotated_corners[2][1],
            fill=line_color, width=line_width, tags=f"component_{idx}"
        )
        
        # 绘制方块（使用stipple实现透明效果）
        if color_mode == "red":
            box_color = "#ffcccc" if selected else "#ff9999"
        else:
            box_color = "#ccccff" if selected else "#9999ff"
        self.canvas.create_polygon(
            rotated_corners, fill=box_color, outline=outline_color, width=line_width,
            stipple="gray50", tags=f"component_{idx}"
        )
        
        # 绘制文字（字体大小也随缩放调整）
        font_size = int(20 * self.zoom_scale)
        self.canvas.create_text(
            mid_x, mid_y, text=text, fill="black",
            font=("Arial", font_size, "bold"), tags=f"component_{idx}"
        )
    
    def get_nearest_point(self, x, y):
        # 将屏幕坐标转换为世界坐标
        world_x, world_y = self.screen_to_world(x, y)
        
        min_dist = float('inf')
        nearest = None
        
        # 点击范围也需要随缩放调整
        click_radius = 20 * self.zoom_scale
        
        for pos, px, py in [(pos, self.points[pos][0], self.points[pos][1]) for pos in self.points]:
            # 计算世界坐标中的距离
            dist = math.sqrt((world_x - px)**2 + (world_y - py)**2)
            if dist < click_radius:  # 点击范围
                if dist < min_dist:
                    min_dist = dist
                    nearest = pos
        
        return nearest
    
    def is_perpendicular(self, p1, p2, p3):
        """检查 p1-p2 是否垂直于 p2-p3"""
        # 使用行列坐标而不是像素坐标来计算，避免浮点数精度问题
        v1 = (p2[0] - p1[0], p2[1] - p1[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])
        # 点积为0表示垂直
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        return dot_product == 0    
    def update_mode_label(self):
        """更新绘制模式显示标签"""
        mode_text = {
            "line": "当前模式: 连线",
            "square": "当前模式: 方形",
            "component": "当前模式: 元器件"
        }
        self.mode_label.config(text=mode_text.get(self.draw_mode, "当前模式: 连线"))
    
    def on_left_click(self, event):
        x, y = event.x, event.y
        nearest = self.get_nearest_point(x, y)
        
        if nearest is None:
            self.first_point = None
            self.square_points = []
            self.draw_board()
            return
        
        if self.root.winfo_containing(x + self.canvas.winfo_rootx(), y + self.canvas.winfo_rooty()) != self.canvas:
            return
        
        # 根据绘制模式处理点击
        if self.draw_mode == "line":
            self.handle_line_mode(nearest, self.shift_key_pressed, self.alt_key_pressed)
        elif self.draw_mode == "square":
            self.handle_square_mode(nearest)
        elif self.draw_mode == "component":
            self.handle_component_mode(nearest)
    
    def handle_line_mode(self, nearest, shift_pressed, alt_pressed):
        """处理连线模式"""
        if self.first_point is None:
            self.first_point = nearest
            self.draw_board()
        else:
            # 检查按键状态
            # 添加额外的验证条件：只有在 Shift 或 Alt 明确被按下时才执行特殊操作
            # 否则总是创建连线
            if shift_pressed and not alt_pressed:
                # 按住Shift键，创建元器件
                self.save_state()
                start_pos = self.points[self.first_point]
                end_pos = self.points[nearest]
                self.components.append([start_pos, end_pos, "", self.line_color_mode, False])
                self.first_point = None
                self.draw_board()
                self.auto_save_archive()
            elif alt_pressed and not shift_pressed:
                # 按住Alt键，切换到方形绘制模式
                self.draw_mode = "square"
                self.square_points = [self.first_point, nearest]
                self.first_point = None
                self.update_mode_label()
                self.draw_board()
            else:
                # 创建连线（包括两个键都没按，或两个键都按的情况）
                self.save_state()
                start_pos = self.points[self.first_point]
                end_pos = self.points[nearest]
                self.lines.append([start_pos, end_pos, self.line_color_mode, False])
                self.first_point = None
                self.draw_board()
                self.auto_save_archive()
    
    def handle_square_mode(self, nearest):
        """处理方形模式"""
        if len(self.square_points) == 0:
            # 第一个点
            self.square_points = [nearest]
            self.draw_board()
        elif len(self.square_points) == 1:
            # 第二个点
            if nearest != self.square_points[0]:
                self.square_points.append(nearest)
                self.draw_board()
        elif len(self.square_points) == 2:
            p1, p2 = self.square_points
            p3 = nearest
            self.save_state()
            
            if p2 == p3:
                # 第2点和第3点是同一个点，创建新的方形生成逻辑
                p1_pos = self.points[p1]
                p2_pos = self.points[p2]
                
                # 计算从p1到p2的向量
                vector_x = p2_pos[0] - p1_pos[0]
                vector_y = p2_pos[1] - p1_pos[1]
                
                # 归一化向量
                length = math.sqrt(vector_x * vector_x + vector_y * vector_y)
                if length > 0:
                    unit_x = vector_x / length
                    unit_y = vector_y / length
                    
                    # 计算垂直向量（顺时针90度）
                    perp_x = unit_y
                    perp_y = -unit_x
                    
                    # 半个单位长度（使用grid_size的一半）
                    half_unit = self.grid_size / 2
                    
                    # middle1: 从p1沿p1到p2方向长半个单位长度
                    middle1_x = p1_pos[0] - unit_x * half_unit
                    middle1_y = p1_pos[1] - unit_y * half_unit
                    
                    # op1: 从middle1沿垂直方向长半个单位长度
                    op1_x = middle1_x + perp_x * half_unit
                    op1_y = middle1_y + perp_y * half_unit
                    
                    # op2: 从middle1沿垂直反方向长半个单位长度
                    op2_x = middle1_x - perp_x * half_unit
                    op2_y = middle1_y - perp_y * half_unit
                    
                    # middle2: 从p2往p1方向走半个单位
                    middle2_x = p2_pos[0] + unit_x * half_unit
                    middle2_y = p2_pos[1] + unit_y * half_unit
                    
                    # 从middle2沿垂直方向和反方向长出两个点
                    # 点4: 垂直方向
                    p4_x = middle2_x + perp_x * half_unit
                    p4_y = middle2_y + perp_y * half_unit
                    
                    # 点3: 垂直反方向
                    p3_x = middle2_x - perp_x * half_unit
                    p3_y = middle2_y - perp_y * half_unit
                    
                    # 创建方形，顶点顺序为op1, op2, p3, p4
                    # 最后一个True表示不扩展
                    self.squares.append([
                        (op1_x, op1_y), 
                        (op2_x, op2_y), 
                        (p3_x, p3_y), 
                        (p4_x, p4_y), 
                        False,
                        True
                    ])
                
            else:
                # 第2点和第3点不是同一个点，绘制方形
                p4 = (p1[0] + p3[0] - p2[0], p1[1] + p3[1] - p2[1])
                self.squares.append([self.points[p1], self.points[p2], self.points[p3], self.points[p4], False])
            
            self.square_points = []
            self.draw_board()
            self.auto_save_archive()
    
    def handle_component_mode(self, nearest):
        """处理元器件模式"""
        if self.first_point is None:
            self.first_point = nearest
            self.draw_board()
        else:
            # 保存状态
            self.save_state()
            
            # 创建元器件
            start_pos = self.points[self.first_point]
            end_pos = self.points[nearest]
            self.components.append([start_pos, end_pos, "", self.line_color_mode, False])
            
            self.first_point = None
            self.draw_board()
            self.auto_save_archive()
    
    def on_double_click(self, event):
        x, y = event.x, event.y
        
        # 将屏幕坐标转换为世界坐标
        world_x, world_y = self.screen_to_world(x, y)
        
        # 检查是否双击了元器件
        for idx, (start, end, text, color_mode, selected) in enumerate(self.components):
            mid_x = (start[0] + end[0]) / 2
            mid_y = (start[1] + end[1]) / 2
            
            # 简单的距离检查（使用世界坐标）
            dist = math.sqrt((world_x - mid_x)**2 + (world_y - mid_y)**2)
            if dist < 20 * self.zoom_scale:  # 方块范围内（随缩放调整）
                new_text = simpledialog.askstring("编辑文字", "请输入文字:", initialvalue=text)
                if new_text is not None:
                    self.components[idx][2] = new_text
                    # 清除所有点击状态
                    self.first_point = None
                    self.square_points = []
                    self.draw_board()
                    self.auto_save_archive()
                return
    
    def on_right_click(self, event):
        x, y = event.x, event.y
        
        # 将屏幕坐标转换为世界坐标
        world_x, world_y = self.screen_to_world(x, y)
        
        # 取消所有选中
        for line in self.lines:
            line[3] = False
        for comp in self.components:
            comp[4] = False
        for sq in self.squares:
            sq[4] = False
        self.selected_item = None
        
        # 点击检测范围（随缩放调整）
        line_threshold = 10 * self.zoom_scale
        component_threshold = 20 * self.zoom_scale
        
        # 检查是否点击了连线
        for idx, (start, end, color_mode, selected) in enumerate(self.lines):
            # 点到线段的距离（使用世界坐标）
            dist = self.point_to_line_distance(world_x, world_y, start[0], start[1], end[0], end[1])
            if dist < line_threshold:
                self.lines[idx][3] = True
                self.selected_item = ('line', idx)
                self.draw_board()
                return
        
        # 检查是否点击了元器件
        for idx, (start, end, text, color_mode, selected) in enumerate(self.components):
            mid_x = (start[0] + end[0]) / 2
            mid_y = (start[1] + end[1]) / 2
            dist = math.sqrt((world_x - mid_x)**2 + (world_y - mid_y)**2)
            if dist < component_threshold:
                self.components[idx][4] = True
                self.selected_item = ('component', idx)
                self.draw_board()
                return
        
        # 检查是否点击了方形（检查点是否在方形内部）
        for idx, (p1, p2, p3, p4, selected) in enumerate(self.squares):
            if self.point_in_polygon(world_x, world_y, [p1, p2, p3, p4]):
                self.squares[idx][4] = True
                self.selected_item = ('square', idx)
                self.draw_board()
                return
    
    def on_tab_press(self, event):
        # 切换线条颜色模式（只影响新绘制的线条和元器件）
        if self.line_color_mode == "red":
            self.line_color_mode = "blue"
            self.color_label.config(text="当前颜色: 蓝色", fg="blue")
        else:
            self.line_color_mode = "red"
            self.color_label.config(text="当前颜色: 红色", fg="red")
        # 不重绘，只切换模式
    
    def on_escape_press(self, event):
        """ESC 键处理：退出方形模式，回到连线模式"""
        if self.draw_mode == "square":
            self.draw_mode = "line"
            self.square_points = []
            self.update_mode_label()
            self.draw_board()
    
    def on_mouse_wheel(self, event):
        """滚轮缩放处理"""
        # 确定缩放方向
        if event.num == 5 or event.delta < 0:
            # 向下滚动，缩小
            zoom_factor = 0.9
        else:
            # 向上滚动，放大
            zoom_factor = 1.1
        
        # 计算新的缩放比例
        new_scale = self.zoom_scale * zoom_factor
        
        # 限制缩放范围
        if new_scale < 0.2:  # 最小缩小到 20%
            return
        if new_scale > 5.0:  # 最大放大到 500%
            return
        
        # 获取鼠标在画布上的位置
        mouse_x = event.x
        mouse_y = event.y
        
        # 计算缩放前的世界坐标
        world_x = (mouse_x - self.pan_offset_x) / self.zoom_scale
        world_y = (mouse_y - self.pan_offset_y) / self.zoom_scale
        
        # 更新缩放比例
        self.zoom_scale = new_scale
        
        # 计算新的偏移量，使鼠标位置保持不变
        self.pan_offset_x = mouse_x - world_x * self.zoom_scale
        self.pan_offset_y = mouse_y - world_y * self.zoom_scale
        
        # 重新绘制
        self.draw_board()
        
        # 阻止事件继续传播
        return "break"
    
    def on_middle_button_press(self, event):
        """中键按下：开始平移"""
        self.panning = True
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.pan_start_offset_x = self.pan_offset_x
        self.pan_start_offset_y = self.pan_offset_y
        self.canvas.config(cursor="fleur")  # 设置鼠标样式为移动图标
    
    def on_middle_button_release(self, event):
        """中键释放：结束平移"""
        self.panning = False
        self.canvas.config(cursor="")  # 恢复默认鼠标样式
    
    def on_middle_button_drag(self, event):
        """中键拖动：平移画布"""
        if self.panning:
            # 计算移动的距离
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            
            # 更新偏移量
            self.pan_offset_x = self.pan_start_offset_x + dx
            self.pan_offset_y = self.pan_start_offset_y + dy
            
            # 重新绘制
            self.draw_board()
    
    def world_to_screen(self, x, y):
        """将世界坐标转换为屏幕坐标"""
        return (x * self.zoom_scale + self.pan_offset_x,
                y * self.zoom_scale + self.pan_offset_y)
    
    def screen_to_world(self, x, y):
        """将屏幕坐标转换为世界坐标"""
        return ((x - self.pan_offset_x) / self.zoom_scale,
                (y - self.pan_offset_y) / self.zoom_scale)
    
    def save_state(self):
        """保存当前状态到历史栈，用于撤销"""
        import copy
        state = {
            "lines": copy.deepcopy(self.lines),
            "components": copy.deepcopy(self.components),
            "squares": copy.deepcopy(self.squares),
            "line_color_mode": self.line_color_mode,
            "rows": self.rows,
            "cols": self.cols,
            "zoom_scale": self.zoom_scale,
            "pan_offset_x": self.pan_offset_x,
            "pan_offset_y": self.pan_offset_y,
            "label_distance": self.label_distance
        }
        self.undo_stack.append(state)
        # 限制历史记录数量
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)
    
    def undo(self, event=None):
        """撤销上一个操作"""
        if not self.undo_stack:
            messagebox.showinfo("提示", "没有可撤销的操作")
            return
        
        # 从历史栈中取出上一个状态
        state = self.undo_stack.pop()
        
        # 恢复状态
        self.lines = state["lines"]
        self.components = state["components"]
        self.squares = state.get("squares", [])
        self.line_color_mode = state["line_color_mode"]
        self.rows = state["rows"]
        self.cols = state["cols"]
        self.zoom_scale = state.get("zoom_scale", 1.0)
        self.pan_offset_x = state.get("pan_offset_x", 0)
        self.pan_offset_y = state.get("pan_offset_y", 0)
        self.label_distance = state.get("label_distance", 20)
        
        # 更新界面显示
        self.rows_entry.delete(0, tk.END)
        self.rows_entry.insert(0, str(self.rows))
        self.cols_entry.delete(0, tk.END)
        self.cols_entry.insert(0, str(self.cols))
        
        # 更新颜色模式显示
        if self.line_color_mode == "red":
            self.color_label.config(text="当前颜色: 红色", fg="red")
        else:
            self.color_label.config(text="当前颜色: 蓝色", fg="blue")
        
        # 重置状态
        self.first_point = None
        self.square_points = []
        self.selected_item = None
        
        # 重新绘制
        self.draw_board()
    
    def point_in_polygon(self, x, y, polygon):
        """检测点是否在多边形内部（使用射线法）"""
        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        # 计算点到线段的距离
        A = px - x1
        B = py - y1
        C = x2 - x1
        D = y2 - y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            return math.sqrt(A * A + B * B)
        
        param = -1
        if len_sq != 0:
            param = dot / len_sq
        
        if param < 0:
            xx = x1
            yy = y1
        elif param > 1:
            xx = x2
            yy = y2
        else:
            xx = x1 + param * C
            yy = y1 + param * D
        
        dx = px - xx
        dy = py - yy
        return math.sqrt(dx * dx + dy * dy)
    
    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("500x300")
        settings_window.resizable(False, False)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 第一个设置项：文件保存路径
        tk.Label(settings_window, text="文件保存路径:", font=("Arial", 12)).pack(pady=10)
        
        path_frame = tk.Frame(settings_window)
        path_frame.pack(pady=5, padx=20, fill=tk.X)
        
        path_var = tk.StringVar(value=self.save_path)
        path_entry = tk.Entry(path_frame, textvariable=path_var, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse_folder():
            folder = filedialog.askdirectory(initialdir=self.save_path)
            if folder:
                path_var.set(folder)
        
        browse_btn = tk.Button(path_frame, text="浏览", command=browse_folder)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 第二个设置项：行号列号距离点阵的距离
        tk.Label(settings_window, text="行号列号距离点阵的距离:", font=("Arial", 12)).pack(pady=10)
        
        distance_frame = tk.Frame(settings_window)
        distance_frame.pack(pady=5, padx=20, fill=tk.X)
        
        distance_var = tk.StringVar(value=str(self.label_distance))
        distance_entry = tk.Entry(distance_frame, textvariable=distance_var, width=10)
        distance_entry.pack(side=tk.LEFT)
        
        tk.Label(distance_frame, text="像素").pack(side=tk.LEFT, padx=5)
        
        def save_settings():
            # 保存文件路径
            new_path = path_var.get().strip()
            if new_path and os.path.isdir(new_path):
                self.save_path = new_path
            elif new_path:
                try:
                    os.makedirs(new_path, exist_ok=True)
                    self.save_path = new_path
                except Exception as e:
                    messagebox.showerror("错误", f"无法创建目录: {e}")
                    return
            else:
                messagebox.showerror("错误", "请输入有效的路径")
                return
            
            # 保存行号列号距离
            try:
                new_distance = int(distance_var.get().strip())
                if new_distance >= 0:
                    self.label_distance = new_distance
                    self.draw_board()  # 重新绘制以应用新距离
                else:
                    messagebox.showerror("错误", "距离必须大于等于0")
                    return
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                return
            
            settings_window.destroy()
            messagebox.showinfo("成功", "设置已更新")
        
        btn_frame = tk.Frame(settings_window)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="保存", command=save_settings, width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="取消", command=settings_window.destroy, width=10).pack(side=tk.LEFT, padx=10)
    
    def delete_selected(self):
        # 删除前保存状态
        self.save_state()
        if self.selected_item is None:
            messagebox.showinfo("提示", "请先右键选中要删除的连线、元器件或方形")
            return
        
        item_type, idx = self.selected_item
        
        if item_type == 'line':
            del self.lines[idx]
        elif item_type == 'component':
            del self.components[idx]
        elif item_type == 'square':
            del self.squares[idx]
        
        self.selected_item = None
        self.draw_board()
        self.auto_save_archive()
    
    def on_closing(self):
        """窗口关闭事件处理"""
        # 保存设置
        self.save_settings_to_file()
        
        # 检查是否有内容需要保存
        has_content = len(self.lines) > 0 or len(self.components) > 0 or len(self.squares) > 0
        
        if has_content:
            # 弹出确认对话框
            result = messagebox.askyesno("确认", "是否保存当前内容后再退出？")
            if result:
                # 用户选择保存
                self.save_archive()
        
        # 关闭窗口
        self.root.destroy()
    
    def get_settings_file(self):
        """获取设置文件路径"""
        settings_dir = os.path.join(os.path.dirname(__file__), "works")
        return os.path.join(settings_dir, "settings.json")
    
    def save_settings_to_file(self):
        """保存设置到文件"""
        settings_file = self.get_settings_file()
        data = {
            "save_path": self.save_path,
            "label_distance": self.label_distance
        }
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            print(f"保存设置失败: {e}")
    
    def load_settings(self):
        """从文件加载设置"""
        settings_file = self.get_settings_file()
        if not os.path.exists(settings_file):
            return
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.save_path = data.get("save_path", os.path.expanduser(r"~\Documents"))
            self.label_distance = data.get("label_distance", 20)
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def save_image(self):
        from datetime import datetime
        default_filename = datetime.now().strftime("%Y%m%d%H%M")
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=default_filename,
            initialdir=self.save_path,
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        # A4纸尺寸 (mm) 和 打印分辨率 (600 DPI)
        A4_WIDTH_MM = 210
        A4_HEIGHT_MM = 297
        DPI = 600
        HOLE_SPACING_MM = 2.54  # 两个孔圆心之间的距离
        
        # 转换
        pixels_per_mm = DPI / 25.4  # 每毫米像素数
        hole_spacing_px = HOLE_SPACING_MM * pixels_per_mm  # 孔间距像素数（不用int，保留精度）
        
        # 点半径（1mm直径的孔）
        point_radius_px = 0.5 * pixels_per_mm
        
        # 计算内容区域大小
        content_width_px = (self.cols - 1) * hole_spacing_px + hole_spacing_px
        content_height_px = (self.rows - 1) * hole_spacing_px + hole_spacing_px
        
        # A4纸像素尺寸
        a4_width_px = int(A4_WIDTH_MM * pixels_per_mm)
        a4_height_px = int(A4_HEIGHT_MM * pixels_per_mm)
        
        # 计算偏移量使内容居中
        offset_x = (a4_width_px - content_width_px) / 2
        offset_y = (a4_height_px - content_height_px) / 2
        
        # 创建A4尺寸的PIL图像
        image = Image.new("RGBA", (a4_width_px, a4_height_px), "white")
        draw = ImageDraw.Draw(image)
        
        # 计算每个点在A4图片中的坐标
        def to_a4_coords(row, col):
            x = offset_x + col * hole_spacing_px
            y = offset_y + row * hole_spacing_px
            return (x, y)
        
        # 从原始坐标反推行列索引（原始画布的 grid_size 是 50，点位置是 x=j*50+50, y=i*50+50）
        def coords_to_rowcol(pos):
            x, y = pos
            col = int(round((x - self.grid_size) / self.grid_size))
            row = int(round((y - self.grid_size) / self.grid_size))
            if 0 <= row < self.rows and 0 <= col < self.cols:
                return (row, col)
            return None
        
        # 绘制方形（先绘制，在最底层）
        for square_data in self.squares:
            p1, p2, p3, p4, selected = square_data[:5]
            p1_idx = coords_to_rowcol(p1)
            p2_idx = coords_to_rowcol(p2)
            p3_idx = coords_to_rowcol(p3)
            p4_idx = coords_to_rowcol(p4)
            
            if all(idx is not None for idx in [p1_idx, p2_idx, p3_idx, p4_idx]):
                a4_points = [to_a4_coords(*idx) for idx in [p1_idx, p2_idx, p3_idx, p4_idx]]
                draw.polygon(a4_points, fill="#90EE90")
        
        # 绘制连线
        for start, end, color_mode, selected in self.lines:
            line_color = "red" if color_mode == "red" else "blue"
            start_idx = coords_to_rowcol(start)
            end_idx = coords_to_rowcol(end)
            
            if start_idx and end_idx:
                a4_start = to_a4_coords(*start_idx)
                a4_end = to_a4_coords(*end_idx)
                draw.line([a4_start[0], a4_start[1], a4_end[0], a4_end[1]], fill=line_color, width=int(1.0 * pixels_per_mm))
        
        # 绘制元器件
        for start, end, text, color_mode, selected in self.components:
            start_idx = coords_to_rowcol(start)
            end_idx = coords_to_rowcol(end)
            
            if start_idx and end_idx:
                a4_start = to_a4_coords(*start_idx)
                a4_end = to_a4_coords(*end_idx)
                
                mid_x = (a4_start[0] + a4_end[0]) / 2
                mid_y = (a4_start[1] + a4_end[1]) / 2
                
                angle = math.atan2(a4_end[1] - a4_start[1], a4_end[0] - a4_start[0])
                box_width = 2 * pixels_per_mm
                box_height = 1 * pixels_per_mm
                
                corners = [
                    (-box_width/2, -box_height/2),
                    (box_width/2, -box_height/2),
                    (box_width/2, box_height/2),
                    (-box_width/2, box_height/2)
                ]
                
                rotated_corners = []
                for cx, cy in corners:
                    rx = cx * math.cos(angle) - cy * math.sin(angle)
                    ry = cx * math.sin(angle) + cy * math.cos(angle)
                    rotated_corners.append((mid_x + rx, mid_y + ry))
                
                line_color = "red" if color_mode == "red" else "blue"
                draw.line([a4_start[0], a4_start[1], rotated_corners[0][0], rotated_corners[0][1]], fill=line_color, width=int(0.5 * pixels_per_mm))
                draw.line([a4_end[0], a4_end[1], rotated_corners[2][0], rotated_corners[2][1]], fill=line_color, width=int(0.5 * pixels_per_mm))
                
                if color_mode == "red":
                    box_color = "#FF6666"
                    outline_color = "#CC0000"
                else:
                    box_color = "#6666FF"
                    outline_color = "#0000CC"
                draw.polygon(rotated_corners, fill=box_color, outline=outline_color, width=int(0.5 * pixels_per_mm))
                
                # 文字
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", int(0.6 * pixels_per_mm))
                except:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                draw.text((mid_x - text_width/2, mid_y - text_height/2), text, fill=(0, 0, 0, 255), font=font)
        
        # 绘制点（最后绘制，在最上层）
        for i in range(self.rows):
            for j in range(self.cols):
                x, y = to_a4_coords(i, j)
                draw.ellipse(
                    [x - point_radius_px, y - point_radius_px,
                     x + point_radius_px, y + point_radius_px],
                    fill=(0, 0, 0, 255)
                )
        
        # 保存图片（转换为RGB格式）
        rgb_image = image.convert("RGB")
        rgb_image.save(filename)
        messagebox.showinfo("成功", f"A4图片已保存到: {filename}\n(分辨率: {DPI}DPI, 孔间距: {HOLE_SPACING_MM}mm)")
    
    def save_archive(self):
        """保存存档功能，保存当前绘图状态到 JSON 文件"""
        from datetime import datetime
        default_filename = datetime.now().strftime("%Y%m%d%H%M")
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_filename,
            initialdir=self.save_path,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        def pos_to_rowcol(pos):
            x, y = pos
            col = int(round((x - self.grid_size) / self.grid_size))
            row = int(round((y - self.grid_size) / self.grid_size))
            return (row, col)
        
        def rowcol_to_pos(row, col):
            x = col * self.grid_size + self.grid_size
            y = row * self.grid_size + self.grid_size
            return (x, y)
        
        # 转换数据为行列索引格式
        lines_data = []
        for start, end, color_mode, selected in self.lines:
            start_idx = pos_to_rowcol(start)
            end_idx = pos_to_rowcol(end)
            lines_data.append([start_idx, end_idx, color_mode, selected])
        
        components_data = []
        for start, end, text, color_mode, selected in self.components:
            start_idx = pos_to_rowcol(start)
            end_idx = pos_to_rowcol(end)
            components_data.append([start_idx, end_idx, text, color_mode, selected])
        
        squares_data = []
        for square_data in self.squares:
            p1, p2, p3, p4, selected = square_data[:5]
            p1_idx = pos_to_rowcol(p1)
            p2_idx = pos_to_rowcol(p2)
            p3_idx = pos_to_rowcol(p3)
            p4_idx = pos_to_rowcol(p4)
            squares_data.append([p1_idx, p2_idx, p3_idx, p4_idx, selected])
        
        data = {
            "rows": self.rows,
            "cols": self.cols,
            "grid_size": self.grid_size,
            "point_radius": self.point_radius,
            "line_color_mode": self.line_color_mode,
            "lines": lines_data,
            "components": components_data,
            "squares": squares_data,
            "zoom_scale": self.zoom_scale,
            "pan_offset_x": self.pan_offset_x,
            "pan_offset_y": self.pan_offset_y,
            "label_distance": self.label_distance
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            # 更新当前存档文件路径
            self.current_archive_file = filename
            messagebox.showinfo("成功", f"存档已保存到: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存存档失败: {str(e)}")
    
    def auto_save_archive(self):
        """自动保存功能,保存当前绘图状态到当前打开的存档文件"""
        # 如果没有打开的存档文件,则不保存
        if not self.current_archive_file:
            return
        
        def pos_to_rowcol(pos):
            x, y = pos
            col = int(round((x - self.grid_size) / self.grid_size))
            row = int(round((y - self.grid_size) / self.grid_size))
            return (row, col)
        
        def rowcol_to_pos(row, col):
            x = col * self.grid_size + self.grid_size
            y = row * self.grid_size + self.grid_size
            return (x, y)
        
        # 转换数据为行列索引格式
        lines_data = []
        for start, end, color_mode, selected in self.lines:
            start_idx = pos_to_rowcol(start)
            end_idx = pos_to_rowcol(end)
            lines_data.append([start_idx, end_idx, color_mode, selected])
        
        components_data = []
        for start, end, text, color_mode, selected in self.components:
            start_idx = pos_to_rowcol(start)
            end_idx = pos_to_rowcol(end)
            components_data.append([start_idx, end_idx, text, color_mode, selected])
        
        squares_data = []
        for square_data in self.squares:
            p1, p2, p3, p4, selected = square_data[:5]
            p1_idx = pos_to_rowcol(p1)
            p2_idx = pos_to_rowcol(p2)
            p3_idx = pos_to_rowcol(p3)
            p4_idx = pos_to_rowcol(p4)
            squares_data.append([p1_idx, p2_idx, p3_idx, p4_idx, selected])
        
        data = {
            "rows": self.rows,
            "cols": self.cols,
            "grid_size": self.grid_size,
            "point_radius": self.point_radius,
            "line_color_mode": self.line_color_mode,
            "lines": lines_data,
            "components": components_data,
            "squares": squares_data,
            "zoom_scale": self.zoom_scale,
            "pan_offset_x": self.pan_offset_x,
            "pan_offset_y": self.pan_offset_y,
            "label_distance": self.label_distance
        }
        
        try:
            with open(self.current_archive_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # 静默失败,不打扰用户
            print(f"自动保存失败: {str(e)}")
    
    def load_archive(self):
        """加载存档功能，从 JSON 文件恢复绘图状态"""
        filename = filedialog.askopenfilename(
            initialdir=self.save_path,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复数据
            self.rows = data.get("rows", 8)
            self.cols = data.get("cols", 8)
            self.grid_size = data.get("grid_size", 50)
            self.point_radius = data.get("point_radius", 5)
            self.line_color_mode = data.get("line_color_mode", "red")
            self.label_distance = data.get("label_distance", 20)
            
            def rowcol_to_pos(row, col):
                x = col * self.grid_size + self.grid_size
                y = row * self.grid_size + self.grid_size
                return (x, y)
            
            # 转换行列索引为像素坐标
            raw_lines = data.get("lines", [])
            self.lines = []
            for item in raw_lines:
                start_idx, end_idx = item[0], item[1]
                self.lines.append([rowcol_to_pos(*start_idx), rowcol_to_pos(*end_idx), item[2], item[3]])
            
            raw_components = data.get("components", [])
            self.components = []
            for item in raw_components:
                start_idx, end_idx = item[0], item[1]
                self.components.append([rowcol_to_pos(*start_idx), rowcol_to_pos(*end_idx), item[2], item[3], item[4]])
            
            raw_squares = data.get("squares", [])
            self.squares = []
            for item in raw_squares:
                p1_idx, p2_idx, p3_idx, p4_idx = item[0], item[1], item[2], item[3]
                self.squares.append([rowcol_to_pos(*p1_idx), rowcol_to_pos(*p2_idx), rowcol_to_pos(*p3_idx), rowcol_to_pos(*p4_idx), item[4]])
            
            self.zoom_scale = data.get("zoom_scale", 1.0)
            self.pan_offset_x = data.get("pan_offset_x", 0)
            self.pan_offset_y = data.get("pan_offset_y", 0)
            
            # 更新界面显示
            self.rows_entry.delete(0, tk.END)
            self.rows_entry.insert(0, str(self.rows))
            self.cols_entry.delete(0, tk.END)
            self.cols_entry.insert(0, str(self.cols))
            
            # 更新颜色模式显示
            if self.line_color_mode == "red":
                self.color_label.config(text="当前颜色: 红色", fg="red")
            else:
                self.color_label.config(text="当前颜色: 蓝色", fg="blue")
            
            # 重置状态
            self.first_point = None
            self.square_points = []
            self.selected_item = None
            self.draw_mode = "line"  # 重置绘制模式为默认的连线模式
            self.update_mode_label()  # 更新模式显示标签
            
            # 重新绘制
            self.draw_board()
            
            # 设置当前存档文件路径,用于自动保存
            self.current_archive_file = filename
            
            messagebox.showinfo("成功", f"存档已加载: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"加载存档失败: {str(e)}")

if __name__ == "__main__":
    set_taskbar_icon()
    root = tk.Tk()
    app = PegboardDrawingApp(root)
    root.mainloop()