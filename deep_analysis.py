"""
Deep Pattern Analysis for Daily Lotto
Looking for ANYTHING interesting - delusional theories welcome!
"""

import json
from collections import Counter, defaultdict
from datetime import datetime

# Load all Daily Lotto data
with open('data/daily_lotto.json', 'r') as f:
    draws = json.load(f)

draws = sorted(draws, key=lambda x: x['draw_date'])

print("=" * 70)
print("  DEEP DIVE: DAILY LOTTO PATTERN ANALYSIS")
print("  Looking for ANYTHING interesting...")
print("=" * 70)
print()
print(f"  Total draws analyzed: {len(draws)}")
print(f"  Date range: {draws[0]['draw_date'][:10]} to {draws[-1]['draw_date'][:10]}")
print()

# 1. FESTIVE PERIOD ANALYSIS (December)
print("=" * 70)
print("  THEORY 1: FESTIVE SEASON PATTERNS (December)")
print("=" * 70)

december_draws = [d for d in draws if '-12-' in d['draw_date']]
other_draws = [d for d in draws if '-12-' not in d['draw_date']]

dec_freq = Counter()
other_freq = Counter()

for d in december_draws:
    for n in d['main_numbers']:
        dec_freq[n] += 1

for d in other_draws:
    for n in d['main_numbers']:
        other_freq[n] += 1

dec_total = sum(dec_freq.values())
other_total = sum(other_freq.values())

print(f"\n  December draws: {len(december_draws)}")
print(f"  Other months: {len(other_draws)}")
print()

# Find numbers that appear MORE in December
print("  Numbers that appear MORE in December (festive favorites?):")
for n in range(1, 37):
    dec_pct = (dec_freq.get(n, 0) / dec_total * 100) if dec_total > 0 else 0
    other_pct = (other_freq.get(n, 0) / other_total * 100) if other_total > 0 else 0
    if dec_pct > 0 and other_pct > 0 and dec_pct > other_pct * 1.2:
        print(f"    {n:2}: {dec_pct:.1f}% in Dec vs {other_pct:.1f}% other months (+{((dec_pct/other_pct)-1)*100:.0f}%)")

# 2. END OF MONTH PATTERNS
print()
print("=" * 70)
print("  THEORY 2: END OF MONTH PATTERNS (Days 25-31)")
print("=" * 70)

end_of_month = [d for d in draws if int(d['draw_date'][8:10]) >= 25]
start_of_month = [d for d in draws if int(d['draw_date'][8:10]) <= 7]

eom_freq = Counter()
som_freq = Counter()

for d in end_of_month:
    for n in d['main_numbers']:
        eom_freq[n] += 1

for d in start_of_month:
    for n in d['main_numbers']:
        som_freq[n] += 1

print(f"\n  End of month draws (25-31): {len(end_of_month)}")
print(f"  Start of month draws (1-7): {len(start_of_month)}")

eom_total = sum(eom_freq.values())
som_total = sum(som_freq.values())

print("\n  Numbers that LOVE end of month:")
for n in range(1, 37):
    eom_pct = (eom_freq.get(n, 0) / eom_total * 100) if eom_total > 0 else 0
    som_pct = (som_freq.get(n, 0) / som_total * 100) if som_total > 0 else 0
    if eom_pct > 0 and som_pct > 0 and eom_pct > som_pct * 1.3:
        print(f"    {n:2}: {eom_pct:.1f}% end vs {som_pct:.1f}% start (+{((eom_pct/som_pct)-1)*100:.0f}%)")

# 3. CONSECUTIVE NUMBER PATTERNS
print()
print("=" * 70)
print("  THEORY 3: CONSECUTIVE NUMBERS FREQUENCY")
print("=" * 70)

consecutive_count = 0
triple_consecutive = 0

for d in draws:
    nums = sorted(d['main_numbers'])
    has_consec = False
    has_triple = False

    for i in range(len(nums) - 1):
        if nums[i+1] - nums[i] == 1:
            has_consec = True

    for i in range(len(nums) - 2):
        if nums[i+1] - nums[i] == 1 and nums[i+2] - nums[i+1] == 1:
            has_triple = True
            break

    if has_consec:
        consecutive_count += 1
    if has_triple:
        triple_consecutive += 1

