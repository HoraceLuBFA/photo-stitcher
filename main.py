import tkinter as tk # 导入 Tkinter 库，用于创建图形用户界面 (GUI)
from tkinter import ttk # 导入 ttk 模块，用于更现代的组件（如下拉菜单）
from tkinter import filedialog, messagebox, Listbox, END, ANCHOR # 从 Tkinter 模块导入文件对话框、消息框、列表框等组件
from PIL import Image, ImageTk # 从 Pillow (PIL) 库导入图像处理相关的 Image 和 ImageTk 模块
import os # 导入 os 模块，用于和操作系统交互，例如处理文件路径
import tkinterdnd2 # 导入 tkinterdnd2 库，用于实现拖放功能
import re # 导入 re 模块，用于正则表达式解析拖放的路径字符串
import sys # 新增：导入 sys 模块，用于检测操作系统平台

class PhotoStitcherApp: # 定义主应用程序类
    def __init__(self, master): # 类的初始化方法，master 参数是 Tkinter 的根窗口 (现在是 tkinterdnd2.Tk() 实例)
        self.master = master # 保存根窗口的引用到实例变量 self.master
        master.title("图片拼接工具") # 设置应用程序主窗口的标题文字
        master.geometry("800x750") # 设置应用程序主窗口的初始尺寸为 800像素宽 x 750像素高

        self.image_paths = [] # 初始化一个空列表，用于按顺序存储所有导入图片的绝对文件路径
        self.image_objects = {} # 初始化一个空字典，用于缓存Tkinter的PhotoImage对象，防止它们因垃圾回收而导致图片在GUI中消失
        self.rotations = {} # 初始化一个空字典，用于存储每张图片的旋转角度，键为图片路径，值为角度 (0, 90, 180, 270)
        self.image_original_dimensions = {} # 新增：用于缓存图片原始宽高的字典 (键:图片路径, 值:(宽度, 高度)元组)
        self._preview_debounce_job = None # 新增：用于预览更新防抖功能的Tkinter after()任务ID

        # --- GUI布局框架 (Frames) ---
        # 创建主内容框架，作为列表区和右侧控制区的父容器
        main_content_frame = tk.Frame(master, padx=10, pady=5) # padx, pady 设置框架内容与边框的水平和垂直间距
        main_content_frame.pack(fill=tk.BOTH, expand=True) # pack布局：fill=tk.BOTH使其水平垂直填充，expand=True使其随父窗口调整大小

        # 创建左侧的列表区框架，用于容纳图片文件列表框和其滚动条
        list_frame = tk.Frame(main_content_frame) # 将列表区框架放置在主内容框架内
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # pack布局：放置在父框架左侧，水平垂直填充，并随父框架扩展

        # 创建右侧的控制区框架，用于容纳操作按钮和图片预览区
        controls_frame = tk.Frame(main_content_frame) # 将控制区框架放置在主内容框架内
        controls_frame.config(width=300)  # 设置此框架的固定宽度为300像素，以保持右侧控制面板的宽度一致性
        controls_frame.pack_propagate(False)  # 禁止此框架的大小随其内部子组件的大小变化而自动调整，以维持其固定宽度
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10) # pack布局：放置在父框架右侧，垂直填充，并设置10像素的右外边距

        # 创建顶部框架，用于放置"导入图片"按钮和状态信息标签
        top_frame = tk.Frame(master, padx=10, pady=10) # 创建框架，并设置其内容的水平和垂直内边距
        top_frame.pack(fill=tk.X, side=tk.TOP) # pack布局：放置在主窗口顶部，并水平填充整个宽度

        # 创建底部框架，用于放置"拼接图片"按钮以及输出宽度、JPEG质量等设置项
        bottom_frame = tk.Frame(master, padx=10, pady=10) # 创建框架，并设置其内容的水平和垂直内边距
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM) # pack布局：放置在主窗口底部，并水平填充整个宽度


        # --- 顶部框架中的组件 (Top Frame Widgets) ---
        self.import_button = tk.Button(top_frame, text="导入图片", command=self.import_images_dialog) # 创建"导入图片"按钮，点击时执行 self.import_images_dialog 方法
        self.import_button.pack(side=tk.LEFT, padx=(0,10)) # pack布局：放置在顶部框架左侧，并设置10像素的右外边距

        self.status_label = tk.Label(top_frame, text="请导入图片或拖拽图片到此窗口...", anchor="w") # 创建状态标签，用于显示操作提示或结果，文本左对齐 (anchor="w" West)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True) # pack布局：放置在导入按钮右侧，水平填充并扩展以占据顶部框架的剩余空间

        # --- 列表区框架中的组件 (List Frame Widgets) ---
        self.image_listbox = Listbox(list_frame, selectmode=tk.EXTENDED, width=50) # 创建列表框，selectmode=tk.EXTENDED表示支持扩展选择（多选），width设置其字符宽度
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # pack布局：放置在列表区框架左侧，水平垂直填充并扩展
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.image_listbox.yview) # 创建垂直滚动条，其命令与列表框的yview方法关联，实现滚动
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y) # pack布局：放置在列表区框架右侧（即列表框旁边），并垂直填充
        self.image_listbox.config(yscrollcommand=scrollbar.set) # 反向关联：将列表框的滚动行为通知给滚动条，使滚动条滑块能同步移动

        # --- 控制按钮框架中的组件 (Controls Frame Widgets) ---
        self.up_button = tk.Button(controls_frame, text="上移", command=self.move_up) # 创建"上移"按钮，点击时执行 self.move_up 方法
        self.up_button.pack(fill=tk.X, pady=2) # pack布局：按钮水平填充其父框架（控制区）的宽度，上下各有2像素外边距

        self.down_button = tk.Button(controls_frame, text="下移", command=self.move_down) # 创建"下移"按钮，点击时执行 self.move_down 方法
        self.down_button.pack(fill=tk.X, pady=2) # pack布局：按钮水平填充，上下各有2像素外边距
        
        self.delete_button = tk.Button(controls_frame, text="删除", command=self.delete_selected) # 创建"删除"按钮，点击时执行 self.delete_selected 方法
        self.delete_button.pack(fill=tk.X, pady=2) # pack布局：按钮水平填充，上下各有2像素外边距

        self.left_rotate_button = tk.Button(controls_frame, text="左转90°", command=self.rotate_left) # 创建"左转90°"按钮，点击时执行 self.rotate_left 方法
        self.left_rotate_button.pack(fill=tk.X, pady=2) # pack布局：按钮水平填充，上下各有2像素外边距

        self.right_rotate_button = tk.Button(controls_frame, text="右转90°", command=self.rotate_right) # 创建"右转90°"按钮，点击时执行 self.rotate_right 方法
        self.right_rotate_button.pack(fill=tk.X, pady=2) # pack布局：按钮水平填充，上下各有2像素外边距

        self.preview_label = tk.Label(controls_frame, text="图片预览", relief=tk.SUNKEN, anchor=tk.CENTER) # 创建图片预览区标签，relief=tk.SUNKEN使其有凹陷边框效果，anchor=tk.CENTER使文本（如果图片未显示时）居中
        self.preview_label.pack(fill=tk.BOTH, expand=True, pady=10) # pack布局：预览区水平垂直填充并扩展，上下各有10像素外边距
        self.image_listbox.bind("<<ListboxSelect>>", self.show_preview) # 绑定列表框的选中项改变事件 (<<ListboxSelect>>) 到 self.show_preview 方法
        self.preview_label.bind("<Configure>", self._on_preview_configure) # 绑定预览标签的尺寸配置改变事件 (<Configure>) 到 self._on_preview_configure 方法，用于预览图的动态缩放防抖处理
        # 新增：为列表框绑定键盘上下箭头键事件，以控制高亮项的移动
        self.image_listbox.bind("<Up>", self._handle_key_up_arrow) # 绑定向上箭头键事件到 _handle_key_up_arrow 方法
        self.image_listbox.bind("<Down>", self._handle_key_down_arrow) # 绑定向下箭头键事件到 _handle_key_down_arrow 方法
        
        # 根据操作系统平台确定使用 Command 还是 Control 键作为修饰键
        if sys.platform == "darwin":  # "darwin" 表示 macOS 系统
            control_modifier_key = "Command"  # 在 macOS 上使用 Command 键
        else:  # 其他操作系统 (如 Windows, Linux)
            control_modifier_key = "Control"  # 在其他系统上使用 Control 键

        # 为列表框绑定键盘 <Mod-Up/Down> 事件 (Mod 为 Command 或 Control)，用于依次多选
        self.image_listbox.bind(f"<{control_modifier_key}-Up>", self._handle_control_key_up_arrow) # 绑定 <Mod-Up> 到对应处理方法
        self.image_listbox.bind(f"<{control_modifier_key}-Down>", self._handle_control_key_down_arrow) # 绑定 <Mod-Down> 到对应处理方法


        # --- 底部框架中的组件 (Bottom Frame Widgets) ---
        # 使用Grid布局管理器来更灵活地排列底部框架内的组件
        bottom_frame.columnconfigure(1, weight=1) # 配置Grid的第1列（索引从0开始）的列权重为1，使其在水平空间分配上优先获得额外空间（可扩展）
        bottom_frame.columnconfigure(3, weight=1) # 配置Grid的第3列的列权重为1，使其也可水平扩展

        # "输出宽度"相关组件的创建和布局
        tk.Label(bottom_frame, text="输出宽度:").grid(row=0, column=0, sticky="w", padx=(0,5)) # 创建"输出宽度:"文本标签，放置在grid的(0,0)，左对齐(sticky="w" West)，右外边距5像素
        self.output_width_var = tk.StringVar(value="1080") # 创建Tkinter字符串变量，用于存储和控制输出宽度输入框的值，默认"1080"
        self.output_width_var.trace_add("write", self._update_expected_height_display) # 当此变量的值被写入（修改）时，自动调用 self._update_expected_height_display 方法
        self.output_width_entry = tk.Entry(bottom_frame, textvariable=self.output_width_var, width=10) # 创建文本输入框，将其文本内容与 self.output_width_var 关联，设置字符宽度为10
        self.output_width_entry.grid(row=0, column=1, sticky="we", padx=(0,10)) # 输入框放置在grid的(0,1)，水平方向填充(sticky="we" West-East)，右外边距10像素
        tk.Label(bottom_frame, text="像素").grid(row=0, column=2, sticky="w", padx=(0,20)) # 创建"像素"文本标签，放置在grid的(0,2)，左对齐，右外边距20像素

        # "预计总高"相关组件的创建和布局
        tk.Label(bottom_frame, text="预计总高:").grid(row=0, column=3, sticky="e", padx=(10,5)) # 创建"预计总高:"文本标签，放置在grid的(0,3)，右对齐(sticky="e" East)，左外边距10，右外边距5像素
        self.expected_height_var = tk.StringVar(value="0 像素") # 创建Tkinter字符串变量，用于显示计算出的预计总高度，默认"0 像素"
        tk.Label(bottom_frame, textvariable=self.expected_height_var, anchor="w").grid(row=0, column=4, sticky="we") # 创建用于显示预计高度的标签，其文本内容与 self.expected_height_var 关联，文本左对齐，水平填充

        # "JPEG质量"相关组件的创建和布局
        tk.Label(bottom_frame, text="JPEG质量:").grid(row=1, column=0, sticky="w", pady=(5,0), padx=(0,5)) # 创建"JPEG质量:"文本标签，放置在grid的(1,0)，左对齐，顶部外边距5，右外边距5像素
        self.jpeg_quality_var = tk.IntVar(value=95) # 创建Tkinter整数变量，用于存储JPEG压缩质量，默认95
        self.jpeg_quality_scale = tk.Scale(bottom_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.jpeg_quality_var, command=self._update_quality_display_label) # 创建滑块(Scale)控件，范围0-100，水平方向(orient=tk.HORIZONTAL)，其值与 self.jpeg_quality_var 关联，值改变时调用 self._update_quality_display_label
        self.jpeg_quality_scale.grid(row=1, column=1, columnspan=2, sticky="we", pady=(5,0), padx=(0,10)) # 滑块放置在grid的(1,1)，水平跨2列(columnspan=2)，水平填充，顶部外边距5，右外边距10像素
        self.quality_display_label_var = tk.StringVar(value="95%") # 创建Tkinter字符串变量，用于显示当前选择的JPEG质量百分比
        tk.Label(bottom_frame, textvariable=self.quality_display_label_var).grid(row=1, column=3, columnspan=2, sticky="w", pady=(5,0)) # 创建显示质量百分比的标签，其文本与 self.quality_display_label_var 关联，放置在grid的(1,3)，跨2列，左对齐，顶部外边距5
        
        # "输出格式"选择组件的创建和布局
        tk.Label(bottom_frame, text="输出格式:").grid(row=2, column=0, sticky="w", pady=(5,0), padx=(0,5)) # 创建"输出格式:"文本标签，放置在grid的(2,0)，左对齐，顶部外边距5，右外边距5像素
        self.output_format_var = tk.StringVar(value="JPEG") # 创建Tkinter字符串变量，用于存储选择的输出文件格式，默认"JPEG"
        self.output_format_menu = ttk.Combobox(bottom_frame, textvariable=self.output_format_var, values=["JPEG", "PNG"], state="readonly", width=7) # 创建下拉组合框(Combobox)，其值与 self.output_format_var 关联，可选值为"JPEG"和"PNG"，状态为只读(state="readonly")，字符宽度7
        self.output_format_menu.grid(row=2, column=1, sticky="w", pady=(5,0), padx=(0,10)) # 组合框放置在grid的(2,1)，左对齐，顶部外边距5，右外边距10像素
        self.output_format_menu.bind("<<ComboboxSelected>>", self._output_format_changed) # 绑定组合框的选中项改变事件 (<<ComboboxSelected>>) 到 self._output_format_changed 方法


        # "拼接图片并保存"按钮的创建和布局
        self.combine_button = tk.Button(bottom_frame, text="拼接图片并保存", command=self.combine_and_save_images) # 创建按钮，点击时执行 self.combine_and_save_images 方法
        self.combine_button.grid(row=0, column=5, rowspan=3, sticky="nsew", padx=(20,0), pady=(0,0)) # 按钮放置在grid的(0,5)，垂直跨3行(rowspan=3)，四面填充(sticky="nsew" North-South-East-West)，左外边距20像素


        # --- 注册拖放功能 ---
        self.master.drop_target_register(tkinterdnd2.DND_FILES) # 向tkinterdnd2注册主窗口为可接受文件拖放的目标
        self.master.dnd_bind('<<Drop>>', self.handle_drop) # 当有文件被拖放到主窗口上时，调用 self.handle_drop 方法进行处理
        
        # --- 初始化UI相关的显示状态 ---
        self._update_expected_height_display() # 在程序启动时，调用一次以根据当前（默认）设置计算并显示预计的总高度
        self._update_quality_display_label(self.jpeg_quality_var.get()) # 根据IntVar中JPEG质量的初始值，更新并显示对应的百分比标签
        self._output_format_changed() # 根据StringVar中输出格式的初始值，设置JPEG质量滑块的初始状态（例如，如果默认为PNG，则禁用滑块）

    def _output_format_changed(self, event=None): # 当输出格式下拉菜单的选择发生变化时调用的回调方法 (event参数由事件绑定自动传入)
        if not hasattr(self, 'output_format_var') or not hasattr(self, 'jpeg_quality_scale') or not hasattr(self, 'quality_display_label_var'): # 安全检查，确保相关UI组件已初始化，避免在程序启动或销毁不完全时出错
            return # 如果尚未完全初始化，则提前返回，不执行后续操作

        selected_format = self.output_format_var.get() # 获取当前在下拉菜单中选中的输出格式字符串 (例如 "JPEG" 或 "PNG")
        is_png = (selected_format == "PNG") # 判断选中的格式是否为 PNG，结果为布尔值
        
        # 根据选择的格式是否为PNG，来启用或禁用JPEG质量设置滑块
        self.jpeg_quality_scale.config(state=tk.DISABLED if is_png else tk.NORMAL) # 如果is_png为True (选择了PNG)，则设置滑块状态为禁用(tk.DISABLED)；否则，设置为正常(tk.NORMAL)
        
        if is_png: # 如果用户选择了PNG格式
            # 检查当前质量显示标签的内容，只有当它显示的是百分比时（表明之前是JPEG状态），才将其更改为 "N/A"
            if "%" in self.quality_display_label_var.get(): # 检查标签文本中是否包含百分号 '%'
                 self.quality_display_label_var.set("N/A") # 将标签文本设置为 "N/A" (Not Applicable)，因为PNG是无损压缩，质量设置无意义
        else: # 如果用户选择的不是PNG (例如，又切换回了JPEG)
            # 调用 _update_quality_display_label 方法来恢复显示JPEG质量的百分比
            # 该方法会从 self.jpeg_quality_var (滑块关联的变量) 获取当前的质量值并更新标签
            self._update_quality_display_label() 

    def _update_quality_display_label(self, value=None): # 更新JPEG质量百分比显示标签内容的方法 (value参数通常由滑块的command回调自动传入当前值)
        if not hasattr(self, 'jpeg_quality_var') or not hasattr(self, 'quality_display_label_var'): return # 安全检查，确保相关的Tkinter变量已初始化，避免出错
        if value is None: value = self.jpeg_quality_var.get() # 如果此方法被调用时没有传入value参数（例如，在_output_format_changed中被间接调用），则从jpeg_quality_var获取当前滑块的整数值
        self.quality_display_label_var.set(f"{int(float(value))}%") # 将获取到的值（可能是浮点数，先转float再转int取整）格式化为带百分号的字符串，并更新到对应的StringVar，从而改变标签显示

    def _calculate_expected_output_height(self): # 计算并返回所有当前列表中的图片在指定输出宽度下拼接后的预计总高度（像素）
        total_h = 0 # 初始化累计总高度为0
        # 安全检查：确保相关的实例变量（输出宽度变量、图片路径列表、原始尺寸缓存字典）都已存在，防止在程序初始化未完成时调用此方法出错
        if not hasattr(self, 'output_width_var') or not hasattr(self, 'image_paths') or not hasattr(self, 'image_original_dimensions'):
            return 0 # 如果某些必要组件或数据未就绪，则直接返回0

        try:
            target_w_str = self.output_width_var.get() # 从StringVar获取当前设定的输出宽度字符串
            if not target_w_str: return 0 # 如果宽度字符串为空，则无法计算，返回0
            target_w = int(target_w_str) # 将宽度字符串转换为整数
            if target_w <= 0 or not self.image_paths: return 0 # 如果目标宽度无效（非正数）或当前没有导入任何图片，则总高度为0，返回0
        except (ValueError, tk.TclError): return 0 # 捕获可能的字符串转整数错误(ValueError)或Tkinter变量访问错误(TclError)，并返回0

        for img_path in self.image_paths: # 遍历当前 self.image_paths 列表中的每一张图片路径
            try:
                # 尝试从缓存字典 self.image_original_dimensions 中获取图片的原始宽度和高度
                if img_path not in self.image_original_dimensions:
                    # 如果缓存未命中（例如，此图片是旧版程序添加的，或之前缓存失败，或被外部修改）
                    # 则尝试从磁盘加载一次图片以获取其实际尺寸，并更新到缓存中，作为一种后备机制
                    temp_img = Image.open(img_path) # 使用Pillow的Image.open()打开图片文件
                    ow, oh = temp_img.size # 获取图片的原始宽度(ow)和高度(oh)
                    self.image_original_dimensions[img_path] = (ow, oh) # 将获取到的尺寸元组存入缓存字典，键为图片路径
                    print(f"Cache miss for {img_path}, loaded dimensions: ({ow}, {oh})") # 在控制台打印一条调试信息，表明发生了缓存未命中及实时加载
                    temp_img.close() # 获取尺寸后立即关闭图片文件，以释放相关资源
                else:
                    # 如果缓存命中，直接从字典中获取之前存储的原始宽度和高度
                    ow, oh = self.image_original_dimensions[img_path]

                rotation = self.rotations.get(img_path, 0) # 从 self.rotations 字典获取当前图片的旋转角度，如果未指定则默认为0（不旋转）
                # 根据旋转角度确定图片在拼接时的有效宽度和高度（因为旋转90/270度会使宽高互换）
                if rotation == 90 or rotation == 270: # 如果图片被旋转了90度或270度
                    effective_w, effective_h = oh, ow # 那么其有效宽度等于原始高度，有效高度等于原始宽度
                else: # 如果图片未旋转或旋转了180度
                    effective_w, effective_h = ow, oh # 其有效宽度和高度保持原始值
                
                if effective_w == 0: continue # 如果计算出的有效宽度为0（异常情况，例如图片本身有问题），则跳过此图片，避免后续发生除零错误
                aspect_ratio = effective_h / effective_w # 计算图片的有效宽高比（高/宽）
                scaled_h = int(target_w * aspect_ratio) # 根据设定的目标拼接宽度(target_w)和该图片的宽高比，计算出图片在拼接时应缩放到的高度
                total_h += scaled_h # 将计算出的单个图片的高度累加到总高度 total_h
            except FileNotFoundError: # 特别捕获文件未找到的异常（例如，图片在添加到列表后被用户从文件系统删除或移动了）
                print(f"Warning: File not found during height calculation: {img_path}") # 在控制台打印警告信息
                # （可选）从 self.image_original_dimensions 缓存中移除此无效图片路径的条目，以避免后续重复尝试
                if img_path in self.image_original_dimensions: # 检查缓存中是否存在该路径的条目
                    del self.image_original_dimensions[img_path] # 如果存在，则从缓存中删除
                # 注意：在遍历列表（如self.image_paths）时直接从中删除元素可能会导致迭代器失效或跳过某些元素，更安全的做法通常是先标记要删除的元素，然后在遍历结束后统一处理。这里仅处理缓存。
                continue # 跳过当前处理出错（文件未找到）的图片，继续处理列表中的下一张图片
            except Exception as e: # 捕获其他所有在处理单个图片（打开、获取尺寸、计算等）时可能发生的预料之外的异常
                print(f"Warning: Could not process image {img_path} for height calculation: {e}") # 在控制台打印包含具体异常信息的警告
                continue # 同样跳过当前出错的图片，继续处理列表中的下一张图片
        return total_h # 遍历完所有图片后，返回计算出的累计总高度

    def _update_expected_height_display(self, *args): # 更新GUI界面上显示的"预计总高"标签的文本内容 (*args 用于接收由StringVar的trace回调自动传入的额外参数，如变量名、索引、操作类型等，尽管在此方法中未使用它们)
        # 安全检查，确保相关的UI组件（如输出宽度输入框关联的变量、预计高度显示标签关联的变量）和数据（图片路径列表）都已初始化完成，避免在程序启动初期或销毁不完全时调用此方法导致错误
        if not hasattr(self, 'output_width_var') or not hasattr(self, 'expected_height_var') or not hasattr(self, 'image_paths'):
            return # 如果任何必要的组件或数据尚未准备好，则直接返回，不执行后续更新操作

        if not self.image_paths: # 检查当前图片列表是否为空
             self.expected_height_var.set("0 像素") # 如果没有图片，则将预计总高标签的文本直接设置为 "0 像素"
             return # 并结束此方法的执行

        try:
            # 对输出宽度输入框中的内容进行验证，确保其为有效的正整数
            width_str = self.output_width_var.get() # 从关联的StringVar获取当前输出宽度的字符串值
            if not width_str: # 如果获取到的字符串为空（例如，用户清空了输入框）
                self.expected_height_var.set("--- 像素") # 在预计总高标签上显示一个占位符或提示信息，表明宽度输入不完整
                return # 并结束此方法的执行
            if not width_str.isdigit() or int(width_str) <= 0: # 如果字符串内容不是纯数字，或者转换后的数字小于等于0
                self.expected_height_var.set("宽度无效") # 在预计总高标签上显示"宽度无效"的提示信息
                return # 并结束此方法的执行
        except tk.TclError: # 捕获在访问Tkinter变量（如StringVar）时，如果其底层Tcl对象已被销毁（例如在窗口关闭过程中）可能发生的TclError
             return # 发生此类错误时，直接返回，不尝试更新UI，以避免程序崩溃
        except ValueError: # 捕获在尝试将width_str转换为整数时，如果字符串内容无法有效转换为数字（例如包含非数字字符）可能发生的ValueError
            self.expected_height_var.set("宽度无效") # 同样在预计总高标签上显示"宽度无效"
            return # 并结束此方法的执行

        height = self._calculate_expected_output_height() # 调用内部的 _calculate_expected_output_height 方法来获取实际计算出的预计总高度值
        self.expected_height_var.set(f"{height} 像素") # 将计算得到的整数高度值格式化为一个包含" 像素"单位的字符串，并更新到预计总高显示标签关联的StringVar中，从而刷新GUI显示
    
    def _process_new_image_paths(self, file_paths_to_add): # 定义处理一批新添加的（通过文件对话框或拖放）图片文件路径的内部核心方法
        if not file_paths_to_add: return # 如果传入的待添加文件路径列表为空，则直接返回，不执行任何操作
        newly_added = 0 # 初始化一个计数器，用于记录在本次调用中实际新添加到程序列表中的图片数量（用于后续判断是否需要更新UI等）
        for fp_orig in file_paths_to_add: # 遍历传入的每一个原始文件路径字符串
            if self._is_image_file(fp_orig): # 调用辅助方法 _is_image_file 检查该路径是否指向一个被支持的图片文件格式（基于后缀名）
                abs_fp = os.path.abspath(os.path.expanduser(fp_orig)) # 将文件路径转换为绝对路径，并使用 os.path.expanduser 来处理可能存在的用户目录符号（如 '~'）                 
                if abs_fp not in self.image_paths: # 检查转换后的绝对路径是否已经存在于 self.image_paths 列表中，以防止重复添加同一张图片
                    self.image_paths.append(abs_fp) # 如果是新的、不重复的图片路径，则将其添加到实例变量 self.image_paths 列表中进行管理
                    self.image_listbox.insert(END, os.path.basename(abs_fp)); newly_added += 1 # 在GUI的列表框（self.image_listbox）的末尾（END）插入该图片的文件名部分（通过os.path.basename获取），同时将 newly_added 计数器加1
                    # 优化：在图片首次添加到列表时，立即打开它一次以获取并缓存其原始尺寸，这有助于后续在计算预计总高度时避免重复打开文件，从而提高性能
                    try:
                        img = Image.open(abs_fp) # 使用Pillow库的Image.open()方法尝试打开该图片文件
                        self.image_original_dimensions[abs_fp] = img.size # 将图片的原始（宽度, 高度）尺寸元组存储到 self.image_original_dimensions 缓存字典中，键为图片的绝对路径
                        img.close() # 获取尺寸信息后，立即调用img.close()关闭图片文件，以释放文件句柄和相关内存资源，因为此时我们只需要尺寸数据
                    except Exception as e: # 捕获在尝试打开图片、获取尺寸或关闭图片过程中可能发生的任何预料之外的异常
                        print(f"Error opening {abs_fp} to cache dimensions: {e}") # 在控制台打印包含具体图片路径和异常信息的错误提示
                        # 即使在这里缓存原始尺寸失败（例如图片文件损坏或无法访问），也允许程序继续将该图片路径添加到列表中。后续在计算预计总高度时，如果缓存未命中，会再次尝试加载或按错误处理逻辑跳过此图片。
                        pass # 使用pass语句忽略此处的异常，确保程序流程继续
                                    
        if newly_added > 0: # 检查在遍历完所有待添加路径后，是否有至少一张新的、不重复的图片被成功添加到了列表中
            self.status_label.config(text=f"已导入 {len(self.image_paths)} 张图片。") # 如果有新图片添加，则更新主界面顶部的状态标签，显示当前列表中图片的总数量
            last_idx = self.image_listbox.size() - 1 # 获取当前列表框中最后一项的索引（由于新图片是插入到末尾的，所以最后一项即为最新添加的项之一）
            self.image_listbox.selection_clear(0, END); self.image_listbox.selection_set(last_idx) # 首先清除列表框中任何之前的选中状态，然后将最新添加的项（由last_idx指定）设置为新的选中项
            self.image_listbox.activate(last_idx); self.image_listbox.see(last_idx); self.show_preview() # 将最新添加的项设置为"活动"项（通常用于键盘导航），并调用 self.image_listbox.see(last_idx) 来确保该项在列表框的可见区域内（如果列表过长，则会滚动到该项），最后调用 self.show_preview() 来更新右侧的图片预览区域以显示新选中的图片
        elif not self.image_paths: # 如果在处理完所有待添加路径后，newly_added为0（没有新图片被添加），并且 self.image_paths 列表本身也为空（意味着之前就没有图片，或者所有尝试添加的都是无效或重复的）
            self.status_label.config(text="未导入有效图片。请拖拽PNG, JPG, JPEG图片到此窗口。") # 则更新状态标签，提示用户程序当前没有有效图片，并指引如何操作
        self._update_expected_height_display() # 无论本次操作是否实际添加了新图片，都调用一次 self._update_expected_height_display() 方法，以确保界面上显示的"预计总高"信息能根据当前图片列表和设置（如输出宽度）得到及时更新

    def move_up(self): # 定义当用户点击"上移"按钮时调用的方法，用于将列表框中当前选中的图片向上移动一个位置
        sel = self.image_listbox.curselection(); idx = sel[0] if sel else -1 # 获取当前列表框中选中项的索引。如果sel为空（无选中），则idx为-1；否则，idx为选中项的索引（因为是单选，所以取第一个）
        if idx > 0: # 检查选中项的索引是否大于0（即选中的不是第一项，第一项不能再上移）
            txt=self.image_listbox.get(idx); self.image_listbox.delete(idx); self.image_listbox.insert(idx-1, txt) # 获取选中项的文本（文件名），从列表框中删除该项，然后在原位置的上一位（idx-1）插入该文本
            self.image_listbox.selection_set(idx-1); self.image_listbox.activate(idx-1) # 将新位置的项（原选中项的上一个位置）设置为选中状态和活动状态
            p = self.image_paths.pop(idx); self.image_paths.insert(idx-1, p) # 在内部数据列表 self.image_paths 中同步移动图片路径：先移除原索引处的路径，再将其插入到新索引（idx-1）处
            self.show_preview() # 更新右侧的图片预览，以显示当前新选中的图片（如果上移操作导致选中项改变）
            self._update_expected_height_display() # 调用方法更新预计总高度的显示，因为图片顺序变化可能影响总高度（如果未来支持不同图片有不同缩放策略）或者只是保持UI一致性

    def move_down(self): # 定义当用户点击"下移"按钮时调用的方法，用于将列表框中当前选中的图片向下移动一个位置
        sel = self.image_listbox.curselection(); idx = sel[0] if sel else -1 # 获取当前列表框中选中项的索引，处理方式同 move_up
        if idx != -1 and idx < self.image_listbox.size()-1: # 检查是否有选中项（idx != -1），并且选中的不是最后一项（最后一项不能再下移）
            txt=self.image_listbox.get(idx); self.image_listbox.delete(idx); self.image_listbox.insert(idx+1, txt) # 获取选中项的文本，从列表框中删除，然后在原位置的下一位（idx+1）插入
            self.image_listbox.selection_set(idx+1); self.image_listbox.activate(idx+1) # 将新位置的项（原选中项的下一个位置）设置为选中状态和活动状态
            p = self.image_paths.pop(idx); self.image_paths.insert(idx+1, p) # 在内部数据列表 self.image_paths 中同步移动图片路径
            self.show_preview() # 更新图片预览
            self._update_expected_height_display() # 调用方法更新预计总高度的显示
            
    def delete_selected(self): # 定义当用户点击"删除"按钮时调用的方法，用于删除列表框中当前选中的图片及其关联数据
        selected_indices = self.image_listbox.curselection() # 获取当前列表框中所有选中项的索引元组
        if not selected_indices: # 如果没有选中任何图片
            messagebox.showwarning("无选择", "请选择要删除的图片。"); return # 显示警告消息框并直接返回
        
        # 将选中的索引按降序排序，这样从后往前删除时不会影响前面未处理项的索引
        sorted_indices_to_delete = sorted(selected_indices, reverse=True)
        
        min_deleted_idx = selected_indices[0] # 记录被删除项中最小的原始索引，用于后续重新定位选择

        for idx in sorted_indices_to_delete: # 遍历排序后的索引列表
            if 0 <= idx < len(self.image_paths): # 再次确认索引有效性，防止意外
                removed_path = self.image_paths.pop(idx) # 从 self.image_paths 列表中移除对应索引处的图片路径，并保存被移除的路径
                self.image_listbox.delete(idx) # 从GUI的列表框中删除对应索引处的项
                
                # 清理与已删除图片相关的缓存数据
                if removed_path in self.image_objects: del self.image_objects[removed_path] # 如果该图片路径在 PhotoImage 对象缓存中，则删除它
                if removed_path in self.rotations: del self.rotations[removed_path] # 如果该图片路径在旋转角度缓存中，则删除它
                if removed_path in self.image_original_dimensions: # 如果该图片路径在原始尺寸缓存中
                    del self.image_original_dimensions[removed_path] # 则从原始尺寸缓存中删除它
            else:
                print(f"Warning: Invalid index {idx} during deletion. List size: {self.image_listbox.size()}, Paths size: {len(self.image_paths)}")

        self.status_label.config(text=f"已导入 {len(self.image_paths)} 张图片。") # 更新状态标签，显示当前剩余的图片总数
        
        if not self.image_listbox.size(): # 如果列表框中已没有任何项目（即图片列表已清空）
            self.preview_label.config(image=None, text="图片预览"); self.preview_label.image=None # 清除图片预览区的图像和文本，恢复到初始"图片预览"状态
            if not self.image_paths: self.status_label.config(text="请导入图片或拖拽图片到此窗口...") # 如果内部图片路径列表也为空，则更新状态标签为初始提示信息
        else: # 如果列表框中还有其他项目
            # 尝试选择一个合适的项目作为删除后的新选中项
            # 优先选择原被删除项区域的起始位置（如果那里现在有新项目）
            new_selection_idx = min(min_deleted_idx, self.image_listbox.size() - 1)
            if new_selection_idx >= 0 : # 确保索引有效
                self.image_listbox.selection_set(new_selection_idx) # 设置选中项
                self.image_listbox.activate(new_selection_idx)    # 设置活动项
                self.image_listbox.see(new_selection_idx)         # 滚动到该项
            self.show_preview() # 更新图片预览以显示新选中的图片（如果有）
            
        self._update_expected_height_display() # 调用方法更新预计总高度的显示

    def rotate_image(self, direction): # 定义核心的图片旋转逻辑，被 rotate_left 和 rotate_right 方法调用
        selected_indices = self.image_listbox.curselection() # 获取当前列表框中所有选中项的索引元组
        if not selected_indices: # 如果没有选中任何图片
            messagebox.showwarning("无选择", "请选择要旋转的图片。"); return # 显示警告消息框并直接返回

        rotated_count = 0 # 记录成功旋转的图片数量
        for idx in selected_indices: # 遍历所有选中的索引
            if 0 <= idx < len(self.image_paths): # 检查索引的有效性
                img_path = self.image_paths[idx] # 获取选中图片的路径
                current_rot = self.rotations.get(img_path,0) # 从 self.rotations 字典获取其当前的旋转角度（默认为0）
                # 根据传入的 direction 参数（"left" 或 "right"）计算新的旋转角度
                # Pillow的rotate方法中，正角度表示逆时针旋转。所以"左转"是+90度，"右转"是-90度。
                # 使用模运算 (% 360) 确保角度值始终在 0 到 270 度之间 (0, 90, 180, 270)。
                new_rot = (current_rot + (90 if direction == "left" else -90) + 360) % 360
                self.rotations[img_path] = new_rot # 将计算出的新旋转角度更新到 self.rotations 字典中
                rotated_count +=1 # 增加旋转计数
            else:
                print(f"Warning: Invalid index {idx} during rotation. List size: {self.image_listbox.size()}, Paths size: {len(self.image_paths)}")

        if rotated_count > 0: # 如果至少有一张图片被旋转了
            self.show_preview() # 调用 self.show_preview() 来刷新预览以显示活动项（可能已旋转）的效果
            self._update_expected_height_display() # 图片旋转可能导致其有效宽高变化，从而影响预计总高度，因此需要更新显示

    def rotate_left(self): self.rotate_image("left") # 当用户点击"左转90°"按钮时调用的方法，它简单地调用核心旋转方法 rotate_image 并指定方向为"left"

    def rotate_right(self): # 定义当用户点击"右转90°"按钮时调用的方法
        self.rotate_image("right") # 调用核心旋转方法 rotate_image 并指定方向为"right"

    def combine_and_save_images(self): # 定义当用户点击"拼接图片并保存"按钮时执行的方法
        if not self.image_paths: # 检查当前是否有已导入的图片路径列表
            messagebox.showerror("错误", "没有图片可以拼接。"); # 如果没有图片，则显示错误消息框
            return # 并提前结束方法执行
        
        try: # 开始一个try-except块，用于验证输出宽度的有效性
            target_w_str = self.output_width_var.get() # 从StringVar获取用户在输入框中设定的目标输出宽度字符串
            if not target_w_str: # 检查获取到的字符串是否为空（例如，用户删除了输入框中的内容）
                messagebox.showerror("宽度无效", "输出宽度不能为空。"); return # 如果为空，显示错误消息并返回
            target_w = int(target_w_str) # 尝试将宽度字符串转换为整数
            if target_w <= 0: # 检查转换后的整数宽度是否为正数
                messagebox.showerror("宽度无效", "输出宽度必须是正整数。"); return # 如果宽度非正，显示错误消息并返回
        except ValueError: # 如果在尝试将字符串转换为整数时发生ValueError（例如，输入了非数字字符）
            messagebox.showerror("宽度无效", "输出宽度必须是有效的正整数。"); return # 显示统一的宽度无效错误消息并返回
        
        out_fmt=self.output_format_var.get() # 获取用户选择的输出文件格式（"JPEG" 或 "PNG"）
        jpg_q=self.jpeg_quality_var.get() # 获取用户设定的JPEG图片质量（0-100）
        self.status_label.config(text="处理中..."); self.master.update_idletasks() # 更新状态栏提示为"处理中..."，并强制UI刷新以立即显示此消息
        
        proc_imgs=[]; total_h=0 # 初始化一个空列表 proc_imgs 用于存放处理后的Pillow Image对象，初始化 total_h 为0用于累计拼接后图片的总高度
        for i_path in self.image_paths: # 遍历已导入的每一张图片路径
            try:
                img=Image.open(i_path).convert("RGB") # 打开图片文件，并将其转换为RGB格式（确保颜色通道一致性，JPEG不支持alpha通道）
                rot=self.rotations.get(i_path,0); # 获取该图片的旋转角度（默认为0）
                if rot: img=img.rotate(rot,expand=True,fillcolor=(255,255,255)) # 如果有旋转角度，则应用旋转。expand=True确保旋转后内容不丢失，fillcolor用白色填充可能产生的空白区域
                ow,oh=img.size # 获取（可能已旋转的）图片的原始宽度和高度
                if not ow or not oh: # 检查图片是否有有效的非零宽度和高度
                    print(f"Skipping image with zero dimension: {i_path}") # 如果宽度或高度为0，则打印跳过信息
                    continue # 跳过此无效图片，继续处理下一张
                # 再次确认原始宽度 ow 不为零，以避免后续计算 aspect_ratio 时发生除零错误
                if ow == 0: 
                    print(f"Skipping image with zero width: {i_path}") # 如果宽度为0，打印跳过信息
                    continue # 跳过此图片
                aspect_ratio = oh / ow # 计算图片的宽高比（高/宽）
                nh=int(target_w * aspect_ratio) # 根据目标输出宽度和图片的宽高比，计算该图片在拼接时应缩放到的新高度
                # 确保计算出的新高度至少为1像素，以避免Pillow的resize方法因高度为0而出错
                nh = max(1, nh)
                resized=img.resize((target_w,nh),Image.Resampling.LANCZOS) # 使用LANCZOS高质量重采样滤波器将图片缩放到目标宽度和计算出的新高度
                proc_imgs.append(resized); total_h+=nh # 将处理（缩放）后的Image对象添加到 proc_imgs 列表中，并将其高度累加到 total_h
            except FileNotFoundError: # 如果在尝试打开图片时发现文件不存在（例如，在添加到列表后被用户删除或移动了）
                messagebox.showwarning("文件丢失", f"图片 {os.path.basename(i_path)} 未找到，已跳过。") # 显示警告消息框，提示用户哪个文件未找到并已被跳过
                print(f"File not found during combining: {i_path}") # 在控制台也打印此信息，便于调试
                continue # 跳过当前文件，继续处理列表中的下一张图片
            except Exception as e: # 捕获在处理单张图片过程中可能发生的其他所有预料之外的异常（如图片损坏、Pillow处理错误等）
                messagebox.showerror("图片处理错误", f"处理 {os.path.basename(i_path)} 错: {e}") # 显示错误消息框，指出哪张图片处理出错以及具体的错误信息
                self.status_label.config(text="处理失败。") # 更新状态栏提示为"处理失败。"
                return # 中断整个拼接过程，不再处理后续图片
        
        if not proc_imgs: # 如果在遍历完所有图片路径后，proc_imgs 列表仍然为空（意味着没有一张图片被成功处理）
            self.status_label.config(text="无成功处理图片。注意：可能所有图片都无法打开或尺寸无效。"); # 更新状态栏提示，告知用户没有图片被成功处理，并给出可能的原因
            return # 提前结束方法执行
        
        # 创建一张新的空白Pillow Image对象作为最终拼接的底图
        # 宽度为target_w，高度为之前累计的total_h，背景色为白色(255,255,255)
        comb_img=Image.new('RGB',(target_w,total_h),(255,255,255)); cy=0 # 初始化当前粘贴位置的垂直偏移量cy为0
        for img in proc_imgs: # 遍历所有已成功处理并缩放的Image对象
            comb_img.paste(img,(0,cy)); cy+=img.height # 将当前图片粘贴到底图 comb_img 上，水平位置为0，垂直位置为cy。然后将cy增加刚粘贴图片的高度，为下一张图片做准备。
        
        self.status_label.config(text="选择保存路径..."); self.master.update_idletasks() # 更新状态栏，提示用户选择保存路径，并强制UI刷新
        def_ext = (".jpg" if out_fmt=="JPEG" else ".png") # 根据用户选择的输出格式确定默认的文件扩展名
        f_types = [(f"{out_fmt} files", f"*.{out_fmt.lower()}"), ("All files", "*.*")] # 定义文件类型过滤器，用于文件保存对话框
        s_path = filedialog.asksaveasfilename( # 弹出文件保存对话框，让用户选择保存位置和文件名
            initialdir=os.path.expanduser("~/Desktop"), # 设置对话框的初始目录为用户桌面
            defaultextension=def_ext, # 设置默认的文件扩展名
            filetypes=f_types, # 应用上面定义的文件类型过滤器
            title=f"保存为 {out_fmt}" # 设置对话框的标题
        )
        if s_path: # 如果用户在对话框中选择了路径并点击了"保存"（s_path不为空）
            try:
                if out_fmt=="JPEG": comb_img.save(s_path,"JPEG",quality=jpg_q) # 如果输出格式为JPEG，则使用指定的质量保存
                else: comb_img.save(s_path,"PNG",optimize=True) # 如果输出格式为PNG，则启用优化选项进行保存
                messagebox.showinfo("成功", f"已保存到: {s_path}") # 显示成功保存的消息框
                self.status_label.config(text=f"已保存: {os.path.basename(s_path)}") # 更新状态栏，显示已保存的文件名
            except Exception as e: # 如果在保存文件过程中发生任何异常
                messagebox.showerror("保存错误", f"保存出错: {e}") # 显示保存错误的消息框，并包含具体的错误信息
                self.status_label.config(text="保存失败。") # 更新状态栏为"保存失败。"
        else: # 如果用户在文件保存对话框中点击了"取消"（s_path为空）
            self.status_label.config(text="保存已取消。") # 更新状态栏为"保存已取消。"

    def _is_image_file(self, filepath): # 定义一个辅助方法，用于检查给定的文件路径是否指向一个支持的图片文件格式
        if not isinstance(filepath, str): # 首先确保传入的 filepath 参数确实是一个字符串类型
            return False # 如果不是字符串，则无法判断，直接返回False
        return filepath.lower().endswith(('.png', '.jpg', '.jpeg')) # 将文件路径转换为小写，然后检查其是否以 '.png', '.jpg', 或 '.jpeg' 中的任何一个后缀结尾。如果是，则返回True，否则返回False。

    def import_images_dialog(self): # 定义当用户点击"导入图片"按钮时执行的方法，用于通过文件对话框选择并导入图片
        file_types = [("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")] # 定义文件类型过滤器，用于文件选择对话框，优先显示支持的图片格式
        # 调用Tkinter的文件对话框 askopenfilenames，允许用户选择一个或多个文件。
        # title设置对话框标题，filetypes应用上面的过滤器，initialdir设置初始打开的目录为用户的主目录（例如 /Users/username 或 C:\Users\username）
        files = filedialog.askopenfilenames(title="选择图片", filetypes=file_types, initialdir=os.path.expanduser("~"))
        if files: self._process_new_image_paths(list(files)) # 如果用户选择了文件（files不为空，它是一个包含所选文件路径的元组），则将其转换为列表，并调用内部方法 _process_new_image_paths 来处理这些新选择的图片路径
        # _process_new_image_paths 方法内部会负责将图片添加到列表、更新UI、缓存尺寸以及调用 _update_expected_height_display

    def handle_drop(self, event): # 定义处理从外部拖放文件到程序窗口时的事件回调方法 (event 参数由 tkinterdnd2 库在发生拖放事件时自动传入)
        data_string = event.data.strip() # 从事件对象 event 中获取拖放的数据（通常是文件路径字符串列表），并移除首尾的空白字符
        paths_candidates = [] # 初始化一个空列表，用于存放初步解析出的可能的文件路径候选

        # 根据拖放数据字符串的格式，尝试解析出单个或多个文件路径
        # 不同的操作系统或拖放源可能以不同方式格式化路径列表（例如，空格分隔，或用花括号包裹带空格的路径）
        if '{' not in data_string and '}' not in data_string and '\n' not in data_string: # 如果字符串中不包含花括号和换行符，则尝试按空格分割，这适用于多个无空格路径或单个路径被空格包围的情况
            paths_candidates = data_string.split(' ') # 使用空格作为分隔符将字符串分割成路径候选列表
        else: # 如果字符串中可能包含花括号（用于包裹带空格的路径）或换行符（某些系统可能用换行分隔多路径）
            # 使用正则表达式 re.findall 来查找两种模式：
            # 1. `{[^{}]+}`: 匹配由花括号包裹的、内部不含花括号的任何字符序列（这能正确处理带空格的文件名被花括号包围的情况）
            # 2. `[^{\s}]+`: 匹配任何不包含花括号或空白字符的连续字符序列（这能处理不带花括号的、无空格的文件名）
            paths_candidates = re.findall(r'{[^{}]+}|[^{\s}]+', data_string)
        
        paths_candidates = [p for p in paths_candidates if p] # 列表推导式：从 paths_candidates 中移除所有空字符串（例如，多个空格分隔可能产生空字符串）

        processed_paths = [] # 初始化一个空列表，用于存放最终经过验证和处理后的有效图片文件绝对路径
        for p_str in paths_candidates: # 遍历每一个初步解析出的路径候选字符串
            path = p_str.strip() # 移除候选路径字符串首尾的空白字符
            if path.startswith('{') and path.endswith('}'): # 如果路径以花括号开头并以花括号结尾
                path = path[1:-1] # 则移除首尾的花括号，得到内部的实际路径字符串
            path = path.strip('\'"') # 进一步移除路径字符串首尾可能存在的单引号或双引号（某些拖放源可能会添加）
            
            try: # 尝试将清理后的路径字符串转换为绝对路径，并处理用户目录符号
                abs_path = os.path.abspath(os.path.expanduser(path))
            except Exception: # 如果在路径转换过程中发生任何异常（例如路径格式非法）
                abs_path = path # 则退回使用原始清理后的路径字符串作为候选绝对路径（这可能仍然无效，但后续os.path.exists会检查）
            
            # 检查处理后的路径是否存在于文件系统中，并且是否是一个支持的图片文件
            if os.path.exists(abs_path) and self._is_image_file(abs_path): 
                processed_paths.append(abs_path) # 如果路径有效且是图片文件，则将其添加到 processed_paths 列表中
        
        if processed_paths: # 如果在所有候选路径处理完毕后，processed_paths 列表中有至少一个有效的图片路径
            self._process_new_image_paths(processed_paths) # 则调用内部方法 _process_new_image_paths 来处理这些新拖入的图片
        else: # 如果没有找到任何有效的图片路径（例如，用户拖入的是非图片文件、文件夹或无效路径）
            self.status_label.config(text="未拖入有效图片。请拖拽PNG, JPG, JPEG图片。") # 更新状态栏，提示用户未拖入有效图片，并指引支持的格式
            
    def show_preview(self, event=None): # 定义显示图片预览的方法, event参数在由事件绑定（如列表选择、窗口配置改变）调用时会自动传入，直接调用时可忽略
        # 如果此方法是由 _on_preview_configure 中的 after() 延迟调用的，则清除之前设置的计时器ID，防止重复执行或内存泄漏
        self._preview_debounce_job = None 

        lb = self.image_listbox # 获取列表框实例的引用
        active_idx = -1 # 初始化活动项索引为-1 (无效)
        try:
            active_idx = lb.index(tk.ACTIVE) # 尝试获取当前活动项（有键盘焦点的项）的索引
        except tk.TclError: # 如果没有活动项（例如列表为空，或刚失去焦点），tk.ACTIVE会引发TclError
            # 即使curselection()有内容，如果没有tk.ACTIVE项（例如，窗口失焦后焦点丢失），也可能需要回退
            current_selection = lb.curselection() # 获取当前所有选中项的索引元组
            if current_selection: # 如果有选中项
                active_idx = current_selection[-1] # 将活动索引设置为最后一个选中的项目（作为一种备选逻辑）
            else: # 如果既没有活动项也没有选中项
                self.preview_label.config(image=None, text="图片预览") # 清除预览区图像和文本
                self.preview_label.image = None # 清除对PhotoImage对象的引用
                return # 提前结束方法

        if not (0 <= active_idx < len(self.image_paths)): # 验证计算出的active_idx是否在self.image_paths的有效范围内
            # 这种情况可能在列表内容与image_paths不同步时发生，或者active_idx计算逻辑有误
            actual_size = lb.size() # 获取列表框中实际的项目数量
            paths_size = len(self.image_paths) # 获取内部图片路径列表的长度
            # print(f"Debug: active_idx {active_idx} out of bounds. Listbox size: {actual_size}, image_paths size: {paths_size}")

            if actual_size == 0 or paths_size == 0 : # 如果列表框或内部路径列表为空
                 self.preview_label.config(image=None, text="图片预览")
                 self.preview_label.image = None
                 return

            # 尝试使用列表框的最后一个选中项（如果存在）作为后备
            current_selection = lb.curselection()
            if current_selection:
                active_idx = current_selection[-1] # 使用最后一个选中项的索引
                if not (0 <= active_idx < paths_size): # 再次检查此后备索引的有效性
                    self.preview_label.config(image=None, text="索引无效")
                    self.preview_label.image = None
                    return
            else: # 如果没有选中项，并且之前的active_idx无效
                 self.preview_label.config(image=None, text="无有效项")
                 self.preview_label.image = None
                 return


        image_path = self.image_paths[active_idx] # 根据最终确定的有效索引，从 self.image_paths 列表中找到对应的图片文件绝对路径

        try: # 开始一个异常处理块，用于捕获在打开图片、处理图片或更新UI时可能发生的任何错误，以防止程序崩溃
            img = Image.open(image_path) # 使用Pillow库的Image.open()方法打开指定路径的图片文件，返回一个Image对象

            rotation_angle = self.rotations.get(image_path, 0) # 从 self.rotations 字典中获取该图片的旋转角度，如果路径不在字典中（即未被旋转过），则默认为0度
            if rotation_angle != 0: # 如果图片的旋转角度不是0（即需要进行旋转操作）
                img = img.rotate(rotation_angle, expand=True) # 使用Pillow的rotate方法旋转图片。expand=True确保旋转后的图像能完整显示，可能会改变图像尺寸以容纳所有像素。

            img_w, img_h = img.size # 获取旋转后（如果进行了旋转）图片的宽度(img_w)和高度(img_h)

            if img_w == 0 or img_h == 0: # 检查图片的宽度或高度是否为0（可能是由于图片文件损坏、无效旋转或其他Pillow处理问题导致）
                raise ValueError("图片宽度或高度为0") # 如果是，则主动抛出一个ValueError异常，以便在后续的except块中统一处理显示错误信息

            self.preview_label.update_idletasks() # 强制Tkinter处理所有挂起的空闲任务，包括UI更新和尺寸计算，以确保接下来获取的预览标签尺寸是最新的实际尺寸
            container_w = self.preview_label.winfo_width() # 获取预览标签（self.preview_label）当前的实际渲染宽度（以像素为单位）
            container_h = self.preview_label.winfo_height() # 获取预览标签当前的实际渲染高度（以像素为单位）

            # 检查获取到的预览标签容器尺寸是否过小（例如，当窗口正在被用户快速调整大小或尚未完全绘制完成时，尺寸可能暂时很小）
            if container_w < 10 or container_h < 10: # 设置一个较小的阈值（例如10像素）来判断尺寸是否有效
                # 如果尺寸过小，可以选择在预览标签上显示一个提示文本，如"调整中..."，但为了避免在快速拖动时文本闪烁，这里选择直接返回，暂时不更新预览图像。
                # self.preview_label.config(image=None, text="调整中...") 
                # self.preview_label.image = None
                return # 提前结束方法，等待预览标签尺寸稳定后再进行下一次（通常由Configure事件再次触发）的预览更新
            
            # 直接使用预览标签容器的当前实际尺寸作为图片缩放的目标宽度和高度
            target_w = container_w
            target_h = container_h
            
            scale_w = target_w / img_w # 计算宽度方向上的缩放比例（目标宽度 / 图片原始宽度）
            scale_h = target_h / img_h # 计算高度方向上的缩放比例（目标高度 / 图片原始高度）
            scale = min(scale_w, scale_h) # 取两个缩放比例中较小的一个，以确保图片在缩放后能够完整地显示在目标区域内，并保持原始的宽高比

            if scale <= 0: # 对计算出的缩放比例进行有效性检查（理论上不应发生，除非img_w/h为0或负，或者target_w/h为0或负，但前面已有检查）
                # 如果缩放比例无效，可以选择显示错误提示或简单返回，不更新预览
                # self.preview_label.config(image=None, text="尺寸错误")
                # self.preview_label.image = None
                return # 提前结束方法

            display_w = int(img_w * scale) # 根据选定的最终缩放比例(scale)计算图片在预览区实际显示的宽度
            display_h = int(img_h * scale) # 根据选定的最终缩放比例(scale)计算图片在预览区实际显示的高度
            
            display_w = max(1, display_w) # 确保计算出的显示宽度至少为1像素，以避免Pillow的resize方法传入0或负值导致错误
            display_h = max(1, display_h) # 确保计算出的显示高度至少为1像素
            
            img_resized = img.resize((display_w, display_h), Image.Resampling.LANCZOS) # 使用Pillow的resize方法将（可能已旋转的）图片调整到计算出的display_w和display_h尺寸。Image.Resampling.LANCZOS是一种高质量的图像下采样（缩小）滤波器。
            photo_img = ImageTk.PhotoImage(img_resized) # 将Pillow的Image对象（img_resized）转换为Tkinter兼容的PhotoImage对象，以便在Label组件中显示
            
            self.preview_label.config(image=photo_img, text="") # 更新预览标签（self.preview_label）的配置：设置其image属性为新创建的photo_img对象，并将text属性设置为空字符串（以清除任何之前的文本提示）
            self.preview_label.image = photo_img # 关键步骤：将PhotoImage对象的引用也保存在self.preview_label.image（或任何其他不会被垃圾回收的长效变量）中，以防止Tkinter因Python的垃圾回收机制过早回收该对象而导致图片不显示
            self.image_objects[image_path] = photo_img # 同时，也将此PhotoImage对象存储在 self.image_objects 字典中（以图片路径为键），作为另一层保险或用于其他可能的缓存目的
        except Exception as e: # 捕获在try块中（图片打开、处理、UI更新等）可能发生的任何类型的异常
            # 当显示预览发生错误时，尝试在预览标签上显示错误信息，但要避免错误信息不断叠加刷新
            current_text = self.preview_label.cget("text") # 获取预览标签当前显示的文本内容
            if "无法预览" not in current_text : # 只有当当前文本中不包含"无法预览"时（表明不是连续的同类错误刷新），才更新错误信息
                 try:
                     self.preview_label.config(image=None, text=f"无法预览:\n{e}") # 清除预览标签的图像，并将其文本设置为包含具体错误信息的提示
                     self.preview_label.image = None # 清除对可能存在的旧PhotoImage对象的引用
                 except tk.TclError: # 捕获在尝试config预览标签时，如果其底层Tcl组件已销毁（例如窗口正在关闭）可能发生的错误
                     pass # 如果组件已销毁，则忽略错误，不做任何操作
            print(f"Error showing preview for {image_path} (event: {event}): {e}") # 在控制台打印详细的错误信息，包括图片路径、触发事件（如果有）和异常本身，便于调试

    def _handle_key_up_arrow(self, event): # 当在列表框中按下向上箭头键时调用的方法 (event参数由Tkinter自动传入)
        lb = self.image_listbox # 获取列表框实例的引用，方便后续使用
        is_shifted = (event.state & 0x0001) != 0 # 检查Shift键是否被按下 (0x0001是Shift的掩码)

        if is_shifted:
            # 如果Shift键被按下，则不执行自定义逻辑，也不返回"break"。
            # 这允许Tkinter的默认Listbox行为来处理Shift+Up的范围选择。
            # <<ListboxSelect>>事件应该会被Tkinter的默认处理触发，
            # 从而调用self.show_preview来更新预览。
            # self.master.after_idle(self.show_preview) # 可选：如果<<ListboxSelect>>不够可靠，可稍后强制更新
            return

        # --- 以下是非Shift情况下的自定义逻辑 ---
        current_selection = lb.curselection() # 获取当前列表框中选中项的索引元组 (例如 (2,) 表示第3项被选中)
        current_active = -1 # 初始化当前活动项索引
        try:
            current_active = lb.index(tk.ACTIVE) # 获取当前活动项的索引
        except tk.TclError: # 如果没有活动项
            if current_selection: # 但有选中项
                current_active = current_selection[0] # 将活动项视为第一个选中项

        new_index = -1 # 初始化目标新索引

        if current_active == -1 : # 如果列表框中没有活动项 (通常也意味着没有选中项)
            if lb.size() > 0: # 检查列表框中是否有任何项目
                new_index = lb.size() - 1 # 如果没有活动/选中项时按上箭头，则将选择定位到列表的最后一项
        elif current_active > 0: # 如果当前活动项不是列表中的第一项 (索引大于0)
            new_index = current_active - 1 # 计算上一项的索引
        else: # 活动项已经是第一项 (current_active == 0)
            new_index = 0 # 保持在第一项

        if new_index != -1: # 如果计算出了有效的新索引
            lb.selection_clear(0, END) # 首先清除列表框中可能存在的任何旧的选择状态
            lb.selection_set(new_index) # 将计算出的新索引位置的项设置为选中状态
            lb.activate(new_index)      # 将该项设置为活动项 (通常是键盘焦点所在的项)
            lb.see(new_index)           # 滚动列表框，以确保新选中的项在可见区域内
            self.show_preview() # 显式调用show_preview以确保在键盘导航后更新预览 (针对非Shift情况)
        
        return "break" # 返回 "break" 告诉Tkinter此事件已被完全处理，阻止Listbox控件执行其默认的向上箭头键行为 (对于非Shift情况)

    def _handle_key_down_arrow(self, event): # 当在列表框中按下向下箭头键时调用的方法 (event参数由Tkinter自动传入)
        lb = self.image_listbox # 获取列表框实例的引用
        is_shifted = (event.state & 0x0001) != 0 # 检查Shift键是否被按下

        if is_shifted:
            # 如果Shift键被按下，允许Tkinter的默认Listbox行为处理Shift+Down。
            # self.master.after_idle(self.show_preview) # 可选的强制更新
            return

        # --- 以下是非Shift情况下的自定义逻辑 ---
        current_selection = lb.curselection() # 获取当前选中项的索引元组
        current_active = -1
        try:
            current_active = lb.index(tk.ACTIVE)
        except tk.TclError:
            if current_selection:
                current_active = current_selection[0]
        
        new_index = -1

        if current_active == -1 : # 如果没有活动/选中项
            if lb.size() > 0: # 检查列表框中是否有项目
                new_index = 0 # 如果没有活动/选中项时按向下箭头，则将选择定位到列表的第一项
        elif current_active < lb.size() - 1: # 如果当前活动项不是列表中的最后一项
            new_index = current_active + 1 # 计算下一项的索引
        else: # 活动项已经是最后一项
            new_index = lb.size() - 1 # 保持在最后一项
        
        if new_index != -1:
            lb.selection_clear(0, END) # 清除旧选择
            lb.selection_set(new_index) # 设置新选择 (单选逻辑)
            lb.activate(new_index)      # 激活新选择
            lb.see(new_index)           # 滚动到新选择
            self.show_preview() # 显式调用show_preview以确保在键盘导航后更新预览 (针对非Shift情况)

        return "break" # 返回 "break" 阻止默认行为 (对于非Shift情况)

    def _handle_control_key_up_arrow(self, event): # 处理 Ctrl/Cmd + 向上箭头键事件
        lb = self.image_listbox # 获取列表框实例
        if lb.size() == 0: return "break" # 如果列表为空，则不执行任何操作并阻止默认行为

        current_active_idx = -1 # 初始化当前活动项的索引为-1（表示没有活动项）
        try:
            current_active_idx = lb.index(tk.ACTIVE) # 尝试获取当前活动项的索引
        except tk.TclError: # 如果没有活动项（例如，列表框刚获得焦点或之前没有活动项）
            current_active_idx = lb.size() # 将索引视为列表末尾（下一个向上将是最后一项）

        new_active_idx = -1 # 初始化新的目标活动项索引
        if current_active_idx > 0: # 如果当前活动项不是第一项
            new_active_idx = current_active_idx - 1 # 则新活动项是上一项
        elif current_active_idx <= 0 : # 如果当前活动项是第一项，或者是由于上述except块中设置为size()的情况（向上就是最后一项）
             new_active_idx = lb.size() - 1 if current_active_idx == lb.size() else 0 # 处理循环或停在顶部的逻辑
             if current_active_idx == 0 and lb.index(tk.ACTIVE) == 0: #如果已经是第一个且激活了，就保持不变
                 new_active_idx = 0
             elif lb.size() > 0 : # 确保有项目
                 new_active_idx = lb.size() -1 # 若从无到有按上，则激活最后一个
             else: # 列表为空的情况，虽然前面检查过，但以防万一
                 return "break"
        
        if new_active_idx == -1 and lb.size() > 0: # 后备：如果上面的逻辑未能确定new_active_idx，且列表不空，则选择最后一个
            new_active_idx = lb.size() -1
        elif new_active_idx == -1 : # 如果还是-1（例如列表为空导致的），则返回
            return "break"


        lb.activate(new_active_idx) # 将计算出的新索引位置的项设置为活动项（焦点框移动）
        
        # 切换新活动项的选中状态
        if lb.selection_includes(new_active_idx): # 检查新活动项当前是否已被选中
            lb.selection_clear(new_active_idx) # 如果已选中，则取消选中
        else:
            lb.selection_set(new_active_idx) # 如果未选中，则将其选中
            
        lb.see(new_active_idx) # 滚动列表框以确保新的活动项在可见区域内
        self.show_preview() # 更新预览区域以显示新的活动项的图片
        return "break" # 返回 "break" 以阻止Tkinter的默认事件处理

    def _handle_control_key_down_arrow(self, event): # 处理 Ctrl/Cmd + 向下箭头键事件
        lb = self.image_listbox # 获取列表框实例
        if lb.size() == 0: return "break" # 如果列表为空，则不执行任何操作并阻止默认行为

        current_active_idx = -1 # 初始化当前活动项的索引
        try:
            current_active_idx = lb.index(tk.ACTIVE) # 尝试获取当前活动项的索引
        except tk.TclError: # 如果没有活动项
           current_active_idx = -1 # 保持-1，下面会处理成第一项

        new_active_idx = -1 # 初始化新的目标活动项索引
        if current_active_idx == -1 : # 如果之前没有活动项 (例如，列表框刚获得焦点)
            new_active_idx = 0 # 则新的活动项将是列表的第一项
        elif current_active_idx < lb.size() - 1: # 如果当前活动项不是列表的最后一项
            new_active_idx = current_active_idx + 1 # 则新活动项是下一项
        elif current_active_idx == lb.size() -1: # 如果当前活动项已经是最后一项
            new_active_idx = lb.size() -1 # 保持在最后一项（不循环）
        else: # 列表为空或其他意外情况
            return "break"

        lb.activate(new_active_idx) # 设置新的活动项
        
        # 切换新活动项的选中状态
        if lb.selection_includes(new_active_idx): # 检查新活动项是否已选中
            lb.selection_clear(new_active_idx) # 如果已选中，则取消选中
        else:
            lb.selection_set(new_active_idx) # 如果未选中，则将其选中
            
        lb.see(new_active_idx) # 确保新活动项可见
        self.show_preview() # 更新预览
        return "break" # 阻止默认事件处理

    # --- 新增：用于处理预览标签<Configure>事件的防抖(debounce)方法 ---
    def _on_preview_configure(self, event=None): # 当预览标签的尺寸被配置（改变）时，由<Configure>事件绑定调用此方法
        if self._preview_debounce_job: # 检查实例变量 _preview_debounce_job 是否已存在一个计时器ID（表明之前已有一次尺寸改变事件触发了计时，但尚未执行）
            self.master.after_cancel(self._preview_debounce_job) # 如果存在，则取消之前设置的延迟任务，以防止旧的、可能已过时的更新请求被执行
        # 设置一个新的延迟任务：在250毫秒（0.25秒）后，使用lambda函数调用 self.show_preview(event) 方法。
        # 这种延迟执行的机制称为"防抖"，它可以确保只有当用户停止调整窗口/控件尺寸一小段时间后，预览更新逻辑才会实际执行一次，
        # 从而避免了在用户快速连续拖动调整大小时，show_preview被极其频繁地调用，导致大量不必要的计算和UI闪烁，提高程序响应性和性能。
        self._preview_debounce_job = self.master.after(250, lambda: self.show_preview(event)) # 将after()方法返回的计时器ID保存到 self._preview_debounce_job，以便后续可以取消它


