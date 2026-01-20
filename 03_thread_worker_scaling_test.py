"""
멀티스레드 워커 수 증가에 따른 성능 변화 테스트
- 워커 수를 늘려가며 수확체감 현상 확인
- 비동기와 비교하여 한계점 파악
"""

import asyncio
import aiohttp
import requests
import time
import tracemalloc
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed

# 테스트 설정
BASE_URL = "https://jsonplaceholder.typicode.com"
NUM_REQUESTS = 200  # 요청 수 (테스트 시간 단축을 위해 200개)
WORKER_COUNTS = [50, 100, 200, 1000]  # 테스트할 워커 수


# ============== 멀티스레드 방식 ==============
def thread_fetch(url: str) -> dict:
    """스레드에서 단일 API 호출"""
    response = requests.get(url)
    return response.json()


def thread_fetch_all(urls: list[str], max_workers: int) -> list[dict]:
    """멀티스레드 방식으로 모든 API 동시 호출"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(thread_fetch, url): url for url in urls}
        for future in as_completed(future_to_url):
            results.append(future.result())
    return results


# ============== 비동기 방식 ==============
async def async_fetch(session: aiohttp.ClientSession, url: str) -> dict:
    """비동기 방식으로 단일 API 호출"""
    async with session.get(url) as response:
        return await response.json()


async def async_fetch_all(urls: list[str]) -> list[dict]:
    """비동기 방식으로 모든 API 동시 호출"""
    headers = {"Accept-Encoding": "gzip, deflate"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [async_fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    return results


# ============== 테스트 실행 ==============
def run_test():
    # URL 목록 생성
    urls = []
    for i in range(1, NUM_REQUESTS + 1):
        if i % 3 == 0:
            urls.append(f"{BASE_URL}/posts/{(i % 100) + 1}")
        elif i % 3 == 1:
            urls.append(f"{BASE_URL}/comments/{(i % 500) + 1}")
        else:
            urls.append(f"{BASE_URL}/todos/{(i % 200) + 1}")

    print(f"{'='*70}")
    print(f"멀티스레드 워커 수 증가에 따른 성능 변화 테스트")
    print(f"총 요청 수: {NUM_REQUESTS}개")
    print(f"테스트 워커 수: {WORKER_COUNTS}")
    print(f"{'='*70}\n")

    results = []

    # 1. 비동기 테스트 (기준점)
    print("[기준] 비동기 방식 테스트 중...")
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    asyncio.run(async_fetch_all(urls))
    async_time = time.perf_counter() - start
    _, async_memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"       ✓ 완료: {async_time:.2f}초 | 피크 메모리: {async_memory_peak / 1024 / 1024:.2f}MB\n")

    # 2. 워커 수별 멀티스레드 테스트
    for workers in WORKER_COUNTS:
        print(f"[워커 {workers:3d}개] 멀티스레드 테스트 중...")
        gc.collect()
        tracemalloc.start()
        start = time.perf_counter()

        try:
            thread_fetch_all(urls, workers)
            elapsed = time.perf_counter() - start
            _, memory_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            ratio = elapsed / async_time
            results.append({
                "workers": workers,
                "time": elapsed,
                "memory": memory_peak,
                "ratio": ratio
            })
            print(f"           ✓ 완료: {elapsed:.2f}초 | 피크 메모리: {memory_peak / 1024 / 1024:.2f}MB | 비동기 대비 {ratio:.2f}배\n")
        except Exception as e:
            tracemalloc.stop()
            print(f"           ✗ 실패: {e}\n")
            results.append({
                "workers": workers,
                "time": None,
                "memory": None,
                "ratio": None
            })

    # 결과 요약
    print(f"{'='*70}")
    print("📊 결과 요약")
    print(f"{'='*70}")
    print(f"\n{'워커 수':^10} | {'소요 시간':^12} | {'피크 메모리':^12} | {'비동기 대비':^12}")
    print("-" * 55)
    print(f"{'비동기':^10} | {async_time:^10.2f}초 | {async_memory_peak / 1024 / 1024:^10.2f}MB | {'1.00x (기준)':^12}")
    print("-" * 55)

    for r in results:
        if r["time"]:
            print(f"{r['workers']:^10} | {r['time']:^10.2f}초 | {r['memory'] / 1024 / 1024:^10.2f}MB | {r['ratio']:^10.2f}x")
        else:
            print(f"{r['workers']:^10} | {'실패':^10} | {'-':^10} | {'-':^10}")

    # 분석
    print(f"\n{'='*70}")
    print("📈 분석")
    print(f"{'='*70}")

    if len(results) >= 2 and results[-1]["time"] and results[-2]["time"]:
        # 워커 증가 대비 성능 향상률 계산
        first = results[0]
        last = results[-1]
        worker_increase = last["workers"] / first["workers"]
        time_improvement = first["time"] / last["time"] if last["time"] else 0

        print(f"워커 수 {first['workers']} → {last['workers']} ({worker_increase:.1f}배 증가)")
        print(f"속도 향상: {time_improvement:.2f}배 (이상적이라면 {worker_increase:.1f}배)")
        print(f"효율성: {(time_improvement / worker_increase) * 100:.1f}%")

        if time_improvement < worker_increase * 0.5:
            print("\n⚠️  수확체감 현상 발생! 워커 수 증가 대비 성능 향상이 크지 않음")

        # 비동기와 동등해지는 지점 확인
        for r in results:
            if r["time"] and r["time"] <= async_time * 1.2:  # 20% 오차 허용
                print(f"\n✅ 워커 {r['workers']}개에서 비동기와 유사한 성능 달성")
                print(f"   하지만 메모리는 {r['memory'] / async_memory_peak:.1f}배 더 사용")
                break
        else:
            print(f"\n❌ 테스트한 워커 수 범위 내에서 비동기 성능에 도달하지 못함")


if __name__ == "__main__":
    run_test()
