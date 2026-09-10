# AutoMM STATE

> 本文件由 `runtime/workflow_state.json` 渲染，请勿以手工修改本文件的方式驱动状态。

## 基本状态

- 更新时间：2026-09-10T13:57:24.825057+00:00
- 控制状态：paused
- 活动题目：CUMCM2026-C
- 当前小问：prob02
- 当前阶段：robustness

## 任务

failed=1 | succeeded=3

## 最近动作

act-90ee16ed918e4f29: poll_email

## 警告

- 本次为 agent_transport 失败后的恢复重试（前两次唤醒分别因宿主机 C: 盘 ENOSPC 与 dsh headless 传输中断而未产生响应）。本阶段产物由失败前的运行写入且未有任何 record_artifact 事务提交，本次已逐项复核完整性与数据事实并补充核验记录，未重写题面、数据与分解结论。
- 本动作上下文 question_id 为 prob01，故本次只能把 artifacts.problem_understanding 逻辑标记记录到 prob01；prob02~prob04 的共享题面理解文档已就绪，其对应逻辑标记将在各小问依次进入 problem_understanding 阶段时由相应动作记录。
- 歧义 A9 已核实成立：附件时间标签为 0:10…0:00+1（时段右端点），而附件 5 模板时间段标签自 0:10-0:20 起，存在一个间隔的整体偏移，交付阶段必须先统一口径再填写，不得直接按标签逐行对齐。
- dependency_graph.yaml 的 conclusion_id/version/content_hash 仍为空，属预期状态，将由各小问 record_conclusion 时回填。
- dry 判定依据为 all_candidates_decided（全部 18 条候选均已 used/rejected），本轮未触及 25 条或 30 分钟上限，也未出现无新假设族的迹象；prob02~prob04 的文献方向（紧急购电/违约结算、滚动调整、波动电价随机或鲁棒优化）与本轮不同，届时须更换术语与证据路径重新开轮，不得复用本轮查询。
- 题面歧义 A9 已核实为附件时间标签 0:10…0:00+1（时段右端点）与附件 5 模板时段标签自 0:10-0:20 起的整体偏移，本轮确认其无文献可支撑；交付阶段必须先统一口径再填写，不得按标签逐行对齐。
- 关键假设 P1（0:00 与 24:00 储电量共同取 6000 kWh）、P3/P4（90% 解释为单向效率、5000 kW 按 833.33 kWh/10min 折算并统一计量侧）目前只有题面硬约束与储能技术范围对照（ref-prob01-storage-luo-2015），没有同设备实测来源；进入 assumption_definition 时必须保留为 project_assumption，并由 sanity/robustness 对两种效率口径做对照。
- 本轮为文献检索性质：未运行任何计算、未修改原始数据与附件；新增文件仅限 prob01 文献产物、题目引用表，以及 runtime/research_probe/ 下 4 个临时检索与轮次驱动探针（Crossref/OpenAlex/Semantic Scholar 元数据查询），后者不构成正式产物。
- Semantic Scholar 公共接口在本轮出现 HTTP 429 限流，相关摘要改用 OpenAlex 与出版方/机构仓储权威页面核验；Crossref 与 OpenAlex 全程可用，未使用搜索摘要作为引用依据，未伪造任何 DOI、作者或结论。
- 关键假设 asm-02（终端共同取 6000 kWh）、asm-03（弃光不反送）、asm-04（单向 90%）、asm-05（833.33 kWh 与计量侧）只有题面硬约束、附录 1 数据与技术范围对照，没有同设备实测来源，已按项目假设处理；必须由 sanity/robustness 对 asm-02 端点取值 {4800,6000,7200} 以及 asm-04/asm-05 的效率与计量口径各做一组对照。
- asm-10 忽略电池退化成本会高估频繁充放电的经济性并使全天购电费偏低，须在论文边界章节声明；Grimaldi 2024（摘要级）指出退化项可使年净收益变化约 13%~24%，本题无循环/老化/温度数据故不建模。
- asm-07 限定 prob01 结果为单日代表日结论，不可外推全年；prob02~prob04 的电价与预测结构不同，须更换术语与证据路径重新开文献轮次，不得复用本轮查询。
- I3 中「弃光=0 可行」仅为 agent_inference，尚未经任何优化证实；formulation/computation 必须验证，若实际出现弃光须给出发生时段与原因（如 SOC 已达上界且充电功率受限）。
- 本动作未创建任何计算任务、未修改原始数据与附件；仅执行只读数据汇总探针（附件1 与附件5 模板结构）与静态校验。
- asm-12 的交付标签重写规则与附件5 模板字面标签不一致，属有意为之的口径统一；若 delivery 阶段选择保留模板原标签，必须在论文与 result1.xlsx 中同步记录映射关系，不得静默改变。
- open_item I3（预期存在 curtail_t≡0 的可行调度）仍未证实：附件 1 全天正余电 6247.96 kWh、单时段最大余电 352.92 kWh（<833.33 kWh）、余电集中在 t=58..87，formulation 不预设该结论，computation 必须报告实际弃光总量，若>0 须给出发生时段与原因（如 SOC 达上界且充电功率受限）。
- open_item I2（144 个 0-1 的 MILP 应可证最优）仅为推断，须由 computation 以 solver status、best bound 与 gap 证实；若超时或 gap 缺失，按 PASS_WITH_WARNING 保留技术债说明，不得直接人工阻塞。
- asm-02（E_0=E_144=6000）、asm-04（单向 90%）、asm-05（833.33 kWh 与并网点侧计量）均为 project_assumption，缺少同设备实测来源；必须由 robustness 对 E_0∈{4800,6000,7200} 以及往返效率 0.9（单侧 0.9487）与电池侧计量口径各做一组对照，并报告 Cost_day 变化方向与幅度。
- I1 的『LP 松弛最优值等于 MILP 最优值』仅是 6470 个随机小规模实例上的数值证据，不是定理，且未在真实 144 时段实例上验证；不得据此省略 0-1、不得外推到 prob02~prob04。
- LP 松弛在退化实例中存在多重最优，求解器可能返回 min(C_t,D_t)>0 的点；主模型保留 (C6) 后必须复算，交付的 C_t/D_t 只能取自 MILP 解或经互斥后处理的解。
- asm-12 的交付标签重写规则与附件 5 模板字面标签不一致，属有意为之的口径统一；若交付阶段选择保留模板原标签，必须在论文与 result1.xlsx 中同步记录映射关系，不得静默改变。
- asm-10（不建模电池退化）会高估频繁充放电的经济性、使 Cost_day 偏低，须在论文边界章节声明；本模型亦不反送、不含上网电价，若实际存在正上网电价会高估购电费。
- asm-07 限定 prob01 结果为单日代表日结论，不可外推全年；prob02~prob04 的电价与预测结构不同（紧急购电结算、计划-调整违约、波动电价），模型与文献路径必须重建，仅继承本版本的设备层结构与符号。
- 本阶段未求解 144 时段竞赛实例：M1 在真实数据上的 Cost_day、弃光总量（open_item I3，若>0 须给时段与原因）、solver status/best bound/gap（open_item I2）以及 LP 与 MILP 目标差都仍待 computation 阶段的隔离 task 给出，implementation 不做任何数值结论。
- M2 为删除 (C6) 的真松弛，其最优值必然 ≤ M1，但 LP 原始解在退化实例中可能同时充放电；交付的 C_t/D_t 只能取 milp 模式解，若 computation 报告 LP 严格更优或 MILP 解 min(C_t,D_t)>1e-9，必须回 mathematical_formulation 复核，不得直接交付。
- result1.xlsx 的时间标签按 asm-12 有意重写为物理区间，与附件 5 模板字面标签（整体偏移一个时段）不一致；若交付阶段改回模板原标签，必须在论文与结果文件中同步记录映射关系，不得静默改变。
- task_id 由 code_hash/config_hash/input_hash/假设与公式版本/backend 共同决定；implementation.md §7 的 13bf04ee604e54581fa2 仅在全部身份字段不变时成立，任何代码或配置改动都会产生新 task_id，重跑也必须使用新的 output_directory 且不得覆盖旧 attempt。
- runtime/tmp/ 下的 prob01_smoke/ 与 prob01_task_spec_probe.py 只是接口探针与可重建临时物，不构成正式产物链，也不代表竞赛实例结果；正式结果只能来自 computation 阶段 supervised worker 的隔离 task 输出目录。
- 本环境 scipy 为 1.18.1 且 HiGHS 可用、pulp 未安装；代码只依赖 scipy.optimize.milp，若计算环境缺少 scipy≥1.11 或求解器异常，按 code_runtime/infrastructure_transient 路由重试，不得直接人工阻塞。
- 默认 mip_rel_gap=1e-4：若 300 s 内只得到可行 incumbent 而未证全局最优（status=1），代码仍以退出码 0 交付并保留 best bound 与 gap，由 sanity 按 PASS_WITH_WARNING 处理并保留技术债说明。
- 可用内存仅约 0.96~1.02 GB（总 15.74 GB，占用 93.9%），effective_workers 被压到 1：本轮 MILP 单任务可以启动，但若 worker 或 HiGHS 因内存压力被回收/异常退出，应按 infrastructure_transient 或 code_runtime 路由重试并在重试时释放内存，不得直接人工阻塞。
- task_id=13bf04ee604e54581fa2 的身份字段（code_hash/config_hash/input_hash/假设与公式版本/backend）已核验未变；本动作之后若需重跑或调整代码/配置/时限/gap，必须产生新 task_id 并使用新 output_directory，禁止覆盖本 attempt 结果。
- 本动作未产出任何计算结果：open_item I2（solver status/best bound/gap）与 I3（弃光总量与发生时段）仍待该 task 终态；M2（LP 真松弛）仅作下界与退化诊断，交付的 C_t/D_t 只能取自 M1（milp）解。
- runtime/tmp/prob01_resource_spec_probe.py 与 runtime/tmp/prob01_resource_probe.json 只是资源探针与可重建临时物，不构成正式产物链。
- prob01 level_1_4: L1-L4 硬门禁全部通过：task 13bf04ee604e54581fa2 终态 succeeded(rc=0)、7 个交付产物非空且 hash/数据完整性可追溯（data/附件1.xlsx 与原始附件逐字节相同）；独立回代 (C1)~(C8) 得平衡残差 2.27e-13、SOC 残差 1.82e-12、终端残差 0、互斥违反 0、边界/功率/非负性违反 0、NaN/Inf 0；solver status=0、objective=best_bound=35126.94858928963、mip_gap=0.0、node_count=1 证实 I2；curtail_total=0.0 证实 I3；Cost_day=35126.948589289634 元落在独立解析界 [20622.7344, 48052.0466] 内；实现与 formulation (C1)~(C8) 语义逐条一致、big-M=Pbar 由 (C5) 导出、量纲与能量守恒闭合；result1.xlsx 按 asm-12 重写为物理区间标签且与 solution 一致；8 个引用 ID 在文献池与引用表均 verified+used。判定 PASS_WITH_WARNING 仅因 6 项非阻断技术债：交付 y_binary 一个 −1.52e-15 噪声、formulation §3.6 约束计数措辞不准、asm-02/04/05 待 robustness 对照、asm-12 标签口径需交付阶段登记、E 贴运行上下界需敏感性说明、asm-10/07/03 边界需论文声明。无失败类型、无需回退。
- 交付文件 solution.csv/solution.json 的 y_binary 列有一个取值 −1.52e-15（其余为精确 0/1，整数性最大偏差 7.5e-15）：属求解器数值噪声，不违反 y≥0、不影响任何指标；建议交付阶段把 |y|<1e-9 归零。
- formulation.md §3.6 写「等式约束 288 条，不等式约束约 720 条」，而实现报告为 289 等式（288 + 终端 E_144）/288 不等式：模型语义逐条一致，仅文档计数不准，建议下一公式版本修正措辞，不构成 formulation/实现不一致。
- asm-02（E_0=E_144=6000）、asm-04（单向 90%）、asm-05（并网点侧计量、833.33 kWh）仍为 project_assumption，缺少同设备实测来源；robustness 阶段必须完成 E_0∈{4800,6000,7200}、往返效率 0.9（单侧 0.9487）与电池侧计量口径的对照，并报告 Cost_day 变化方向与幅度。
- asm-12 的时间标签重写规则与附件 5 模板字面标签（整体偏移一个时段）不一致，属有意统一；交付阶段若改回模板原标签，必须在论文与 result1.xlsx 中同步记录映射关系，不得静默改变。
- 弃光=0 使 E 同时贴到运行上界 10800（t=34,35,87,91~108）与下界 1200（t=124~131），最优解受储电量边界强约束；robustness 应报告 E_0/Emax 端点取值对 Cost_day 的敏感性，避免把「贴界」误读为设备余量。
- asm-10 不建模电池退化会高估频繁充放电经济性、使 Cost_day 偏低；asm-07 仅代表日不外推全年；asm-03 不反送、无上网电价。三条须在论文边界章节声明（已在 formulation §10 登记，本报告复核确认）。
- 视觉复核由程序化审计完成而非像素级目检：本环境最终响应模型不支持图像输入（read_image 返回模型不支持图像）。审计覆盖缺字/裁切/重叠/标签图例/配色/三维配套，但不能替代对图意误导性的人工判断；建议论文定稿团队在有图像能力的终端对 9 张 PNG 再做一次目检，本阶段结论不因此降级。
- 上游技术债随图移交 robustness：asm-02（E_0=E_144=6000）、asm-04/asm-05（单向 90% 效率与并网点侧计量口径）须按 E_0∈{4800,6000,7200}、往返 0.9（单侧 0.9487）与电池侧口径做对照；asm-12 标签口径与附件 5 模板存在整体一个时段偏移（有意统一），交付阶段须登记映射。
- 弃光=0 使 E 同时贴运行上界 10800 与下界 1200，最优解受边界强约束；图中已以对照线标注并在 caption 声明不得解读为设备余量，robustness 应报告端点取值对 Cost_day 的敏感性。
- asm-10（不计电池退化会高估频繁充放电经济性、使 Cost_day 偏低）、asm-07（仅代表日、不外推全年）、asm-03（不反送、无上网电价）须在论文边界章节声明。
- 交付 y_binary 存在 −1.52e-15 数值噪声（不影响任何指标），建议交付阶段对 |y|<1e-9 归零；图表未用 y_binary 做数值标注，故不受影响。
- 本动作是 robustness 阶段的第一步（预注册 + 提交隔离 task）：下一次唤醒 Runner 将命中 queued 分支执行 start_queued 启动 supervised worker；任务终态后的 robustness 唤醒必须按 plan.md §6 执行聚合（复核 summary.json 的 C1-C6 与基线锚定、运行 --register-figures 登记敏感性图、写 stability_conclusion.md、经 commands 记录 record_figure_review 与 record_optional_stage），否则 robustness 无法闭合、小问无法 locally_completed。
- 正式扫描规模为 43 情景 × (MILP+LP) + 200 次蒙特卡洛 MILP，按 probe 实测单次求解约 0.1 s 估计应在 1 分钟量级内完成，远低于 900 s 超时；但当前可用内存仅约 1 GB（effective_workers=1），若 worker 或 HiGHS 被内存压力回收，按 infrastructure_transient / code_runtime 路由重试（新 attempt），不得直接人工阻塞。
- probe 中 C4a 无弃光占比 0.8 只是含无储能参照的 5 情景子集结果，不构成正式判定；正式 C4 以 43 情景为准（无储能参照必然产生 6247.96 kWh 弃光）。
- asm-12 的整体错位（循环移位 1 个时段）仅使 Cost_day 变化 -0.100 元（-2.85e-6，probe 实测），说明其对最优费用影响极小；但其对 result1.xlsx 行序/标签的影响仍须在交付阶段按计划登记映射，不得静默改变。
- 基线最优解贴运行上下界（弃光=0 使 E 同时贴 10800 与 1200）：B 组端点情景将给出 E0∈{4800,6000,7200} 与 Emax∈{9600,10800,12000} 的费用方向与幅度；报告须声明「贴界不等于设备余量」，不得据此推断设备裕度。
- 若正式扫描出现 C1 失败（任一情景 status≠0 或硬门禁违反），脚本以退出码 3 结束、task 记为 failed，按 plan.md §2 判定规则应路由回 mathematical_formulation 或 implementation，不得记录 robustness completed 或进入 Level 6。
- robustness 的 Level 6 sanity 由 sanity-checker 在 robustness 记 completed 后执行（workflow.py 的 P3 分支），本 Agent 不自评、不代签。
- 下一次唤醒 Runner 将命中 queued 分支 start_queued 启动 66b12e7cd283813a098e；任务终态后的 robustness 唤醒必须按 plan.md §6 与 task_spec_v002.yaml 执行聚合，否则 robustness 无法闭合、小问无法 locally_completed、也进不了 Level 6：①复核 robustness_v002/summary.json 的 C1–C6 与基线锚定（35126.94858928963 元，绝对容差 1e-6）；②以 `prob01_robustness.py --register-figures --output problems/CUMCM2026-C/prob01/versions/assumption_v001/robustness_v002` 登记敏感性图到 figures.yaml；③写 stability_conclusion.md；④经 commands 记录 record_figure_review（每张图）与 record_optional_stage(stage=robustness, decision=completed, reason=...)。
- 输出目录已变更：被接受的扫描只在 robustness_v002/；robustness/ 下的同名数值文件是 attempt-001 失败残留，不得作为图源（source_data）或结论引用，聚合动作的 --register-figures 与 stability_conclusion.md 必须指向 robustness_v002/，而不是 robustness/。
- attempt-001 残留（**非权威，仅供预判，不得直接引用为结论**）显示该预注册扫描的判定倾向为 fragile：C1 通过（43/43 status=0、max mip_gap=0、无硬门禁违反、锚定偏差 7.276e-12）、C2 通过，但 C3 因 E_load_±20%（-36.92%/+44.99%）超出 25% 包络而不通过、C4a 无弃光占比 88.4%（<90%，其中无储能参照 A2 必然弃光 6247.96 kWh）、C6 的 95% 区间宽度 +28.21%（>15%）不通过；方向核验 41/43（A3 电池侧计量实测 -0.072% 与预测「上升」相反，B3 Emax=9600 实测 +2.575% 与预测「不升」相反）。若新任务复现，聚合动作应按 plan.md §2 记 robustness completed，并在结论、论文边界与 Level 6 报告列出脆弱参数、方向与幅度；C4a 的口径问题（是否把必然弃光的无储能参照计入分母）只能在 stability_conclusion.md 中标注为 post-hoc 解释，**不得**事后修改预注册阈值。
- task 身份字段含 code_hash：robustness_v002 与 66b12e7cd283813a098e 绑定，任何后续代码/配置/时限/gap 改动都会再产生新 task_id 与新输出目录；禁止覆盖该 task 的结果，也禁止把 attempt-001 的残留改判为成功。
- 内存风险仍在：可用内存约 1 GB（effective_workers=1）。attempt-001 实测 43×(MILP+LP)+200 次蒙特卡洛约 38 s 完成，远低于 900 s 超时；若 worker 或 HiGHS 因内存压力被回收/异常退出，按 infrastructure_transient 或 code_runtime 路由新 attempt（新输出目录）重试，不得直接人工阻塞。
- robustness 的 Level 6 sanity 由 sanity-checker 在本阶段记 completed 后执行（workflow.py P3 分支），本 Agent 不自评、不代签。
- verdict = fragile 必须写入论文边界章节与 Level 6 报告：load 是首要脆弱参数，±20% 预测误差对应费用区间 [22159.431, 50929.885] 元（−36.916%/+44.988%），25% 包络在需求侧 ±20% 误差下不成立。
- C4(a)/C4(b) 的口径问题只能在 stability_conclusion.md §8 中作为 post-hoc 解释：剔除刻意构造的无储能参照后 C4(a)=38/42=90.476% 通过；按每情景同条件参照重算后 K3 全部成立。不得据此回改预注册阈值或判据。
- 技术债 R2：C3 包络组实现未包含 C_efficiency（η 的 ±5%/±10% 与往返口径），与 plan.md §2 文本不一致；实测 η 最大偏差 7.861%，纳入也不改变 verdict，建议下一版本显式修正包络集合。
- 技术债 R3：预注册方向预测 B3 的 not_up 与「收紧上界则费用不降」的可行域单调性矛盾，属预测登记缺陷而非数值不稳定。
- 技术债 R4：本环境最终响应模型不支持图像输入，6 张图采用与上游 visualization 阶段一致的程序化审计（分辨率、非纯色、边界暗像素、色彩丰富度、墨迹占比，并与 figures.yaml / figure_index.json / summary.json 交叉核对），不能替代人眼对图意误导性的判断，建议在有图像能力的终端对全部 15 张 PNG 补一次目检。
- stability_conclusion.md 的正文由此前因 JSON 响应不可解析而失败的唤醒写入（未提交任何 record 事务）；本次已逐项复核其数值、通道与来源，并修正两处口径笔误，修正不改变任何结论。
- 上游技术债随结论移交交付与论文阶段：U1 交付 y_binary 的 −1.52e-15 噪声需把 |y|<1e-9 归零；U2 formulation.md §3.6 约束计数措辞；U3 asm-12 时间标签映射须在 result1.xlsx 与论文同步登记；U4 asm-10 不建模退化使 Cost_day 偏低、asm-07 仅代表日不外推全年、asm-03 不反送且无上网电价，三者须在边界章节声明。
- 环境约束：可用内存约 1 GB、effective_workers=1；本次扫描 34.65 s 完成、未受影响，但重跑或扩样仍应按 infrastructure_transient / code_runtime 路由新 attempt 与新输出目录，禁止覆盖 robustness_v002/。
- Level 6 sanity 由 sanity-checker 在本阶段记 completed 后执行，本 Agent 不自评、不代签；若 Level 6 判定需修订，按 failure_class 路由回 mathematical_formulation 或 implementation。
- prob01 level_6: Level 6 独立复核通过（PASS_WITH_WARNING）：robustness 权威产物 task 66b12e7cd283813a098e 的 43 情景×(MILP+LP)+200 次蒙特卡洛完整可追溯，C1 数值合法性（43/43 status=0、max mip_gap=0、最坏残差 平衡 3.41e-12/SOC 2.73e-12/互斥 1.57e-12、NaN/Inf=0）、基线锚定（|Δ|=7.276e-12 元 ≤1e-6）、C2 口径稳定性（最大 −3.773%）与方向核验（41/43）均通过；预注册 verdict=fragile 成立（C3 因 load ±20% −36.916%/+44.988% 超出 25% 包络），C4(a)/C4(b)/C6 宽度未通过项已在 stability_conclusion.md 如实登记并经独立同条件口径复核（K3 42/42 成立）。无硬门禁失败，故不路由回退；技术债 R1-R6 与 U1-U4 已登记并移交论文边界与交付阶段。
- verdict=fragile 必须写入论文边界章节与交付说明：load 是首要脆弱参数，±20% 预测误差对应 Cost_day∈[22159.431, 50929.885] 元（−36.916%/+44.988%），组合压力 F1 +73.986%、F3 +68.539%，25% 费用包络在需求侧 ±20% 误差下不成立。
- R6：robustness_v002/stability_conclusion.md §10 的 stable_id 笔误（6ec5b3f7fb ≠ 6ec5b3b7fb）在交付阶段修正或加注；figures.yaml 登记本身正确。
- R4：本环境不支持图像输入，6 张敏感性图仅程序化审计通过，不能替代人眼对图意误导性的判断，建议在有图像能力的终端对接受版本 15 张 PNG 补一次目检。
- R2：C3 包络组实现未包含 C_efficiency（η）；纳入后最大 7.861% 不改变 verdict，建议下一版本显式修正包络集合。R3：B3 预注册方向 not_up 属登记缺陷。
- C4(a)/C4(b) 口径须按「预注册口径未通过、同条件口径复核通过」双记，不得据此回改 plan.md 的预注册阈值或 verdict。
- 上游技术债随结论移交交付与论文阶段：U1 交付 y_binary |y|<1e-9 归零；U2 formulation §3.6 约束计数措辞；U3 asm-12 标签映射须在 result1.xlsx 与论文同步登记；U4 asm-10/07/03 边界声明。
- 环境约束：可用内存约 1 GB、effective_workers=1；本次扫描 34.65 s 未受影响，重跑或扩样按 infrastructure_transient/code_runtime 路由新 attempt 与新输出目录，禁止覆盖 robustness_v002/。
- 本阶段文档由此前 agent_transport 失败前的运行写入且未提交任何 record_artifact 事务；本次唤醒按恢复策略复用已有产物，只做只读复核与一处口径澄清，未重写题面、数据与分解结论。未运行任何计算、未修改任何原始数据与附件。
- runtime/tmp/prob02_understanding_verify.py、prob02_understanding_verify.json、prob02_template_label_probe.py 只是只读探测探针与可重建临时物，不构成正式产物链，也不代表任何计算结果。
- A2（跨日储能边界=日循环或连续，决定 2025-02-01 0:00 的储能初值与全年可行性）与 A10（交付范围自 2025-02-01 起的原因）仍未解决，必须在 assumption_definition 固定后再进入 formulation。
- A3（0:00 制定计划时的信息集：负载/光伏完全信息 vs 预测）直接决定紧急购电是否发生，属本问模型性质的核心歧义，本阶段未固定，须在文献与假设阶段显式处理。
- A4（余电处理：弃光/上网）、A5（互斥建模与 334 天 × 144 时段规模可解性）、A11（供电充足计量口径与紧急购电时段粒度）仍待后续阶段研究；本阶段未预设任何结论。
- A13 补充相关：附件 1 电价已核验为 2025 全年日均代表日曲线，本问按题面直接使用该曲线，其统计含义须在论文注明，不得与附件 4 的逐日波动电价混淆；A14（效率作用位置与 5000 kW 计量侧）随 H5 继承，须在假设/公式阶段固定。
- 交付模板时段标签整体偏移（A9）及字面笔误 7:0-7:10 必须在交付阶段按统一口径填写并登记映射关系，不得静默按模板标签逐行对齐。
- 符号 D（交付天数 334）与 D_dt（储能放电量）字面相近，虽非同名冲突，建议公式阶段避免单独用 D 表示天数或加注区分，以免跨小问阅读歧义。
- prob03 与 prob04 的 shared/problem_understanding.md 已存在但对应 artifacts 标记仍为 false，属预期状态；其文献方向（预报驱动的计划—调整、波动电价随机/鲁棒优化）与本问不同，进入各自阶段时须更换术语与证据路径。
- dry 判定依据为 all_candidates_decided（全部 22 条候选均已 used/rejected），本轮未触及 25 条上限，也未出现无新假设族的迹象；若 assumption/formulation 决定引入预报/不确定性（随机或鲁棒）或违约结算模型，必须更换术语与证据路径重新开轮，不得复用本轮查询。
- A3（0:00 制定计划时的信息集）是 prob02 的模型性质核心：若取完美信息（附件 2 实际负载/光伏已知），则 u>0 只在物理不可行时出现，5 倍电价退化为对不可行性的惩罚；若取预报口径，则 u 的规模取决于预报误差（ref-prob02-pvforecast-mayer-2021 仅提供「预测≠实际」的定性前提，不能给出误差量级）。文献不能裁决该点，必须在 assumption_definition 固定并绑定引用，不得由 formulation 或 computation 自行假定。
- A2（跨日储能边界=日循环或连续）直接决定 334 天是否可逐日解耦：取日循环则本问分解为 334 个独立 144 时段 MILP（与 prob01 同量级），取连续则需整体长时段模型与分解或滚动策略。文献只提供「日循环是常见设定」与「边界处理影响结果」的先例，不能决定取值，必须在 assumption_definition 固定，并说明 2025-02-01 0:00 初值（A10）的设定理由。
- 7 条题录级来源（含 han-2025、ma-2022、minh-2024 三条 A 级期刊）因出版方页面 403 或数据库无摘要而只完成题录级核验；它们只支撑题名级主张，不得用于任何定量或公式细节；后续若需其方法细节，必须换用可获取正文的权威页面重新核验，或改用摘要级来源。
- 本轮为文献检索性质：未运行任何计算、未创建计算 task、未修改原始数据与附件；新增文件仅限 prob02 文献产物、题目引用表，以及 runtime/research_probe/ 下 5 个临时检索与核验探针（crossref_search.py 复用、openalex_search_prob02.py、openalex_ta_search_prob02.py、doi_check_prob02.py、openalex_abstracts_prob02.py、run_prob02_round.py、semantic scholar 摘要查询），后者不构成正式产物链。
- 本轮 ScienceDirect 页面返回 403，故未使用出版方正文；Elsevier 系列条目多无公开摘要，相关条目一律标记 metadata_only 并限制主张范围。Semantic Scholar 可用于题录交叉核对但部分条目无摘要；Crossref 与 OpenAlex 全程可用。所有 DOI 均由 Crossref 解析确认身份，未使用搜索摘要作为引用依据，未伪造任何 DOI、作者、期刊或结论。
- ref-prob02-marketdesign-hu-2018 与 ref-prob02-voll-leahy-2011 支持「价格上限/未供电定价应与失负荷价值(VOLL)对照」，但 VOLL 的具体数值依赖系统与用户构成，不能迁移到本题；题面 5 倍紧急电价是硬约束，文献只提供其机制定位，不构成合理性证明。
- prob03（计划—调整与上下调偏差结算）与 prob04（波动电价随机/鲁棒优化）的文献方向与本轮不同：prob03 需补充上下调偏差/违约电价结算与预报更新的证据路径，prob04 需补充电价随机过程/鲁棒优化的证据路径，进入各自 literatur_review 时必须更换术语与证据路径重新开轮。
- 上游技术债随结论移交：prob01 的 asm-02/04/05（端点储电量、单向 90% 效率、5000 kW 计量侧）与 asm-10/07/03（不建模退化、仅代表日不外推全年、不反送且无上网电价）在本问继续适用，仍属 project_assumption，须在 prob02 假设与论文边界章节沿用声明；弃光（A4）若在 prob02 实际发生，须按段报告时段与原因。
- A3 口径张力：题面问题2 的数据清单只列「附件1 的电价和附件2 的数据」，未列附件3；本版本把 0:00 预报纳入计划信息集属口径选择（已写入 version.yaml 的 boundary_note 与 assumptions.md 第 2、6 节）。论文边界章节与交付说明必须显式声明该口径并给出 alt-01 完全信息对照，不得静默采用。
- 完全信息口径（alt-01）下紧急购电恒为 0：因此主模型所有的非零紧急购电都来自 0:00 预报误差，一旦附件3 与附件2 的时段/日期对齐口径出错，表3 与全年紧急购电量会被系统性改变。formulation/computation 必须固定并核验「预报 k 小时→整点区间→10 分钟时段」的展开规则（open_item I5）。
- 本次探针只完成附件3 的 0:00 报表同日对齐核验（14.89% < 16.53% < 16.49%）；6:00/12:00/18:00 报表的跨日展开与对齐属 prob03，本问不得引用本次探针中这三项的误差数值。
- 日循环边界在题面问题2 未明写（问题1 才明写两端相等）：本版本按表2 逐日交付两端储电量与逐日可解性取日循环，alt-03（连续跨日、1 月预热）保留为 robustness 对照；若 robustness 显示连续口径更贴合题面，须新建假设版本而不是就地修改。
- 执行层口径（asm-07：储能按 0:00 计划执行、紧急购电是唯一补救手段）会放大紧急购电量；alt-06（实际数据下实时再调度储能、计划购电量不变）只能作为 ablation，不得进入主模型，也不得在结果出现后替换主口径。
- alt-02 的误差统计（11056 kWh/日）等数据事实来自 runtime/tmp 下的只读探针脚本与 json，属可重建临时物，不构成正式产物链，也不代表任何优化计算结果。
- A9 标签口径：附件2/附件4 为右端点标签，附件5 result2.xlsx 标签整体后移一个间隔且含字面笔误 7:0-7:10（应为 7:00-7:10）；交付阶段必须统一口径、登记映射关系，并在 result2.xlsx 与论文中同步，不得静默改变。
- 本动作未运行任何计算、未创建任何计算 task、未修改原始数据与附件；新增文件仅本版本的两份产物与 runtime/tmp 下 6 个只读探针脚本及其输出（prob02_assumption_probe / prob02_info_probe / prob02_alignment_probe / prob02_forecast_probe / prob02_template_probe / prob02_pdf_* ），后者不构成正式产物链。
- 口径张力（最高优先）：题面问题 2 的数据清单只列『附件 1 的电价和附件 2 的数据』，本模型按 asm-02 把附件 3 的 0:00 预报纳入计划信息集；若改用附件 2 实际值（alt-01）则 u≡0、表 3 全为 0、紧急购电机制退化为空。论文边界章节与交付说明必须显式声明本口径并给出 alt-01 对照，不得在结果出来后改口径。
- asm-03 缺口式中的 curtail 必须按执行层实际弃光实现（缺口时段为 0），唯一闭式为 formulation.md 式 (R)：s=κ*+(pv−pvfc)dt、u=(−s)⁺、κ_act=s⁺；若误取计划层 κ*，会在 272 个不可避免弃光时段与弃光并存地产生紧急购电并系统性高估紧急购电量。
- 计划层不得使用实际 pv（信息集约束）：asm-05 的 min Σ(price·q+5·price·u) 在本版本实现为『计划层 min Σ price·q + 执行层 u 闭式 + Cost_total 评估』；把实际 pv 写进计划层目标或平衡即未来信息泄漏，且与 alt-01 混同。
- 全天购电费口径歧义 A-D1：result2.xlsx 与论文表 1 的『全天购电量/全天购电费』本版本取计划口径（Q_plan/Cost_plan，与 asm-04 门禁一致）；交付阶段必须登记该映射并同时给出含紧急购电费的 Cost_total，不得只给一个数。
- HiGHS 默认 mip_rel_gap=1e-4 会把 gap 内的可行解报为 status=0（本阶段以同一随机实例实测到 0.319 元的假优差）；implementation 必须在任务规格中显式设定 mip_rel_gap（建议 0 或 ≤1e-6）并同时报告 best_bound 与 mip_gap，否则不得宣称逐日全局最优。
- assumption_v001 的 I1 引用的是小时级预报缺口（如 2025-06-21 为 3 618.4 kWh），与本阶段逐 10 分钟判定的正部合计（3 812.266 kWh）不同；因 Σ(x)⁺≥(Σx)⁺ 二者必然不等，交付与表 3 一律以逐 10 分钟判定为准，勿混用两套数。
- 全局符号表只为 curtail_t 与 y_t 登记了 prob01 的单日形式；本版本按表头约定『带日期下标的符号与单日符号表示同一物理量』使用 κ_dt 与 y_dt（含义未变、未改动 global_symbols.yaml），建议 prob02 结论归档时补登记这两行；D（天数 334）与 D_dt（放电量）全文已按下标区分。
- 表 3 的紧急购电上界是逐 10 分钟预报缺口（还需扣掉 κ*），不是 u 的预测值；u=0 的日期必须显式登记为 0；交付窗口『零弃光』的预期必须放弃：不可避免弃光在 27 天 272 时段（预报口径）/34 天 241 时段（实际口径）必然发生，κ（计划层）与 κ_act（执行层）两个层次不得混用。
- 计划层可能退化（多个同费用最优解、C/D 不同），交付的 C/D 必须取自 MILP 解或经互斥后处理，并登记所交付解的选择规则、solver 版本与 seed；不同最优解会给出不同的 κ*/u/κ_act 明细。
- 附件 5『紧急购电量』模板每天只预留 3 行示例；实际 334 天中部分日期的紧急购电段数可能为 0 或 >3，交付脚本必须按实际段数增删行且日期列只在首段出现，不得因模板行数限制丢弃或错并段。
- 口径张力（最高优先）：题面问题 2 的数据清单只列「附件 1 的电价和附件 2 的数据」，本实现按 asm-02 把附件 3 的 0:00 预报纳入计划信息集；若改用附件 2 实际值（alt-01）则 u≡0、表 3 全为 0。论文边界章节与交付说明必须显式声明本口径并给出 alt-01 对照，不得在结果出来后改口径。
- 执行层必须按式 (R) 实现：asm-03 缺口式中的 curtail 若误取计划层 κ*，会在不可避免弃光的 272 个预报时段（实际口径 241）同时产生紧急购电与弃光，系统性高估紧急购电量；本实现已按 s=κ*+(pv−pvfc)dt、u=(−s)⁺、κ_act=s⁺ 落地。
- 计划层不得使用实际 pv（信息集约束）：把实际 pv 写入计划层目标或平衡即未来信息泄漏，并使 u≡0，与 alt-01 混同。
- 全天购电量/全天购电费口径歧义 A-D1：本实现取计划口径（Q_plan/Cost_plan，与 asm-04 门禁一致）；交付阶段必须登记该映射并同时单独给出含紧急购电费的 Cost_total，不得只给一个数。
- HiGHS 默认 mip_rel_gap=1e-4 会把 gap 内可行解报为 status=0；本实现已显式设 1e-6 并报告 best_bound/mip_gap，但若某日 status=1 或 gap 未闭合，须按 PASS_WITH_WARNING 保留技术债并说明未证该日全局最优，不得仅凭 status=0 宣称全局最优。
- 计划层在退化情形下可能有多个同费用最优解（C/D 不同）；交付的 C/D 只能取自 M1 解，且须登记所交付解的选择规则、solver 版本与 seed；不同最优解会给出不同的 κ*/u/κ_act 明细。
- 不可避免弃光在交付窗口必然发生（预报口径 272 时段/27 天、实际口径 241 时段/34 天），「零弃光」预期必须放弃；计划层 κ 与执行层 κ_act 两个层次不得混用，表 3 的紧急购电上界是逐 10 分钟预报缺口（还需扣掉 κ*），不是 u 的预测值。
- assumption_v001 的 I1 引用小时级预报缺口（如 2025-06-21 为 3 618.4 kWh），与本实现的逐 10 分钟正部合计（3 812.266 kWh）必然不等；交付与表 3 一律以逐 10 分钟判定为准，勿混用两套数。
- 附件 5「紧急购电量」模板每天只预留 3 行示例；本实现按实际段数增删行、日期列只在首段出现、u=0 的日期显式登记为一行（时间段「无」、购电量 0）；sanity 应按本映射核验分段合计等于逐时段 u 之和（容差 1e-6）。
- 本阶段未实测竞赛实例的单日 MILP 耗时：若显著慢于 prob01 同类 144 时段问题，1500 s 软总预算会触发剩余日期的短时限求解并可能产生 status=1 的日期；这属可接受技术债（PASS_WITH_WARNING），但必须在 computation 报告中如实体现，不得事后调整预注册判据或阈值。
- 环境约束仍在：可用内存约 1 GB、effective_workers=1；334 个逐日 MILP 规模小，但若 worker 或 HiGHS 被内存压力回收/异常退出，按 infrastructure_transient / code_runtime 路由新 attempt 与新输出目录，不得直接人工阻塞。
- task identity 绑定 code_hash/config_hash/input_hash/假设与公式版本/backend：本动作之后任何代码、配置、时限或 gap 改动都会产生新 task_id；重跑必须使用新的 output_directory，禁止覆盖预测 task_id ea71568e2cf6c5326ded 的结果，也不得把 smoke 探针输出当作竞赛实例结果。
- 可用内存仅约 1.37 GB（总 15.74 GB），effective_workers 被压到 1：本轮 334 天逐日 MILP+LP 单任务可以启动，但若 worker 或 HiGHS 因内存压力被回收/异常退出，应按 infrastructure_transient 或 code_runtime 路由新 attempt（新输出目录）重试，不得直接人工阻塞。
- task_id=ea71568e2cf6c5326ded 的身份字段（code_hash/config_hash/input_hash/假设与公式版本/backend/timeout）已核验未变；本动作之后若需调整代码、配置、时限、总预算或 gap，必须产生新 task_id 并使用新 output_directory，禁止覆盖本 attempt 结果。
- 本动作未产出任何计算结果：I1（逐日紧急购电量与表 3 四日结果）、I2（逐日 solver status/best_bound/mip_gap）、I4（κ_act 总量与时段）与 M1 vs M2 目标差仍待该 task 终态；交付的 C_t/D_t 只能取自 M1（milp）解，M2 真 LP 松弛仅作下界与退化诊断。
- 口径张力随上游移交：本 task 按 asm-02 以附件 3 的 0:00 预报为计划信息集；若终态后改用附件 2 实际值（alt-01）则 u≡0。该口径不得在结果出现后替换，论文边界章节与交付说明须显式声明并给出 alt-01 对照。
- 运行时间风险：本阶段未实测竞赛实例的单日 MILP 耗时；若显著慢于 prob01 同类 144 时段问题，1500 s 软总预算会触发剩余日期的短时限求解并可能产生 status=1（可行非最优）的日期。这属可接受技术债（PASS_WITH_WARNING），必须由 sanity 在结果报告中如实体现，不得事后调整预注册判据或阈值。
- runtime/tmp/prob02_task_spec_probe.py、runtime/tmp/prob02_task_spec_probe.json 与 runtime/tmp/prob02_resource_probe.json 只是资源/身份探针与可重建临时物，不构成正式产物链；smoke 探针输出 runtime/tmp/prob02_smoke/ 同理，不得当作竞赛实例结果。
- prob02 level_1_4: L1-L4 硬门禁全部通过：task ea71568e2cf6c5326ded 终态 succeeded(rc=0)、8 个交付产物非空且 code/input/source_config/config hash 与 run_manifest 裸 sha256 独立重算一致（data/ 4 个附件与 request/attachments/ 逐字节相同）；从 solution.csv 独立回代 (C1)(C2)(R)(C3)~(C8) 得计划层平衡 5.00e-07、执行层平衡 5.33e-07、SOC 1.00e-05、终端 0.0、储电量/功率越界 0.0、互斥 1.85e-11、执行层互补 0.0、κ 上界越界 0.0、非负 −2.11e-10、整性 0.0、NaN/Inf 0（内存精度残差 ≤1.4e-10）；334/334 status=0、max mip_gap=2.01e-16、best_bound=objective 证实 I2，弃光 961 173.6810/2 355 847.6824 kWh 证实 I4；Cost_plan=12 570 533.9138 元落在解析界 [6 749 147.6122, 16 565 407.2763] 内、Cost_em=4 828 772.4163≤5 815 010.6013、Cost_total=17 399 306.3301≥6 660 821.0595、Q_plan=20 385 219.0362≥18 177 074.097，两条能量恒等式闭合；式 (E) 展开、电价/负载/光伏与附件 1/2/3 逐位一致，量纲与 big-M=Pbar 由 (C5) 导出自洽，result2.xlsx 三表按 asm-15/asm-17 正确映射且与 solution 一致；18 个引用 ID 均 verified+used、关键假设门禁 passed；u>0 的 10 877 时段全部满足 pv<pvfc。判定 PASS_WITH_WARNING 仅因 8 项非阻断技术债：W1 formulation §3.7 (D-ex) 符号笔误（实现正确、须在论文前修正）、W2 asm-02 口径张力需边界声明与 alt-01 对照、W3 计划口径 vs Cost_total 须双报、W4 asm-06/09 待 robustness 端点与效率对照、W5 asm-08/14 边界声明、W6 asm-15 标签映射登记、W7 零弃光预期修正、W8 surplus 负值读数说明。无失败类型、无需回退。
- W1（文档，须修正）：formulation.md §3.7 式 (D-ex) 与首条全局恒等式的 (pv−pvfc)dt 项符号写反（文档式 +，正确式 −）；实测 Σu−Σκ_act=−1 199 058.283 与正确式一致、与文档式（−723 289.079）不符；实现 (R) 与全部交付数值正确，属文档笔误。建议在 formulation_v002 或交付勘误中修正，论文定稿前不得把 (D-ex) 原样引用；若修正公式版本会改变 task 身份字段并产生新 task_id，本结果无需重跑。
- W2（口径张力，最高优先）：题面问题 2 的数据清单只列附件 1 电价与附件 2 数据，本模型按 asm-02 把附件 3 的 0:00 预报纳入计划信息集；若改用附件 2 实际值（alt-01）则 u≡0、紧急购电机制退化为空。论文边界章节与交付说明必须显式声明本口径并给出 alt-01 对照，不得在结果出现后改口径。
- W3（口径歧义 A-D1）：result2.xlsx 与论文表 1 的「全天购电量/全天购电费」取计划口径（Q_plan_d/Cost_plan_d，与 asm-04 门禁一致）；交付阶段必须登记该映射并单独给出含紧急购电费的 Cost_total=17 399 306.3301 元，不得只给一个数。
- W4（assumption 待 robustness 对照）：asm-06（E₀=E₁₄₄=6000 日循环）、asm-09（单向 90%、并网点侧计、833.33 kWh）均为 project_assumption，缺少同设备实测来源；robustness 必须完成 E^cyc∈{4800,6000,7200}、往返 0.9（单侧 0.9487）与电池侧计量口径的对照并报告 Cost 变化方向与幅度。
- W5（边界声明）：asm-08（不反送、无上网电价）、asm-14（不建模电池退化，会高估套利、使 Cost 偏低）须在论文边界章节声明；asm-02/06/09 的口径选择亦须一并登记。
- W6（交付映射）：asm-15 的时间标签重写（物理区间）与附件 5 模板字面标签存在整体一个时段偏移（有意统一）；交付阶段必须在 result2.xlsx 与论文中同步登记映射关系，不得静默改变，也不得按模板标签逐行对齐。
- W7（预期修正）：交付窗口「零弃光」的预期不成立——计划弃光 961 173.6810 kWh（2 306 时段）、实际弃光 2 355 847.6824 kWh（16 440 时段），远大于探针登记的不可避免部分（272/241 时段）；论文须如实报告并按段给出发生时段与原因（日循环 (C4) 与单时段功率上限导致的强制弃光）。
- W8（读数说明）：solution.csv 的最小值 −440.83 来自派生量 surplus_kwh（执行层净盈余 s 可为负），不是任何物理量负值；交付与绘图不得把 surplus 当作弃光或购电量使用。
- W1（文档，须修正）：formulation.md §3.7 式 (D-ex) 与首条全局恒等式的 (pv−pvfc)dt 项符号写反（文档式 +，正确式 −）；实测 Σu−Σκ_act=−1 199 058.283 与正确式一致、与文档式（−723 289.079）不符；实现 (R) 与全部交付数值正确。建议在 formulation_v002 或交付勘误中修正，论文定稿前不得把 (D-ex) 原样引用。
- sanity_check 阶段确认：computation 阶段登记的 W2–W8 仍为非阻断技术债并随结论移交——W2 asm-02 预报口径须在论文边界声明并给 alt-01（u≡0）对照；W3 计划口径 Q_plan/Cost_plan 与 Cost_total 须双报；W4 asm-06（E^cyc∈{4800,6000,7200}）与 asm-09（单向 90%/电池侧计量）待 robustness 对照；W5 asm-08/asm-14 边界声明；W6 asm-15 标签映射登记；W7 弃光非零须按段报告；W8 surplus 负值读数说明。本阶段复核无新增技术债。
- 本环境最终响应模型不支持图像输入（read_image 明确返回「模型不支持图像输入」），视觉复核由可复现的程序化审计完成（CJK 字形覆盖、文本裁切、两两重叠、标签/图例完整性、色板区分度、三维视角与二维配套），不能替代对图意误导性的像素级人工判断；建议论文定稿团队在有图像能力的终端对 10 张 PNG 补一次目检，本阶段结论不因此降级。
- W2 口径张力随图移交：图中紧急购电完全源自 0:00 预报误差（u>0 时段全部满足 pv<pvfc），若改用附件 2 实际值（alt-01）则 u≡0；论文边界章节与交付说明必须显式声明并给出 alt-01 对照，不得在结果出现后改口径。
- W3 口径歧义：图中「全天购电量/全天购电费」取计划口径（Q_plan/Cost_plan），含紧急购电费的 Cost_total=17 399 306.33 元已单独给出；交付阶段必须登记该映射并双报，不得只给一个数。
- W4 假设待对照：asm-06（E^cyc∈{4800,6000,7200} 日循环两端 6000 kWh）与 asm-09（单向 90%、并网点侧计量、833.33 kWh/10min）仍为 project_assumption，本阶段未做任何数值结论，必须由 robustness 给出 Cost 变化方向与幅度。
- W5/W6/W7/W8 随图移交：asm-08（不反送、无上网电价）与 asm-14（不建模电池退化）须在论文边界章节声明；asm-15 时间标签映射（与附件 5 模板整体相差一个时段且模板含 7:0-7:10 笔误）须在 result2.xlsx 与论文同步登记；弃光须按段报告时段与原因；surplus 负值为派生量读数说明。
- W1 文档债：formulation.md §3.7 式 (D-ex) 的 (pv−pvfc)dt 项符号笔误须在论文定稿前修正或勘误，本实现与全部交付数值正确；本阶段不修改公式版本，避免改变 task 身份字段。
- 三维曲面的峰值按小时聚合、二维热力图峰值按逐 10 分钟，两者日期不同（2025-09-30 小时合计 vs 2025-05-26 逐时段），caption 已分别标注；引用时不得混用两种口径。
- 本阶段未运行任何优化或重算、未修改原始数据与上游产物；新增文件仅限 figures 目录的脚本、10 张 PNG、10 个质量报告、visual_review.json 与 visual_review_report.md，以及 figures.yaml 的图表登记。robustness 若重跑或改代码须使用新 task_id 与新输出目录，禁止覆盖 ea71568e2cf6c5326ded 的结果。

## 阻塞项

- 无

## 下次唤醒

2026-09-10T14:07:24.825057+00:00
