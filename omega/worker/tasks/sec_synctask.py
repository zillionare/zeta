import asyncio
import logging
import traceback
from functools import wraps
from typing import Callable, Dict, List, Tuple, Union

import arrow
import async_timeout
import cfg4py
from omicron import cache
from omicron.models.security import Security

from omega.worker import exception
from omega.worker.abstract_quotes_fetcher import AbstractQuotesFetcher as fetcher

cfg = cfg4py.get_instance()

logger = logging.getLogger(__name__)


async def secs_task_exit(state, error=None):
    if error is None:  # pragma: no cover
        error = traceback.format_exc()
        logger.warning("worker exited with error:%s", error)

    # 删除is_running 并写上错误堆栈信息
    former_error = await cache.sys.hget(state, "error")
    p = cache.sys.pipeline()

    if former_error:
        p.hmset(state, "error", former_error + "\n" + error)
    else:
        p.hmset(state, "error", error)

    p.hmset(state, "status", -1)  # 设置状态为失败

    await p.execute()


def worker_secs_task():
    def inner(f):
        @wraps(f)
        async def decorated_function(params):
            state = params.get("state")
            timeout = params.get("timeout")
            name = params.get("name")
            logger.debug("worker task: %s, timeout %d", name, timeout)

            try:
                async with async_timeout.timeout(timeout):
                    await cache.sys.hincrby(state, "worker_count")  # 标记worker执行次数
                    try:
                        ret = await f(params)
                        cache.sys.hmset(state, "status", 1)  # 0运行，1成功，-1失败
                        return ret
                    except exception.WorkerException as e:
                        await secs_task_exit(state, e.msg)
                    except Exception as e:  # pragma: no cover
                        logger.exception(e)
                        await secs_task_exit(state)
            except asyncio.exceptions.TimeoutError:  # pragma: no cover
                await secs_task_exit(state, error="worker task timeout")
                return False

        return decorated_function

    return inner


async def mark_task_done(state, count=1):
    p = cache.sys.pipeline()
    p.hmset(state, "done_count", count)
    await p.execute()


@worker_secs_task()
async def sync_security_list(params: Dict):
    state = params.get("state")
    target_date = params.get("end")

    securities = await fetcher.get_security_list(target_date)
    if securities is None or len(securities) < 100:
        msg = "failed to get security list(%s)" % target_date.strftime("%Y-%m-%d")
        logger.error(msg)
        await secs_task_exit(state, msg)
        return False

    if arrow.now().date() == target_date:  # 更新今天的缓存数据
        await Security.update_secs_cache(securities)

    await Security.save_securities(securities, target_date)
    await mark_task_done(state, len(securities))

    logger.info("secs are fetched and saved.")
    return True