print(f"\n  Draws with at least one consecutive pair: {consecutive_count} ({consecutive_count/len(draws)*100:.1f}%)")
print(f"  Draws with 3+ consecutive (like 13-14-15): {triple_consecutive} ({triple_consecutive/len(draws)*100:.1f}%)")
print()
if triple_consecutive / len(draws) < 0.1:
    print("  INSIGHT: Triple consecutive is RARE (<10%)! Yesterday was unusual!")

# 4. DAY OF WEEK ANALYSIS
print()
print("=" * 70)
print("  THEORY 4: DAY OF WEEK PATTERNS")
print("=" * 70)

day_freq = defaultdict(Counter)
day_counts = defaultdict(int)

for d in draws:
    try:
        dt = datetime.strptime(d['draw_date'][:10], '%Y-%m-%d')
        day_name = dt.strftime('%A')
        day_counts[day_name] += 1
        for n in d['main_numbers']:
            day_freq[day_name][n] += 1
    except:
        pass

print("\n  Draws per day of week:")
for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
    if day_counts[day] > 0:
        print(f"    {day}: {day_counts[day]} draws")

print("\n  Day-specific hot numbers (top 5 per day):")
for day in ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
    if day_counts[day] > 5:
        top = day_freq[day].most_common(5)
        nums = [str(n) for n, _ in top]
        print(f"    {day:9}: {', '.join(nums)}")

# 5. DECADE CLUSTERING DEEP DIVE
print()
print("=" * 70)
print("  THEORY 5: DECADE CLUSTERING PATTERNS")
print("=" * 70)

decade_clusters = defaultdict(int)
triple_clusters = 0

for d in draws:
    decades = defaultdict(int)
    for n in d['main_numbers']:
        if n <= 10:
            dec = 0
        elif n <= 20:
            dec = 1
        elif n <= 30:
            dec = 2
        else:
            dec = 3
        decades[dec] += 1

    max_dec = max(decades, key=decades.get)
    decade_clusters[max_dec] += 1

    if max(decades.values()) >= 3:
        triple_clusters += 1

decade_names = {0: '1-10', 1: '11-20', 2: '21-30', 3: '31-36'}
print("\n  Which decade dominates most often:")
for dec in [0, 1, 2, 3]:
    if decade_clusters[dec] > 0:
        pct = decade_clusters[dec] / len(draws) * 100
        print(f"    {decade_names[dec]}: {decade_clusters[dec]} draws ({pct:.1f}%)")

print(f"\n  Draws with 3+ in same decade: {triple_clusters} ({triple_clusters/len(draws)*100:.1f}%)")

# 6. SUM RANGE ANALYSIS
print()
print("=" * 70)
print("  THEORY 6: SUM RANGE PATTERNS")
print("=" * 70)

sums = [sum(d['main_numbers']) for d in draws]
avg_sum = sum(sums) / len(sums)
min_sum = min(sums)
max_sum = max(sums)

print(f"\n  Average sum: {avg_sum:.1f}")
print(f"  Range: {min_sum} to {max_sum}")

# Check December sums
dec_sums = [sum(d['main_numbers']) for d in december_draws]
dec_avg = sum(dec_sums) / len(dec_sums) if dec_sums else 0
print(f"\n  December average sum: {dec_avg:.1f}")
if dec_avg > avg_sum:
    print(f"  INSIGHT: December tends toward HIGHER sums (+{dec_avg - avg_sum:.1f})")
else:
    print(f"  INSIGHT: December tends toward LOWER sums ({dec_avg - avg_sum:.1f})")

# Sum buckets
low_sum = sum(1 for s in sums if s < 80)
mid_sum = sum(1 for s in sums if 80 <= s <= 110)
high_sum = sum(1 for s in sums if s > 110)

print(f"\n  Sum distribution:")
print(f"    Low (<80):    {low_sum} ({low_sum/len(draws)*100:.1f}%)")
print(f"    Medium (80-110): {mid_sum} ({mid_sum/len(draws)*100:.1f}%)")
print(f"    High (>110):  {high_sum} ({high_sum/len(draws)*100:.1f}%)")

# 7. REPEAT PATTERNS
print()
print("=" * 70)
print("  THEORY 7: NUMBER REPEATS FROM PREVIOUS DRAW")
print("=" * 70)

