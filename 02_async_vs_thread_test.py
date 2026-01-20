"""
비동기 vs 멀티스레드 API 호출 성능 비교 테스트
- 무료 공개 API (JSONPlaceholder) 사용
- 수백 개 요청의 성능 차이를 직접 확인
"""

import asyncio
import aiohttp
import requests
import time
import tracemalloc
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed

# 테스트할 API URL (JSONPlaceholder - 무료 테스트용 API)
BASE_URL = "https://jsonplaceholder.typicode.com"
NUM_REQUESTS = 200  # 요청 수
MAX_WORKERS = 50  # 스레드 풀 최대 워커 수


# ============== 멀티스레드 방식 ==============
def thread_fetch(url: str) -> dict:
    """스레드에서 단일 API 호출"""
    response = requests.get(url)
    return response.json()


def thread_fetch_all(urls: list[str]) -> list[dict]:
    """멀티스레드 방식으로 모든 API 동시 호출"""
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 모든 URL에 대해 스레드 작업 제출
        future_to_url = {executor.submit(thread_fetch, url): url for url in urls}

        # 완료된 순서대로 결과 수집
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
    # brotli 압축 문제 방지를 위해 Accept-Encoding 헤더 설정
    headers = {"Accept-Encoding": "gzip, deflate"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [async_fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    return results


# ============== 테스트 실행 ==============
def run_test():
    # 테스트용 URL 목록 생성 (posts, comments, todos 등 다양한 엔드포인트)
    urls = []
    for i in range(1, NUM_REQUESTS + 1):
        # 다양한 엔드포인트 순환 사용
        if i % 3 == 0:
            urls.append(f"{BASE_URL}/posts/{(i % 100) + 1}")
        elif i % 3 == 1:
            urls.append(f"{BASE_URL}/comments/{(i % 500) + 1}")
        else:
            urls.append(f"{BASE_URL}/todos/{(i % 200) + 1}")

    print(f"{'='*60}")
    print(f"비동기 vs 멀티스레드 API 호출 성능 비교")
    print(f"총 요청 수: {NUM_REQUESTS}개")
    print(f"스레드 풀 워커 수: {MAX_WORKERS}개")
    print(f"{'='*60}\n")

    # 1. 비동기 테스트
    print("[1] 비동기 방식 테스트 중...")
    gc.collect()  # 가비지 컬렉션으로 메모리 정리
    tracemalloc.start()
    start = time.perf_counter()
    async_results = asyncio.run(async_fetch_all(urls))
    async_time = time.perf_counter() - start
    async_memory_current, async_memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"    ✓ 완료: {len(async_results)}개 응답")
    print(f"    ⏱ 소요 시간: {async_time:.2f}초")
    print(f"    💾 메모리: 현재 {async_memory_current / 1024 / 1024:.2f}MB, 피크 {async_memory_peak / 1024 / 1024:.2f}MB\n")

    # 2. 멀티스레드 테스트
    print("[2] 멀티스레드 방식 테스트 중...")
    gc.collect()  # 가비지 컬렉션으로 메모리 정리
    tracemalloc.start()
    start = time.perf_counter()
    thread_results = thread_fetch_all(urls)
    thread_time = time.perf_counter() - start
    thread_memory_current, thread_memory_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"    ✓ 완료: {len(thread_results)}개 응답")
    print(f"    ⏱ 소요 시간: {thread_time:.2f}초")
    print(f"    💾 메모리: 현재 {thread_memory_current / 1024 / 1024:.2f}MB, 피크 {thread_memory_peak / 1024 / 1024:.2f}MB\n")

    # 결과 비교
    print(f"{'='*60}")
    print("📊 결과 비교")
    print(f"{'='*60}")
    print(f"비동기 (asyncio + aiohttp): {async_time:.2f}초 | 피크 메모리: {async_memory_peak / 1024 / 1024:.2f}MB")
    print(f"멀티스레드 (ThreadPool):    {thread_time:.2f}초 | 피크 메모리: {thread_memory_peak / 1024 / 1024:.2f}MB")

    # 승자 표시
    print()
    # 시간 비교
    if async_time < thread_time:
        ratio = thread_time / async_time
        print(f"⏱ 속도: 비동기가 약 {ratio:.2f}배 빠름!")
    else:
        ratio = async_time / thread_time
        print(f"⏱ 속도: 멀티스레드가 약 {ratio:.2f}배 빠름!")

    # 메모리 비교
    if async_memory_peak < thread_memory_peak:
        ratio = thread_memory_peak / async_memory_peak
        print(f"💾 메모리: 비동기가 약 {ratio:.2f}배 적게 사용!")
    else:
        ratio = async_memory_peak / thread_memory_peak
        print(f"💾 메모리: 멀티스레드가 약 {ratio:.2f}배 적게 사용!")

    # 샘플 응답 출력
    print(f"{'='*60}")
    print("📝 샘플 응답 (첫 번째)")
    print(f"{'='*60}")
    print(async_results[0])


if __name__ == "__main__":
    run_test()
