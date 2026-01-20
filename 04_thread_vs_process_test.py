"""
멀티스레드 vs 멀티프로세스 CPU 바운드 작업 성능 비교
- CPU 집약적 작업에서 GIL의 영향 확인
- 멀티프로세스의 진정한 병렬 처리 성능 비교
"""

import time
import tracemalloc
import gc
import math
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import multiprocessing

# 테스트 설정
NUM_TASKS = 100  # 작업 수
COMPLEXITY = 50000  # 연산 복잡도 (소수 계산 범위)


# ============== CPU 바운드 작업 ==============
def cpu_intensive_task(n: int) -> dict:
    """
    CPU 집약적 작업: 소수 개수 계산
    - 순수 CPU 연산만 사용
    - I/O 없음
    """
    count = 0
    for num in range(2, n):
        if is_prime(num):
            count += 1
    return {"range": n, "prime_count": count}


def is_prime(n: int) -> bool:
    """소수 판별"""
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True


# ============== 동기 방식 (기준) ==============
def sync_run(tasks: list[int]) -> list[dict]:
    """동기 방식으로 순차 실행"""
    results = []
    for task in tasks:
        results.append(cpu_intensive_task(task))
    return results


# ============== 멀티스레드 방식 ==============
def thread_run(tasks: list[int], max_workers: int) -> list[dict]:
    """멀티스레드 방식으로 실행"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(cpu_intensive_task, task): task for task in tasks}
        for future in as_completed(futures):
            results.append(future.result())
    return results


# ============== 멀티프로세스 방식 ==============
def process_run(tasks: list[int], max_workers: int) -> list[dict]:
    """멀티프로세스 방식으로 실행"""
    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(cpu_intensive_task, task): task for task in tasks}
        for future in as_completed(futures):
            results.append(future.result())
    return results


# ============== 테스트 실행 ==============
def run_test():
    # CPU 코어 수 확인
    cpu_count = multiprocessing.cpu_count()

    # 작업 목록 생성 (각기 다른 복잡도)
    tasks = [COMPLEXITY + (i * 1000) for i in range(NUM_TASKS)]

    print(f"{'='*70}")
    print(f"멀티스레드 vs 멀티프로세스 CPU 바운드 성능 비교")
    print(f"{'='*70}")
    print(f"CPU 코어 수: {cpu_count}개")
    print(f"작업 수: {NUM_TASKS}개")
    print(f"연산 복잡도: {COMPLEXITY} ~ {COMPLEXITY + NUM_TASKS * 1000} 범위 소수 계산")
    print(f"{'='*70}\n")

    results_summary = []

    # 1. 동기 방식 (기준)
    print("[1] 동기 방식 (순차 실행) 테스트 중...")
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    sync_run(tasks)
    sync_time = time.perf_counter() - start
    _, sync_memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"    ✓ 완료: {sync_time:.2f}초 | 피크 메모리: {sync_memory_peak / 1024 / 1024:.2f}MB\n")
    results_summary.append(("동기 (순차)", sync_time, sync_memory_peak, 1.0))

    # 2. 멀티스레드 테스트
    print(f"[2] 멀티스레드 방식 ({cpu_count} workers) 테스트 중...")
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    thread_run(tasks, cpu_count)
    thread_time = time.perf_counter() - start
    _, thread_memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    thread_speedup = sync_time / thread_time
    print(f"    ✓ 완료: {thread_time:.2f}초 | 피크 메모리: {thread_memory_peak / 1024 / 1024:.2f}MB")
    print(f"    📈 동기 대비 {thread_speedup:.2f}배 속도\n")
    results_summary.append(("멀티스레드", thread_time, thread_memory_peak, thread_speedup))

    # 3. 멀티프로세스 테스트
    print(f"[3] 멀티프로세스 방식 ({cpu_count} workers) 테스트 중...")
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    process_run(tasks, cpu_count)
    process_time = time.perf_counter() - start
    _, process_memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    process_speedup = sync_time / process_time
    print(f"    ✓ 완료: {process_time:.2f}초 | 피크 메모리: {process_memory_peak / 1024 / 1024:.2f}MB")
    print(f"    📈 동기 대비 {process_speedup:.2f}배 속도\n")
    results_summary.append(("멀티프로세스", process_time, process_memory_peak, process_speedup))

    # 결과 요약
    print(f"{'='*70}")
    print("📊 결과 요약")
    print(f"{'='*70}")
    print(f"\n{'방식':^15} | {'소요 시간':^12} | {'피크 메모리':^12} | {'속도 향상':^12}")
    print("-" * 60)
    for name, elapsed, memory, speedup in results_summary:
        print(f"{name:^15} | {elapsed:^10.2f}초 | {memory / 1024 / 1024:^10.2f}MB | {speedup:^10.2f}x")

    # 분석
    print(f"\n{'='*70}")
    print("📈 분석")
    print(f"{'='*70}")

    print(f"""
┌────────────────────────────────────────────────────────────────────┐
│                         GIL (Global Interpreter Lock)              │
├────────────────────────────────────────────────────────────────────┤
│  Python의 GIL은 한 번에 하나의 스레드만 Python 바이트코드 실행      │
│                                                                    │
│  • 멀티스레드: GIL로 인해 CPU 작업은 실제로 병렬 실행 안 됨         │
│    → 스레드 전환 오버헤드만 추가되어 오히려 느려질 수 있음          │
│                                                                    │
│  • 멀티프로세스: 각 프로세스가 독립적인 GIL 보유                    │
│    → 진정한 병렬 실행 가능, CPU 코어 수만큼 성능 향상               │
└────────────────────────────────────────────────────────────────────┘
""")

    # 이론적 최대 속도 향상
    print(f"이론적 최대 속도 향상 (코어 수): {cpu_count}배")
    print(f"멀티스레드 실제 속도 향상: {thread_speedup:.2f}배 (효율: {thread_speedup / cpu_count * 100:.1f}%)")
    print(f"멀티프로세스 실제 속도 향상: {process_speedup:.2f}배 (효율: {process_speedup / cpu_count * 100:.1f}%)")

    if thread_speedup < 1.5:
        print("\n⚠️  멀티스레드는 CPU 바운드 작업에서 거의 효과 없음 (GIL 때문)")

    if process_speedup > thread_speedup * 1.5:
        print(f"✅ 멀티프로세스가 멀티스레드보다 {process_speedup / thread_speedup:.1f}배 빠름!")

    # 사용 가이드
    print(f"\n{'='*70}")
    print("💡 사용 가이드")
    print(f"{'='*70}")
    print("""
┌─────────────┬──────────────────┬──────────────────┐
│   작업 유형  │    권장 방식      │      이유        │
├─────────────┼──────────────────┼──────────────────┤
│ I/O 바운드  │ 비동기 (asyncio) │ 가장 효율적      │
│ (API 호출)  │ 또는 멀티스레드  │ GIL 영향 적음    │
├─────────────┼──────────────────┼──────────────────┤
│ CPU 바운드  │ 멀티프로세스     │ GIL 우회         │
│ (연산 집약) │ (ProcessPool)    │ 진정한 병렬 처리 │
└─────────────┴──────────────────┴──────────────────┘
""")


if __name__ == "__main__":
    run_test()
