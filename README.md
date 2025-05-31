# Photo Stitcher (长图拼接工具)

[中文](#中文) | [English](#english)

---

## 中文

Photo Stitcher 是一款用户友好的桌面应用程序，使用 Python 和 Tkinter 构建，用于将多张图片垂直拼接成一张长图。它支持多种图片格式、重新排序、旋转以及可配置的输出选项。

### 功能特性

* **图片导入**:
  * 通过文件对话框支持 JPG, JPEG, PNG 格式。
  * 支持将图片文件拖放到应用程序窗口进行导入。
* **图片管理**:
  * 在可重新排序的列表中显示导入的图片。
  * 允许用户在列表中上移或下移图片。
  * 允许用户从列表中删除图片。
  * 支持在列表中多选图片进行批量操作（删除、旋转）。
* **图片预览**:
  * 显示当前选中图片的预览。
* **图片旋转**:
  * 支持对选中图片进行90度向左或向右旋转。
  * 预览会更新以反映旋转效果。
  * 最终输出的图片会反映所有应用的旋转。
* **拼接选项**:
  * 根据图片在列表中的顺序垂直合并图片。
  * 用户可配置的输出宽度（单位：像素）。
  * 根据当前图片和输出宽度，自动计算并显示拼接后图片的预计总高度。
  * 用户可选择输出格式（JPEG 或 PNG）。
  * 如果选择JPEG输出，可调节JPEG压缩质量（0-100%）。
* **输出**:
  * 通过保存文件对话框，将最终拼接好的图片保存到用户指定的位置和文件名。

### 快速上手 (预编译版 - 仅 macOS)

对于 macOS 用户，使用 Photo Stitcher 最简单的方式是下载预编译的应用程序：

1. 前往本项目的 [**Releases 页面**](https://github.com/HoraceLuBFA/photo-stitcher/releases)。
2. 下载 `PhotoStitcher.zip` 文件。
3. 解压得到 `PhotoStitcher.app` ，双击或复制到“应用程序”中运行。
4. 首次运行时，如果遇到安全警告，您可能需要右键点击应用图标，然后选择"打开"。或者，您可能需要在"系统偏好设置"的"安全性与隐私"中调整设置为允许来自"App Store 和被认可的开发者"的应用。

### 从源码运行

以下说明适用于希望从 Python 源代码运行本应用或参与开发的用户。

#### 1. 环境要求

* Python 3.x
* Pillow (PIL Fork)
* tkinterdnd2

#### 2. 安装步骤

1. **克隆仓库（或下载源代码）:**

    ```bash
    git clone https://your-repository-url/photo-stitcher.git
    cd photo-stitcher
    ```

  *(如果您将项目托管在 GitHub 或类似平台，请将 `https://your-repository-url/photo-stitcher.git` 替换为您的实际仓库 URL。)*

2. **安装依赖:**
    建议使用虚拟环境。

    ```bash
    python -m venv venv
    # Windows 系统
    venv\Scripts\activate
    # macOS/Linux 系统
    source venv/bin/activate
    ```

    然后安装所需包:

    ```bash
    pip install Pillow tkinterdnd2
    ```

#### 3. 如何运行

导航到包含 `main.py` 的目录（例如，如果您的 `main.py` 在 `photo_stitcher` 文件夹内，则进入该文件夹），然后运行 `main.py` 脚本：

```bash
python main.py
```

或者，如果您位于 `photo_stitcher` 的父目录中：

```bash
python photo_stitcher/main.py
```

### **使用说明**

1. **导入图片**:
   * 点击"导入图片"按钮，或将图片文件（JPG, JPEG, PNG）拖拽到程序窗口中。
2. **管理列表**:

   * 在列表中选择一张图片进行预览。
   * 使用"上移"、"下移"按钮调整图片顺序。
   * 使用"删除"按钮移除选中的图片。
   * 使用键盘方向键进行单项选择导航，使用 Ctrl/Cmd + 方向键调整多项选择。

3. **旋转图片**:
   * 选中一张或多张图片，然后使用"左转90°"或"右转90°"按钮。

4. **设置输出选项**:

   * **输出宽度**: 输入最终合成图片的期望宽度（像素）。
   * **预计总高**: 会根据当前图片列表和输出宽度自动更新。
   * **输出格式**: 选择JPEG或PNG格式。
   * **JPEG质量**: 如果选择了JPEG格式，可以通过滑块调整压缩质量（0-100%）。PNG格式此选项无效。

5. **拼接并保存**:
   * 点击"拼接图片并保存"按钮。程序会提示您选择保存位置和文件名。

### 许可证

本项目采用 MIT 许可证 - 详情请参阅下面的 [LICENSE](#license-text) 部分。

---

## English

Photo Stitcher is a user-friendly desktop application built with Python and Tkinter for vertically stitching multiple images into a single, long image. It supports various image formats, reordering, rotation, and configurable output options.

### Features

* **Image Import**:
  * Supports JPG, JPEG, and PNG formats via a file dialog.
  * Supports drag-and-drop of image files onto the application window.
  * Image Management**:
  * Displays imported images in a reorderable list.
  * Allows users to move images up or down in the list.
  * Allows users to delete images from the list.
  * Supports multi-selection in the list for batch operations (delete, rotate).
* **Image Preview**:
  * Shows a preview of the currently selected image(s).
* **Image Rotation**:
  * Supports 90-degree left and right rotation for selected images.
  * Preview updates to reflect rotations.
  * Final output reflects all applied rotations.
* **Stitching Options**:
  * Combines images vertically based on their order in the list.
  * User-configurable output width (in pixels).
  * Calculates and displays the expected total height of the stitched image based on current images and output width.
  * User-selectable output format (JPEG or PNG).
  * Adjustable JPEG quality (0-100%) if JPEG output is selected.
* **Output**:
  * Saves the final stitched image to a user-specified location and filename via a save file dialog.

### Quick Start (Pre-compiled Application for macOS)

For macOS users, the easiest way to use Photo Stitcher is to download the pre-compiled application:

1. Go to the [**Releases page**](https://github.com/HoraceLuBFA/photo-stitcher/releases) for this project.
2. Download the `PhotoStitcher.zip` file.
3. Unzip it to get `PhotoStitcher.app`. Double-click it to run, or copy it to your "Applications" folder.
4. On the first run, if you encounter a security warning, you might need to right-click the app icon and select "Open". Alternatively, you may need to adjust your settings in "System Preferences" under "Security & Privacy" to allow apps downloaded from "App Store and identified developers".

### Running from Source

These instructions are for users who want to run the application from its Python source code or contribute to its development.

#### 1. Requirements

* Python 3.x
* Pillow (PIL Fork)
* tkinterdnd2

#### 2. Installation

1. **Clone the repository (or download the source code):**

    ```bash
    git clone https://your-repository-url/photo-stitcher.git
    cd photo-stitcher
    ```

  *(Please replace `https://your-repository-url/photo-stitcher.git` with your actual repository URL if you host it on GitHub or a similar platform.)*

2. **Install dependencies:**
    It's recommended to use a virtual environment.

    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

    Then install the required packages:

    ```bash
    pip install Pillow tkinterdnd2
    ```

#### 3. Usage

Navigate to the directory containing `main.py` (e.g., the `photo_stitcher` directory if your `main.py` is inside it) and run the `main.py` script:

```bash
python main.py
```

Or, if you are in the parent directory of `photo_stitcher`:

```bash
python photo_stitcher/main.py
```

### **How to Use**

1. **Import Images**

   * Click the "导入图片" (Import Images) button or drag and drop image files (JPG, JPEG, PNG) onto the window.

2. **Manage List**:

   * Select an image in the list to preview it.
   * Use "上移" (Move Up), "下移" (Move Down) to reorder.
   * Use "删除" (Delete) to remove selected image(s).
   * Use arrow keys for single selection navigation, and Ctrl/Cmd + arrow keys for adjusting multiple selections.

3. **Rotate Images**: Select image(s) and use "左转90°" (Rotate Left) or "右转90°" (Rotate Right).

4. **Set Output Options**:

   * **输出宽度 (Output Width)**: Enter the desired width in pixels for the final image.
   * **预计总高 (Expected Total Height)**: Automatically updates based on images and output width.
   * **输出格式 (Output Format)**: Choose between JPEG and PNG.
   * **JPEG质量 (JPEG Quality)**: Adjust the slider (0-100%) if JPEG is selected. This is disabled for PNG.

5. **Combine and Save**:

   * Click "拼接图片并保存" (Stitch Images and Save). You will be prompted to choose a save location and filename.

### License

This project is licensed under the MIT License - see the [LICENSE](#license-text) section below for details.

---

## <a name="license-text"></a>LICENSE

```text
MIT License

Copyright (c) [2025] [HoraceLuBFA]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
