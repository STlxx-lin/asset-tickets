"""
test_adversarial_challenger.py — 对抗性逻辑、边界极限与访问控制安全测试套件

由 Challenger 1 (Adversarial Logic & Access Control Verifier) 编写并执行。
针对以下 3 大核心修复靶点执行实证性对抗压测与安全攻击探测：
1. has_pending_edit_review (极端日志序列、时间戳乱序、缺失/None、多轮退回重修再提审、并发与噪声、压力性能)
2. get_work_orders (权限对抗、空集合/空元组/空列表/空字典、SQL注入载荷探测、混合恶意参数、超管分支)
3. _rollback (数据库更新返回值边界矩阵、多字段回滚、异常与非标准返回码)
"""
import datetime
import random
import time
import unittest
from unittest.mock import MagicMock, patch

import pymysql

from src.core import status_sync
from src.core.database import DatabaseManager


class TestAdversarialHasPendingEditReview(unittest.TestCase):
    """靶点 1：has_pending_edit_review 对抗性与极限场景测试"""

    def test_01_multi_cycle_rejection_and_resubmission(self):
        """测试 1.1: 多轮提审-退回-重修-再提审循环的状态机演进与终态判定"""
        # 模拟真实业务中经历 3 轮完整提审退回重修流程
        lifecycle_logs = [
            {'action_type': '创建工单', 'timestamp': '2026-08-10 09:00:00'},
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-10 10:00:00'}, # 轮次 1
            {'action_type': '视频后期审核退回', 'timestamp': '2026-08-10 11:30:00'},
            {'action_type': '后期重新剪辑', 'timestamp': '2026-08-10 14:00:00'},
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-11 09:30:00'}, # 轮次 2
            {'action_type': '视频后期审核通过', 'timestamp': '2026-08-11 10:00:00'}, # 历史通过记录！
            {'action_type': '视频后期审核退回', 'timestamp': '2026-08-12 15:00:00'}, # 客户要求修改再次退回
            {'action_type': '后期重新剪辑', 'timestamp': '2026-08-12 16:00:00'},
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-13 11:00:00'}, # 轮次 3：最新提交
        ]

        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=lifecycle_logs):
            # 此时最新相关事件是 '提交视频后期审核'，尽管历史上曾有 '视频后期审核通过'，必须正确识别为待审核
            self.assertTrue(status_sync.has_pending_edit_review('WO_MULTI_CYCLE'))

        # 若在轮次 3 之后质检员执行了审核退回
        after_rejection = lifecycle_logs + [{'action_type': '视频后期审核退回', 'timestamp': '2026-08-13 14:00:00'}]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=after_rejection):
            self.assertFalse(status_sync.has_pending_edit_review('WO_MULTI_CYCLE'))

        # 若在退回后重新剪辑，仍非待审核
        after_reedit = after_rejection + [{'action_type': '后期重新剪辑', 'timestamp': '2026-08-13 15:00:00'}]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=after_reedit):
            self.assertFalse(status_sync.has_pending_edit_review('WO_MULTI_CYCLE'))

        # 重新提交后再次变为待审核
        after_resubmit_4 = after_reedit + [{'action_type': '提交视频后期审核', 'timestamp': '2026-08-13 17:00:00'}]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=after_resubmit_4):
            self.assertTrue(status_sync.has_pending_edit_review('WO_MULTI_CYCLE'))

    def test_02_shuffled_and_reverse_order_logs(self):
        """测试 1.2: 乱序混杂日志与完全反序日志对抗"""
        ordered_logs = [
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-01 10:00:00'},
            {'action_type': '视频后期审核退回', 'timestamp': '2026-08-02 10:00:00'},
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-03 10:00:00'},
            {'action_type': '视频后期审核通过', 'timestamp': '2026-08-04 10:00:00'},
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-05 10:00:00'}, # 真实最新
        ]

        # 场景 A: 逆序列表（物理最新存储在索引 0）
        reversed_logs = list(reversed(ordered_logs))
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=reversed_logs):
            self.assertTrue(status_sync.has_pending_edit_review('WO_REVERSED'))

        # 场景 B: 随机打乱 50 次，排序键必须保证 100% 结果一致
        rng = random.Random(42)
        for i in range(50):
            shuffled = list(ordered_logs)
            rng.shuffle(shuffled)
            with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=shuffled):
                self.assertTrue(status_sync.has_pending_edit_review(f'WO_SHUFFLED_{i}'))

    def test_03_missing_or_none_timestamps(self):
        """测试 1.3: 时间戳缺失、为 None 或为纯空字符串对抗"""
        # 场景 A: 新的提审记录有有效时间戳，而旧记录时间戳为 None/缺失
        # 有效时间戳字符串在字典序中大于 ''，因此提审记录稳稳排在首位
        valid_resubmit_logs = [
            {'action_type': '视频后期审核退回', 'timestamp': None},
            {'action_type': '后期重新剪辑'}, # 完全缺失 timestamp 键
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-14 15:00:00'},
        ]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=valid_resubmit_logs):
            self.assertTrue(status_sync.has_pending_edit_review('WO_VALID_TS'))

        # 场景 B: 提审记录的时间戳为 None，而历史上存在有时间戳的旧审核通过记录
        # 字典序中 '' < '2026...'，经过 reverse=True 后，有时间戳的旧通过记录排在首位
        # 这揭示了边界事实：缺失时间戳的记录会被降级为最久远历史事件
        none_ts_logs = [
            {'action_type': '视频后期审核通过', 'timestamp': '2026-08-01 10:00:00'},
            {'action_type': '提交视频后期审核', 'timestamp': None},
        ]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=none_ts_logs):
            self.assertFalse(status_sync.has_pending_edit_review('WO_NONE_DEGRADED'))

        # 场景 C: 所有日志均无时间戳（全部为 None 或缺失），键全为 ''
        # 实测证实 Python sorted(..., reverse=True) 保持相等 key 的原有相对顺序（稳定排序）
        all_none_logs = [
            {'action_type': '视频后期审核退回', 'timestamp': None},
            {'action_type': '提交视频后期审核', 'timestamp': None},
        ]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=all_none_logs):
            # 排序后维持原顺序，遍历命中第 1 项为退回，故为 False
            self.assertFalse(status_sync.has_pending_edit_review('WO_ALL_NONE'))

    def test_04_iso8601_and_datetime_objects(self):
        """测试 1.4: 时间戳格式异构（datetime 对象与标准字符串混杂）"""
        mixed_logs = [
            {'action_type': '视频后期审核退回', 'timestamp': datetime.datetime(2026, 8, 1, 9, 0, 0)},
            {'action_type': '提交视频后期审核', 'timestamp': datetime.datetime(2026, 8, 1, 10, 0, 0)}, # 最新
        ]
        # str(datetime.datetime) 得到 '2026-08-01 10:00:00'，可正常参与字典序比较
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=mixed_logs):
            self.assertTrue(status_sync.has_pending_edit_review('WO_DATETIME_OBJ'))

    def test_05_concurrent_identical_timestamps(self):
        """测试 1.5: 同一秒（完全相同时间戳）并发动作的 Tie-breaker 特性实测"""
        same_time = '2026-08-14 12:00:00'

        # 场景 A: 底层数据库按 ORDER BY timestamp DESC 正常返回（物理后插入的排在列表前部）
        # [提审, 退回] (提审发生在后，排在列表 index 0)
        logs_descending = [
            {'action_type': '提交视频后期审核', 'timestamp': same_time},
            {'action_type': '视频后期审核退回', 'timestamp': same_time},
        ]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=logs_descending):
            # 稳定排序保持相等 key 元素原顺序，第 1 项依然是提审，返回 True
            self.assertTrue(status_sync.has_pending_edit_review('WO_SAME_TIME_DESC'))

        # 场景 B: 若底层以正序传入 [退回, 提审] (提审在后)
        logs_ascending = [
            {'action_type': '视频后期审核退回', 'timestamp': same_time},
            {'action_type': '提交视频后期审核', 'timestamp': same_time},
        ]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=logs_ascending):
            # 稳定排序保持相等 key 元素原顺序，第 1 项依然是退回，返回 False
            # 此实测表明：同秒内多次操作时，算法依赖输入源的平局顺序
            self.assertFalse(status_sync.has_pending_edit_review('WO_SAME_TIME_ASC'))

    def test_06_edge_cases_single_action_types(self):
        """测试 1.6: 边界场景（空列表、纯单项动作、纯无关动作）"""
        # 空日志
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=[]):
            self.assertFalse(status_sync.has_pending_edit_review('WO_EMPTY'))

        # 仅有审核通过
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=[{'action_type': '视频后期审核通过', 'timestamp': '2026-08-14 10:00:00'}]):
            self.assertFalse(status_sync.has_pending_edit_review('WO_ONLY_PASS'))

        # 仅有审核退回
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=[{'action_type': '视频后期审核退回', 'timestamp': '2026-08-14 10:00:00'}]):
            self.assertFalse(status_sync.has_pending_edit_review('WO_ONLY_REJECT'))

        # 仅有重新剪辑
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=[{'action_type': '后期重新剪辑', 'timestamp': '2026-08-14 10:00:00'}]):
            self.assertFalse(status_sync.has_pending_edit_review('WO_ONLY_REEDIT'))

        # 仅有无关动作
        unrelated = [
            {'action_type': '新建工单', 'timestamp': '2026-08-14 09:00:00'},
            {'action_type': '分配工单', 'timestamp': '2026-08-14 09:30:00'},
            {'action_type': '修改备注', 'timestamp': '2026-08-14 10:00:00'},
        ]
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=unrelated):
            self.assertFalse(status_sync.has_pending_edit_review('WO_UNRELATED'))

    def test_07_noise_action_tolerance(self):
        """测试 1.7: 提审后插入大量无关日志噪声，验证过滤鲁棒性"""
        logs = [
            {'action_type': '提交视频后期审核', 'timestamp': '2026-08-14 10:00:00'},
        ]
        # 在提审之后，发生 500 条无关日志（时间戳更新）
        for i in range(1, 501):
            ts = f"2026-08-14 10:{i//60:02d}:{i%60:02d}"
            logs.append({'action_type': f'无关操作_{i}', 'timestamp': ts})

        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=logs):
            # 无关日志不应冲刷或遮蔽提审状态
            self.assertTrue(status_sync.has_pending_edit_review('WO_NOISE'))

    def test_08_database_exception_resilience(self):
        """测试 1.8: 数据库层抛出异常时的韧性防御"""
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', side_effect=pymysql.OperationalError(2006, 'MySQL server has gone away')):
            # 发生数据库异常时应安全捕获并返回 False，禁止抛出未捕获异常导致客户端崩溃
            res = status_sync.has_pending_edit_review('WO_DB_CRASH')
            self.assertFalse(res)

        # 针对返回非列表/包含损坏字典的防御
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=[None, "broken_log"]):
            res = status_sync.has_pending_edit_review('WO_MALFORMED_DATA')
            self.assertFalse(res)

    def test_09_stress_large_log_volume(self):
        """测试 1.9: 万级日志极限压力测试 (O(n log n) 排序性能验证)"""
        stress_logs = []
        base_time = datetime.datetime(2026, 1, 1, 0, 0, 0)
        for i in range(10000):
            ts = (base_time + datetime.timedelta(minutes=i)).strftime('%Y-%m-%d %H:%M:%S')
            action = '系统日常轮询' if i != 9999 else '提交视频后期审核'
            stress_logs.append({'action_type': action, 'timestamp': ts})

        random.shuffle(stress_logs)
        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=stress_logs):
            start = time.perf_counter()
            res = status_sync.has_pending_edit_review('WO_STRESS_10K')
            elapsed = time.perf_counter() - start
            self.assertTrue(res)
            # 10,000 条日志排序并检索必须在 100ms 内完成
            self.assertLess(elapsed, 0.1, f"万级日志耗时超过阈值: {elapsed:.4f}s")

    def test_10_extreme_interleaved_lifecycle_stress(self):
        """测试 1.10: 50 轮高频反复审核退回重修再提审穿插无关事件的乱序穿透测试"""
        rng = random.Random(1337)
        base_dt = datetime.datetime(2026, 1, 1, 8, 0, 0)
        logs = []
        current_time = base_dt

        # 生成 50 轮提审-退回循环
        for round_idx in range(50):
            current_time += datetime.timedelta(hours=1)
            logs.append({'action_type': '提交视频后期审核', 'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')})
            # 穿插大量无关日志
            for noise_idx in range(5):
                current_time += datetime.timedelta(minutes=2)
                logs.append({'action_type': f'评论沟通_{round_idx}_{noise_idx}', 'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')})
            current_time += datetime.timedelta(hours=1)
            logs.append({'action_type': '视频后期审核退回', 'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')})
            current_time += datetime.timedelta(hours=1)
            logs.append({'action_type': '后期重新剪辑', 'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')})

        # 第 51 轮：最后一次提交审核
        current_time += datetime.timedelta(hours=1)
        logs.append({'action_type': '提交视频后期审核', 'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')})
        # 之后追加若干无关日志
        current_time += datetime.timedelta(minutes=5)
        logs.append({'action_type': '自动消息提醒已发送', 'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')})

        # 完全打乱物理顺序
        rng.shuffle(logs)

        with patch.object(status_sync.db_manager, 'get_logs_by_order_id', return_value=logs):
            self.assertTrue(status_sync.has_pending_edit_review('WO_50_ROUNDS'))



