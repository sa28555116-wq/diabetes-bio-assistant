import tkinter as tk
from tkinter import messagebox
import json
import os
import datetime
import winsound
import sys
from pathlib import Path

def resource_path(relative_path):
    """ PyInstaller 임시 폴더 또는 실행 파일 위치에서 리소스를 찾습니다. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_save_path(filename):
    """ 실행 파일과 같은 위치에 데이터를 저장합니다. """
    if getattr(sys, 'frozen', False):
        # EXE로 실행 중인 경우 EXE 폴더
        base_dir = os.path.dirname(sys.executable)
    else:
        # 스크립트로 실행 중인 경우 소스 폴더
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

# 데이터 파일 경로 설정
DATA_FILE = get_save_path("todopad_data.json")

class TodoPadApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TodoPad - 투두 리스트 & 메모장")
        self.root.geometry("850x500")
        
        # 윈도우 아이콘 등이 있다면 resource_path 사용
        # self.root.iconbitmap(resource_path("icon.ico"))

        # 메인 폰트 설정
        self.font_main = ("Malgun Gothic", 10)
        self.font_title = ("Malgun Gothic", 11, "bold")

        # 현재 선택된 할 일의 인덱스 추적
        self.current_index = -1

        # 이미 울린 알람 추적 (중복 방지)
        self.triggered_alarms = set()

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

        # 알람 체크 루프 시작
        self.check_alarms()

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

        # 알람 시간 입력창 (HH:MM)
        self.alarm_entry = tk.Entry(entry_frame, font=self.font_main, width=7)
        self.alarm_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.alarm_entry.insert(0, "HH:MM")
        self.alarm_entry.bind("<FocusIn>", lambda e: self.alarm_entry.delete(0, tk.END) if self.alarm_entry.get() == "HH:MM" else None)

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
            alarm_info = f" ⏰ {item['alarm_time']}" if item.get("alarm_time") else ""
            self.todo_listbox.insert(tk.END, prefix + item["title"] + alarm_info)
        
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
        alarm_time = self.alarm_entry.get().strip()
        
        if not title:
            messagebox.showwarning("주의", "할 일을 입력해주세요!")
            return

        # 알람 시간 검증 (필요한 경우)
        valid_alarm = ""
        if alarm_time and alarm_time != "HH:MM":
            try:
                # HH:MM 형식 확인
                datetime.datetime.strptime(alarm_time, "%H:%M")
                valid_alarm = alarm_time
            except ValueError:
                messagebox.showwarning("주의", "알람 시간을 HH:MM 형식으로 입력해주세요 (예: 14:30)")
                return

        # 새로운 형식으로 추가
        new_item = {"title": title, "done": False, "memo": "", "alarm_time": valid_alarm}
        self.data["todo_list"].append(new_item)
        self.update_listbox()
        
        # 입력창 초기화
        self.todo_entry.delete(0, tk.END)
        self.alarm_entry.delete(0, tk.END)
        self.alarm_entry.insert(0, "HH:MM")

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

    def check_alarms(self):
        """1초마다 실행되며 알람 시간이 된 항목이 있는지 확인합니다."""
        now = datetime.datetime.now().strftime("%H:%M")
        
        for item in self.data["todo_list"]:
            alarm_time = item.get("alarm_time")
            # 완료되지 않았고, 알람 시간이 설정되어 있으며, 현재 시간과 일치하는 경우
            if not item["done"] and alarm_time:
                if alarm_time == now:
                    # 해당 시간대에 아직 알람이 울리지 않은 경우에만 실행
                    alarm_id = f"{item['title']}_{alarm_time}"
                    if alarm_id not in self.triggered_alarms:
                        self.play_alarm(item["title"])
                        self.triggered_alarms.add(alarm_id)
        
        # 1분마다 triggered_alarms 정리 (메모리 관리 및 다음 날 재사용 가능하도록)
        # 하지만 실제로는 앱이 계속 켜져있을 때 매 분마다 정리는 복잡하므로 
        # 간단히 시간만 다르면(분 단위가 넘어가면) 셋을 비우는 방식도 고려 가능.
        # 여기서는 단순히 1초마다 반복 호출.
        self.root.after(1000, self.check_alarms)

    def play_alarm(self, task_title):
        """알람 소리를 재생하고 메시지 박스를 띄웁니다."""
        # 윈도우 비프음 재생 (주파수 1000Hz, 지속시간 1000ms)
        try:
            winsound.Beep(1000, 1000)
        except:
            pass
        
        messagebox.showinfo("⏰ 알람", f"할 일 시간입니다!\n\n내용: {task_title}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TodoPadApp(root)
    root.mainloop()