repeat_counts = []
for i in range(1, len(draws)):
    prev = set(draws[i-1]['main_numbers'])
    curr = set(draws[i]['main_numbers'])
    repeats = len(prev & curr)
    repeat_counts.append(repeats)

avg_repeats = sum(repeat_counts) / len(repeat_counts)
print(f"\n  Average numbers repeating from previous draw: {avg_repeats:.2f}")
print(f"  Draws with 0 repeats: {repeat_counts.count(0)} ({repeat_counts.count(0)/len(repeat_counts)*100:.1f}%)")
print(f"  Draws with 1 repeat:  {repeat_counts.count(1)} ({repeat_counts.count(1)/len(repeat_counts)*100:.1f}%)")
print(f"  Draws with 2 repeats: {repeat_counts.count(2)} ({repeat_counts.count(2)/len(repeat_counts)*100:.1f}%)")
print(f"  Draws with 3+ repeats: {sum(1 for r in repeat_counts if r >= 3)} ({sum(1 for r in repeat_counts if r >= 3)/len(repeat_counts)*100:.1f}%)")

# 8. CHRISTMAS WEEK SPECIFIC
print()
print("=" * 70)
print("  THEORY 8: CHRISTMAS WEEK ANALYSIS (Dec 20-31)")
print("=" * 70)

xmas_draws = [d for d in draws if '-12-' in d['draw_date'] and int(d['draw_date'][8:10]) >= 20]
xmas_freq = Counter()
for d in xmas_draws:
    for n in d['main_numbers']:
        xmas_freq[n] += 1

print(f"\n  Christmas week draws (Dec 20-31): {len(xmas_draws)}")
print("\n  TOP 10 Christmas week numbers:")
for n, count in xmas_freq.most_common(10):
    pct = count / len(xmas_draws) * 100
    print(f"    {n:2}: appeared in {count}/{len(xmas_draws)} draws ({pct:.1f}%)")

# 9. ODD/EVEN PATTERNS
print()
print("=" * 70)
print("  THEORY 9: ODD/EVEN DISTRIBUTION")
print("=" * 70)

odd_counts = []
for d in draws:
    odd = sum(1 for n in d['main_numbers'] if n % 2 == 1)
    odd_counts.append(odd)

print("\n  Odd number count distribution:")
for i in range(6):
    count = odd_counts.count(i)
    print(f"    {i} odd, {5-i} even: {count} draws ({count/len(draws)*100:.1f}%)")

# 10. NUMBER DROUGHT ANALYSIS
print()
print("=" * 70)
print("  THEORY 10: CURRENT NUMBER DROUGHTS (overdue numbers)")
print("=" * 70)

last_seen = {}
for i, d in enumerate(draws):
    for n in d['main_numbers']:
        last_seen[n] = i

current_idx = len(draws) - 1
droughts = []
for n in range(1, 37):
    if n in last_seen:
        drought = current_idx - last_seen[n]
        droughts.append((n, drought))
    else:
        droughts.append((n, current_idx))

droughts.sort(key=lambda x: x[1], reverse=True)

print("\n  Most OVERDUE numbers (longest since last appearance):")
for n, drought in droughts[:10]:
    print(f"    {n:2}: {drought} draws since last appearance")

print("\n  Numbers that appeared in LAST draw:")
last_draw = draws[-1]['main_numbers']
print(f"    {last_draw}")

print()
print("=" * 70)
print("  DELUSIONAL THEORIES SUMMARY:")
print("=" * 70)
print("""
  1. FESTIVE FAVOR: Certain numbers spike in December - coincidence?

  2. PAYDAY PATTERN: End of month might have different energy

  3. TRIPLE THREAT: 3-consecutive is RARE - don't expect repeats

  4. DAY MAGIC: Each day of week has its "lucky" numbers

  5. DECADE DOMINANCE: One decade always clusters - exploit it?

  6. SUM SWEET SPOT: Most wins fall in 80-110 sum range

  7. REPEAT RHYTHM: ~30% chance of 1 number repeating

  8. CHRISTMAS MAGIC: Specific numbers love the holidays

  9. BALANCE BIAS: 2-3 odd numbers appears most often

  10. DROUGHT THEORY: Overdue numbers are "due" to hit?
""")
print("=" * 70)