class TestAdversarialGetWorkOrders(unittest.TestCase):
    """靶点 2：get_work_orders 权限防越权与 SQL 注入对抗测试"""

    def setUp(self):
        self.db = DatabaseManager()

    def test_01_empty_containers_access_control(self):
        """测试 2.1: 空容器类型（列表/元组/集合/字典/空字符串）100% 阻断与零越权"""
        with patch.object(self.db, 'connect', return_value=True):
            self.db.connection = MagicMock()

            # 1. 空列表 []
            res_list = self.db.get_work_orders([])
            self.assertEqual(res_list, [])
            self.db.connection.cursor.assert_not_called()

            # 2. 空元组 ()
            res_tuple = self.db.get_work_orders(())
            self.assertEqual(res_tuple, [])
            self.db.connection.cursor.assert_not_called()

            # 3. 空集合 set()
            res_set = self.db.get_work_orders(set())
            self.assertEqual(res_set, [])
            self.db.connection.cursor.assert_not_called()

            # 4. 空字典 {}
            res_dict = self.db.get_work_orders({})
            self.assertEqual(res_dict, [])
            self.db.connection.cursor.assert_not_called()

            # 5. 空字符串 ""
            res_str = self.db.get_work_orders("")
            self.assertEqual(res_str, [])
            self.db.connection.cursor.assert_not_called()

    def test_02_sql_injection_payloads(self):
        """测试 2.2: SQL 注入探测载荷，验证参数化隔离与防拼接"""
        injection_payloads = [
            ["' OR '1'='1"],
            ["' OR 1=1 --"],
            ["admin' --"],
            ["'; DROP TABLE mcs_by_takuya_work_orders; --"],
            ["' UNION SELECT 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20 --"],
            ['" OR ""="'],
            ["1; SELECT * FROM mcs_by_takuya_users;"],
        ]

        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            self.db.connection = mock_conn

            for payload in injection_payloads:
                res = self.db.get_work_orders(payload)
                self.assertEqual(res, [])
                # 核心断言：execute 调用必须是带有参数占位符的参数化调用，参数必须严格作为元组/列表传入
                args, _ = mock_cursor.execute.call_args
                query_sql = args[0]
                query_params = args[1]
                # SQL 模板中只能有 %s，绝不能包含未转义的注入 payload 字符
                self.assertIn("WHERE d.name IN (%s)", query_sql)
                self.assertNotIn("' OR '1'='1", query_sql)
                self.assertNotIn("DROP TABLE", query_sql)
                self.assertEqual(query_params, payload)

    def test_03_blank_and_special_departments(self):
        """测试 2.3: 纯空格、空字符串元素、None 元素及不存在的部门"""
        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            self.db.connection = mock_conn

            special_cases = [
                [""], # 含空字符串
                ["   "], # 纯空格
                [None], # 包含 None 元素
                ["NonExistentDepartment_XYZ_99999"],
            ]
            for depts in special_cases:
                res = self.db.get_work_orders(depts)
                self.assertEqual(res, [])
                mock_cursor.execute.assert_called()
                args, _ = mock_cursor.execute.call_args
                self.assertIn("WHERE d.name IN (%s)", args[0])
                self.assertEqual(args[1], depts)

    def test_04_mixed_valid_and_malicious_departments(self):
        """测试 2.4: 混合合法部门与注入攻击载荷，验证无法越权查出全量数据"""
        mixed_depts = ["剪辑部", "' OR 1=1 --", "美工部"]
        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [{'id': 'WO1', 'department': '剪辑部'}]
            self.db.connection = mock_conn

            res = self.db.get_work_orders(mixed_depts)
            self.assertEqual(len(res), 1)
            args, _ = mock_cursor.execute.call_args
            # 必须构造出 3 个 %s 占位符
            self.assertIn("WHERE d.name IN (%s,%s,%s)", args[0])
            self.assertEqual(args[1], mixed_depts)

    def test_05_superadmin_none_branch(self):
        """测试 2.5: 超级管理员显式 None 分支"""
        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [{'id': 'WO_ALL_1'}, {'id': 'WO_ALL_2'}]
            self.db.connection = mock_conn

            # 显式传入 None 或默认值
            res = self.db.get_work_orders(None)
            self.assertEqual(len(res), 2)
            args, _ = mock_cursor.execute.call_args
            # 超管查询绝不应含有 WHERE d.name IN 过滤子句
            self.assertNotIn("WHERE d.name IN", args[0])

    def test_06_large_department_list_stress(self):
        """测试 2.6: 大规模部门列表 (500 个部门) 动态占位符拼装压测"""
        large_depts = [f"Dept_{i}" for i in range(500)]
        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            self.db.connection = mock_conn

            res = self.db.get_work_orders(large_depts)
            self.assertEqual(res, [])
            args, _ = mock_cursor.execute.call_args
            expected_placeholders = ','.join(['%s'] * 500)
            self.assertIn(f"WHERE d.name IN ({expected_placeholders})", args[0])
            self.assertEqual(len(args[1]), 500)

    def test_07_invalid_types_resilience(self):
        """测试 2.7: 非法畸形数据类型 (非可迭代非空对象) 异常防御"""
        with patch.object(self.db, 'connect', return_value=True):
            self.db.connection = MagicMock()
            # 传入整数 99999：非 None，bool 为 True，但在 len(user_departments) 触发 TypeError
            res = self.db.get_work_orders(99999) # type: ignore
            # 应被 except Exception 安全捕获并返回 []，绝不泄露数据或崩溃
            self.assertEqual(res, [])

    def test_08_sql_injection_bypass_attempts(self):
        """测试 2.8: 深入对抗 - 换行符注入、注释闭合与十六进制逃逸载荷"""
        bypass_payloads = [
            "剪辑部\nOR 1=1 --",
            "剪辑部\r\nUNION SELECT 1,2,3",
            "0x27204f5220313d31", # 十六进制字面量
            "'; EXEC xp_cmdshell('dir'); --",
            "/* inline comment */ 剪辑部",
        ]
        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            self.db.connection = mock_conn

            res = self.db.get_work_orders(bypass_payloads)
            self.assertEqual(res, [])
            args, _ = mock_cursor.execute.call_args
            # 必须严格保持 5 个参数占位符，且载荷仅作为参数数组传入
            self.assertIn("WHERE d.name IN (%s,%s,%s,%s,%s)", args[0])
            self.assertEqual(args[1], bypass_payloads)

    def test_09_none_and_empty_departments_isolation(self):
        """测试 2.9: 权限隔离对照测试：验证 None (超管) 与 [] (空权限用户) 严格区分"""
        with patch.object(self.db, 'connect', return_value=True):
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_cursor.fetchall.return_value = [{'id': 'WO_SUPER_ONLY'}]
            self.db.connection = mock_conn

            # 空权限用户：必须立即返回 []，且绝对不能调用数据库 cursor
            res_restricted = self.db.get_work_orders([])
            self.assertEqual(res_restricted, [])
            mock_cursor.execute.assert_not_called()

            # 超管：必须调用 cursor 并执行不带 WHERE d.name IN 的查询
            res_admin = self.db.get_work_orders(None)
            self.assertEqual(len(res_admin), 1)
            mock_cursor.execute.assert_called_once()
            self.assertNotIn("WHERE d.name IN", mock_cursor.execute.call_args[0][0])


