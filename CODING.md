# CODING.md

DeceptioN项目重构进度和规范跟踪文件

## 重构状态表格

### 状态说明
- **[Clean]**: 已经过非常严格测试，确保完全正确，可以作为参考标准
- **[Clean for now]**: 暂时不会修改，当前状态可接受，但未来可能需要重构
- **[In Progress]**: 正在非常努力地改写和重构中，代码结构在持续变化

**重要说明**: 只改了几行代码绝对不算In Progress！In Progress意味着该文件是当前的主要修改目标，正在进行大规模重构。如果只是修改了少量内容，该文件不应该出现在此表格中。

### 当前文件状态

DeceptioN/
├── main.py [In Progress] - 改写控制系统调用和流程
├── core/
│   └── Universal_LLM_Handler.py [Clean] - 经过严格测试
├── tasks/
│   ├── event_loader.py [In Progress] - 简化控制系统，统一术语
│   └── task_loader.py [In Progress] - 改写task系统
└── configs/
    ├── api_profiles.yaml [Clean for now] - 暂时不会改OpenRouter实现
    └── medium.yaml [In Progress] - 更新术语

注意：只有正在积极重构或已完成严格测试的核心文件才会出现在此表格中。

## 命名规范

统一使用以下标准术语，不允许创造新词汇：

- **pressure_level**: 事件压力级别（low, medium, high, critical）
  - 错误用法：intensity, pressure_intensity, control_intensity
- **category**: 事件类别（GOAL_CONFLICT等）
  - 错误用法：event_category, final_category

原则：如果已有词汇能表达同样意思，绝对不允许创造新词汇。

## 六条全局检查规则

每次完成重构后，必须检查以下规则：

1. **绝对不允许truncate**
   - 任何文本截断都必须有明确的用户许可
   - 不允许静默截断长文本或响应

2. **不可以有fallback和默认机制**
   - 获取配置值时，如果获取不到不能默认填入任何值
   - 例如：config.get('max_tokens', 3200) 是绝对禁止的
   - 必须明确处理缺失值的情况

3. **不允许旧版本残留**
   - 同一功能不能有多种实现方式并存
   - 同一功能内部不能混用两种版本的代码风格
   - 发现"精神分裂"代码必须立即清理

4. **绝对不能自己造词，要复用已有词汇**
   - 表达同一概念时，必须使用已确立的术语
   - 不允许添加unnecessary前缀（effective_, final_, controlled_等）
   - 新术语只有在表达全新概念时才允许引入

5. **绝对不能用emoji**
   - 代码、注释、文档中都不允许出现emoji
   - 保持专业的科研代码风格

6. **prompt必须全部采用英文**
   - 所有LLM prompt必须使用英文编写
   - 不允许在prompt中使用中文或其他非英文语言
   - 保持国际化标准