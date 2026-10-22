---
name: card-product-workflow
description: "Plan, build, debug, verify, and document digital business-card products, from reference-product research to role-based sharing, visitor inquiries, media review, and release evidence. Use for this product workflow or a closely related iteration; not for copying a commercial product's code or branding."
---

# 数字名片产品全流程

把宽泛产品目标转为可验证的业务闭环，并让实现、证据与使用说明保持一致。可从研究、开发、修复或交付中的任意阶段进入，不要求重复已完成的工作。

## 先建立当前事实

确认目标用户、目标平台、角色、现有代码、当前版本和本次授权范围。区分早期原型、当前产品与未来计划；仓库中存在某个模块不代表它仍在当前产品中提供。

若用户只给参考产品或截图，先分析可观察的能力和使用场景，形成独立设计。不要直接复制对方代码、品牌、人物或受限素材。

将需求写入 [需求与角色模板](assets/templates/requirements-and-roles.md)：每项包含使用者、触发动作、期望结果、失败恢复、证据和状态。先解决关键缺失信息；不因常规实现选择反复要求用户确认。

## 按问题选择参考资料

- 产品研究、范围收敛、时间盒：[discovery-and-scope.md](references/discovery-and-scope.md)。
- 员工／管理员／所有者和访客边界：[roles-and-data.md](references/roles-and-data.md)。
- 多方案、字体、长字段、原生输入：[ui-and-readability.md](references/ui-and-readability.md)。
- 分享、独立入口、头像审核和媒体状态：[sharing-and-media.md](references/sharing-and-media.md)。
- 旧咨询兼容、编辑草稿、缓存与迟到响应：[compatibility-and-drafts.md](references/compatibility-and-drafts.md)。
- 冻结产物、验证范围、上传回执：[verification-and-release.md](references/verification-and-release.md)。
- 有相似故障时再读：[lessons-learned.md](references/lessons-learned.md)。

## 实现与修复的关键约束

1. 画出会影响归属或副作用的状态转换，再修改代码。上传、审核、公开可见、分享请求成功、实际收件是不同状态。
2. 访客与再次转发始终保留原持卡人。服务端决定权限和公开字段；缓存不能代替链接有效性或审核检查。
3. 对发送结果未知的操作，先核对回执与实际结果，不自动重复发送。恢复旧任务前查询同一任务，不凭超时创建第二次副作用。
4. 新增结构化字段时保留旧自由文本。只为已可靠识别的字段提供拨号等专用操作，不猜测旧字符串的含义。
5. 输入、媒体和界面状态按目标运行时验证。浏览器通过不能证明原生组件通过；模拟器通过不能证明手机或实际收件通过。
6. 保持现有功能与身份边界，使用与修改风险相称的测试。不要用测试总数替代本次问题的复现与针对性检查。

## 证据与交付

使用 [证据矩阵](assets/templates/evidence-matrix.md)，将每项结果绑定到版本、不可变产物标识、入口、环境、场景与时间。明确列出未测、失败、待确认；后续版本不能自动继承旧版本的验收结论。

可运行 `python scripts/check_evidence.py <evidence.json>` 检查矩阵是否自洽。它检查记录的范围与一致性，**不能证明记录真实发生**；演示数据不能生成真实发布就绪结论。

使用 [交付回执](assets/templates/release-receipt.md) 分别记录构建、上传、体验入口、审核与正式发布。只有本次已授权的外部动作才能执行；其他项目中的持续上传偏好不自动适用于新项目。

按照 [角色手册模板](assets/templates/role-guide-outline.md) 更新使用说明。以身份分册，在相关动作旁说明设备差异，每册均保留完整访客流程。截图注明真实来源版本与渲染环境，不冒称新版真机截图。

## 公开作品集

另建干净发布目录，只提炼方法与重新撰写的匿名案例。公司代码、原始截图、内部文档、会话、云端标识和原 Git 历史不直接进入公开包。公开素材使用从零生成的通用图与虚构数据；内部浅模糊截图不作为公开去敏感信息的保证。

参照 [公开边界说明](references/publication-and-privacy.md) 复核归属与泄露面。发布前列明将上传的文件、仓库位置和可见范围；使用现有明确授权，不绕过平台本人认证。