class TestAdversarialRollback(unittest.TestCase):
    """靶点 3：_rollback 异常回滚对抗测试"""

    def test_01_return_code_boundary_matrix(self):
        """测试 3.1: update_work_order_fields 返回值全矩阵覆盖"""
        test_matrix = [
            (-1, True, "底层异常返回 -1 必须判定为失败"),
            (0, True, "未匹配更新行数 0 必须判定为失败"),
            (-2, True, "异常错误码 -2 必须判定为失败"),
            (-99, True, "未知负数错误码 -99 必须判定为失败"),
            (1, False, "更新成功 1 行必须判定为成功 (无 failure)"),
            (2, False, "更新成功 2 行必须判定为成功 (无 failure)"),
        ]

        for return_val, should_fail, desc in test_matrix:
            with patch.object(status_sync.db_manager, 'update_work_order_fields', return_value=return_val):
                failures = status_sync._rollback('WO_TEST', {'status': '已派单'})
                if should_fail:
                    self.assertEqual(len(failures), 1, f"{desc}: 实际未记录 failure")
                    self.assertIn(f"错误码: {return_val}", failures[0])
                else:
                    self.assertEqual(failures, [], f"{desc}: 实际误报了 failure: {failures}")

    def test_02_multi_field_failure_reporting(self):
        """测试 3.2: 多字段复合回滚失败时的字段名完整呈现"""
        updates = {
            'status': '前期处理中',
            'art_status': '设计中',
            'edit_product_path': '/nas/vol2/edit/demo.mp4',
            'art_start_time': '2026-08-14 10:00:00',
        }
        with patch.object(status_sync.db_manager, 'update_work_order_fields', return_value=-1):
            failures = status_sync._rollback('WO_MULTI', updates)
            self.assertEqual(len(failures), 1)
            err = failures[0]
            # 必须包含所有试图回滚的字段名称
            for field in updates:
                self.assertIn(field, err)
            self.assertIn('错误码: -1', err)

    def test_03_empty_updates_rollback(self):
        """测试 3.3: 空 updates 字典边界"""
        # 当 updates 为空时，根据 database.py:543 行，返回 0
        with patch.object(status_sync.db_manager, 'update_work_order_fields', return_value=0):
            failures = status_sync._rollback('WO_EMPTY_UPDATES', {})
            # 返回 0 会被捕获为回滚失败
            self.assertEqual(len(failures), 1)
            self.assertIn("回滚字段[]失败(错误码: 0)", failures[0])

    def test_04_db_exception_propagation_and_type_error(self):
        """测试 3.4: 极端非标准返回值（如 None 或字符串）与异常穿透测试"""
        # 若底层返回 None，测试 res <= 0 是否会触发 TypeError
        with patch.object(status_sync.db_manager, 'update_work_order_fields', return_value=None), \
             self.assertRaises(TypeError):
            status_sync._rollback('WO_NONE_VAL', {'status': '已派单'})

        # 若底层抛出未捕获的严重数据库异常（如 DatabaseError），_rollback 会向上透传还是捕获？
        # _rollback 内部未加 try-except，会向外部 status_sync 的调用者抛出
        with patch.object(status_sync.db_manager, 'update_work_order_fields', side_effect=pymysql.DatabaseError("DB fatal")), \
             self.assertRaises(pymysql.DatabaseError):
            status_sync._rollback('WO_FATAL', {'status': '已派单'})

    def test_05_update_work_order_fields_whitelist_enforcement(self):
        """测试 3.5: database.update_work_order_fields 针对非法未授权字段的防御机制"""
        db = DatabaseManager()
        # 尝试注入非法字段（非白名单）
        res = db.update_work_order_fields('WO_HACK', {'password_hash': 'hacked', 'status': '已完成'})
        # 白名单检查必须直接阻断并返回 -1
        self.assertEqual(res, -1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
