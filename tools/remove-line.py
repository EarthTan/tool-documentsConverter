import tkinter as tk
from tkinter import scrolledtext

def remove_empty_lines(s: str) -> str:
    return "\n".join(line for line in s.splitlines() if line.strip())

def clean_and_copy():
    content = text.get("1.0", "end-1c")
    cleaned = remove_empty_lines(content)
    text.delete("1.0", "end")
    text.insert("1.0", cleaned)
    root.clipboard_clear()
    root.clipboard_append(cleaned)
    status_var.set("已清除空行并复制到剪贴板")

def paste_from_clipboard():
    try:
        clip = root.clipboard_get()
    except tk.TclError:
        clip = ""
    text.insert("insert", clip)

root = tk.Tk()
root.title("清除空行并复制到剪贴板")

text = scrolledtext.ScrolledText(root, wrap="none", width=80, height=20)
text.pack(padx=8, pady=8, fill="both", expand=True)

btn_frame = tk.Frame(root)
btn_frame.pack(fill="x", padx=8, pady=(0,8))

clean_btn = tk.Button(btn_frame, text="清除空行并复制", command=clean_and_copy)
clean_btn.pack(side="left", padx=(0,6))

paste_btn = tk.Button(btn_frame, text="从剪贴板粘贴", command=paste_from_clipboard)
paste_btn.pack(side="left", padx=(0,6))

clear_btn = tk.Button(btn_frame, text="清除文本框", command=lambda: text.delete("1.0", "end"))
clear_btn.pack(side="left")

status_var = tk.StringVar()
status_var.set("")
status_label = tk.Label(root, textvariable=status_var, anchor="w")
status_label.pack(fill="x", padx=8, pady=(0,8))

root.mainloop()