import os
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import ezdxf
import numpy as np
import trimesh
from shapely.geometry import Polygon


def convert(path, width_mm, thickness_mm, out_dir):
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("이미지를 읽을 수 없어요.")
    _, bw = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
    contours, hierarchy = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("윤곽선을 찾지 못했어요. 흰 배경에 검은 부품 이미지를 써보세요.")

    x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))
    scale = width_mm / max(w - 1, 1)

    def to_mm(c):
        return [((float(p[0][0]) - x) * scale, -(float(p[0][1]) - y) * scale) for p in c]

    # 2D: DXF
    doc = ezdxf.new()
    doc.units = 4  # mm
    msp = doc.modelspace()
    for c in contours:
        msp.add_lwpolyline(to_mm(c), close=True)
    doc.saveas(os.path.join(out_dir, "output.dxf"))

    # 3D: STL
    parts = []
    for i, c in enumerate(contours):
        if hierarchy[0][i][3] == -1:
            holes = [to_mm(contours[j]) for j in range(len(contours)) if hierarchy[0][j][3] == i]
            parts.append(trimesh.creation.extrude_polygon(Polygon(to_mm(c), holes), thickness_mm))
    mesh = trimesh.util.concatenate(parts)
    mesh.export(os.path.join(out_dir, "output.stl"))
    return len(contours), [round(float(v), 1) for v in mesh.extents]


root = tk.Tk()
root.title("image2cad")
root.geometry("400x320")

state = {"path": None}
width_var = tk.StringVar(value="100")
thick_var = tk.StringVar(value="10")

file_label = tk.Label(root, text="이미지를 선택하세요", wraplength=360)


def choose():
    p = filedialog.askopenfilename(filetypes=[("이미지", "*.png *.jpg *.jpeg")])
    if p:
        state["path"] = p
        file_label.config(text=os.path.basename(p))


def run():
    if not state["path"]:
        messagebox.showwarning("안내", "먼저 이미지를 선택하세요.")
        return
    try:
        w = float(width_var.get())
        t = float(thick_var.get())
    except ValueError:
        messagebox.showerror("오류", "가로와 두께는 숫자로 입력하세요.")
        return
    out_dir = filedialog.askdirectory(title="저장할 폴더 선택")
    if not out_dir:
        return
    try:
        n, ext = convert(state["path"], w, t, out_dir)
    except Exception as e:
        messagebox.showerror("오류", str(e))
        return
    messagebox.showinfo(
        "완료",
        f"윤곽선 {n}개 | 3D 크기 {ext[0]} x {ext[1]} x {ext[2]} mm\n\noutput.dxf, output.stl 저장 완료",
    )


tk.Label(root, text="image2cad", font=("Helvetica", 20, "bold")).pack(pady=(16, 4))
tk.Label(root, text="부품 이미지를 2D(DXF)와 3D(STL)로 변환해요").pack()
tk.Button(root, text="이미지 선택", command=choose).pack(pady=10)
file_label.pack()
tk.Label(root, text="부품 가로 길이 (mm)").pack(pady=(12, 0))
tk.Entry(root, textvariable=width_var, justify="center").pack()
tk.Label(root, text="두께 (mm)").pack(pady=(8, 0))
tk.Entry(root, textvariable=thick_var, justify="center").pack()
tk.Button(root, text="변환하기", command=run).pack(pady=14)

root.mainloop()