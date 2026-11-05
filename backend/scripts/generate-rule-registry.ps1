param(
  [Parameter(Mandatory = $true)]
  [string]$OutputPath
)

if (Test-Path -LiteralPath $OutputPath) {
  throw "Output already exists: $OutputPath"
}
$general = @(
  @('code.swallowed_exception','静默吞异常模式','except: pass','language'),
  @('code.bare_exception','宽泛或裸异常捕获','except Exception/BaseException','language'),
  @('code.dynamic_execution','动态代码执行调用','eval/exec/compile','language'),
  @('code.hardcoded_secret','敏感凭据硬编码','Token/Secret/Key 字面量','language'),
  @('code.unmanaged_open','悬空资源泄漏','无 with 的裸 open','language'),
  @('code.dead_code_after_exit','退出语句后的死代码','return/raise 后的不可达语句','language'),
  @('code.deep_control_flow','深层控制流嵌套','多层条件或循环嵌套','language'),
  @('code.global_mutable_state','全局可变状态污染','global 声明与模块级可变修改','language'),
  @('workflow.test_collaboration_gap','业务变更缺少测试协同','业务代码修改而单元测试未协同修改','process')
)
$framework = @(
  @('api.drf_public_parameter_added','公有接口新增必填参数','DRF 公有函数或接口新增无默认值参数'),
  @('api.drf_public_parameter_removed','公有接口删除既有参数','DRF 公有函数或接口删除既有参数'),
  @('api.django_url_pattern_changed','路由映射变化','URL 模式增删改'),
  @('api.drf_viewset_action_changed','ViewSet 暴露动作变化','ViewSet HTTP 动作或方法变动'),
  @('auth.drf_permission_decorator_removed','安全装饰器剥离','关键权限装饰器删除'),
  @('auth.drf_permission_policy_downgrade','DRF 权限策略显式降级','AllowAny 或空权限策略'),
  @('auth.drf_object_permission_bypass','对象级权限过滤绕过','get_queryset 权限过滤逻辑变动'),
  @('auth.django_permission_module_changed','权限定义模块逻辑变化','permissions.py 内部逻辑自主变更'),
  @('data.django_destructive_migration','破坏性数据库迁移风险','RemoveField/DeleteModel/RunSQL'),
  @('data.django_non_null_constraint_tightened','非空约束收紧','新增 null=False 且无默认值'),
  @('data.django_raw_sql_execution','绕过 ORM 的原生 SQL','raw 或 cursor.execute'),
  @('data.django_transaction_boundary_changed','事务与并发边界变化','atomic/commit/rollback'),
  @('config.django_sensitive_settings_changed','敏感配置变化','settings.py 安全与环境常量')
)
$large_change = @('workflow.large_change_scope','大规模变更范围','修改行数、文件数、模块数、Hunk 数或依赖层跨度超过规则阈值','process')
function Make-Rule($spec, $family, $dependency, $risk, $severity, $basisKind, $level) {
  $id=$spec[0]; $name=$spec[1]; $target=$spec[2]
  [ordered]@{
    rule_id=$id; name=$name; version='v1'; rule_family=$family; lifecycle='draft'; owner='Prisk-System'
    classification=[ordered]@{
      risk_nature=$risk; dependency_level=$dependency; applicability=@('Python'); target_layer=if($id -eq 'workflow.large_change_scope'){@('change_metadata','diff_delta')}elseif($family -eq 'breaking_impact'){@('ast_syntax','diff_delta')}else{@('ast_syntax','diff_delta')}
      evidence_type=if($id -eq 'workflow.large_change_scope'){@('metric_value','symbol_pair')}elseif($family -eq 'breaking_impact'){@('code_slice','symbol_pair')}else{@('code_slice','symbol_pair')}; severity=$severity; gatekeeper=($id -eq 'auth.drf_permission_policy_downgrade' -or $id -eq 'data.django_destructive_migration'); gatekeeper_condition=if($id -eq 'auth.drf_permission_policy_downgrade'){'受保护视图被改为 AllowAny 或空权限策略时'}elseif($id -eq 'data.django_destructive_migration'){'非初始迁移中出现 RemoveField、DeleteModel 或裸 RunSQL 时'}else{$null}
    }
    rationale=[ordered]@{
      observed_problem="$target 可能在变更中引入，需要显式记录为可复核信号。"
      why_worth_detecting='帮助审查者定位需要上下文复核的变更。'
      expected_consequence='可能增加缺陷、兼容性、维护或复核成本。'
      coverage_gap='现有 v1.0.0 粗粒度演示规则未对该模式作专门定义。'
      value='为规则研究和后续实证验证提供明确、可复现的假设。'
    }
    definition=[ordered]@{
      target=$target
      trigger=('检测到与' + $target + '一致的结构或变更条件时生成 Finding。')
      trigger_features=if($id -eq 'workflow.large_change_scope'){,@(
        [ordered]@{name='total_changed_lines';source='stage03.summary.additions + stage03.summary.deletions';value_type='integer';operator='gte';threshold=$null;required=$true},
        [ordered]@{name='files_changed';source='stage03.summary.files_changed';value_type='integer';operator='gte';threshold=$null;required=$true},
        [ordered]@{name='modules_changed';source='derived.module_count';value_type='integer';operator='gte';threshold=$null;required=$false},
        [ordered]@{name='hunks_changed';source='derived.hunk_count';value_type='integer';operator='gte';threshold=$null;required=$false},
        [ordered]@{name='dependency_layer_span';source='derived.dependency_layer_span';value_type='integer';operator='gte';threshold=$null;required=$false},
        [ordered]@{name='test_collaboration_gap';source='stage03.summary.test_collaboration_gap';value_type='boolean';operator='eq';threshold=$true;required=$false}
      )}else{,@([ordered]@{name='target_pattern';source='stage04.v1.structural_objects';value_type='string';operator='contains';threshold=$target;required=$true})}
      non_trigger='无法从输入证据确认目标模式时不触发。'
      inputs=@('stage04.v1 structural objects','base/head Diff')
      finding="$id Finding，包含规则 ID、严重度、影响类型和证据位置。"
      evidence_location=@('file path','node or diff lines')
      context_slice='展示命中节点及其 Diff 前后上下文。'
      impact_type=if($risk -eq 'external_impact'){'external_impact'}else{'pr_intrinsic_risk'}
    }
    basis=[ordered]@{kind=$basisKind; references=@('待补充论文、CWE/OWASP、官方文档或项目依据')}
    limitations=[ordered]@{
      false_positive='合法场景或防御性代码可能满足结构条件。'
      false_negative='动态调用、间接配置或解析失败可能导致漏报。'
      dynamic_language='Python 动态特性可能使静态结构证据不完整。'
      does_not_decide='不直接判定缺陷、漏洞或实际运行时后果。'
      manual_review='需要结合调用方、配置、测试和业务上下文人工复核。'
    }
    validation_obligation=[ordered]@{
      level=$level; method=if($family -eq 'code_smell'){'正例、反例和边界构造样例；后续补充文献依据。'}elseif($family -eq 'backend_contract'){'NetBox 真实 PR、人工标注和已知案例。'}else{'统计稳定性及其对人工复核排序的影响。'}
      dataset=if($family -eq 'backend_contract' -or $family -eq 'breaking_impact'){'NetBox 冻结数据集；后续明确 PR 范围。'}else{'待确定的构造样例或项目数据集。'}
      oracle=if($family -eq 'backend_contract' -or $family -eq 'breaking_impact'){'人工标注与可靠历史案例。'}else{'规则定义和测试预期。'}
      metrics=if($id -eq 'workflow.large_change_scope'){@('命中频次','阈值敏感性','人工复核排序相关性')}elseif($family -eq 'backend_contract' -or $family -eq 'breaking_impact'){@('命中频次','Precision','Recall')}else{@('构造样例通过率','证据完整率')}
      acceptance_criteria='待后续验证设计确定；当前不预填验证结果。'
      unresolved_questions=@('具体引用和数据范围待补齐','误报与漏报边界待验证')
    }
  }
}
$rules=@()
foreach($s in $general){$rules += Make-Rule $s 'code_smell' $s[3] 'pr_intrinsic' 'Medium' 'literature_and_language_docs' 'literature_inherited'}
foreach($s in $framework){$isImpact=$s[0] -like 'data.django_destructive*' -or $s[0] -like 'data.django_non_null*' -or $s[0] -like 'data.django_transaction*'; $dep=if($s[0] -like 'data.django_*'){'database'}else{'framework'}; $risk=if($isImpact -or $s[0] -like 'auth.*permission*'){'external_impact'}else{'pr_intrinsic'}; $severity=if($s[0] -like 'data.django_destructive*'){'Critical'}else{'High'}; $family=if($isImpact){'breaking_impact'}else{'backend_contract'}; $rules += Make-Rule $s $family $dep $risk $severity 'framework_docs_and_project_constraints' 'empirical_required'}
$rules += Make-Rule $large_change 'breaking_impact' 'process' 'external_impact' 'High' 'software_engineering_research_and_project_data' 'empirical_required'
$doc=[ordered]@{schema_version='rule-registry.v1'; rules=$rules}
$doc | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

