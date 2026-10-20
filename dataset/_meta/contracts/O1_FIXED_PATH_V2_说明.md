# O1-S / O1-C 固定路径最简输出 V2
O1-S 仅输出 decision、slot_start；REJECT 时 slot_start=null。O1-C 仅输出 decision、allocations，ACCEPT 的每项含 request_id、slot_start，恰好覆盖全部请求且每个请求 ID 仅出现一次；REJECT 时 allocations=[]。路径来自 private/fixed_paths.json，模型不能改变路径。
评分时将最简输出与固定路径还原为完整分配，读取 private/root_case.json、private/private_truth.json，调用匹配的冻结 X2/X3 Validator 检查约束和源认证目标。private/source_reference_output.json 是原自主选路参考分配，private/reference_output.json 是 O1 最简参考答卷。
当前 O1 目标为固定路径下最小化全网碎片化；源根对象的 task_type、case_id 继续保留 X2/X3 身份，当前题型请读 identity.json/task。来源 metadata 曾继承的 X2/X3 主目标仅在 provenance 中保存，不当作 O1 的当前自主选路合同。
public/output_schema.json 是根据原冻结 O1_MINIMAL_FIXED_PATH_V2 适配器整理的格式约束，不替代科学检查。请求 ID 唯一性、频谱可行性、正确拒绝、最优性仍需相应评分器；参考 JSON 不一定是唯一最优解。
源源码版本哈希见 SCORING_VERSION_BINDINGS.json 和每例 identity.json/validator_source_sha256。模型仅接收两条原公开消息；不将评分端的公式或私有最优目标加入模型上下文。
本整理不重新求解，不修改提示词、真值或科学认证范围，不新增接口准入。
