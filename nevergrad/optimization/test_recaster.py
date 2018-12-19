# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import time
from unittest import TestCase
from typing import Callable, Optional
import genty
import numpy as np
from ..common.typetools import ArrayLike
from . import recaster
from . import optimizerlib


def test_message() -> None:
    message = recaster.Message(1, 2, blublu=3)
    np.testing.assert_equal(message.done, False)
    np.testing.assert_equal(message.args, [1, 2])
    np.testing.assert_equal(message.kwargs, {"blublu": 3})
    message.result = 3
    np.testing.assert_equal(message.done, True)
    np.testing.assert_equal(message.result, 3)


def fake_caller(func: Callable[[int], int]) -> int:
    output = 0
    for k in range(10):
        output += func(k)
    return output


@genty.genty
class DirtyOptimizerTests(TestCase):

    @genty.genty_dataset(  # type: ignore
        finished=(10, 30),
        unfinished=(2, None),  # should not hang at deletion!
    )
    def test_messaging_thread(self, num_iter: int, output: Optional[int]) -> None:
        thread = recaster.MessagingThread(fake_caller)
        num_answers = 0
        while num_answers < num_iter:
            if thread.messages and not thread.messages[0].done:
                thread.messages[0].result = 3
                num_answers += 1
            time.sleep(0.001)
        np.testing.assert_equal(thread.output, output)


def test_automatic_thread_deletion() -> None:
    thread = recaster.MessagingThread(fake_caller)
    assert thread.is_alive()


def fake_cost_function(x: ArrayLike) -> float:
    return float(np.sum(np.array(x) ** 2))


class FakeOptimizer(recaster.SequentialRecastOptimizer):

    def get_optimization_function(self) -> Callable[[Callable], ArrayLike]:
        suboptim = optimizerlib.OnePlusOne(dimension=2, budget=self.budget)
        return suboptim.optimize


def test_recast_optimizer() -> None:
    optimizer = FakeOptimizer(dimension=2, budget=100)
    optimizer.optimize(fake_cost_function)
    assert optimizer._messaging_thread is not None
    np.testing.assert_equal(optimizer._messaging_thread._thread.call_count, 100)


def test_recast_optimizer_with_error() -> None:
    optimizer = FakeOptimizer(dimension=2, budget=100)
    np.testing.assert_raises(TypeError, optimizer.optimize)  # did hang in some versions


def test_recast_optimizer_and_stop() -> None:
    optimizer = FakeOptimizer(dimension=2, budget=100)
    optimizer.ask()
    # thread is not finished... but should not hang!