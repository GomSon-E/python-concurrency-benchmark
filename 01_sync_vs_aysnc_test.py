"""
비동기 vs 동기 API 호출 성능 비교 테스트
- 무료 공개 API (JSONPlaceholder) 사용
- 수백 개 요청의 성능 차이를 직접 확인
"""

import asyncio
import aiohttp
import requests
import time

# 테스트할 API URL (JSONPlaceholder - 무료 테스트용 API)
BASE_URL = "https://jsonplaceholder.typicode.com"
NUM_REQUESTS = 200  # 요청 수


# ============== 동기 방식 ==============
def sync_fetch(url: str) -> dict:
    """동기 방식으로 단일 API 호출"""
    response = requests.get(url)
    return response.json()


def sync_fetch_all(urls: list[str]) -> list[dict]:
    """동기 방식으로 모든 API 순차 호출"""
    results = []
    for url in urls:
        results.append(sync_fetch(url))
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
    print(f"비동기 vs 동기 API 호출 성능 비교")
    print(f"총 요청 수: {NUM_REQUESTS}개")
    print(f"{'='*60}\n")

    # 1. 비동기 테스트 (먼저 실행 - 더 빠르므로)
    print("[1] 비동기 방식 테스트 중...")
    start = time.perf_counter()
    async_results = asyncio.run(async_fetch_all(urls))
    async_time = time.perf_counter() - start
    print(f"    ✓ 완료: {len(async_results)}개 응답")
    print(f"    ⏱ 소요 시간: {async_time:.2f}초\n")

    # 2. 동기 테스트 (시간이 오래 걸림 - 선택적 실행)
    print("[2] 동기 방식 테스트 중... (오래 걸릴 수 있음)")

    # 동기 테스트는 시간이 오래 걸리므로 일부만 테스트
    sync_test_count = min(20, NUM_REQUESTS)  # 최대 20개만 테스트
    sync_urls = urls[:sync_test_count]

    start = time.perf_counter()
    sync_results = sync_fetch_all(sync_urls)
    sync_time = time.perf_counter() - start
    print(f"    ✓ 완료: {len(sync_results)}개 응답")
    print(f"    ⏱ 소요 시간: {sync_time:.2f}초 ({sync_test_count}개 기준)\n")

    # 결과 비교
    print(f"{'='*60}")
    print("📊 결과 비교")
    print(f"{'='*60}")

    # 동기 방식으로 전체 요청 시 예상 시간 계산
    estimated_sync_time = (sync_time / sync_test_count) * NUM_REQUESTS

    print(f"비동기 ({NUM_REQUESTS}개): {async_time:.2f}초")
    print(f"동기 예상 ({NUM_REQUESTS}개): {estimated_sync_time:.2f}초")
    print(f"\n🚀 비동기가 약 {estimated_sync_time / async_time:.1f}배 빠름!")

    # 샘플 응답 출력
    print(f"\n{'='*60}")
    print("📝 샘플 응답 (첫 번째)")
    print(f"{'='*60}")
    print(async_results[0])


if __name__ == "__main__":
    run_test()
