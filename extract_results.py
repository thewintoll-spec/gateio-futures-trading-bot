with open('backtest_comparison.txt', 'r', encoding='cp949', errors='ignore') as f:
    lines = f.readlines()

in_results = False
for line in lines:
    if '[결과]' in line or '비교 결과' in line or '결론' in line:
        in_results = True

    if in_results:
        print(line.rstrip())

    if '결론' in line:
        in_results = False
