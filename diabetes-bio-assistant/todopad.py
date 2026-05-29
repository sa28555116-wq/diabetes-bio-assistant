import tkinter as tk
from tkinter import messagebox
import json
import os

from pathlib import Path

# 데이터 파일 경로 설정 (파일이 위치한 폴더 기준 절대 경로)
BASE_DIR = Path(__file__).parent
DATA_FILE = str(BASE_DIR / "todopad_data.json")

class TodoPadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TodoPad - 투두 리스트 & 메모장")
        self.root.geometry("850x500")

        # 메인 폰트 설정
        self.font_main = ("Malgun Gothic", 10)
        self.font_title = ("Malgun Gothic", 11, "bold")

        # 현재 선택된 할 일의 인덱스 추적
        self.current_index = -1

        # 데이터 로드 및 마이그레이션
        self.load_data()

        # 전체 레이아웃 구성
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=4, bg="#ccc")
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        # 1. 왼쪽 투두 리스트 프레임
        self.todo_frame = tk.Frame(self.paned_window, padx=10, pady=10)
        self.paned_window.add(self.todo_frame, width=350)

        self.setup_todo_ui()

        # 2. 오른쪽 메모장 프레임
        self.memo_frame = tk.Frame(self.paned_window, padx=10, pady=10)
        self.paned_window.add(self.memo_frame)

        self.setup_memo_ui()

        # 종료 시 자동 저장 설정
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_todo_ui(self):
        # 제목 및 새로고침 버튼 프레임
        title_frame = tk.Frame(self.todo_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(title_frame, text="✅ 할 일 목록", font=self.font_title).pack(side=tk.LEFT)
        
        # 새로고침 버튼 (외부 앱 연동 시 필요)
        refresh_btn = tk.Button(title_frame, text="↻", command=self.refresh_data, font=("Arial", 12, "bold"), bg="#eee", relief="flat", padx=5)
        refresh_btn.pack(side=tk.RIGHT)

        # 입력창 및 추가 버튼 프레임
        entry_frame = tk.Frame(self.todo_frame)
        entry_frame.pack(fill=tk.X, pady=(0, 10))

        self.todo_entry = tk.Entry(entry_frame, font=self.font_main)
        self.todo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.todo_entry.bind("<Return>", lambda e: self.add_todo())

        add_btn = tk.Button(entry_frame, text="추가", command=self.add_todo, width=8, bg="#4CAF50", fg="white", relief="flat")
        add_btn.pack(side=tk.RIGHT)

        # 리스트박스 및 스크롤바
        list_frame = tk.Frame(self.todo_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.todo_scrollbar = tk.Scrollbar(list_frame)
        self.todo_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.todo_listbox = tk.Listbox(
            list_frame, 
            font=self.font_main, 
            yscrollcommand=self.todo_scrollbar.set,
            selectmode=tk.SINGLE,
            activestyle='none'
        )
        self.todo_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.todo_scrollbar.config(command=self.todo_listbox.yview)
        
        # 리스트박스 선택 이벤트 바인딩
        self.todo_listbox.bind("<<ListboxSelect>>", self.on_task_select)

        # 하단 버튼 프레임
        btn_frame = tk.Frame(self.todo_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        # 체크(완료) 버튼
        self.check_btn = tk.Button(btn_frame, text="체크/해제", command=self.toggle_done, bg="#2196F3", fg="white", relief="flat")
        self.check_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 삭제 버튼
        del_btn = tk.Button(btn_frame, text="선택 삭제", command=self.delete_todo, bg="#f44336", fg="white", relief="flat")
        del_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        # 리스트박스 업데이트
        self.update_listbox()

    def setup_memo_ui(self):
        # 제목
        tk.Label(self.memo_frame, text="📝 메모장 (할 일을 선택하면 내용이 나타납니다)", font=self.font_title).pack(anchor="w", pady=(0, 10))

        # 메모 입력창 및 스크롤바
        memo_scroll = tk.Scrollbar(self.memo_frame)
        memo_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.memo_text = tk.Text(
            self.memo_frame, 
            font=self.font_main, 
            yscrollcommand=memo_scroll.set,
            undo=True,
            padx=5, pady=5,
            state=tk.DISABLED # 초기에는 비활성화 (항목 선택 전)
        )
        self.memo_text.pack(fill=tk.BOTH, expand=True)
        memo_scroll.config(command=self.memo_text.yview)

    def update_listbox(self):
        """데이터를 바탕으로 리스트박스를 다시 그립니다."""
        self.todo_listbox.delete(0, tk.END)
        for item in self.data["todo_list"]:
            prefix = "[v] " if item["done"] else "[ ] "
            self.todo_listbox.insert(tk.END, prefix + item["title"])
        
        # 이전 선택 유지 시도
        if 0 <= self.current_index < len(self.data["todo_list"]):
            self.todo_listbox.selection_set(self.current_index)
            self.todo_listbox.see(self.current_index)

    def on_task_select(self, event=None):
        """할 일을 선택했을 때 이전 메모를 저장하고 새 메모를 불러옵니다."""
        selected = self.todo_listbox.curselection()
        if not selected:
            return

        new_index = selected[0]

        # 현재 인덱스의 메모 저장
        if self.current_index != -1 and self.current_index < len(self.data["todo_list"]):
            self.data["todo_list"][self.current_index]["memo"] = self.memo_text.get("1.0", tk.END).strip()

        # 새 인덱스의 메모 로드
        self.current_index = new_index
        task_data = self.data["todo_list"][new_index]

        self.memo_text.config(state=tk.NORMAL)
        self.memo_text.delete("1.0", tk.END)
        self.memo_text.insert("1.0", task_data.get("memo", ""))

    def toggle_done(self):
        """선택된 항목의 완료 상태를 토글합니다."""
        selected = self.todo_listbox.curselection()
        if selected:
            idx = selected[0]
            self.data["todo_list"][idx]["done"] = not self.data["todo_list"][idx]["done"]
            self.update_listbox()
        else:
            messagebox.showwarning("주의", "체크할 항목을 선택해주세요!")

    def add_todo(self):
        title = self.todo_entry.get().strip()
        if title:
            # 새로운 형식으로 추가
            new_item = {"title": title, "done": False, "memo": ""}
            self.data["todo_list"].append(new_item)
            self.update_listbox()
            self.todo_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("주의", "할 일을 입력해주세요!")

    def delete_todo(self):
        selected = self.todo_listbox.curselection()
        if selected:
            idx = selected[0]
            if messagebox.askyesno("확인", f"'{self.data['todo_list'][idx]['title']}' 항목을 삭제하시겠습니까?"):
                self.data["todo_list"].pop(idx)
                self.current_index = -1
                self.memo_text.delete("1.0", tk.END)
                self.memo_text.config(state=tk.DISABLED)
                self.update_listbox()
        else:
            messagebox.showwarning("주의", "삭제할 항목을 선택해주세요!")

    def load_data(self):
        """데이터를 로드하고 이전 형식(문자열 리스트)을 새 형식(딕셔너리 리스트)으로 변환합니다."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = {"todo_list": []}
        else:
            self.data = {"todo_list": []}
        
        # 데이터 구조 보정 로직
        if not isinstance(self.data, dict):
            self.data = {"todo_list": []}
            
        current_list = self.data.get("todo_list", [])
        if not isinstance(current_list, list):
            current_list = []
            
        migrated_list = []
        # 옛날 방식의 전역 메모가 있다면 첫 번째 항목으로 옮기기 위해 보관
        old_memo = self.data.get("memo_text", "")
        
        for i, item in enumerate(current_list):
            if isinstance(item, str):
                # 문자열인 경우 딕셔너리로 변환
                memo = old_memo if i == 0 else ""
                migrated_list.append({
                    "title": item,
                    "done": False,
                    "memo": memo
                })
            elif isinstance(item, dict):
                # 딕셔너리인 경우 누락된 필드 채우기
                migrated_item = {
                    "title": item.get("title", "제목 없음"),
                    "done": item.get("done", False),
                    "memo": item.get("memo", "")
                }
                migrated_list.append(migrated_item)
        
        self.data["todo_list"] = migrated_list
        # 마이그레이션이 끝난 옛날 필드는 제거
        if "memo_text" in self.data:
            del self.data["memo_text"]

    def save_data(self):
        """현재 상태를 파일에 저장합니다."""
        try:
            # 현재 열려있는 메모 저장
            if self.current_index != -1 and self.current_index < len(self.data["todo_list"]):
                self.data["todo_list"][self.current_index]["memo"] = self.memo_text.get("1.0", tk.END).strip()

            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"저장 중 오류 발생: {e}")

    def refresh_data(self):
        """파일에서 데이터를 다시 불러와 UI를 갱신합니다."""
        self.load_data()
        self.update_listbox()
        # 선택 상태 초기화
        self.current_index = -1
        self.memo_text.config(state=tk.NORMAL)
        self.memo_text.delete("1.0", tk.END)
        self.memo_text.config(state=tk.DISABLED)
        messagebox.showinfo("알림", "데이터를 새로고침했습니다.")

    def on_closing(self):
        """종료 시 데이터를 저장하고 창을 닫습니다."""
        try:
            self.save_data()
        except:
            pass
        finally:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TodoPadApp(root)
    root.mainloop()
