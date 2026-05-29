import json
import re
from collections import Counter
from pathlib import Path


DNA_RE = re.compile(r"[ACGTUacgtu]")
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}
STOP_CODONS = {"TAA", "TAG", "TGA"}


def load_knowledge(path: str) -> dict:
    target = Path(path)
    if not target.is_absolute():
        target = Path(__file__).parent / path
    return json.loads(target.read_text(encoding="utf-8"))


def find_gene(knowledge: dict, symbol: str) -> dict | None:
    symbol_upper = symbol.strip().upper()
    for gene in knowledge.get("genes", []):
        if gene["symbol"].upper() == symbol_upper:
            return gene
    return None


def list_gene_symbols(knowledge: dict) -> list[str]:
    return [gene["symbol"] for gene in knowledge.get("genes", [])]


def list_disease_names(knowledge: dict) -> list[str]:
    return [disease["name"] for disease in knowledge.get("diseases", [])]


def find_disease(knowledge: dict, name: str) -> dict | None:
    lookup = name.strip().lower()
    for disease in knowledge.get("diseases", []):
        if disease["name"].lower() == lookup:
            return disease
    return None


def normalize_sequence(raw_text: str) -> str:
    lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(">"):
            continue
        lines.append(stripped)
    source = "".join(lines) if lines else raw_text
    letters = "".join(DNA_RE.findall(source))
    if not letters:
        raise ValueError("입력에서 DNA/RNA 서열을 찾지 못했습니다.")
    return letters.upper().replace("U", "T")


def fasta_name(raw_text: str) -> str | None:
    for line in raw_text.splitlines():
        if line.startswith(">"):
            return line[1:].strip()
    return None


def gc_content(sequence: str) -> float:
    gc = sum(1 for base in sequence if base in {"G", "C"})
    return round((gc / len(sequence)) * 100, 2) if sequence else 0.0


def nucleotide_composition(sequence: str) -> dict:
    counts = Counter(sequence)
    return {base: counts.get(base, 0) for base in "ACGT"}


def translate(sequence: str) -> str:
    protein = []
    for i in range(0, len(sequence) - 2, 3):
        protein.append(CODON_TABLE.get(sequence[i:i + 3], "X"))
    return "".join(protein)


def longest_orf(sequence: str) -> dict | None:
    best = None
    for frame in range(3):
        i = frame
        while i <= len(sequence) - 3:
            codon = sequence[i:i + 3]
            if codon == "ATG":
                j = i
                while j <= len(sequence) - 3:
                    next_codon = sequence[j:j + 3]
                    if next_codon in STOP_CODONS:
                        coding = sequence[i:j + 3]
                        protein = translate(coding)
                        candidate = {
                            "frame": frame + 1,
                            "start": i + 1,
                            "end": j + 3,
                            "length_nt": len(coding),
                            "length_aa": max(len(protein) - 1, 0),
                            "protein_preview": protein[:80],
                        }
                        if best is None or candidate["length_nt"] > best["length_nt"]:
                            best = candidate
                        i = j
                        break
                    j += 3
            i += 3
    return best


def codon_summary(sequence: str) -> list[dict]:
    usable = len(sequence) - (len(sequence) % 3)
    codons = [sequence[i:i + 3] for i in range(0, usable, 3)]
    counts = Counter(codons)
    total = sum(counts.values())
    return [
        {
            "codon": codon,
            "count": count,
            "frequency": round((count / total) * 100, 2),
        }
        for codon, count in counts.most_common(8)
    ] if total else []


def analyze_sequence(raw_text: str) -> dict:
    sequence = normalize_sequence(raw_text)
    return {
        "input_name": fasta_name(raw_text),
        "length_nt": len(sequence),
        "gc_percent": gc_content(sequence),
        "composition": nucleotide_composition(sequence),
        "starts_with_atg": sequence.startswith("ATG"),
        "ends_with_stop": sequence[-3:] in STOP_CODONS if len(sequence) >= 3 else False,
        "longest_orf": longest_orf(sequence),
        "top_codons": codon_summary(sequence),
        "sequence_preview": sequence[:120],
    }


def make_hypothesis(gene: dict | None, sequence_report: dict | None) -> list[str]:
    notes = []
    if gene:
        notes.append(gene["hypothesis"])
        notes.extend(gene.get("recommended_experiments", []))
    else:
        notes.append("유전자를 먼저 선택하면 질병 연결성과 추가 실험 제안을 더 구체화할 수 있습니다.")

    if sequence_report:
        if sequence_report["length_nt"] < 300:
            notes.append("입력 서열이 짧아 전체 CDS가 아닐 가능성이 있으므로 full-length CDS 확보를 우선 권장합니다.")
        if not sequence_report["starts_with_atg"]:
            notes.append("서열이 ATG로 시작하지 않아 완전한 coding region이 아닐 수 있습니다.")
        if not sequence_report["ends_with_stop"]:
            notes.append("정상적인 stop codon으로 끝나지 않아 부분 서열 또는 미완성 입력 가능성이 있습니다.")
        if sequence_report["gc_percent"] > 60:
            notes.append("GC 비율이 높은 편이라 PCR primer 설계 시 annealing 조건 최적화가 필요할 수 있습니다.")
        orf = sequence_report["longest_orf"]
        if orf is None:
            notes.append("뚜렷한 ORF가 보이지 않아 비암호화 서열이거나 조각 서열일 수 있습니다.")
        elif orf["length_aa"] < 100:
            notes.append("가장 긴 ORF가 짧아 truncation 또는 부분 입력 가능성을 검토해볼 수 있습니다.")

    if gene and gene["symbol"] == "TCF7L2":
        notes.append("TCF7L2는 비암호화 조절 변이의 영향이 커서 SNP 분석과 발현 비교를 함께 보는 것이 특히 중요합니다.")
    if gene and gene["symbol"] in {"HNF1A", "GCK", "KCNJ11"}:
        notes.append("이 유전자들은 coding variant의 영향이 상대적으로 중요하므로 서열 정렬과 variant annotation이 유용합니다.")

    seen = []
    for note in notes:
        if note not in seen:
            seen.append(note)
    return seen