if __name__ == '__main__': # Python 脚本的标准入口点检查：仅当此脚本被直接执行（而不是作为模块导入到其他脚本中）时，以下代码块才会运行
    root = tkinterdnd2.Tk()  # 创建一个 tkinterdnd2.Tk() 实例作为应用程序的根窗口。使用 tkinterdnd2.Tk() 而不是标准的 tk.Tk() 是为了启用窗口的拖放(Drag and Drop)功能。
    app = PhotoStitcherApp(root) # 创建 PhotoStitcherApp 应用程序类的实例，将上面创建的根窗口 root作为参数传递给构造函数。
    # 为几个在 __init__ 中创建的、值会动态改变的UI组件（如输出宽度输入框、JPEG质量滑块、输出格式下拉菜单）重新绑定或确认其回调事件。
    # 这样做是为了确保即使在 __init__ 之后实例化 app 对象，这些回调也能正确设置。
    # 使用 hasattr 进行安全检查，以防某些属性在特定条件下未被初始化（尽管在此代码中它们总会被初始化）。
    if hasattr(app, 'output_width_var') and app.output_width_var: # 检查 app 对象是否有 output_width_var 属性并且它不是None
        app.output_width_var.trace_add("write", app._update_expected_height_display) # 当输出宽度变量的值被写入（改变）时，调用 app._update_expected_height_display 方法
    
    if hasattr(app, 'jpeg_quality_scale') and app.jpeg_quality_scale: # 检查 jpeg_quality_scale 属性
        app.jpeg_quality_scale.config(command=app._update_quality_display_label) # 将滑块的值改变事件的命令设置为 app._update_quality_display_label 方法
    
    if hasattr(app, 'output_format_menu') and app.output_format_menu: # 检查 output_format_menu 属性
        app.output_format_menu.bind("<<ComboboxSelected>>", app._output_format_changed) # 当下拉菜单的选中项改变时，调用 app._output_format_changed 方法
    
    # 手动调用一次相关的更新方法，以确保在程序启动时，UI上显示的初始状态（如预计高度、质量标签、滑块状态）是正确的，并且与内部数据一致。
    if hasattr(app, '_update_quality_display_label'): app._update_quality_display_label() # 更新质量百分比标签的初始显示
    if hasattr(app, '_output_format_changed'): app._output_format_changed() # 根据初始输出格式设置JPEG滑块的可用状态
    if hasattr(app, '_update_expected_height_display'): app._update_expected_height_display() # 根据初始设置计算并显示预计总高度
    
    root.mainloop() # 启动Tkinter的主事件循环。这将使窗口保持可见，并开始监听和响应用户的交互事件（如按钮点击、鼠标移动、键盘输入等），直到窗口被关闭。
