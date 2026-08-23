# OceanBase SQL/pyobvector 不使用部分 Milvus-shaped 参数，public signature 仍需保持一致。
# ruff: noqa: ARG002

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from steins_ai.models import SteinsAIException

from ..base import BaseVectorStorage
from .models import VectorQueryResult, VectorSearchResult

if TYPE_CHECKING:
    from pyobvector import FtsIndexParam, IndexParams, ObPartition
    from sqlalchemy import Column


class OceanBaseStorage(BaseVectorStorage):
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        db_name: str = "",
        **kwargs: Any,
    ) -> None:
        """
        初始化 OceanBase 客户端实例

        Args:
            uri (str): OceanBase 服务地址
            user (str): 数据库用户名
            password (str): 数据库密码
            db_name (str): OceanBase 数据库名称，可为空
            **kwargs: 其他 pyobvector/SQLAlchemy 连接参数
        """
        try:
            from pyobvector import MilvusLikeClient
            from pyobvector.client.hybrid_search import HybridSearch
        except ImportError as e:
            raise SteinsAIException(
                "OceanBaseStorage | __init__ | 缺少 dev dependency: pyobvector==0.2.29"
            ) from e

        self._db_name = db_name
        self._client_kwargs = {
            "uri": uri,
            "user": user,
            "password": password,
            **kwargs,
        }

        try:
            self._client = MilvusLikeClient(db_name="", **self._client_kwargs)
            if db_name and db_name in {
                str(row[0])
                for row in self._client.perform_raw_text_sql("SHOW DATABASES")
            }:
                self._client.engine.dispose()
                self._client = MilvusLikeClient(
                    db_name=db_name,
                    **self._client_kwargs,
                )
            self._engine = self._client.engine
            self._hybrid = HybridSearch(engine=self._engine)
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | __init__ | 操作发生非预期错误:{e!s}"
            ) from e

    async def create_db(
        self,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        """
        创建 OceanBase 数据库

        Args:
            timeout (float | None): 对齐 Milvus 接口，当前 OceanBase SQL 不使用
            **kwargs: 对齐 Milvus 接口，当前 OceanBase SQL 不使用
        """
        if not self._db_name:
            raise SteinsAIException("OceanBaseStorage | create_db | db_name 不能为空")

        try:
            await asyncio.to_thread(self._create_db_and_rebind_sync)
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | create_db | 操作发生非预期错误:{e!s}"
            ) from e

    async def list_db(
        self,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """列出 OceanBase 数据库列表"""
        try:
            rows = await asyncio.to_thread(
                self._client.perform_raw_text_sql,
                "SHOW DATABASES",
            )
            return [str(row[0]) for row in rows]
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | list_db | 操作发生非预期错误:{e!s}"
            ) from e

    async def has_collection(
        self,
        collection: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> bool:
        """检查 OceanBase table 是否存在"""
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | has_collection | db_name 不能为空"
            )

        try:
            return await asyncio.to_thread(
                self._client.has_collection,
                collection,
                timeout=timeout,
            )
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | has_collection | 操作发生非预期错误:{e!s}"
            ) from e

    async def list_collection(
        self,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """列出当前数据库中的 table"""
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | list_collection | db_name 不能为空"
            )

        try:
            rows = await asyncio.to_thread(
                self._client.perform_raw_text_sql,
                "SHOW TABLES",
            )
            return [str(row[0]) for row in rows]
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | list_collection | 操作发生非预期错误:{e!s}"
            ) from e

    async def list_partition(
        self,
        collection: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """列出 OceanBase 物理分区"""
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | list_partition | db_name 不能为空"
            )

        try:
            return await asyncio.to_thread(
                self._list_partition_sync,
                collection,
            )
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | list_partition | 操作发生非预期错误:{e!s}"
            ) from e

    async def drop_collection(
        self,
        collection: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        """删除 OceanBase table"""
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | drop_collection | db_name 不能为空"
            )

        try:
            await asyncio.to_thread(self._client.drop_collection, collection)
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | drop_collection | 操作发生非预期错误:{e!s}"
            ) from e

    async def drop_partition(
        self,
        collection: str,
        partition: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> None:
        """删除 OceanBase 物理分区"""
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | drop_partition | db_name 不能为空"
            )

        try:
            await asyncio.to_thread(
                self._drop_partition_sync,
                collection,
                partition,
            )
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | drop_partition | 操作发生非预期错误:{e!s}"
            ) from e

    async def create_collection(
        self,
        collection: str,
        columns: list[Column],
        timeout: float | None = None,
        *,
        vector_indexes: IndexParams | None = None,
        fulltext_indexes: list[FtsIndexParam] | None = None,
        partitions: ObPartition | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        使用 pyobvector schema primitives 创建 OceanBase table

        Args:
            collection (str): table 名称
            columns (list[Column]): SQLAlchemy 列定义
            timeout (float | None): 对齐 Milvus 接口，当前 pyobvector 方法不使用
            vector_indexes (IndexParams | None): 向量索引配置
            fulltext_indexes (list[FtsIndexParam] | None): 全文索引配置
            partitions (ObPartition | None): 物理分区配置
            **kwargs: table options，例如字符集和排序规则

        Returns:
            bool: 创建成功返回 True
        """
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | create_collection | db_name 不能为空"
            )
        if self._db_name not in await self.list_db():
            await self.create_db()
        if await self.has_collection(collection, timeout=timeout):
            raise SteinsAIException(
                f"{self.__class__.__name__} | create_collection | "
                f"表 {collection!r} 已存在"
            )

        try:
            await asyncio.to_thread(
                self._create_collection_sync,
                collection,
                columns,
                vector_indexes,
                fulltext_indexes,
                partitions,
                kwargs,
            )
            return True
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | create_collection | 操作发生非预期错误:{e!s}"
            ) from e

    async def create_partition(
        self,
        collection: str,
        partition: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        为 RANGE table 增加 OceanBase 物理分区

        Args:
            collection (str): table 名称
            partition (str): 分区名称
            timeout (float | None): 对齐 Milvus 接口，当前 OceanBase SQL 不使用
            **kwargs: OceanBase-specific 参数，需要 upper_bound

        Returns:
            bool: 创建成功返回 True
        """
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | create_partition | db_name 不能为空"
            )

        upper_bound = kwargs.get("upper_bound")
        if upper_bound is None:
            raise SteinsAIException(
                f"{self.__class__.__name__} | create_partition | 缺少 upper_bound"
            )
        if isinstance(upper_bound, int) and not isinstance(upper_bound, bool):
            bound = str(upper_bound)
        elif isinstance(upper_bound, str) and upper_bound.upper() == "MAXVALUE":
            bound = "MAXVALUE"
        else:
            raise SteinsAIException(
                f"{self.__class__.__name__} | create_partition | "
                "upper_bound 仅支持整数或 MAXVALUE"
            )

        try:
            await asyncio.to_thread(
                self._create_partition_sync,
                collection,
                partition,
                bound,
            )
            return True
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | create_partition | 操作发生非预期错误:{e!s}"
            ) from e

    async def delete_partition(
        self,
        collection: str,
        partition: str,
    ) -> bool:
        """删除 OceanBase 物理分区"""
        await self.drop_partition(collection, partition)
        return True

    async def add(
        self,
        collection: str,
        partition: str,
        data: list[dict],
        batch_size: int | None = None,
    ) -> None:
        """向 OceanBase table 写入数据"""
        if not data:
            return
        if not self._db_name:
            raise SteinsAIException("OceanBaseStorage | add | db_name 不能为空")

        size = 1_000 if batch_size is None else batch_size
        if size <= 0:
            raise SteinsAIException("OceanBaseStorage | add | batch_size 必须大于 0")

        try:
            await asyncio.to_thread(
                self._insert_batches,
                collection,
                partition,
                data,
                size,
            )
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | add | 操作发生非预期错误:{e!s}"
            ) from e

    async def delete(
        self,
        collection: str,
        partition: str,
        filter: str,
    ) -> None:
        """删除满足 OceanBase SQL 条件的数据"""
        if not self._db_name:
            raise SteinsAIException("OceanBaseStorage | delete | db_name 不能为空")

        from sqlalchemy import text

        try:
            await asyncio.to_thread(
                self._client.delete,
                collection_name=collection,
                partition_name=partition,
                flter=[text(filter)],
            )
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | delete | 操作发生非预期错误:{e!s}"
            ) from e

    async def search(
        self,
        collection: str,
        search_data: list,
        search_filter: str = "",
        partition_list: list[str] | None = None,
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[VectorSearchResult]:
        """
        执行 Dense ANN 或 BM25 检索

        Args:
            collection (str): table 名称
            search_data (list): 单个 Dense 向量或单个 BM25 查询文本
            search_filter (str): Dense 检索使用的 SQL predicate
            partition_list (list[str] | None): 物理分区名称列表
            output_fields (list[str] | None): 返回字段列表
            **kwargs: anns_field、limit、search_params 等检索参数

        Returns:
            list[VectorSearchResult]: 检索结果列表
        """
        if not self._db_name:
            raise SteinsAIException("OceanBaseStorage | search | db_name 不能为空")

        search_params = kwargs.pop("search_params", {}) or {}
        metric = search_params.get("metric_type", "COSINE").upper()
        anns_field = kwargs.pop("anns_field", None)
        limit = kwargs.pop("limit", 10)
        if not anns_field:
            raise SteinsAIException("OceanBaseStorage | search | 缺少 anns_field")

        if metric == "BM25":
            if partition_list:
                raise SteinsAIException(
                    f"{self.__class__.__name__} | search | BM25 不支持物理分区名过滤"
                )
            if search_filter:
                raise SteinsAIException(
                    f"{self.__class__.__name__} | search | BM25 不翻译 SQL filter"
                )
            if len(search_data) != 1 or not isinstance(search_data[0], str):
                raise SteinsAIException(
                    f"{self.__class__.__name__} | search | BM25 只接受一个查询文本"
                )

            body: dict[str, Any] = {
                "query": {"match": {anns_field: search_data[0]}},
                "size": limit,
            }
            if output_fields is not None:
                body["_source"] = output_fields
            hybrid_filter = kwargs.pop("filter", None)
            if hybrid_filter is not None:
                body["query"] = {
                    "bool": {
                        "must": [body["query"]],
                        "filter": (
                            hybrid_filter
                            if isinstance(hybrid_filter, list)
                            else [hybrid_filter]
                        ),
                    }
                }

            try:
                hits = await asyncio.to_thread(
                    self._hybrid.search,
                    index=collection,
                    body=body,
                    **kwargs,
                )
                return [
                    VectorSearchResult(
                        record={
                            key: value for key, value in hit.items() if key != "_score"
                        },
                        score=hit["_score"],
                    )
                    for hit in hits
                ]
            except Exception as e:
                raise SteinsAIException(
                    f"OceanBaseStorage | search | 操作发生非预期错误:{e!s}"
                ) from e

        if metric not in {"L2", "NEG_IP", "COSINE", "IP"}:
            raise SteinsAIException(
                f"{self.__class__.__name__} | search | 不支持 metric_type={metric!r}"
            )
        if not search_data or isinstance(search_data[0], list):
            raise SteinsAIException(
                f"{self.__class__.__name__} | search | 只接受单个向量，不支持 batch"
            )

        from sqlalchemy import text

        try:
            hits = await asyncio.to_thread(
                self._client.search,
                collection_name=collection,
                data=search_data,
                anns_field=anns_field,
                with_dist=True,
                flter=[text(search_filter)] if search_filter else None,
                limit=limit,
                output_fields=output_fields,
                search_params={**search_params, "metric_type": metric},
                partition_names=partition_list,
                **kwargs,
            )
            result = []
            for hit in hits:
                record = dict(hit)
                _, score = record.popitem()
                result.append(VectorSearchResult(record=record, score=score))
            return result
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | search | 操作发生非预期错误:{e!s}"
            ) from e

    async def query(
        self,
        collection: str,
        query_filter: str,
        partition_list: list[str] | None = None,
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[VectorQueryResult]:
        """根据 OceanBase SQL 条件查询数据"""
        if not self._db_name:
            raise SteinsAIException("OceanBaseStorage | query | db_name 不能为空")

        from sqlalchemy import text

        try:
            hits = await asyncio.to_thread(
                self._client.query,
                collection_name=collection,
                flter=[text(query_filter)],
                partition_names=partition_list,
                output_fields=output_fields,
                **kwargs,
            )
            return [VectorQueryResult(record=hit) for hit in hits]
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | query | 操作发生非预期错误:{e!s}"
            ) from e

    def search_iterator(
        self,
        _collection: str,
        _search_data: list,
        _search_filter: str,
        _output_fields: list[str] | None,
        _partition_list: list[str] | None = None,
        **_kwargs: Any,
    ) -> list[VectorSearchResult]:
        """迭代器搜索占位接口，当前 pyobvector 路径不支持"""
        raise SteinsAIException(
            "OceanBaseStorage | search_iterator | 异步迭代搜索上游尚未实现，故不支持"
        )

    async def hybrid_search(
        self,
        collection: str,
        requests: list[dict[str, Any]],
        ranker: dict[str, Any],
        partition_list: list[str] | None = None,
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[VectorSearchResult]:
        """
        执行 BM25 + Dense ANN 的 OceanBase-native RRF 混合检索

        Args:
            collection (str): table 名称
            requests (list[dict[str, Any]]): 一个 BM25 和一个 vector request
            ranker (dict[str, Any]): RRF 配置
            partition_list (list[str] | None): 当前混合检索不支持物理分区名
            output_fields (list[str] | None): 返回字段列表
            **kwargs: 其他 HybridSearch 参数

        Returns:
            list[VectorSearchResult]: 混合检索结果列表
        """
        if not self._db_name:
            raise SteinsAIException(
                "OceanBaseStorage | hybrid_search | db_name 不能为空"
            )
        if partition_list:
            raise SteinsAIException(
                f"{self.__class__.__name__} | hybrid_search | 不支持物理分区名过滤"
            )

        request_types = [request.get("type") for request in requests]
        if (
            len(requests) != 2
            or request_types.count("bm25") != 1
            or request_types.count("vector") != 1
        ):
            raise SteinsAIException(
                f"{self.__class__.__name__} | hybrid_search | "
                "需要且仅需要一个 bm25 和一个 vector request"
            )
        if ranker.get("type") != "rrf":
            raise SteinsAIException("OceanBaseStorage | hybrid_search | 仅支持 RRF")

        bm25 = requests[request_types.index("bm25")]
        vector = requests[request_types.index("vector")]
        if (
            not {"field", "data", "limit"} <= bm25.keys()
            or not {
                "field",
                "data",
                "limit",
            }
            <= vector.keys()
        ):
            raise SteinsAIException(
                "OceanBaseStorage | hybrid_search | request 字段不完整"
            )
        if not isinstance(bm25["data"], str):
            raise SteinsAIException(
                f"{self.__class__.__name__} | hybrid_search | "
                "bm25 data 必须是单个查询文本"
            )
        if (
            not isinstance(vector["data"], list)
            or not vector["data"]
            or isinstance(vector["data"][0], list)
        ):
            raise SteinsAIException(
                f"{self.__class__.__name__} | hybrid_search | "
                "vector data 必须是单个向量"
            )

        match: dict[str, Any] = {
            "match": {
                bm25["field"]: {
                    "query": bm25["data"],
                    "boost": bm25.get("boost", 0.3),
                }
            }
        }
        if bm25.get("filter") is not None:
            bm25_filter = bm25["filter"]
            match = {
                "bool": {
                    "must": [match],
                    "filter": (
                        bm25_filter if isinstance(bm25_filter, list) else [bm25_filter]
                    ),
                }
            }

        knn: dict[str, Any] = {
            "field": vector["field"],
            "k": vector["limit"],
            "query_vector": vector["data"],
            "boost": vector.get("boost", 0.7),
        }
        if vector.get("filter") is not None:
            vector_filter = vector["filter"]
            knn["filter"] = (
                vector_filter if isinstance(vector_filter, list) else [vector_filter]
            )

        body: dict[str, Any] = {
            "query": match,
            "knn": knn,
            "rank": {
                "rrf": {
                    "rank_constant": ranker.get("rank_constant", 60),
                    "rank_window_size": ranker.get("rank_window_size", 10),
                }
            },
            "size": kwargs.pop("limit", min(bm25["limit"], vector["limit"])),
        }
        if output_fields is not None:
            body["_source"] = output_fields

        try:
            hits = await asyncio.to_thread(
                self._hybrid.search,
                index=collection,
                body=body,
                **kwargs,
            )
            return [
                VectorSearchResult(
                    record={
                        key: value for key, value in hit.items() if key != "_score"
                    },
                    score=hit["_score"],
                )
                for hit in hits
            ]
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | hybrid_search | 操作发生非预期错误:{e!s}"
            ) from e

    async def close(self) -> None:
        """关闭当前 SQLAlchemy Engine"""
        try:
            await asyncio.to_thread(self._engine.dispose)
        except Exception as e:
            raise SteinsAIException(
                f"OceanBaseStorage | close | 操作发生非预期错误:{e!s}"
            ) from e

    def _create_db_and_rebind_sync(self) -> None:
        from pyobvector import MilvusLikeClient
        from pyobvector.client.hybrid_search import HybridSearch

        database = self._engine.dialect.identifier_preparer.quote_identifier(
            self._db_name
        )
        self._client.perform_raw_text_sql(f"CREATE DATABASE {database}")
        self._engine.dispose()

        client = MilvusLikeClient(
            db_name=self._db_name,
            **self._client_kwargs,
        )
        engine = client.engine
        hybrid = HybridSearch(engine=engine)
        self._client = client
        self._engine = engine
        self._hybrid = hybrid

    def _list_partition_sync(self, collection: str) -> list[str]:
        from sqlalchemy import text

        statement = text(
            "SELECT PARTITION_NAME FROM information_schema.PARTITIONS "
            "WHERE TABLE_SCHEMA = :database AND TABLE_NAME = :table "
            "AND PARTITION_NAME IS NOT NULL ORDER BY PARTITION_ORDINAL_POSITION"
        )
        with self._engine.connect() as connection:
            rows = connection.execute(
                statement,
                {"database": self._db_name, "table": collection},
            )
            return [str(row[0]) for row in rows]

    def _drop_partition_sync(self, collection: str, partition: str) -> None:
        preparer = self._engine.dialect.identifier_preparer
        table = preparer.quote_identifier(collection)
        part = preparer.quote_identifier(partition)
        self._client.perform_raw_text_sql(f"ALTER TABLE {table} DROP PARTITION {part}")
        self._client.refresh_metadata([collection])

    def _create_collection_sync(
        self,
        collection: str,
        columns: list[Column],
        vector_indexes: IndexParams | None,
        fulltext_indexes: list[FtsIndexParam] | None,
        partitions: ObPartition | None,
        table_kwargs: dict[str, Any],
    ) -> None:
        self._client.create_table_with_index_params(
            table_name=collection,
            columns=columns,
            vidxs=vector_indexes,
            fts_idxs=fulltext_indexes,
            partitions=partitions,
            **table_kwargs,
        )
        self._client.refresh_metadata([collection])

    def _create_partition_sync(
        self,
        collection: str,
        partition: str,
        upper_bound: str,
    ) -> None:
        preparer = self._engine.dialect.identifier_preparer
        table = preparer.quote_identifier(collection)
        part = preparer.quote_identifier(partition)
        self._client.perform_raw_text_sql(
            f"ALTER TABLE {table} ADD PARTITION "
            f"(PARTITION {part} VALUES LESS THAN ({upper_bound}))"
        )
        self._client.refresh_metadata([collection])

    def _insert_batches(
        self,
        collection: str,
        partition: str,
        data: list[dict],
        batch_size: int,
    ) -> None:
        for start in range(0, len(data), batch_size):
            self._client.insert(
                collection_name=collection,
                partition_name=partition,
                data=data[start : start + batch_size],
            )