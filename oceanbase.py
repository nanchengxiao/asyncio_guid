import asyncio
from typing import Any

from pyobvector import FtsIndexParam, IndexParams, ObPartition
from pyobvector.client.hybrid_search import HybridSearch
from sqlalchemy import Column, Index, column, func, select, table, text

from steins_ai.models import SteinsAIException

from .base import BaseVectorStorage
from .models import VectorQueryResult, VectorSearchResult


class OceanBaseStorage(BaseVectorStorage):
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        db_name: str,
        **kwargs: Any,
    ) -> None:
        """
        初始化 OceanBase 客户端实例

        Args:
            uri (str): OceanBase 服务地址
            user (str): OceanBase 用户名
            password (str): OceanBase 密码
            db_name (str): OceanBase 数据库名称
            **kwargs: 其他连接参数
        """
        from pyobvector import MilvusLikeClient

        self._client = MilvusLikeClient(
            uri=uri,
            user=user,
            password=password,
            db_name=db_name,
            **kwargs,
        )

    async def create_db(self, db_name: str) -> None:
        """
        创建 OceanBase 数据库

        Args:
            db_name (str): OceanBase 数据库名称
        """
        # 对数据库名进行必要的 SQL 标识符转义
        db_name = self._client.engine.dialect.identifier_preparer.quote(db_name)
        await asyncio.to_thread(
            self._client.perform_raw_text_sql,
            f"CREATE DATABASE {db_name}",
        )

    async def list_db(self) -> list[str]:
        """列出 OceanBase 数据库列表"""
        result = await asyncio.to_thread(
            self._client.perform_raw_text_sql,
            "SHOW DATABASES",
        )
        # 调用 fetchall() 解析
        rows = await asyncio.to_thread(result.fetchall)
        return [row[0] for row in rows]

    async def has_collection(
        self,
        collection: str,
        timeout: float | None = None,
    ) -> bool:
        """
        检查 OceanBase 表是否存在

        Args:
            collection (str): 要检查的 OceanBase 表名称。
            timeout (float | None): 兼容参数,pyobvector 0.2.29 当前不会使用
        """
        return await asyncio.to_thread(
            self._client.has_collection,
            collection_name=collection,
            timeout=timeout,
        )

    async def list_collection(self) -> list[str]:
        """列出 OceanBase 表列表"""
        result = await asyncio.to_thread(
            self._client.perform_raw_text_sql,
            "SHOW TABLES",
        )
        rows = await asyncio.to_thread(result.fetchall)
        return [row[0] for row in rows]

    async def list_partition(self, collection: str) -> list[str]:
        """
        列出 OceanBase 表的一级分区列表，不包含二级子分区

        Args:
            collection (str): 要列出 OceanBase 分区的表名称。
        """
        try:
            # 查询 OceanBase MySQL 模式视图 information_schema.PARTITIONS 系统表，获取表及一级/二级分区信息。
            partitions = table(
                "PARTITIONS",
                column("PARTITION_NAME"),
                column("TABLE_SCHEMA"),
                column("TABLE_NAME"),
                schema="information_schema",
            )
            # 构造查询语句
            statement = (
                select(partitions.c.PARTITION_NAME)
                .distinct()
                .where(
                    func.database() == partitions.c.TABLE_SCHEMA,
                    collection == partitions.c.TABLE_NAME,
                    partitions.c.PARTITION_NAME.is_not(None),
                )
            )
            text_sql = statement.compile(
                dialect=self._client.engine.dialect,
                compile_kwargs={"literal_binds": True},
            )
            result = await asyncio.to_thread(
                self._client.perform_raw_text_sql,
                str(text_sql),
            )
            rows = await asyncio.to_thread(result.fetchall)
            return [row[0] for row in rows]
        except Exception as e:
            error_msg = (
                f"{self.__class__.__name__} | list_partition | 操作发生非预期错误:{e!s}"
            )
            raise SteinsAIException(error_msg) from e

    async def drop_collection(self, collection: str) -> None:
        """
        删除 OceanBase 表

        Args:
            collection (str): 要删除的 OceanBase 表名称。
        """
        try:
            await asyncio.to_thread(
                self._client.drop_collection,
                collection_name=collection,
            )
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | drop_collection | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def create_collection(
        self,
        collection: str,
        columns: list[Column],
        *,
        indexes: list[Index] | None = None,
        vector_indexes: IndexParams | None = None,
        fulltext_indexes: list[FtsIndexParam] | None = None,
        partitions: ObPartition | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        使用 pyobvector 原生 Schema 创建 OceanBase 表

        Args:
            collection (str): 要创建的 OceanBase 表名称。
            columns (list[Column]): 表字段定义。
            indexes (list[Index] | None): 普通索引定义。
            vector_indexes (IndexParams | None): 向量索引定义。
            fulltext_indexes (list[FtsIndexParam] | None): 全文索引定义。
            partitions (ObPartition | None): 分区定义。
            **kwargs: 其他建表参数。

        Returns:
            bool: 创建成功返回 True。

        Notes:
            - DBMS_HYBRID_SEARCH 使用的表需通过 kwargs 传入
            mysql_organization="heap"。
        """
        try:
            await asyncio.to_thread(
                self._client.create_table_with_index_params,
                table_name=collection,
                columns=columns,
                indexes=indexes,
                vidxs=vector_indexes,
                fts_idxs=fulltext_indexes,
                partitions=partitions,
                **kwargs,
            )
            return True
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | create_collection | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def create_partition(
        self,
        collection: str,
        partition_definition: str,
    ) -> bool:
        """
        创建 OceanBase 表的分区

        Args:
            collection (str): 表名称
            partition_definition (str): 可信的 OceanBase 原生分区定义。
                该字符串会原样拼接进 DDL,禁止传入不可信输入。

        Returns:
            bool: 创建分区操作的结果
        """
        if not partition_definition.strip():
            raise ValueError("partition_definition 不能为空")

        try:
            table_name = self._client.engine.dialect.identifier_preparer.quote(
                collection
            )
            await asyncio.to_thread(
                self._client.perform_raw_text_sql,
                f"ALTER TABLE {table_name} ADD PARTITION ({partition_definition})",
            )
            return True
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | create_partition | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def delete_partition(self, collection: str, partition: str) -> bool:
        """
        删除指定 OceanBase 表的分区

        Args:
            collection (str): 表名称
            partition (str): 分区名称

        Returns:
            bool: 删除分区操作的结果
        """
        try:
            quote = self._client.engine.dialect.identifier_preparer.quote
            await asyncio.to_thread(
                self._client.perform_raw_text_sql,
                f"ALTER TABLE {quote(collection)} DROP PARTITION {quote(partition)}",
            )
            return True
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | delete_partition | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def add(
        self,
        collection: str,
        partition: str,
        data: list[dict],
    ) -> None:
        """
        向指定 OceanBase 表和分区添加数据

        Args:
            collection (str): 表名称
            partition (str): 分区名称
            data (list[dict]): 要插入的数据列表,每个元素为字典格式
        """
        try:
            await asyncio.to_thread(
                self._client.insert,
                collection_name=collection,
                partition_name=partition,
                data=data,
            )
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | add | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def delete(
        self,
        collection: str,
        partition: str,
        filter: str,
    ) -> None:
        """
        从指定 OceanBase 表和分区删除满足条件的数据

        Args:
            collection (str): 表名称
            partition (str): 分区名称
            filter (str): 可信的 OceanBase SQL 过滤条件,用于指定要删除的记录
        """
        if not filter.strip():
            raise ValueError("filter 不能为空")

        try:
            await asyncio.to_thread(
                self._client.delete,
                collection_name=collection,
                partition_name=partition,
                flter=[text(filter)],
            )
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | delete | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def search(
        self,
        collection: str,
        search_data: list | dict,
        search_filter: str = "",
        partition_list: list[str] | None = None,
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[VectorSearchResult]:
        """
        在指定 OceanBase 表和分区中执行向量相似性搜索

        Args:
            collection (str): 表名称
            partition_list (list[str] | None): 分区名称列表
            search_data (list | dict): 单个稠密或稀疏查询向量,不支持批量查询
            search_filter (str): 可信的 OceanBase SQL 过滤条件,用于指定要搜索的记录
            output_fields (list[str] | None): 返回字段列表
            **kwargs: 其他搜索参数,如 anns_field、limit 和 search_params

        Notes:
            pyobvector 0.2.29 会忽略 timeout。

        Returns:
            list[VectorSearchResult]: 搜索结果,每个元素包含匹配的记录和距离分数
        """
        try:
            hits = await asyncio.to_thread(
                self._client.search,
                collection_name=collection,
                data=search_data,
                with_dist=True,
                flter=[text(search_filter)] if search_filter else None,
                partition_names=partition_list,
                output_fields=output_fields,
                **kwargs,
            )

            result = []
            for hit in hits:
                record = dict(hit)
                if output_fields is None:
                    # pyobvector 0.2.29 没有为距离字段设置固定名称。
                    # 当前实现会将距离值作为搜索结果的最后一个字段返回。
                    score_field = list(record)[-1] if record else None
                else:
                    score_fields = [
                        field for field in record if field not in output_fields
                    ]
                    score_field = score_fields[0] if len(score_fields) == 1 else None

                if score_field is None:
                    raise ValueError("搜索结果缺少唯一的距离字段")

                score = record.pop(score_field)
                if score is None:
                    raise ValueError("搜索结果的距离字段不能为空")

                try:
                    score = float(score)
                except (TypeError, ValueError) as e:
                    raise ValueError("搜索结果的距离字段必须为数值") from e

                result.append(VectorSearchResult(record=record, score=score))

            return result
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | search | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def query(
        self,
        collection: str,
        query_filter: str,
        partition_list: list[str] | None = None,
        output_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> list[VectorQueryResult]:
        """
        根据过滤条件查询数据

        Args:
            collection (str): 表名称
            query_filter (str): 可信的 OceanBase SQL 过滤条件
            partition_list (list[str] | None): 分区名称列表
            output_fields (list[str] | None): 返回字段列表
            **kwargs: 兼容参数,pyobvector 0.2.29 当前不会使用

        Notes:
            pyobvector 0.2.29 会忽略 timeout 和其他额外查询参数。

        Returns:
            list[VectorQueryResult]: 查询结果列表,包含匹配的字典记录
        """
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
            error_msg = f"{self.__class__.__name__} | query | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    def search_iterator(
        self,
        _collection: str,
        _search_data: list,
        _search_filter: str,
        _output_fields: list[str] | None,
        _partition_list: list[str] | None = None,
        **_kwargs: Any,
    ) -> list[VectorSearchResult]:
        """
        使用迭代器执行向量相似性搜索,适用于大量结果的场景,通过迭代器分批获取结果

        pyobvector 当前未提供搜索迭代器。
        """
        try:
            raise SteinsAIException("pyobvector 当前未提供搜索迭代器")
        except Exception as e:
            error_msg = f"{self.__class__.__name__} | search_iterator | 操作发生非预期错误:{e!s}"
            raise SteinsAIException(error_msg) from e

    async def hybrid_search(
        self,
        collection: str,
        body: dict[str, Any],
        **kwargs: Any,
    ) -> list[VectorSearchResult]:
        """
        执行 OceanBase 全文或混合检索

        Args:
            collection (str): 表名称
            body (dict[str, Any]): DBMS_HYBRID_SEARCH 查询体
            **kwargs: 兼容参数,pyobvector 0.2.29 当前不会使用

        Returns:
            list[VectorSearchResult]: 搜索结果,每个元素包含匹配的记录和 `_score` 相关性分数

        Notes:
            - 目标表必须以 mysql_organization="heap" 创建。
        """
        try:
            hybrid = await asyncio.to_thread(
                HybridSearch,
                engine=self._client.engine,
            )
            hits = await asyncio.to_thread(
                hybrid.search,
                index=collection,
                body=body,
                **kwargs,
            )

            result = []
            for hit in hits:
                record = dict(hit)
                score = record.pop("_score")
                result.append(VectorSearchResult(record=record, score=score))

            return result
        except Exception as e:
            error_msg = (
                f"{self.__class__.__name__} | hybrid_search | 操作发生非预期错误:{e!s}"
            )
            raise SteinsAIException(error_msg) from e

    async def close(self) -> None:
        """关闭当前 SQLAlchemy Engine"""
        await asyncio.to_thread(self._client.engine.dispose)
