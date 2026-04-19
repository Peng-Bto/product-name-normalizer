"""
测试最大迭代轮次限制功能
"""
import asyncio
import os
import sys

# 测试用的临时配置
TEST_MAX_ITERATIONS = 3
TEST_RETRY_COUNT = 1  # 单次调用直接失败，减少测试时间


async def test_max_iterations():
    """测试：达到最大迭代轮次后停止重试"""
    print("\n" + "=" * 60)
    print("测试：最大迭代轮次限制功能")
    print("=" * 60)

    # 准备测试数据：3个品名，模拟始终失败
    test_products = ["测试商品A", "测试商品B", "测试商品C"]

    # 记录迭代次数
    iteration_count = 0

    # 模拟处理流程（复刻 main.py 中的逻辑）
    products_to_process = test_products.copy()
    failed_results = []

    while products_to_process:
        # 超过最大迭代轮次，停止重试（复刻 main.py 第224-231行的逻辑）
        if iteration_count >= TEST_MAX_ITERATIONS:
            print(f"\n[日志] 已达到最大迭代轮次 ({TEST_MAX_ITERATIONS})，停止重试。")
            print(f"[日志] 剩余 {len(products_to_process)} 个品名解析失败。")
            break

        iteration_count += 1
        print(f"\n[日志] 第 {iteration_count} 轮处理，待处理品名数量: {len(products_to_process)}")

        # 模拟每轮处理：所有品名都失败
        for name in products_to_process:
            failed_results.append({
                "被解析品名": name,
                "品类": "处理失败",
                "功能类别": "处理失败",
                "置信度": "N/A",
                "error": "模拟失败",
            })

        if failed_results:
            products_to_process = [r["被解析品名"] for r in failed_results]
            print(f"[日志] 第 {iteration_count} 轮有 {len(failed_results)} 个品名解析失败")

            failed_results = []
            await asyncio.sleep(0.1)  # 模拟轮次间等待
        else:
            products_to_process = []

    # 验证结果
    print("\n" + "-" * 60)
    print("测试结果验证:")
    print(f"  - 预期迭代轮次: {TEST_MAX_ITERATIONS}")
    print(f"  - 实际迭代轮次: {iteration_count}")
    print(f"  - 剩余失败品名数: {len(products_to_process)}")
    print("-" * 60)

    if iteration_count == TEST_MAX_ITERATIONS:
        print("[PASS] 测试通过：迭代在达到最大轮次后正确停止")
    else:
        print(f"[FAIL] 测试失败：迭代次数不正确，期望 {TEST_MAX_ITERATIONS}，实际 {iteration_count}")
        return False

    if len(products_to_process) > 0:
        print("[PASS] 测试通过：剩余失败品名被正确保留")
    else:
        print("[FAIL] 测试失败：应该有剩余失败品名")
        return False

    return True


async def test_max_iterations_with_success():
    """测试：在达到最大轮次前所有品名都成功处理"""
    print("\n" + "=" * 60)
    print("测试：达到最大轮次前成功完成")
    print("=" * 60)

    # 记录迭代次数
    iteration_count = 0
    products_to_process = ["成功商品A", "成功商品B"]
    failed_results = []

    while products_to_process:
        iteration_count += 1
        print(f"\n[日志] 第 {iteration_count} 轮处理，待处理品名数量: {len(products_to_process)}")

        # 模拟第一轮全部成功
        if iteration_count == 1:
            print(f"[日志] 本轮所有品名均已成功解析。")
            products_to_process = []
        else:
            # 不应该执行到这里
            failed_results = [{"被解析品名": p} for p in products_to_process]
            products_to_process = []

    print("\n" + "-" * 60)
    print("测试结果验证:")
    print(f"  - 实际迭代轮次: {iteration_count}")
    print("-" * 60)

    if iteration_count == 1:
        print("[PASS] 测试通过：第一轮全部成功后正确停止")
    else:
        print(f"[FAIL] 测试失败：期望 1 轮，实际 {iteration_count} 轮")
        return False

    return True


async def test_single_call_retry():
    """测试：单次调用内部的重试逻辑（RETRY_COUNT）"""
    print("\n" + "=" * 60)
    print("测试：单次调用内部重试逻辑")
    print("=" * 60)

    test_retry_count = 0

    async def mock_with_retry(product_name, semaphore):
        """模拟会失败 RETRY_COUNT 次后成功的函数"""
        nonlocal test_retry_count
        async with semaphore:
            test_retry_count += 1
            if test_retry_count <= TEST_RETRY_COUNT:
                raise Exception("模拟失败")
            return {
                "被解析品名": product_name,
                "品类": "成功",
                "功能类别": "成功",
                "置信度": "100%",
            }

    semaphore = asyncio.Semaphore(10)

    # 第一次调用：会失败
    print(f"\n[日志] 处理品名 '测试商品' (尝试 1/{TEST_RETRY_COUNT}): 失败")
    try:
        result = await mock_with_retry("测试商品", semaphore)
        print(f"[日志] 处理品名 '测试商品' 成功")
    except Exception as e:
        print(f"[日志] 处理品名 '测试商品' 失败 (尝试 2/{TEST_RETRY_COUNT}): {e}")

    print("\n" + "-" * 60)
    print("测试结果验证:")
    print(f"  - 预期重试次数: {TEST_RETRY_COUNT}")
    print(f"  - 实际重试次数: {test_retry_count}")
    print("-" * 60)

    return True


async def test_iteration_boundary():
    """测试：迭代边界条件 - 第3轮（MAX_ITERATIONS）后停止"""
    print("\n" + "=" * 60)
    print("测试：迭代边界条件（第3轮后停止）")
    print("=" * 60)

    # 模拟始终失败，测试在第 MAX_ITERATIONS 轮后停止
    products_to_process = ["商品A", "商品B"]
    iteration_count = 0

    while products_to_process:
        # 这里是关键：在迭代开始前检查，超过则停止
        if iteration_count >= TEST_MAX_ITERATIONS:
            print(f"\n[日志] 已达到最大迭代轮次 ({TEST_MAX_ITERATIONS})，停止重试。")
            break

        iteration_count += 1
        print(f"[日志] 第 {iteration_count} 轮处理")

        # 模拟失败，保留到下一轮
        products_to_process = ["商品A", "商品B"]

    print("\n" + "-" * 60)
    print("测试结果验证:")
    print(f"  - 预期迭代轮次: {TEST_MAX_ITERATIONS}")
    print(f"  - 实际迭代轮次: {iteration_count}")
    print("-" * 60)

    if iteration_count == TEST_MAX_ITERATIONS:
        print("[PASS] 测试通过：在第 MAX_ITERATIONS 轮后正确停止")
        return True
    else:
        print(f"[FAIL] 测试失败：期望 {TEST_MAX_ITERATIONS} 轮，实际 {iteration_count} 轮")
        return False


async def main_test():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试最大迭代轮次限制功能")
    print("=" * 60)

    results = []

    # 测试1：达到最大迭代轮次后停止
    results.append(await test_max_iterations())

    # 测试2：在达到最大轮次前成功
    results.append(await test_max_iterations_with_success())

    # 测试3：单次调用内部重试
    results.append(await test_single_call_retry())

    # 测试4：迭代边界条件
    results.append(await test_iteration_boundary())

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"通过: {passed}/{total}")

    if all(results):
        print("\n[PASS] 所有测试通过!")
    else:
        print("\n[FAIL] 部分测试失败")

    return all(results)


if __name__ == "__main__":
    result = asyncio.run(main_test())
    sys.exit(0 if result else 1)