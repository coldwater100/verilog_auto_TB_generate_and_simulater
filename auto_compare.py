import os
import json

# ------------------------------------------------------------
# 공용 CSV 읽기 (UTF-8)
# ------------------------------------------------------------
def read_csv(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


# ------------------------------------------------------------
# 비교 결과 저장 (개별 compare_caseN.txt)
# ------------------------------------------------------------
def save_compare_result(case_id, is_equal, zero_x_mismatch_list, error_msg, output_dir="results"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = os.path.join(output_dir, f"compare_case{case_id}.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"=== Compare Result for CASE {case_id} ===\n\n")

        if error_msg:
            f.write(f"[FAIL] {error_msg}\n")
            return

        if is_equal:
            f.write("[PASS] Golden CSV와 RTL CSV가 동일합니다 (0↔x 허용)\n")

            if zero_x_mismatch_list:
                f.write("\n※ 0과 x가 치환된 항목 목록:\n")
                for (line, g, r) in zero_x_mismatch_list:
                    f.write(f"  line {line}: golden={g}, rtl={r}\n")
            else:
                f.write("\n0-x 치환 항목 없음.\n")
        else:
            f.write("[FAIL] CSV mismatch detected.\n")

    print(f"[+] 결과 저장: {filename}")


# ------------------------------------------------------------
# CSV 비교 (UTF-8 안전)
# ------------------------------------------------------------
def compare_csv(golden_lines, rtl_lines, case_id, output_dir="results"):
    if golden_lines is None or rtl_lines is None:
        save_compare_result(case_id, False, [], "파일 누락", output_dir)
        return False, "파일 누락", []

    if len(golden_lines) != len(rtl_lines):
        save_compare_result(case_id, False, [], "CSV 라인 수가 다름", output_dir)
        return False, "CSV 라인 수 다름", []

    zero_x_mismatch = []

    for idx, (g, r) in enumerate(zip(golden_lines, rtl_lines)):
        g = g.strip()
        r = r.strip()

        # header
        if idx == 0:
            if g.lower().startswith("cycle") and r.lower().startswith("cycle"):
                continue
            err = f"Header mismatch at line {idx}"
            save_compare_result(case_id, False, [], err, output_dir)
            return False, err, []

        try:
            _, g_val = g.split(",")
            _, r_val = r.split(",")
        except:
            err = f"Invalid CSV format at line {idx}"
            save_compare_result(case_id, False, [], err, output_dir)
            return False, err, []

        g_val = g_val.strip()
        r_val = r_val.strip()

        if len(g_val) != len(r_val):
            err = f"Length mismatch at line {idx}"
            save_compare_result(case_id, False, [], err, output_dir)
            return False, err, []

        equal = True
        for c1, c2 in zip(g_val, r_val):
            if c1 == c2:
                continue
            if (c1 == '0' and c2 == 'x') or (c1 == 'x' and c2 == '0'):
                continue
            equal = False
            break

        if not equal:
            err = f"Mismatch at line {idx}"
            save_compare_result(case_id, False, [], err, output_dir)
            return False, err, []

        if g_val != r_val:
            zero_x_mismatch.append((idx, g_val, r_val))

    save_compare_result(case_id, True, zero_x_mismatch, None, output_dir)
    return True, None, zero_x_mismatch


# ------------------------------------------------------------
# config_caseN.json 읽기
# ------------------------------------------------------------
def load_all_configs(results_dir="results"):
    configs = []
    for fname in os.listdir(results_dir):
        if fname.startswith("config_case") and fname.endswith(".json"):
            full = os.path.join(results_dir, fname)
            with open(full, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                configs.append(cfg)

    configs.sort(key=lambda x: x["case_id"])
    return configs


# ------------------------------------------------------------
# 통합 로그(summary log) 저장
# ------------------------------------------------------------
def save_summary_log(summary_list, output_dir="results", filename="compare_summary.txt"):
    path = os.path.join(output_dir, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write("========== Compare Summary ==========\n\n")

        for item in summary_list:
            case_id, ok, errmsg, zx_count = item

            if ok:
                f.write(f"CASE {case_id}: PASS (0-x mismatch {zx_count}개)\n")
            else:
                f.write(f"CASE {case_id}: FAIL - {errmsg}\n")

        f.write("\n=====================================\n")
        passed = sum(1 for x in summary_list if x[1])
        total = len(summary_list)
        f.write(f"총 결과: {passed}/{total} PASS\n")

    print(f"[+] 통합 로그 저장: {path}")


# ------------------------------------------------------------
# 메인
# ------------------------------------------------------------
def main():
    print("[+] auto_compare 시작 (UTF-8 mode)\n")

    configs = load_all_configs()
    print(f"[+] 발견된 config 파일: {len(configs)}\n")

    summary = []

    total = len(configs)
    passed = 0

    for cfg in configs:
        case_id = cfg["case_id"]

        golden_path = f"results/golden_case{case_id}.csv"
        rtl_path    = f"results/csv_result_case{case_id}.csv"

        print(f"[CASE {case_id}] Comparing:")
        print(f"   golden: {golden_path}")
        print(f"   rtl   : {rtl_path}")

        golden_lines = read_csv(golden_path)
        rtl_lines    = read_csv(rtl_path)

        ok, errmsg, zx_list = compare_csv(golden_lines, rtl_lines, case_id)

        if ok:
            print("   → PASS\n")
            passed += 1
            summary.append((case_id, True, None, len(zx_list)))
        else:
            print("   → FAIL\n")
            summary.append((case_id, False, errmsg, 0))

    print("========================================")
    print(f"전체 결과: {passed}/{total} CASE PASS")
    print("========================================")

    # ★ 통합 로그 작성 ★
    save_summary_log(summary)


# ------------------------------------------------------------
# 실행부
# ------------------------------------------------------------
if __name__ == "__main__":
    main()
