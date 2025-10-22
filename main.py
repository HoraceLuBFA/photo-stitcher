import tkinter as tk  # Tkinter GUI toolkit
from tkinter import ttk  # themed widgets
from tkinter import filedialog, messagebox, Listbox, END, ANCHOR  # common Tk helpers
from PIL import Image, ImageTk  # Pillow image utilities
import os  # filesystem helpers
import tkinterdnd2  # drag-and-drop support
import re  # parse DnD payloads
import sys  # platform detection

class PhotoStitcherApp:  # main application class
    def __init__(self, master):  # master is tkinterdnd2.Tk
        self.master = master  # keep root reference
        master.title("图片拼接工具")  # window title
        master.geometry("800x750")  # default window size

        self.image_paths = []  # ordered list of imported image paths
        self.image_objects = {}  # keep PhotoImage references alive
        self.rotations = {}  # rotation per image path
        self.image_original_dimensions = {}  # cache original w/h
        self._preview_debounce_job = None  # debounce job id for preview

        # --- Layout Frames ---
        main_content_frame = tk.Frame(master, padx=10, pady=5)  # list + controls container
        main_content_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(main_content_frame)  # left list
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        controls_frame = tk.Frame(main_content_frame)  # right controls
        controls_frame.config(width=300)
        controls_frame.pack_propagate(False)
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)

        top_frame = tk.Frame(master, padx=10, pady=10)  # import + status
        top_frame.pack(fill=tk.X, side=tk.TOP)

        bottom_frame = tk.Frame(master, padx=10, pady=10)  # output settings + action
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)


        # --- Top Widgets ---
        self.import_button = tk.Button(top_frame, text="导入图片", command=self.import_images_dialog)  # import button
        self.import_button.pack(side=tk.LEFT, padx=(0,10))

        self.status_label = tk.Label(top_frame, text="请导入图片或拖拽图片到此窗口...", anchor="w")  # status label
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- List Widgets ---
        self.image_listbox = Listbox(list_frame, selectmode=tk.EXTENDED, width=50)  # image queue
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.image_listbox.yview)  # list scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_listbox.config(yscrollcommand=scrollbar.set)

        # --- Control Buttons ---
        self.up_button = tk.Button(controls_frame, text="上移", command=self.move_up)
        self.up_button.pack(fill=tk.X, pady=2)

        self.down_button = tk.Button(controls_frame, text="下移", command=self.move_down)
        self.down_button.pack(fill=tk.X, pady=2)
        
        self.delete_button = tk.Button(controls_frame, text="删除", command=self.delete_selected)
        self.delete_button.pack(fill=tk.X, pady=2)

        self.left_rotate_button = tk.Button(controls_frame, text="左转90°", command=self.rotate_left)
        self.left_rotate_button.pack(fill=tk.X, pady=2)

        self.right_rotate_button = tk.Button(controls_frame, text="右转90°", command=self.rotate_right)
        self.right_rotate_button.pack(fill=tk.X, pady=2)

        self.preview_label = tk.Label(controls_frame, text="图片预览", relief=tk.SUNKEN, anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True, pady=10)
        self.image_listbox.bind("<<ListboxSelect>>", self.show_preview)
        self.preview_label.bind("<Configure>", self._on_preview_configure)  # debounce resize
        self.image_listbox.bind("<Up>", self._handle_key_up_arrow)
        self.image_listbox.bind("<Down>", self._handle_key_down_arrow)
        
        # Choose modifier key by platform (Command on macOS, Control elsewhere)
        if sys.platform == "darwin":
            control_modifier_key = "Command"
        else:
            control_modifier_key = "Control"

        # Bind modifier + arrows to adjust multi-selection
        self.image_listbox.bind(f"<{control_modifier_key}-Up>", self._handle_control_key_up_arrow)
        self.image_listbox.bind(f"<{control_modifier_key}-Down>", self._handle_control_key_down_arrow)


        # --- Bottom Widgets ---
        bottom_frame.columnconfigure(1, weight=1)
        bottom_frame.columnconfigure(3, weight=1)

        tk.Label(bottom_frame, text="输出宽度:").grid(row=0, column=0, sticky="w", padx=(0,5))  # output width
        self.output_width_var = tk.StringVar(value="1080")
        self.output_width_var.trace_add("write", self._update_expected_height_display)
        self.output_width_entry = tk.Entry(bottom_frame, textvariable=self.output_width_var, width=10)
        self.output_width_entry.grid(row=0, column=1, sticky="we", padx=(0,10))
        tk.Label(bottom_frame, text="像素").grid(row=0, column=2, sticky="w", padx=(0,20))  # px unit

        tk.Label(bottom_frame, text="预计总高:").grid(row=0, column=3, sticky="e", padx=(10,5))  # expected total height
        self.expected_height_var = tk.StringVar(value="0 像素")
        tk.Label(bottom_frame, textvariable=self.expected_height_var, anchor="w").grid(row=0, column=4, sticky="we")

        tk.Label(bottom_frame, text="JPEG质量:").grid(row=1, column=0, sticky="w", pady=(5,0), padx=(0,5))  # JPEG quality
        self.jpeg_quality_var = tk.IntVar(value=95)
        self.jpeg_quality_scale = tk.Scale(bottom_frame, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.jpeg_quality_var, command=self._update_quality_display_label)
        self.jpeg_quality_scale.grid(row=1, column=1, columnspan=2, sticky="we", pady=(5,0), padx=(0,10))
        self.quality_display_label_var = tk.StringVar(value="95%")
        tk.Label(bottom_frame, textvariable=self.quality_display_label_var).grid(row=1, column=3, columnspan=2, sticky="w", pady=(5,0))
        
        tk.Label(bottom_frame, text="输出格式:").grid(row=2, column=0, sticky="w", pady=(5,0), padx=(0,5))  # output format
        self.output_format_var = tk.StringVar(value="JPEG")
        self.output_format_menu = ttk.Combobox(bottom_frame, textvariable=self.output_format_var, values=["JPEG", "PNG"], state="readonly", width=7)
        self.output_format_menu.grid(row=2, column=1, sticky="w", pady=(5,0), padx=(0,10))
        self.output_format_menu.bind("<<ComboboxSelected>>", self._output_format_changed)


        self.combine_button = tk.Button(bottom_frame, text="拼接图片并保存", command=self.combine_and_save_images)  # stitch & save
        self.combine_button.grid(row=0, column=5, rowspan=3, sticky="nsew", padx=(20,0), pady=(0,0))


        # Drag-and-drop registration
        self.master.drop_target_register(tkinterdnd2.DND_FILES)
        self.master.dnd_bind('<<Drop>>', self.handle_drop)
        
        # --- Initial UI State ---
        self._update_expected_height_display()
        self._update_quality_display_label(self.jpeg_quality_var.get())
        self._output_format_changed()

    def _output_format_changed(self, event=None):  # toggle quality slider based on format
        if not hasattr(self, 'output_format_var') or not hasattr(self, 'jpeg_quality_scale') or not hasattr(self, 'quality_display_label_var'):
            return

        selected_format = self.output_format_var.get()
        is_png = (selected_format == "PNG")
        
        self.jpeg_quality_scale.config(state=tk.DISABLED if is_png else tk.NORMAL)
        
        if is_png:
            if "%" in self.quality_display_label_var.get():
                 self.quality_display_label_var.set("N/A")
        else:
            self._update_quality_display_label() 

    def _update_quality_display_label(self, value=None):  # refresh quality percent label
        if not hasattr(self, 'jpeg_quality_var') or not hasattr(self, 'quality_display_label_var'): return
        if value is None: value = self.jpeg_quality_var.get()
        self.quality_display_label_var.set(f"{int(float(value))}%")

    def _calculate_expected_output_height(self):  # compute expected stitched height
        total_h = 0
        if not hasattr(self, 'output_width_var') or not hasattr(self, 'image_paths') or not hasattr(self, 'image_original_dimensions'):
            return 0

        try:
            target_w_str = self.output_width_var.get()
            if not target_w_str: return 0
            target_w = int(target_w_str)
            if target_w <= 0 or not self.image_paths: return 0
        except (ValueError, tk.TclError): return 0

        for img_path in self.image_paths:
            try:
                if img_path not in self.image_original_dimensions:
                    temp_img = Image.open(img_path)
                    ow, oh = temp_img.size
                    self.image_original_dimensions[img_path] = (ow, oh)
                    print(f"Cache miss for {img_path}, loaded dimensions: ({ow}, {oh})")
                    temp_img.close()
                else:
                    ow, oh = self.image_original_dimensions[img_path]

                rotation = self.rotations.get(img_path, 0)
                if rotation == 90 or rotation == 270:
                    effective_w, effective_h = oh, ow
                else:
                    effective_w, effective_h = ow, oh
                
                if effective_w == 0: continue
                aspect_ratio = effective_h / effective_w
                scaled_h = int(target_w * aspect_ratio)
                total_h += scaled_h
            except FileNotFoundError:
                print(f"Warning: File not found during height calculation: {img_path}")
                if img_path in self.image_original_dimensions:
                    del self.image_original_dimensions[img_path]
                continue
            except Exception as e:
                print(f"Warning: Could not process image {img_path} for height calculation: {e}")
                continue
        return total_h

    def _update_expected_height_display(self, *args):  # update UI label for expected height
        if not hasattr(self, 'output_width_var') or not hasattr(self, 'expected_height_var') or not hasattr(self, 'image_paths'):
            return

        if not self.image_paths:
             self.expected_height_var.set("0 像素")
             return

        try:
            width_str = self.output_width_var.get()
            if not width_str:
                self.expected_height_var.set("--- 像素")
                return
            if not width_str.isdigit() or int(width_str) <= 0:
                self.expected_height_var.set("宽度无效")
                return
        except tk.TclError:
             return
        except ValueError:
            self.expected_height_var.set("宽度无效")
            return

        height = self._calculate_expected_output_height()
        self.expected_height_var.set(f"{height} 像素")
    
    def _process_new_image_paths(self, file_paths_to_add):  # add a batch of new image paths
        if not file_paths_to_add: return
        newly_added = 0
        for fp_orig in file_paths_to_add:
            if self._is_image_file(fp_orig):
                abs_fp = os.path.abspath(os.path.expanduser(fp_orig))                 
                if abs_fp not in self.image_paths:
                    self.image_paths.append(abs_fp)
                    self.image_listbox.insert(END, os.path.basename(abs_fp)); newly_added += 1
                    # prime dimension cache on first add
                    try:
                        img = Image.open(abs_fp)
                        self.image_original_dimensions[abs_fp] = img.size
                        img.close()
                    except Exception as e:
                        print(f"Error opening {abs_fp} to cache dimensions: {e}")
                        pass
                                    
        if newly_added > 0:
            self.status_label.config(text=f"已导入 {len(self.image_paths)} 张图片。")
            last_idx = self.image_listbox.size() - 1
            self.image_listbox.selection_clear(0, END); self.image_listbox.selection_set(last_idx)
            self.image_listbox.activate(last_idx); self.image_listbox.see(last_idx); self.show_preview()
        elif not self.image_paths:
            self.status_label.config(text="未导入有效图片。请拖拽PNG, JPG, JPEG图片到此窗口。")
        self._update_expected_height_display()

    def move_up(self):  # move selected item up
        sel = self.image_listbox.curselection(); idx = sel[0] if sel else -1
        if idx > 0:
            txt=self.image_listbox.get(idx); self.image_listbox.delete(idx); self.image_listbox.insert(idx-1, txt)
            self.image_listbox.selection_set(idx-1); self.image_listbox.activate(idx-1)
            p = self.image_paths.pop(idx); self.image_paths.insert(idx-1, p)
            self.show_preview()
            self._update_expected_height_display()

    def move_down(self):  # move selected item down
        sel = self.image_listbox.curselection(); idx = sel[0] if sel else -1
        if idx != -1 and idx < self.image_listbox.size()-1:
            txt=self.image_listbox.get(idx); self.image_listbox.delete(idx); self.image_listbox.insert(idx+1, txt)
            self.image_listbox.selection_set(idx+1); self.image_listbox.activate(idx+1)
            p = self.image_paths.pop(idx); self.image_paths.insert(idx+1, p)
            self.show_preview()
            self._update_expected_height_display()
            
    def delete_selected(self):  # delete selected items
        selected_indices = self.image_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("无选择", "请选择要删除的图片。"); return
        # delete from end to avoid shifting indices
        sorted_indices_to_delete = sorted(selected_indices, reverse=True)
        min_deleted_idx = selected_indices[0]

        for idx in sorted_indices_to_delete:
            if 0 <= idx < len(self.image_paths):
                removed_path = self.image_paths.pop(idx)
                self.image_listbox.delete(idx)
                if removed_path in self.image_objects: del self.image_objects[removed_path]
                if removed_path in self.rotations: del self.rotations[removed_path]
                if removed_path in self.image_original_dimensions:
                    del self.image_original_dimensions[removed_path]
            else:
                print(f"Warning: Invalid index {idx} during deletion. List size: {self.image_listbox.size()}, Paths size: {len(self.image_paths)}")

        self.status_label.config(text=f"已导入 {len(self.image_paths)} 张图片。")
        
        if not self.image_listbox.size():
            self.preview_label.config(image=None, text="图片预览"); self.preview_label.image=None
            if not self.image_paths: self.status_label.config(text="请导入图片或拖拽图片到此窗口...")
        else:
            new_selection_idx = min(min_deleted_idx, self.image_listbox.size() - 1)
            if new_selection_idx >= 0:
                self.image_listbox.selection_set(new_selection_idx)
                self.image_listbox.activate(new_selection_idx)
                self.image_listbox.see(new_selection_idx)
            self.show_preview()
        
        self._update_expected_height_display()

    def rotate_image(self, direction):  # core rotation logic
        selected_indices = self.image_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("无选择", "请选择要旋转的图片。"); return

        rotated_count = 0
        for idx in selected_indices:
            if 0 <= idx < len(self.image_paths):
                img_path = self.image_paths[idx]
                current_rot = self.rotations.get(img_path,0)
                # left = +90, right = -90 (Pillow uses CCW positive)
                new_rot = (current_rot + (90 if direction == "left" else -90) + 360) % 360
                self.rotations[img_path] = new_rot  # store new rotation
                rotated_count +=1  # count rotated items
            else:
                print(f"Warning: Invalid index {idx} during rotation. List size: {self.image_listbox.size()}, Paths size: {len(self.image_paths)}")

        if rotated_count > 0:
            self.show_preview()  # refresh preview
            self._update_expected_height_display()  # height may change after rotations

    def rotate_left(self): self.rotate_image("left")  # rotate 90° counterclockwise

    def rotate_right(self):  # rotate 90° clockwise
        self.rotate_image("right")

    def combine_and_save_images(self):  # stitch images and save to file
        if not self.image_paths:
            messagebox.showerror("错误", "没有图片可以拼接。");
            return
        
        try:  # validate output width
            target_w_str = self.output_width_var.get()
            if not target_w_str:
                messagebox.showerror("宽度无效", "输出宽度不能为空。"); return
            target_w = int(target_w_str)
            if target_w <= 0:
                messagebox.showerror("宽度无效", "输出宽度必须是正整数。"); return
        except ValueError:
            messagebox.showerror("宽度无效", "输出宽度必须是有效的正整数。"); return
        
        out_fmt=self.output_format_var.get()  # output format
        jpg_q=self.jpeg_quality_var.get()  # JPEG quality
        self.status_label.config(text="处理中..."); self.master.update_idletasks()  # show busy status
        
        proc_imgs=[]; total_h=0  # resized images + running height
        for i_path in self.image_paths:
            try:
                img=Image.open(i_path).convert("RGB")  # normalize mode
                rot=self.rotations.get(i_path,0);  # rotation degrees
                if rot: img=img.rotate(rot,expand=True,fillcolor=(255,255,255))  # rotate if needed
                ow,oh=img.size
                if not ow or not oh:
                    print(f"Skipping image with zero dimension: {i_path}")
                    continue
                if ow == 0: 
                    print(f"Skipping image with zero width: {i_path}")
                    continue
                aspect_ratio = oh / ow
                nh=int(target_w * aspect_ratio)
                nh = max(1, nh)
                resized=img.resize((target_w,nh),Image.Resampling.LANCZOS)  # high-quality resample
                proc_imgs.append(resized); total_h+=nh
            except FileNotFoundError:
                messagebox.showwarning("文件丢失", f"图片 {os.path.basename(i_path)} 未找到，已跳过。")
                print(f"File not found during combining: {i_path}")
                continue
            except Exception as e:
                messagebox.showerror("图片处理错误", f"处理 {os.path.basename(i_path)} 错: {e}")
                self.status_label.config(text="处理失败。")
                return
        
        if not proc_imgs:
            self.status_label.config(text="无成功处理图片。注意：可能所有图片都无法打开或尺寸无效。");
            return
        
        comb_img=Image.new('RGB',(target_w,total_h),(255,255,255)); cy=0  # final canvas
        for img in proc_imgs:
            comb_img.paste(img,(0,cy)); cy+=img.height
        
        self.status_label.config(text="选择保存路径..."); self.master.update_idletasks()  # prompt to save
        def_ext = (".jpg" if out_fmt=="JPEG" else ".png")
        f_types = [(f"{out_fmt} files", f"*.{out_fmt.lower()}"), ("All files", "*.*")]
        s_path = filedialog.asksaveasfilename(
            initialdir=os.path.expanduser("~/Desktop"),
            defaultextension=def_ext,
            filetypes=f_types,
            title=f"保存为 {out_fmt}"
        )
        if s_path:
            try:
                if out_fmt=="JPEG": comb_img.save(s_path,"JPEG",quality=jpg_q)
                else: comb_img.save(s_path,"PNG",optimize=True)
                messagebox.showinfo("成功", f"已保存到: {s_path}")
                self.status_label.config(text=f"已保存: {os.path.basename(s_path)}")
            except Exception as e:
                messagebox.showerror("保存错误", f"保存出错: {e}")
                self.status_label.config(text="保存失败。")
        else:
            self.status_label.config(text="保存已取消。")

    def _is_image_file(self, filepath):  # check supported image suffix
        if not isinstance(filepath, str):
            return False
        return filepath.lower().endswith(('.png', '.jpg', '.jpeg'))

    def import_images_dialog(self):  # open dialog to add images
        file_types = [("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        files = filedialog.askopenfilenames(title="选择图片", filetypes=file_types, initialdir=os.path.expanduser("~"))
        if files: self._process_new_image_paths(list(files))
        # handler will update list, cache dims, refresh UI

    def handle_drop(self, event):  # parse dropped file list and import
        data_string = event.data.strip()
        paths_candidates = []

        # Some platforms use space-separated paths, others wrap in braces or use newlines.
        if '{' not in data_string and '}' not in data_string and '\n' not in data_string:
            paths_candidates = data_string.split(' ')
        else:
            paths_candidates = re.findall(r'{[^{}]+}|[^\s{}]+', data_string)
        
        paths_candidates = [p for p in paths_candidates if p]

        processed_paths = []
        for p_str in paths_candidates:
            path = p_str.strip()
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            path = path.strip('\'"')
            
            try:
                abs_path = os.path.abspath(os.path.expanduser(path))
            except Exception:
                abs_path = path
            
            if os.path.exists(abs_path) and self._is_image_file(abs_path): 
                processed_paths.append(abs_path)
        
        if processed_paths:
            self._process_new_image_paths(processed_paths)
        else:
            self.status_label.config(text="未拖入有效图片。请拖拽PNG, JPG, JPEG图片。")
            
    def show_preview(self, event=None):  # render preview of active/selected image
        # Clear pending debounce job if this is the delayed call.
        self._preview_debounce_job = None 

        lb = self.image_listbox
        active_idx = -1
        try:
            active_idx = lb.index(tk.ACTIVE)
        except tk.TclError:
            current_selection = lb.curselection()
            if current_selection:
                active_idx = current_selection[-1]
            else:
                self.preview_label.config(image=None, text="图片预览")
                self.preview_label.image = None
                return

        if not (0 <= active_idx < len(self.image_paths)):
            actual_size = lb.size()
            paths_size = len(self.image_paths)

            if actual_size == 0 or paths_size == 0 :
                 self.preview_label.config(image=None, text="图片预览")
                 self.preview_label.image = None
                 return

            current_selection = lb.curselection()
            if current_selection:
                active_idx = current_selection[-1]
                if not (0 <= active_idx < paths_size):
                    self.preview_label.config(image=None, text="索引无效")
                    self.preview_label.image = None
                    return
            else:  # no selection and invalid active_idx
                 self.preview_label.config(image=None, text="无有效项")
                 self.preview_label.image = None
                 return

        image_path = self.image_paths[active_idx]  # resolve path for active item

        try:  # open, rotate if needed, and render to preview
            img = Image.open(image_path)

            rotation_angle = self.rotations.get(image_path, 0)
            if rotation_angle != 0:
                img = img.rotate(rotation_angle, expand=True)

            img_w, img_h = img.size

            if img_w == 0 or img_h == 0:
                raise ValueError("图片宽度或高度为0")

            self.preview_label.update_idletasks()
            container_w = self.preview_label.winfo_width()
            container_h = self.preview_label.winfo_height()

            # if container is too small, skip until next configure
            if container_w < 10 or container_h < 10:
                return
            
            # Scale to fit preview container while preserving aspect ratio
            target_w = container_w
            target_h = container_h
            
            scale_w = target_w / img_w
            scale_h = target_h / img_h
            scale = min(scale_w, scale_h)

            if scale <= 0:
                return

            display_w = int(img_w * scale)
            display_h = int(img_h * scale)
            
            display_w = max(1, display_w)
            display_h = max(1, display_h)
            
            img_resized = img.resize((display_w, display_h), Image.Resampling.LANCZOS)
            photo_img = ImageTk.PhotoImage(img_resized)
            
            self.preview_label.config(image=photo_img, text="")
            self.preview_label.image = photo_img  # keep reference to avoid GC
            self.image_objects[image_path] = photo_img
        except Exception as e:
            current_text = self.preview_label.cget("text")
            if "无法预览" not in current_text:
                 try:
                     self.preview_label.config(image=None, text=f"无法预览:\n{e}")
                     self.preview_label.image = None
                 except tk.TclError:
                     pass
            print(f"Error showing preview for {image_path} (event: {event}): {e}")

    def _handle_key_up_arrow(self, event):  # Up arrow without Shift: move selection up
        lb = self.image_listbox
        is_shifted = (event.state & 0x0001) != 0

        if is_shifted:
            # let default Listbox Shift+Up behavior handle range selection
            return

        # Non-Shift custom handling
        current_selection = lb.curselection()
        current_active = -1
        try:
            current_active = lb.index(tk.ACTIVE)
        except tk.TclError:
            if current_selection:
                current_active = current_selection[0]

        new_index = -1

        if current_active == -1:
            if lb.size() > 0:
                new_index = lb.size() - 1
        elif current_active > 0:
            new_index = current_active - 1
        else:
            new_index = 0

        if new_index != -1:
            lb.selection_clear(0, END)
            lb.selection_set(new_index)
            lb.activate(new_index)
            lb.see(new_index)
            self.show_preview()
        
        return "break"

    def _handle_key_down_arrow(self, event):  # Down arrow without Shift: move selection down
        lb = self.image_listbox
        is_shifted = (event.state & 0x0001) != 0

        if is_shifted:
            # let default Listbox Shift+Down behavior handle range selection
            return

        # Non-Shift custom handling
        current_selection = lb.curselection()
        current_active = -1
        try:
            current_active = lb.index(tk.ACTIVE)
        except tk.TclError:
            if current_selection:
                current_active = current_selection[0]
        
        new_index = -1

        if current_active == -1:
            if lb.size() > 0:
                new_index = 0
        elif current_active < lb.size() - 1:
            new_index = current_active + 1
        else:
            new_index = lb.size() - 1
        
        if new_index != -1:
            lb.selection_clear(0, END)
            lb.selection_set(new_index)
            lb.activate(new_index)
            lb.see(new_index)
            self.show_preview()

        return "break"

    def _handle_control_key_up_arrow(self, event):  # Ctrl/Cmd + Up toggles selection
        lb = self.image_listbox
        if lb.size() == 0: return "break"

        current_active_idx = -1
        try:
            current_active_idx = lb.index(tk.ACTIVE)
        except tk.TclError:
            current_active_idx = lb.size()

        new_active_idx = -1
        if current_active_idx > 0:
            new_active_idx = current_active_idx - 1
        elif current_active_idx <= 0:
             new_active_idx = lb.size() - 1 if current_active_idx == lb.size() else 0
             if current_active_idx == 0 and lb.index(tk.ACTIVE) == 0:
                 new_active_idx = 0
             elif lb.size() > 0:
                 new_active_idx = lb.size() -1
             else:
                 return "break"
        
        if new_active_idx == -1 and lb.size() > 0:
            new_active_idx = lb.size() -1
        elif new_active_idx == -1:
            return "break"

        lb.activate(new_active_idx)
        
        # toggle selection on the new active index
        if lb.selection_includes(new_active_idx):
            lb.selection_clear(new_active_idx)
        else:
            lb.selection_set(new_active_idx)
            
        lb.see(new_active_idx)
        self.show_preview()
        return "break"

    def _handle_control_key_down_arrow(self, event):  # Ctrl/Cmd + Down toggles selection
        lb = self.image_listbox
        if lb.size() == 0: return "break"

        current_active_idx = -1
        try:
            current_active_idx = lb.index(tk.ACTIVE)
        except tk.TclError:
           current_active_idx = -1

        new_active_idx = -1
        if current_active_idx == -1:
            new_active_idx = 0
        elif current_active_idx < lb.size() - 1:
            new_active_idx = current_active_idx + 1
        elif current_active_idx == lb.size() -1:
            new_active_idx = lb.size() -1
        else:
            return "break"

        lb.activate(new_active_idx)
        
        if lb.selection_includes(new_active_idx):
            lb.selection_clear(new_active_idx)
        else:
            lb.selection_set(new_active_idx)
            
        lb.see(new_active_idx)
        self.show_preview()
        return "break"

    # Debounce handler for preview <Configure> events
    def _on_preview_configure(self, event=None):  # debounce preview recalculation on resize
        if self._preview_debounce_job:
            self.master.after_cancel(self._preview_debounce_job)
        self._preview_debounce_job = self.master.after(250, lambda: self.show_preview(event))


if __name__ == '__main__':  # app entry point
    root = tkinterdnd2.Tk()  # DnD-enabled root window
    app = PhotoStitcherApp(root)
    # Bind dynamic callbacks; guard with hasattr in case of future changes.
    if hasattr(app, 'output_width_var') and app.output_width_var:
        app.output_width_var.trace_add("write", app._update_expected_height_display)
    
    if hasattr(app, 'jpeg_quality_scale') and app.jpeg_quality_scale:
        app.jpeg_quality_scale.config(command=app._update_quality_display_label)
    
    if hasattr(app, 'output_format_menu') and app.output_format_menu:
        app.output_format_menu.bind("<<ComboboxSelected>>", app._output_format_changed)
    
    # Initialize labels and state
    if hasattr(app, '_update_quality_display_label'): app._update_quality_display_label()
    if hasattr(app, '_output_format_changed'): app._output_format_changed()
    if hasattr(app, '_update_expected_height_display'): app._update_expected_height_display()
    
    root.mainloop()  # start Tk event loop
