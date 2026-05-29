import json
import tkinter as tk
import subprocess
import sys
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from bio_diabetes_core import (
    analyze_sequence,
    find_disease,
    find_gene,
    list_disease_names,
    list_gene_symbols,
    load_knowledge,
    make_hypothesis,
)


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "diabetes_knowledge.json"


class DiabetesBioAssistantApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Type 2 Diabetes Bio Assistant")
        self.root.geometry("1240x840")
        self.root.minsize(1120, 760)

        self.knowledge = load_knowledge(str(DATA_PATH))
        self.selected_gene = tk.StringVar(value=list_gene_symbols(self.knowledge)[0])
        self.selected_disease = tk.StringVar(value=list_disease_names(self.knowledge)[0])
        self.status_var = tk.StringVar(value="Ready")
        self.sequence_report: dict | None = None

        self._configure_style()
        self._build_layout()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Malgun Gothic", 10))
        style.configure("Title.TLabel", font=("Malgun Gothic", 18, "bold"))

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=16)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="Type 2 Diabetes Bio Assistant", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="유전자-질병-약물 정보를 연결하고 FASTA 기초 분석과 연구 가설 추천을 제공하는 교육용 앱",
        ).pack(anchor="w", pady=(4, 0))

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        self.gene_tab = ttk.Frame(notebook, padding=14)
        self.seq_tab = ttk.Frame(notebook, padding=14)
        self.drug_tab = ttk.Frame(notebook, padding=14)
        self.hypothesis_tab = ttk.Frame(notebook, padding=14)
        notebook.add(self.gene_tab, text="1. Gene Lookup")
        notebook.add(self.seq_tab, text="2. Sequence Analysis")
        notebook.add(self.drug_tab, text="3. Disease & Drug")
        notebook.add(self.hypothesis_tab, text="4. Hypothesis")

        self._build_gene_tab()
        self._build_seq_tab()
        self._build_drug_tab()
        self._build_hypothesis_tab()

        footer = ttk.Frame(self.root, padding=(16, 0, 16, 16))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(
            footer,
            text="Research/Education only. 공개 자료 요약 앱이며 실제 진단·처방 판단을 대신하지 않습니다.",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=1, sticky="e")

        self.refresh_gene_info()
        self.refresh_drug_info()
        self.refresh_hypothesis()

    def _make_text(self, parent: ttk.Widget, bg: str = "#fbfcff") -> tk.Text:
        widget = tk.Text(parent, wrap="word", font=("Consolas", 10), bg=bg, relief="flat", padx=10, pady=10)
        return widget

    def _build_gene_tab(self) -> None:
        self.gene_tab.columnconfigure(0, weight=1)
        self.gene_tab.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.gene_tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(controls, text="유전자").pack(side="left")
        combo = ttk.Combobox(
            controls,
            textvariable=self.selected_gene,
            values=list_gene_symbols(self.knowledge),
            state="readonly",
            width=14,
        )
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _event: self.on_gene_changed())
        ttk.Button(controls, text="정보 새로보기", command=self.on_gene_changed).pack(side="left")

        self.gene_text = self._make_text(self.gene_tab)
        self.gene_text.grid(row=1, column=0, sticky="nsew")

    def _build_seq_tab(self) -> None:
        self.seq_tab.columnconfigure(0, weight=1)
        self.seq_tab.columnconfigure(1, weight=1)
        self.seq_tab.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.seq_tab)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Button(controls, text="FASTA 열기", command=self.open_sequence_file).pack(side="left")
        ttk.Button(controls, text="분석 실행", command=self.run_sequence_analysis).pack(side="left", padx=8)
        ttk.Button(controls, text="예시 삽입", command=self.insert_example_sequence).pack(side="left")

        left = ttk.LabelFrame(self.seq_tab, text="입력 서열", padding=10)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        self.seq_input = self._make_text(left, bg="#fffdf8")
        self.seq_input.grid(row=0, column=0, sticky="nsew")

        right = ttk.LabelFrame(self.seq_tab, text="분석 결과", padding=10)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.seq_output = self._make_text(right)
        self.seq_output.grid(row=0, column=0, sticky="nsew")

    def _build_drug_tab(self) -> None:
        self.drug_tab.columnconfigure(0, weight=1)
        self.drug_tab.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.drug_tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(controls, text="질병").pack(side="left")
        combo = ttk.Combobox(
            controls,
            textvariable=self.selected_disease,
            values=list_disease_names(self.knowledge),
            state="readonly",
            width=26,
        )
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_drug_info())
        ttk.Button(controls, text="질병 정보 보기", command=self.refresh_drug_info).pack(side="left")
        
        # 투두 리스트 연동 버튼 추가
        ttk.Button(controls, text="To-Do 리스트에 추천 추가", command=self.send_to_todo).pack(side="left", padx=10)
        
        # 투두 패드 실행 버튼 추가
        ttk.Button(controls, text="To-Do 리스트 열기", command=self.open_todopad).pack(side="left")

        self.drug_text = self._make_text(self.drug_tab)
        self.drug_text.grid(row=1, column=0, sticky="nsew")

    def open_todopad(self) -> None:
        """TodoPad 앱을 별도의 프로세스로 실행합니다."""
        # 현재 폴더(app.py와 같은 폴더)에서 찾기
        todopad_path = Path(__file__).parent / "todopad.py"
        try:
            subprocess.Popen([sys.executable, str(todopad_path)])
            self.status_var.set("TodoPad launched")
        except Exception as e:
            messagebox.showerror("실행 실패", f"TodoPad를 실행할 수 없습니다: {e}")

    def send_to_todo(self) -> None:
        """현재 질병/가설 기반 추천 습관을 TodoPad 데이터 파일에 직접 추가합니다."""
        # 현재 폴더(app.py와 같은 폴더)에서 찾기
        todo_file = Path(__file__).parent / "todopad_data.json"
        
        disease_name = self.selected_disease.get()
        recommendations = [
            {"title": f"[{disease_name}] 매일 30분 가볍게 걷기", "done": False, "memo": "혈당 조절을 위해 식후 걷기가 좋습니다."},
            {"title": f"[{disease_name}] 당분 섭취 줄이기", "done": False, "memo": "설탕, 탄산음료 등 단순 당질 섭취를 제한하세요."},
            {"title": f"[{disease_name}] 정기적인 혈당 체크", "done": False, "memo": "아침 공복 및 식후 혈당을 기록하세요."}
        ]

        try:
            if todo_file.exists():
                with open(todo_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"todo_list": []}

            # 데이터 형식 보정 (옛날 str 형식을 dict 형식으로 변환)
            current_list = data.get("todo_list", [])
            migrated_list = []
            for item in current_list:
                if isinstance(item, str):
                    migrated_list.append({"title": item, "done": False, "memo": ""})
                else:
                    migrated_list.append(item)
            
            # 중복 체크 후 추가
            existing_titles = [t.get("title", "") for t in migrated_list]
            added_count = 0
            for rec in recommendations:
                if rec["title"] not in existing_titles:
                    migrated_list.append(rec)
                    added_count += 1
            
            data["todo_list"] = migrated_list
            
            with open(todo_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            if added_count > 0:
                messagebox.showinfo("연동 성공", f"{added_count}개의 생활습관 추천이 TodoPad에 추가되었습니다.")
            else:
                messagebox.showinfo("확인", "이미 모든 추천 항목이 To-Do 리스트에 있습니다.")
                
        except Exception as e:
            messagebox.showerror("연동 실패", f"데이터 처리 중 오류 발생: {e}")

    def _build_hypothesis_tab(self) -> None:
        self.hypothesis_tab.columnconfigure(0, weight=1)
        self.hypothesis_tab.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.hypothesis_tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(controls, text="가설 다시 생성", command=self.refresh_hypothesis).pack(side="left")

        self.hypothesis_text = self._make_text(self.hypothesis_tab)
        self.hypothesis_text.grid(row=1, column=0, sticky="nsew")

    def on_gene_changed(self) -> None:
        self.refresh_gene_info()
        self.refresh_hypothesis()

    def refresh_gene_info(self) -> None:
        gene = find_gene(self.knowledge, self.selected_gene.get())
        if gene is None:
            return
        lines = [
            f"유전자: {gene['symbol']} ({gene['full_name']})",
            f"핵심 요약: {gene['summary']}",
            "",
            "[관련 질병]",
        ]
        for item in gene["associated_diseases"]:
            lines.append(f"- {item['name']}: {item['evidence']}")
        lines.extend(["", "[추천 실험]"])
        for item in gene["recommended_experiments"]:
            lines.append(f"- {item}")
        lines.extend(["", "[공개 출처]"])
        for source in gene["sources"]:
            lines.append(f"- {source['label']}: {source['url']}")

        self.gene_text.delete("1.0", tk.END)
        self.gene_text.insert("1.0", "\n".join(lines))
        self.status_var.set(f"Loaded gene info: {gene['symbol']}")

    def open_sequence_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="FASTA/TXT 선택",
            filetypes=[("Sequence files", "*.fasta *.fa *.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return
        content = Path(file_path).read_text(encoding="utf-8")
        self.seq_input.delete("1.0", tk.END)
        self.seq_input.insert("1.0", content)
        self.status_var.set(f"Loaded sequence: {Path(file_path).name}")

    def insert_example_sequence(self) -> None:
        demo = (
            ">TCF7L2_demo_fragment\n"
            "ATGCCGCAGCTGAACGGCGGTGGAGGGGATGACCTAGGCGCCAACGACGAACTGATTTCC\n"
            "TTCAAAGACGAGGGCGAACAGGAGGAGAAGAGCTCCGAAAACTCCTCGGCAGAGAGGGAT\n"
            "TTAGCTGATGTCAAATCGTCTCTAGTCAATGAATCAGAAACGAATCAAAAACAGCTCCTC\n"
        )
        self.seq_input.delete("1.0", tk.END)
        self.seq_input.insert("1.0", demo)
        self.status_var.set("Inserted demo sequence")

    def run_sequence_analysis(self) -> None:
        raw_text = self.seq_input.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("입력 필요", "분석할 FASTA 또는 염기서열을 넣어주세요.")
            return
        try:
            report = analyze_sequence(raw_text)
        except Exception as exc:
            messagebox.showerror("분석 실패", str(exc))
            self.status_var.set("Sequence analysis failed")
            return

        self.sequence_report = report
        orf = report["longest_orf"]
        lines = [
            "=== Sequence Analysis ===",
            f"Input name: {report['input_name'] or 'n/a'}",
            f"Length: {report['length_nt']} nt",
            f"GC content: {report['gc_percent']}%",
            f"Starts with ATG: {report['starts_with_atg']}",
            f"Ends with stop codon: {report['ends_with_stop']}",
            f"Composition: {report['composition']}",
            "",
            "[Longest ORF]",
        ]
        if orf:
            lines.extend(
                [
                    f"Frame {orf['frame']} / {orf['start']}-{orf['end']}",
                    f"Length: {orf['length_nt']} nt / {orf['length_aa']} aa",
                    f"Protein preview: {orf['protein_preview']}",
                ]
            )
        else:
            lines.append("No complete ORF found in the forward strand.")

        lines.extend(["", "[Top Codons]"])
        for item in report["top_codons"]:
            lines.append(f"- {item['codon']}: {item['count']} ({item['frequency']}%)")

        self.seq_output.delete("1.0", tk.END)
        self.seq_output.insert("1.0", "\n".join(lines))
        self.refresh_hypothesis()
        self.status_var.set(f"Sequence analyzed: {report['length_nt']} nt")

    def refresh_drug_info(self) -> None:
        disease = find_disease(self.knowledge, self.selected_disease.get())
        if disease is None:
            return
        lines = [
            f"질병: {disease['name']}",
            f"요약: {disease['overview']}",
            "",
            "[관련 약물]",
        ]
        for drug in disease["drugs"]:
            lines.append(f"- {drug['name']} ({drug['drug_class']})")
            lines.append(f"  mechanism: {drug['mechanism']}")
            lines.append(f"  source: {drug['source_url']}")
        lines.extend(["", "[질병 출처]"])
        for source in disease["sources"]:
            lines.append(f"- {source['label']}: {source['url']}")

        self.drug_text.delete("1.0", tk.END)
        self.drug_text.insert("1.0", "\n".join(lines))
        self.status_var.set(f"Loaded disease info: {disease['name']}")

    def refresh_hypothesis(self) -> None:
        gene = find_gene(self.knowledge, self.selected_gene.get())
        suggestions = make_hypothesis(gene, self.sequence_report)
        lines = [
            "=== Research Hypothesis Suggestions ===",
            f"현재 선택 유전자: {gene['symbol'] if gene else 'n/a'}",
            "",
        ]
        lines.extend(f"- {item}" for item in suggestions)
        if self.sequence_report:
            lines.extend(
                [
                    "",
                    "[현재 서열 기반 메모]",
                    f"- 길이: {self.sequence_report['length_nt']} nt",
                    f"- GC%: {self.sequence_report['gc_percent']}",
                    f"- ORF 존재: {self.sequence_report['longest_orf'] is not None}",
                ]
            )
        self.hypothesis_text.delete("1.0", tk.END)
        self.hypothesis_text.insert("1.0", "\n".join(lines))
        self.status_var.set("Hypothesis updated")


def main() -> None:
    root = tk.Tk()
    DiabetesBioAssistantApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
