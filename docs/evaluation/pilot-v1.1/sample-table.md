# 先导样本表

16 条，抓取日 2026-11-07。身份以 [manifest.json](manifest.json) 为准。本表的 merge commit 就是落地 diff 的头提交。落地 diff 的基提交是该合并提交的第一父提交，写在清单的 `landed_base_sha`。

这 16 个编号都不在 v1.0.0 冻结调研的 120 条里，并且全部排除出未来的 v1.4 正式评估集。三条 `base` 不是默认分支 `main`。

| 编号 | 层 | 合并时间 | base | 文件 | 行 | merge commit | 标题 |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| [23175](https://github.com/netbox-community/netbox/pull/23175) | api_serializer | 2026-09-15 | main | 6 | +74/-6 | `321a2fbf26ebcba1beb3bcbaf110351e0f0ecd04` | Fixes #23154: Correct required=False mismatch on L2VPN.type and RackType.form_factor |
| [22473](https://github.com/netbox-community/netbox/pull/22473) | api_serializer | 2026-06-23 | feature（非默认） | 3 | +29/-4 | `41f792c53b33e3bedf8a71866790ccd649d3169a` | #21367 - Add is_primary field to MAC address REST API serializer |
| [22472](https://github.com/netbox-community/netbox/pull/22472) | api_serializer | 2026-06-30 | main | 2 | +35/-1 | `7a1dfb58e302365e6b29befe054c197dee47e431` | 22154 - Remove annotation-only count fields from nested serializers |
| [23071](https://github.com/netbox-community/netbox/pull/23071) | api_serializer | 2026-09-01 | main | 4 | +164/-9 | `f66ce9818ad778eced28a8f7714217ba4c94a85a` | Closes #22989: Reference brief components for nested SerializedPKRelatedField |
| [23631](https://github.com/netbox-community/netbox/pull/23631) | api_endpoint | 2026-11-06 | main | 3 | +160/-26 | `1ab04a269de38990479f144712048c40cbc892b4` | Closes #23564: Batch cable termination lookups in cable and port REST API lists |
| [19846](https://github.com/netbox-community/netbox/pull/19846) | api_endpoint | 2025-07-16 | feature（非默认） | 11 | +56/-61 | `32fb3869a4a929c91b5889944b0d78b11a2a7e96` | Closes #19829: Move object types REST API endpoint to core app |
| [22777](https://github.com/netbox-community/netbox/pull/22777) | auth | 2026-08-11 | main | 6 | +387/-31 | `a94878aa08cf425866f56850e5d35996bf292cc3` | 22745 - Enforce object permissions on Script REST API write operations |
| [22469](https://github.com/netbox-community/netbox/pull/22469) | auth | 2026-06-19 | main | 4 | +151/-2 | `626e1ef1f8e51362b8f595783d8bfd8abcd02781` | #22439 - Restrict custom links by object-level permissions |
| [23205](https://github.com/netbox-community/netbox/pull/23205) | auth | 2026-09-24 | main | 8 | +273/-6 | `6a009845236fba7b18b51b066608b52d659daf45` | Fixes #23196: Prevent plaintext API tokens from being stored in background job results |
| [23276](https://github.com/netbox-community/netbox/pull/23276) | data | 2026-10-29 | main | 1 | +39/-0 | `ec42b5e38ca27cc55032238ed83b0f2e6a732de3` | Closes: #23260 Fix dcim.0245_consolidate_unique_constraints |
| [23429](https://github.com/netbox-community/netbox/pull/23429) | data | 2026-10-19 | main | 3 | +33/-0 | `4aeb69bd7a3e072de817659e3c638b473a3938ee` | Fixes #23425: Widen TaggedItem.object_id to a 64-bit integer |
| [21901](https://github.com/netbox-community/netbox/pull/21901) | data | 2026-04-20 | main | 8 | +295/-19 | `900f1155afb361c616f572b1bb7fbdfaacdf4f37` | 21866 Include the PostgreSQL database schema within system details |
| [23509](https://github.com/netbox-community/netbox/pull/23509) | config | 2026-10-27 | main | 4 | +2/-49 | `58b22d993158391a7d27e6c94bfdaaeac8eb1daf` | Closes #23508: Upgrade to Django REST Framework 3.18.3 |
| [21941](https://github.com/netbox-community/netbox/pull/21941) | config | 2026-04-16 | feature（非默认） | 4 | +26/-6 | `af7a35f83600d062e74cbf27eb88d4b859fcc922` | Closes #21936: Deprecate `LOGIN_REQUIRED` |
| [23606](https://github.com/netbox-community/netbox/pull/23606) | ordinary | 2026-11-05 | main | 5 | +139/-13 | `56daec7debfd51fa991b45d6a40cb592b42b669d` | Fixes #23597: Change-log port mappings created from type templates |
| [23626](https://github.com/netbox-community/netbox/pull/23626) | ordinary | 2026-11-05 | main | 2 | +37/-1 | `12da05a108fb81696940e45268f251ac3d880593` | Closes #23562: Apply `FETCH_PEERS` to ExportTemplate queryset |

完整标题和全部 SHA 在清单里。判断见 [screen.md](screen.md)。
